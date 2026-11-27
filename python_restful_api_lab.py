"""Local-only FastAPI lab; synthetic inventory, no OT writes."""
import re
from http import HTTPStatus
from threading import Lock
from typing import Annotated

from fastapi import FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, StringConstraints
from starlette.exceptions import HTTPException

ID = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9-]{0,31}$")]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Tag = re.compile(r'"[0-9]+"')


class DeviceWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: Name
    enabled: bool


class DeviceCreate(DeviceWrite):
    id: ID


class Device(DeviceCreate):
    revision: int


class Page(BaseModel):
    items: list[Device]
    next_after: str | None


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str


def problems(*codes):
    return {code: {"description": HTTPStatus(code).phrase,
                   "content": {"application/problem+json": {"schema": Problem.model_json_schema()}}}
            for code in codes}


def problem(status: int, detail: str, headers=None):
    body = Problem(title=HTTPStatus(status).phrase, status=status,
                   detail=detail)
    return JSONResponse(body.model_dump(), status_code=status, headers=headers,
                        media_type="application/problem+json")


def create_app() -> FastAPI:
    app = FastAPI(title="Synthetic facility device registry", version="1.0")
    data: dict[str, Device] = {}
    lock = Lock()

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return problem(exc.status_code, exc.detail, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return problem(422, "Request does not match the contract. See OpenAPI.")

    @app.get("/v1/devices", response_model=Page, responses=problems(422))
    def list_devices(after: Annotated[ID | None, Query()] = None,
                     limit: Annotated[int, Query(ge=1, le=50)] = 10):
        with lock:
            ids = sorted(key for key in data if after is None or key > after)
            items = [data[key] for key in ids[:limit]]
            return Page(items=items, next_after=ids[limit - 1] if len(ids) > limit else None)

    @app.post("/v1/devices", status_code=201, response_model=Device, responses={
        201: {"description": "Created", "headers": {"Location": {"schema": {"type": "string"}}}},
        **problems(409, 422),
    })
    def create_device(body: DeviceCreate, response: Response):
        with lock:
            if body.id in data:
                raise HTTPException(409, "Device ID already exists.")
            item = data[body.id] = Device(**body.model_dump(), revision=1)
        response.headers["Location"] = f"/v1/devices/{item.id}"
        return item

    @app.get("/v1/devices/{device_id}", response_model=Device, responses={
        200: {"description": "Current device", "headers": {"ETag": {"schema": {"type": "string"}}}},
        **problems(404, 422),
    })
    def get_device(device_id: ID, response: Response):
        with lock:
            item = data.get(device_id)
        if item is None:
            raise HTTPException(404, "Device not found.")
        response.headers["ETag"] = f'"{item.revision}"'
        response.headers["Cache-Control"] = "no-store"
        return item

    @app.put("/v1/devices/{device_id}", response_model=Device,
             responses=problems(400, 404, 412, 422, 428),
             openapi_extra={"parameters": [{
                 "name": "If-Match",
                 "in": "header",
                 "required": True,
                 "schema": {"type": "string"},
                 "description": "Send exactly one field line with the strong ETag from GET.",
                 "example": '"1"',
             }]})
    def replace_device(device_id: ID, body: DeviceWrite, request: Request):
        # OpenAPI describes the accepted value; raw access detects repeated lines
        # and lets us return 428, not FastAPI's request-validation 422, if absent.
        if_match = request.headers.getlist("if-match")
        if not if_match:
            raise HTTPException(428, "Read the current ETag and supply If-Match.",
                                headers={"Cache-Control": "no-store"})
        if len(if_match) != 1 or not Tag.fullmatch(if_match[0].strip()):
            raise HTTPException(400, 'Supply exactly one If-Match field with a strong tag such as "1".')
        tag = if_match[0].strip()
        with lock:  # Keep the version test and assignment in one critical section.
            current = data.get(device_id)
            if current is None:
                raise HTTPException(404, "Device not found.")
            if tag != f'"{current.revision}"':
                raise HTTPException(412, "Version changed. Read and reconcile before retrying.")
            # A no-op replacement need not create a new revision.
            if body.name == current.name and body.enabled == current.enabled:
                return current
            item = Device(id=device_id, **body.model_dump(), revision=current.revision + 1)
            data[device_id] = item
        # Do not emit ETag on PUT: the server transforms the request representation.
        return item

    return app


app = create_app()

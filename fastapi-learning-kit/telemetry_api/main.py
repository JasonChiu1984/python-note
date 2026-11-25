"""Synthetic local telemetry API. No live devices or production security."""
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from threading import Lock
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class ReadingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device: str = Field(pattern=r"^[A-Z][A-Z0-9_-]{1,31}$")
    temperature_c: float = Field(ge=-100, le=200, strict=True)
    observed_at: AwareDatetime


class ReadingOut(ReadingIn):
    id: UUID


class ReadingPage(BaseModel):
    items: list[ReadingOut]
    offset: int
    limit: int


class ReadingRepository:
    def __init__(self):
        self.lock = Lock()
        self.rows: dict[UUID, dict] = {}

    def create(self, payload: ReadingIn) -> dict:
        key = uuid4()
        row = payload.model_dump()
        row["observed_at"] = payload.observed_at.astimezone(UTC)
        row.update(id=key, stored_at=datetime.now(UTC))
        with self.lock:
            if len(self.rows) >= 1000:
                raise HTTPException(status_code=503, detail="demo storage is full")
            self.rows[key] = row
        return row.copy()

    def get(self, key: UUID) -> dict | None:
        with self.lock:
            row = self.rows.get(key)
            return row.copy() if row else None

    def list(self, offset: int, limit: int, device: str | None) -> list[dict]:
        with self.lock:
            rows = [row for row in self.rows.values() if not device or row["device"] == device]
            return [row.copy() for row in rows[offset:offset + limit]]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.repository = ReadingRepository()
    try:
        yield
    finally:
        del app.state.repository


def get_repo(request: Request) -> ReadingRepository:
    return request.app.state.repository


Repo = Annotated[ReadingRepository, Depends(get_repo)]
router = APIRouter(prefix="/v1/readings", tags=["readings"])


@router.get("", response_model=ReadingPage)
def list_readings(
    repo: Repo,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    device: Annotated[str | None, Query(pattern=r"^[A-Z][A-Z0-9_-]{1,31}$")] = None,
):
    # Convert each record to its public contract before returning nested data.
    items = [ReadingOut.model_validate({key: row[key] for key in ReadingOut.model_fields})
             for row in repo.list(offset, limit, device)]
    return ReadingPage(items=items, offset=offset, limit=limit)


def public_row(row: dict) -> dict:
    # Internal fields, e.g. stored_at, must not enter an API response.
    return {key: row[key] for key in ReadingOut.model_fields}


@router.get("/{reading_id}", response_model=ReadingOut, name="get_reading",
            responses={404: {"description": "Unknown reading"}})
def get_reading(reading_id: UUID, repo: Repo):
    row = repo.get(reading_id)
    if row is None:
        raise HTTPException(status_code=404, detail="reading not found")
    return public_row(row)


@router.post("", status_code=201, response_model=ReadingOut,
             responses={503: {"description": "Lab capacity reached"}})
def create_reading(payload: ReadingIn, repo: Repo, response: Response, request: Request):
    row = repo.create(payload)
    response.headers["Location"] = str(request.url_for("get_reading", reading_id=row["id"]).path)
    return public_row(row)


app = FastAPI(title="Synthetic HVAC Telemetry", version="1.0.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health/live")
def live() -> dict[str, Literal["live"]]:
    return {"status": "live"}


@app.get("/health/ready")
def readiness(repo: Repo) -> dict[str, Literal["ready"]]:
    # Memory lab only: dependency resolves a live repository.
    return {"status": "ready"}

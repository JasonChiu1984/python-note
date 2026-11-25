FROM python:3.12-slim
WORKDIR /work
COPY dist/*.whl /tmp/wheels/
RUN python -m pip install --no-cache-dir /tmp/wheels/*.whl \
    && rm -r /tmp/wheels \
    && useradd --create-home --uid 10001 appuser
USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "telemetry_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

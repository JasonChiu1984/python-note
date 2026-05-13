FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    APP_NAME=deployment-runtime-service \
    APP_PORT=8080 \
    APP_ENV=container

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser

COPY pyproject.toml README.md ./
COPY src ./src

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD python -m deployment_runtime_service.healthcheck

CMD ["python", "-m", "deployment_runtime_service.server"]

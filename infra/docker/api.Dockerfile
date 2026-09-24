FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/workspace/apps/api

WORKDIR /workspace

RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid 10001 --create-home appuser

COPY pyproject.toml ./
COPY apps/api apps/api

RUN pip install --upgrade pip \
    && pip install -e ".[dev]" \
    && chown -R appuser:appgroup /workspace

USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

COPY alembic.ini ./
COPY migrations migrations

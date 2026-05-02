FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends git curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# pyproject.toml references ../LICENSE relative to itself, so place it at /LICENSE.
COPY LICENSE /LICENSE

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/README.md ./README.md
COPY backend/src ./src

RUN pip install --upgrade pip \
 && pip install -e .

COPY backend/tests ./tests
COPY examples /examples

EXPOSE 8080

CMD ["uvicorn", "nexusdocs.api.app:default_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]

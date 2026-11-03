FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
COPY src ./src
RUN pip install --upgrade pip && pip install -e ".[dev]"
COPY . .
ENV PYTHONPATH=/app/src
EXPOSE 8000

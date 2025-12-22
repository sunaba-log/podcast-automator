# Base image used for preparing dependencies and for the final image
FROM python:3.12-slim as baseimage
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --upgrade pip uv
WORKDIR /app


# Prepare dependencies in separate builder to allow efficient docker caching
FROM baseimage as builder
ENV UV_CACHE_DIR=/tmp/docker_builder/uv_cache
COPY app/pyproject.toml app/uv.lock ./
RUN --mount=type=cache,target=$UV_CACHE_DIR uv sync --frozen


# Finally, build the application docker image using the base image and dependencies from the previous steps
FROM baseimage
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY --from=builder /app/.venv /app/.venv
COPY app/src ./src
ENV PYTHONPATH=/app/src
CMD [ "python", "-m", "main" ]

FROM python:3.12-alpine

COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /uvx /bin/
COPY . /app

WORKDIR /app

ENV UV_NO_DEV=1
RUN uv sync --locked

ENTRYPOINT [ "uv", "run", "-m", "dev_assistant" ]

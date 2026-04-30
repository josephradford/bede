FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml .
RUN uv sync --no-dev --no-install-project

COPY src/ src/

RUN uv sync --no-dev

RUN useradd --create-home --uid 1000 bede
USER bede

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import socket; s=socket.create_connection(('localhost', 8002), timeout=5); s.close()" || exit 1

CMD [".venv/bin/python", "-m", "bede_data_mcp"]

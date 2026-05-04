FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project

RUN useradd --create-home --uid 1000 bede
USER bede

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import socket; s=socket.create_connection(('localhost', 8003), timeout=5); s.close()" || exit 1

CMD [".venv/bin/workspace-mcp", "--transport", "streamable-http"]

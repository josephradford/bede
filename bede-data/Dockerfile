FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml .
RUN uv sync --no-dev --no-install-project

COPY src/ src/

RUN uv sync --no-dev

RUN useradd --create-home --uid 1000 bede
USER bede

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

CMD [".venv/bin/uvicorn", "bede_data.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8001"]

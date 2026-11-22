FROM ghcr.io/astral-sh/uv:0.11.10-python3.13-trixie-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --uid 1000 --shell /bin/bash bede && \
    mkdir -p /home/bede/.ssh && \
    chmod 700 /home/bede/.ssh && \
    chown -R bede:bede /home/bede/.ssh

WORKDIR /app

COPY pyproject.toml .
RUN uv sync --no-dev --no-install-project

COPY src/ src/
COPY scripts/ scripts/
COPY mcp.json .

RUN uv sync --no-dev && \
    chmod +x scripts/entrypoint.sh && \
    chown -R bede:bede /app

USER bede

EXPOSE 8080

ENTRYPOINT ["scripts/entrypoint.sh"]

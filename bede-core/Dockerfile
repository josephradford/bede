FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI
RUN curl -fsSL https://claude.ai/install.sh | bash && \
    cp /root/.local/bin/claude /usr/local/bin/claude

# Create non-root user
RUN useradd --create-home --uid 1000 --shell /bin/bash bede && \
    mkdir -p /home/bede/.ssh /home/bede/.claude && \
    chmod 700 /home/bede/.ssh && \
    chown -R bede:bede /home/bede/.ssh /home/bede/.claude

WORKDIR /app

COPY pyproject.toml .
RUN uv sync --no-dev --no-install-project

COPY src/ src/
COPY scripts/ scripts/

RUN uv sync --no-dev && \
    chmod +x scripts/entrypoint.sh && \
    chown -R bede:bede /app

USER bede

EXPOSE 8080

ENTRYPOINT ["scripts/entrypoint.sh"]

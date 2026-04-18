FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates openssh-client supervisor \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://claude.ai/install.sh | bash && \
    cp /root/.local/bin/claude /usr/local/bin/claude

RUN useradd --system --create-home --uid 1000 --shell /bin/bash bede && \
    mkdir -p /home/bede/.ssh /home/bede/.claude && \
    chmod 700 /home/bede/.ssh && \
    chown -R bede:bede /home/bede/.ssh /home/bede/.claude

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
RUN chmod +x scripts/entrypoint.sh scripts/briefing.sh \
    && chown -R bede:bede /app

USER bede

EXPOSE 8001 8002 8003

ENTRYPOINT ["scripts/entrypoint.sh"]

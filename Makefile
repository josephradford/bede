IMAGE := ghcr.io/josephradford/bede
TAG := latest

.PHONY: build push test test-ingest test-mcp

build:
	docker build -t $(IMAGE):$(TAG) .

push: build
	docker push $(IMAGE):$(TAG)

test:
	cd data-ingest && uv run pytest tests/ -v
	cd data-mcp && uv run pytest tests/ -v

test-ingest:
	cd data-ingest && uv run pytest tests/ -v

test-mcp:
	cd data-mcp && uv run pytest tests/ -v

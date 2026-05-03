.PHONY: test test-core test-data test-data-mcp

test:
	cd bede-core && uv run pytest tests/ -v
	cd bede-data && uv run pytest tests/ -v
	cd bede-data-mcp && uv run pytest tests/ -v

test-core:
	cd bede-core && uv run pytest tests/ -v

test-data:
	cd bede-data && uv run pytest tests/ -v

test-data-mcp:
	cd bede-data-mcp && uv run pytest tests/ -v

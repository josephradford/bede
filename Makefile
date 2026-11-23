.PHONY: test test-core test-data test-data-mcp test-workspace-mcp test-web bede-eval

test:
	cd bede-core && uv run pytest tests/ -v
	cd bede-data && uv run pytest tests/ -v
	cd bede-data-mcp && uv run pytest tests/ -v

test-core:
	cd bede-core && uv run pytest tests/ -v

bede-eval:
	cd bede-core && uv run python evals/run_evals.py $(ARGS)

test-data:
	cd bede-data && uv run pytest tests/ -v

test-data-mcp:
	cd bede-data-mcp && uv run pytest tests/ -v

test-workspace-mcp:
	@echo "No tests — bede-workspace-mcp wraps a third-party package with no custom code"

test-web:
	cd bede-web && npm run build

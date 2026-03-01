---
paths:
  - "tests/**"
  - "src/**"
---

# Testing Conventions

## Running tests

```bash
uv run pytest tests/ -x          # Stop on first failure
uv run pytest tests/ -x -q       # Quiet output
uv run pytest tests/unit/ -x     # Unit tests only
```

## Test structure

- `tests/unit/` — unit tests (mock-based, fast)
- `tests/e2e/` — end-to-end tests (require `--dc-e2e` flag and real credentials)
- `tests/fixtures/` — shared mock data

## Conventions

- Tests mirror source structure: `src/mcp_atlassian/jira/issues.py` -> `tests/unit/jira/test_issues.py`
- Use `MagicMock` / `AsyncMock` from `tests/utils/mocks.py` for shared fixtures
- Fork-specific tests (hierarchy, page width) are in `tests/unit/confluence/test_pages.py`
- When adding tools, update the tool count assertion in `tests/unit/utils/test_toolsets.py`

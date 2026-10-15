---
name: testing
description: Test structure, style, fixtures, and coverage guidelines
version: 1.0
# Test layout: only when tests are in play.
paths:
  - "tests/**"
  - "src/genetic_opt/**"
  - "crates/genetic_opt/**"
---

# Testing Guidelines

## Test Structure

Tests are split by **level** into sibling folders under `tests/`,
per the global `testing-python.md` rule:

| Suite | Location | Runs with | Purpose |
|-------|----------|-----------|---------|
| Unit | `tests/unit/` | `uv run pytest tests/unit` | Fast, isolated, no real data |
| Integration | `tests/integration/` | `uv run pytest tests/integration` | Real collaborators, fixtures, servers, DBs |

The shared `tests/conftest.py` stays at the `tests/` root so its
fixtures apply to both levels. Module grouping is kept *within* each
level (`tests/unit/db/`, `tests/unit/api/`).

**Unit tests** live under `tests/unit/`, use fixtures and temporary
paths (`tmp_path`), and never depend on external services or real
data files.

**Integration tests** live under `tests/integration/` and wire real
collaborators together. When one depends on an **external resource not
always present** (a real DB path, service URL, or data vault), gate it
behind an env var and let its fixture **skip gracefully** when unset,
and mark the suite `pytestmark = pytest.mark.integration` — so the
default `pytest tests/` run stays green everywhere. See the global
`testing-python.md` rule for the full pattern.

## Style

- **No test classes.** Use plain functions with `test_` prefix.
- Group tests by module, separated by comment headers:
  ```python
  # ── Module Name Tests ──────────────────────────────────────
  ```
- Use `pytest` idioms: fixtures, parametrize, `pytest.raises`.
- Keep test files named `test_<module>.py` mirroring the source.

## Fixtures

- Define fixtures in the test file when used by that file only.
- Move shared fixtures to `tests/conftest.py` when used across
  files.
- Prefer `tmp_path` (built-in) for temporary files/databases.
- Use `@pytest.fixture` without parentheses for consistency.
- For SQLite-backed fixtures, use the session-scoped template
  pattern — see the shared `testing-python` rule.

## Assertions

- One logical assertion per test when possible.
- Use plain `assert` — avoid `unittest`-style methods.
- For float comparisons: `assert abs(actual - expected) < 1e-9`.

## Naming

- Test functions: `test_<what>_<scenario>` in snake_case.
- Fixture functions: descriptive nouns (`sample_project`,
  `mock_registry`).

## What to Test

- **Do test:** public functions, edge cases, error paths, data
  roundtrips, serialization schemas.
- **Don't test:** private helpers directly (test through public
  API), trivial getters/setters.

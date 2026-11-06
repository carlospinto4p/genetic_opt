# CLAUDE.md — genetic_opt

## Code Style

- Line length: 78 characters (enforced by ruff)
- Type hints required
- Docstring style: Sphinx/reST (`:param:`, `:return:`, `:raises:`)
- In docstrings, prefer single backticks (`` `name` ``) for inline code references

## Common Commands

**IMPORTANT**: Always use `uv run` to execute Python commands. Never run raw `python` commands.

```bash
# Install dependencies
uv sync --all-extras

# Run unit tests (`-n 4`: four worker processes; more start slower)
uv run pytest tests/unit -n 4

# Run the integration tests (they build and run the Rust crate)
uv run pytest tests/integration -v

# Run linter
uv run ruff check src/ tests/

# Run linter with auto-fix
uv run ruff check src/ tests/ --fix

# Rust crate: tests, formatting, linter
cargo test --manifest-path crates/genetic_opt/Cargo.toml
cargo fmt --manifest-path crates/genetic_opt/Cargo.toml --check
cargo clippy --manifest-path crates/genetic_opt/Cargo.toml --all-targets -- -D warnings
```

```bash
# Explainer: API on 5209, front-end on 5208 (`frontend/`)
uv run python -m genetic_opt.web.app
corepack pnpm --dir frontend dev
corepack pnpm --dir frontend run check
corepack pnpm --dir frontend test
corepack pnpm --dir frontend run build
```

## Core Rules

1. **Self-Improvement**: When the user corrects a mistake, ALWAYS update the relevant guidelines (`.claude/rules/` or this file) to prevent it from happening again.

2. **Keep CLAUDE.md Minimal**: Do not include library schemas, architecture details, or information discoverable from the codebase. Keep only essential rules and commands here.

3. **Periodic Reviews**: Triggered by backlog depth — when `/backlog` shows fewer than 5 open items, propose `/scan`, `/improvements`, and `/prune` together.

## Project Configuration

Store project rules and preferences in project config files (e.g., `.claude/settings.json`, `CLAUDE.md`), NOT in memory files. Never save user instructions as memory files.

## Project Overview

A genetic algorithm library with two implementations side by side:
the Python package `src/genetic_opt` and the Rust crate
`crates/genetic_opt`. The Python package does not use the crate. A run
saved by either one has the same layout on disk, and
`runs.fit_result_io.load_fit_result` reads both.

## Changes that break `downstream`

`downstream`, a separate project, uses this package.
When a change here breaks its code, file an item in its `backlog.md`
in the same task, with the lines that break and what to write in their
place, then commit and push it there. Saying so in the reply is not
enough. Set 13th October 2026 at the user's instruction.

## Shell Commands

Never use compound shell commands with `cd && git` or `cd &&` chaining. Always use separate commands or `cd` first, then run the git/shell command independently.

## Testing

After any code change, run the full test suite and fix all failures before committing. Pay special attention to mock patching paths, fixture values, and assertion text that may need updating after refactors.

## Versioning / Release

After version bumps, always stage and commit `uv.lock` along with the version change. Never forget the lock file.

The crate's version in `crates/genetic_opt/Cargo.toml` is kept equal to the one in `pyproject.toml`: bump both, and the `genetic_opt` entry in `crates/genetic_opt/Cargo.lock` with them.


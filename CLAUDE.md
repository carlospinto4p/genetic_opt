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

# Run unit tests
uv run pytest tests/unit -v

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

`numpy` is held below 2.0 and has no built wheel for Python 3.14, so
the first `uv sync` on a machine compiles it (about 3 minutes).

## Core Rules

1. **Self-Improvement**: When the user corrects a mistake, ALWAYS update the relevant guidelines (`.claude/rules/` or this file) to prevent it from happening again.

2. **Keep CLAUDE.md Minimal**: Do not include library schemas, architecture details, or information discoverable from the codebase. Keep only essential rules and commands here.

3. **Update CLAUDE.md Each Iteration**: Review and update this file when rules change or new important patterns emerge.

4. **Periodic Reviews**: Triggered by backlog depth — when `/backlog` shows fewer than 5 open items, propose `/scan`, `/improvements`, and `/prune` together.

## Project Configuration

Store project rules and preferences in project config files (e.g., `.claude/settings.json`, `CLAUDE.md`), NOT in memory files. Never save user instructions as memory files.

## Project Overview

A genetic algorithm library with two implementations side by side:
the Python package `src/genetic_opt` and the Rust crate
`crates/genetic_opt`. The Python package does not use the crate. A run
saved by either one has the same layout on disk, and
`utils.load_fit_result` reads both.

## Shell Commands

Never use compound shell commands with `cd && git` or `cd &&` chaining. Always use separate commands or `cd` first, then run the git/shell command independently.

## Testing

After any code change, run the full test suite and fix all failures before committing. Pay special attention to mock patching paths, fixture values, and assertion text that may need updating after refactors.

## Versioning / Release

After version bumps, always stage and commit `uv.lock` along with the version change. Never forget the lock file.

The crate's version in `crates/genetic_opt/Cargo.toml` is kept equal to the one in `pyproject.toml`: bump both, and the `genetic_opt` entry in `crates/genetic_opt/Cargo.lock` with them.


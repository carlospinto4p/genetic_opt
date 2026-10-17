---
name: testing-areas
description: The Rust crate's tests, and what the suites and its build take
version: 1.1
# Rust suite and recorded times: only when tests or the crate are in play.
paths:
  - "tests/**"
  - "crates/**"
---

# Testing: what is particular to genetic_opt

The additions of this repo to `testing.md`. `programme` pushes that
file to every Python project and refuses to push it over text a
project added inside its sections, so the additions live here.

## The Rust crate's suite

A third suite beside the two in `testing.md`:

| Suite | Location | Runs with | Purpose |
|-------|----------|-----------|---------|
| Rust crate | `crates/genetic_opt/tests/` and inline `#[cfg(test)]` | `cargo test --manifest-path crates/genetic_opt/Cargo.toml` | The Rust implementation |

The integration suite here builds and runs the Rust example program
and loads its output with the Python package. It carries the
`integration` marker and is skipped when `cargo` is not installed.

## Recorded times

What the 2-minute budget of the global `testing-discipline.md` rule is
compared with. One run of each, on a machine with 16 cores.

| Date | Version | What | Time |
|------|---------|------|------|
| 2026-10-17 | v2.0.2 | `uv run pytest tests/unit`, 185 tests | 3.9 s |
| 2026-10-17 | v2.0.2 | `uv run pytest tests/integration`, 5 tests | 0.5 s |
| 2026-10-17 | v2.0.2 | `cargo build` into an empty target folder | 7.8 s |
| 2026-10-17 | v2.0.2 | `cargo test` after that build, 42 tests | 5.3 s |

- The integration run had the crate built already. Of the 5.3 s of
  `cargo test`, the tests took 0.08 s and the rest was compiling.
- The slowest unit tests on 17th October 2026
  (`uv run pytest tests/unit --durations=10`): the two tests that save
  a plot, now in `tests/unit/algorithms/test_save.py`, 0.75 s and
  0.53 s, and
  `test_fit_scores_each_chromosome_once`, 0.32 s, which starts worker
  processes. No fixture takes 100 ms.

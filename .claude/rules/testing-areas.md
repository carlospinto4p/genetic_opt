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
compared with. One run of each, on a machine with 16 cores, with a load
average of 9 to 15 from other work.

| Date | Version | What | Time |
|------|---------|------|------|
| 2026-10-17 | v5.10.11 | `pytest tests/unit`, 309 tests | 6.8 s |
| 2026-10-17 | v5.10.11 | `pytest tests/unit -n 4`, 309 tests | 4.3 s |
| 2026-10-17 | v5.10.11 | `pytest tests/integration`, 35 tests | 3.7 s |
| 2026-10-17 | v5.10.11 | `cargo build`, empty target folder | 8.5 s |
| 2026-10-17 | v5.10.11 | `cargo test` after that build, 62 tests | 4.9 s |
| 2026-10-17 | v5.10.11 | `cargo test` with nothing to compile | 0.3 s |
| 2026-10-17 | v5.10.11 | `pnpm --dir frontend test`, 8 tests | 2.6 s |

- The integration run had the crate built already. Of the 4.9 s of
  `cargo test`, the tests took 0.09 s and the rest was compiling.
- `-n 4` runs the tests in four worker processes. `-n auto` started 16
  and took 6.5 s, as starting each worker costs more than it saves.
- Of the 2.6 s of the front-end tests, Vitest reports 0.64 s; the rest
  is starting `pnpm` and Node.
- The slowest unit tests (`uv run pytest tests/unit --durations=10`):
  the two of `test_a_saved_run_gets_the_plot_that_fit_saves`, 1.1 s
  and 1.0 s, which save a plot twice each, the first of them also
  importing matplotlib, and
  `test_one_seed_gives_the_same_set_run_with_any_hash_seed`, 0.75 s,
  which starts two interpreters. No fixture takes 100 ms.

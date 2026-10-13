---
name: testing-areas
description: What the test suites and the Rust crate build take
version: 1.0
# Recorded times: only when tests or the crate are in play.
paths:
  - "tests/**"
  - "crates/**"
---

# Testing: what is particular to genetic_opt

The additions of this repo to `testing.md`, which `programme` pushes
to every Python project and would overwrite.

## Recorded times

What the 2-minute budget of the global `testing-discipline.md` rule is
compared with. One run of each, on a machine with 16 cores.

| Date | Version | What | Time |
|------|---------|------|------|
| 2026-10-13 | v0.7.4 | `uv run pytest tests/unit`, 89 tests | 5.2 s |
| 2026-10-13 | v0.7.4 | `uv run pytest tests/integration`, 2 tests | 0.5 s |
| 2026-10-13 | v0.7.4 | `cargo build` into an empty target folder | 12.7 s |
| 2026-10-13 | v0.7.4 | `cargo test` after that build, 18 tests | 5.3 s |

- The integration run had the crate built already. Of the 5.3 s of
  `cargo test`, the tests took 0.06 s and the rest was compiling.
- The slowest unit tests on 13th October 2026
  (`uv run pytest tests/unit --durations=10`): the three of
  `test_fit_save.py` that save a run, 1.6 s, 0.8 s and 0.75 s, and
  `test_fit_scores_each_chromosome_once`, 0.6 s, which starts worker
  processes. No fixture takes 100 ms.

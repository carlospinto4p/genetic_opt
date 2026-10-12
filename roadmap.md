# genetic_opt Roadmap

The standing direction for development sessions. `backlog.md` holds the
*items*; this file holds the *ordering, gates, and invariants* that decide
which items to pick and which to refuse. Consult it **before selecting work**.

**Maintenance:** update when a direction-level decision lands, when a gate
clears, or when a phase completes. Keep it short — ordering and gates only;
rationale lives in the docs or ADRs it cites.

## Current phase: not set

_None yet._

## Standing invariants (apply to every session)

_None yet._

## What NOT to do (recent refuted directions)

- **No Python binding of the Rust crate (PyO3, maturin).** Decided on
  12th October 2026 from reading the code; nothing was measured. The
  crate stays as a Rust library that other projects depend on, and the
  Python package stays pure Python.
  - Offering only problems written in Rust gives this package one
    class, the `Knapsack` example. A real problem is written in its
    own project, which ships its own binding.
  - Running Python problems through the Rust engine is not faster.
    Written from recall, unchecked: Python runs one thread of Python
    code at a time, so the engine's threads would score one chromosome
    at a time, where `joblib` uses separate processes today.
  - Either way installing the package would need a wheel built for
    the machine or a Rust toolchain.
  - Reopen it if the Python engine shows up as the slow part of a real
    run. In `downstream` 0.6.0 the slow part was the backtest, moved to
    Rust there.

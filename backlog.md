# Backlog - Genetic-Opt

### 2026.10.12 (`/scan`: security, performance, refactoring, test coverage)

Read from the code by four scanners. Nothing was built and neither
test suite was run. Two items are marked "checked by running"; every
other one is from reading the cited lines. Timings come from one
micro-timing run on a loaded machine and are orders of magnitude.

Since 0.7.8 the `GeneticAlgorithm` class is in
`src/genetic_opt/algorithms/base.py`. The line numbers given for it
below were read in `algorithms/__init__.py` before the move and are
some tens of lines off.

**Refactoring**

- [ ] **[manual]** Decide whether to rename the Python names that
  differ from the crate. Each one breaks `downstream`, so the rest of
  this item was done in 0.17.0 and these were left:
  - `GeneticAlgorithm.historial` (Rust `history`), also the
    `historial` key of a `FitResult` and of `load_fit_result`.
    `downstream` reads it in `rule_optimizer.py:367`, `:457`, `:492`,
    `:516`, `utils.py:111` and two tests.
  - The argument `opt_is_min` (Rust `Problem::minimize`), passed in
    `rule_optimizer.py:313`.
  - `fitness_func` stored as `algo_fitness_func`, which
    `test_rule_optimizer.py:26` calls.
  - `Metric.best`, a dict where Rust has a `Best` struct;
    `test_utils.py:43-44` reads `m.best["score"]`.
  - `GeneticBag` (Rust `Knapsack`), which `downstream` does not use.


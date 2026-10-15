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

**Security**

- [ ] **[manual]** `src/genetic_opt/fit_result_io.py`: since 0.6.1
  `load_fit_result` refuses an unknown key in a `Score` or a
  `Metric`, but still ignores one at the top level of a file and in
  a saved Chromosome. Decide whether to refuse those too. Refusing
  them makes an older version of the package unable to read a file
  written by a newer one that adds a key.
- [ ] **[manual]** `pyproject.toml:5`: the `authors` field carries a
  personal name and a personal email address, published as package
  metadata with every wheel. Decide whether that is wanted.

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

### 2026.10.15 (found while testing the Rust validation errors, 0.17.6)

- [ ] `crates/genetic_opt/src/algorithm.rs`: a `Problem` whose
  `init_population` returns no chromosomes makes `measure` panic on
  `self.population[0]`. Python refuses an empty population with an
  error (`algorithms/base.py`, the empty-population error); the crate
  could return `Error::Validation` from `first_chromosomes`. (LOW, S)

### 2026.10.15 (found while covering the small test gaps, 0.17.7)

- [ ] `format_seconds` gives "1 day, 0.00 seconds" for 86400 seconds,
  in both `src/genetic_opt/functions.py` and
  `crates/genetic_opt/src/format.rs`: a whole number of days falls
  through to the seconds text. Decide the text ("1 day" or
  "1 day, 0:00:00 hours") and write it in both, with a test in
  `tests/unit/test_functions.py` and in `format.rs`. Left untested in
  0.17.7 so the odd text is not fixed in place by a test. (LOW, S)

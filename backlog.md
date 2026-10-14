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

**Test coverage**

- [ ] `load_fit_result` (`fit_result_io.py:26-92`) on an empty or missing
  folder reaches `fit_data_list[-1]` and raises `IndexError`; a
  folder with another file in it and a corrupt BSON or JSON file
  are untested. `remove_duplicates` (`:192-198`),
  `load_decoded_chromosome_func` and `load_gene_func` are never
  passed. (MED, M)
- [ ] Mutation with probability 0 and 1 is untested for Python sets
  (`GeneSet.random_mutate` in `gene_collection.py`) and in Rust
  (`crates/genetic_opt/src/problem.rs:67-81`). Python lists have
  `test_list_mutation_with_probability_0_and_1` since 0.6.9.
  (MED, S)
- [ ] No Python test runs `fit` twice with one seed and compares the
  histories, or `n_jobs=1` against `n_jobs=2`. Rust has
  `a_seed_gives_the_same_run_with_any_number_of_threads`
  (`tests/algorithm.rs:158`). Neither side tests that another seed
  gives another run. (MED, S)
- [ ] `get_population_metrics` (`metrics.py:124-171`) has no test
  with known values; the Rust statistics have one
  (`metrics.rs:85`). All-equal scores and a population of one are
  untested in both, and the Rust `median` of an empty slice
  subtracts 1 from 0 (`metrics.rs:69`). (MED, S)
- [ ] Rust `Error::Validation` paths with no test
  (`algorithm.rs:246-254`, `:270-275`, `:296-301`, and the
  `n_jobs > cores` half of `:235`): a set longer than its gene
  space, a chromosome of the wrong length, parents asked from an
  empty rest, too many threads. A false `crossover_invariant`
  (`:311-318`) is untested, and `a_broken_invariant_stops_the_run`
  (`tests/algorithm.rs:253`) does not check which message came
  back. (MED, S)
- [ ] `single_point_crossover` (`crates/genetic_opt/src/problem.rs:115-129`)
  is reached only through `Knapsack`; its short-input branch and
  inputs of different lengths are untested. `Knapsack::decode` and
  `fitness` (`problems.rs:56-86`) and `decode_bag`
  (`examples/binary.py:43-68`) have no test with a known input,
  only the final 309, and nothing compares the two. (MED, S)
- [ ] No set chromosome (`is_gene_set: true`) and no `Score` with
  `name` or `extra_metrics` is ever written by Rust and loaded by
  Python (`chromosome.rs:56-66`, `score.rs:7-10`); both layout
  tests use the list knapsack. (MED, M)
- [ ] Python, small gaps: `tests/unit/test_functions.py:66` asserts the
  exact text "took 0.00 seconds" and fails after a 5 ms pause;
  `experiment_config.yml` and `fit_plots.jpg`
  are checked for existence only (`tests/unit/test_fit_save.py:35-38`);
  the knapsack test does not assert the number of generations
  (`tests/unit/test_binary_algs.py:21`);
  `experiment_config()` and `extra_config`; the empty-population
  error (`algorithms/base.py:918-919`) and `n_generations=0`;
  the four-panel plot (`plots.py:67-69`, `:86-100`); a `Score` with
  `extra_metrics` saved and loaded; `files.py` on missing and
  corrupt files; `format_seconds` at 0, 60, 3600 and 86400 seconds
  (the last gives "1 day, 0.00 seconds", also in `format.rs`) and
  the "Yi" case of `format_bytes`; and `logs.py`. (LOW, M)
- [ ] Rust, small gaps: the set and minimise tests
  (`tests/algorithm.rs:201-238`) assert "never gets worse" but not
  the known optimum (30 and 3); `Chromosome::new` sorting and
  removing duplicates for a set (`chromosome.rs:16-22`); the
  failure paths of `save.rs:55-91` and a `Problem::experiment_config`
  that returns a value; `population()`, `metrics()`,
  `FitResult.fit_parameters` and the `FitConfig::new` defaults; the
  default-to-BSON branch of `examples/knapsack.rs:20-23`; the
  `Display` text of the errors (`error.rs:6-14`). (LOW, S)

### 2026.10.12 (found while registering the project in `programme`)

- [ ] `numpy` is held below 2.0 (`pyproject.toml:9`) and 1.26.4 has
  no built wheel for Python 3.14, the version `.python-version` now
  asks for. `uv sync` compiled it from source: 3 minutes 25 seconds
  on 12th October 2026, paid again on every new environment. Check
  whether the package works with `numpy` 2 and raise the bound.
- [ ] `.claude/rules/testing.md` holds text of this repo alone: the
  "Rust crate" row of the table, the paragraph on the integration
  suite and the `crates/genetic_opt/**` path. `programme` pushes
  that file to every Python project. Whether its push keeps local
  text was not read. If it does not, move the three to
  `.claude/rules/testing-areas.md`, added in 0.7.7. (LOW, S)
- [ ] The project has no `AGENTS.md`, so Codex and OpenCode do not
  get `CLAUDE.md` and `.claude/rules/`
  (`~/.claude/rules/claude-opencode-sync.md`). `downstream` has none
  either.

### 2026.10.13 (found while making a second `fit` a new run, 0.7.13)

- [ ] `src/genetic_opt/algorithms/save.py:73`: `FitSaver` creates the
  folder of the run when the `GeneticAlgorithm` is built, so a second
  `fit` on the same object writes its `fit_data_<n>` files over those
  of the first. The Rust crate creates a folder in each `fit`
  (`algorithm.rs`, `create_run_folder`). `downstream` writes into
  `self.save_path` before `fit` (`rule_optimizer.py:321-326`), so the
  first folder has to exist at once. (LOW, S)

### 2026.10.13 (found while writing the `FitResult` types, 0.10.0)

- [ ] `src/genetic_opt/algorithms/base.py`: `fit` with a negative
  `n_generations` runs no generation and returns an empty dictionary,
  which is not a `FitResult`. Refuse it with a
  `ValidationException`, as a `population_size` below 1 is. (LOW, S)

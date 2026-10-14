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

- [ ] Argument checks raise the base `GeneticOptException` in
  `chromosome.py:46`, `gene_collection.py:28`, `:85`, `:156`, `:225`
  and `algorithms/base.py:919`, and `ValidationException` in
  `algorithms/base.py:193`, `:424`, `:431` and
  `examples/binary.py:39`. Rust uses `Error::Validation` for all.
  (MED, S)
- [ ] `src/genetic_opt/files.py:17-61`: paths are strings handled by
  `ensure_folder_format`, `get_container_folder`,
  `get_file_extension` and `normalize_path`. `get_file_extension`
  splits on the last dot of the whole path, so `"run.v2/data"`
  gives `"v2/data"`. `pathlib.Path` replaces all four. (MED, M)
- [ ] `src/genetic_opt/gene_space.py:11`: `GeneSpace` is a `TypeVar`
  bound to `AbstractGeneSpace` but is used as a class annotation
  everywhere. Annotate with the class, or rename it. (MED, S)
- [ ] Code with no caller in this repo (check `downstream` first):
  `get_best` and `get_bests` (`algorithms/base.py:541-565`),
  which also pick the bests differently from `_get_fitted_data`;
  `gene_space_func` and `gene_space_func_kwargs`
  (`chromosome.py:137-138`, `gene_collection.py:112-115`,
  `:185-191`); the `.lnk` filter in `files.py:77`, `:104-105`. The
  non-recursive branch of `get_files_inside_folder`
  (`files.py:98-99`) walks the whole tree to keep one entry. In
  `functions.py:43-45` the `only_hours` padding is undone by
  `int()`. (LOW, S)
- [ ] Types and names: `BinaryGeneSpace.select_random` is annotated
  `-> int` and returns an array for a tuple `n`
  (`gene_space.py:53-54`); `score_time` is annotated `int` and
  holds a float (`chromosome.py:62`); `Metric.best` is a dict where
  Rust has a `Best` struct (`metrics.py:32`); the number of bests
  is a literal `5` (`algorithms/base.py:752`) where Rust has
  `N_BESTS`; `files.py:151` names a parameter `path` over
  `os.path`. Across the two implementations: `historial` and
  `history`, `opt_is_min` and `minimize`, `GeneticBag` and
  `Knapsack`, `fitness_func` stored as `algo_fitness_func`. Two
  docstring styles in `algorithms/base.py`. (LOW, M)
- [ ] Stale comments: the 2024 TODO at `fit_result_io.py:25` (the functions
  are tested now); notes from 2023 and 2024 at
  `algorithms/base.py:55-56`, `:186-187`, `:658-661`;
  `examples/__init__.py:4` refers to a `core` module that does not
  exist; `metrics.py:50`, `:53` say `from_dict` where `to_dict`
  makes the dict; commented-out assertions on a key the code no
  longer produces at `tests/unit/test_binary_algs.py:24-26`. (LOW, S)
- [ ] Rust, small: a thread pool build failure is reported as
  `Error::Validation` (`algorithm.rs:172`); `save.rs:67`, `:82`,
  `:88` turn serializer errors into strings; `fit_parameters()`
  copies seven fields one by one (`algorithm.rs:255-264`); the
  modules `problem` and `problems` differ by one letter
  (`lib.rs:15-16`); the crate version is kept equal to
  `pyproject.toml:3` by hand and nothing checks it
  (`Cargo.toml:3-4`). (LOW, S)

**Test coverage**

- [ ] Nothing runs either suite on a push: GitLab CI is disabled
  across the fleet, and the commit hooks added in 0.4.1 run `ruff`,
  `cargo fmt` and `cargo clippy` but no test. A pre-push hook
  running `pytest tests/unit` and `cargo test` is the alternative.
  (HIGH, S)
- [ ] Python set chromosomes have no test: every test passes
  `chromosome_as_set=False`. `GeneSet`
  (`gene_collection.py:132-230`) and the set branches of
  `chromosome.py:54`, `:82-83`, `:106-108` never run inside a `fit`.
  Rust has `set_chromosomes_stay_sets...`
  (`tests/algorithm.rs:201`). (HIGH, M)
- [ ] `opt_is_min=True` is used by no Python test, so the ascending
  sort at `algorithms/base.py:945-948` never runs. Rust has
  `minimize_keeps_the_lowest_scores`. (HIGH, S)
- [ ] `tests/unit/test_binary_algs.py:50`:
  `len(calls) == len(set(calls))` holds for an empty file, so the
  test passes if the logging wrapper is never called. Add
  `assert calls`. (MED, S)
- [ ] `tests/unit/test_fit_save.py`: since 0.6.3 the loaded history is
  compared with the one `fit` returns, but `fit_metrics` is not
  checked. The run has at most 4 files, so the ordering of `fit_data_10` after `fit_data_2`
  that `fit_result_io.py:79` handles never runs. (MED, S)
- [ ] Python error paths with no test: the three
  `ValidationException` cases (`algorithms/base.py:423-433`,
  `:192-196`) and `examples/binary.py:38-41`; `InvariantException`
  from `mutation_invariant` and `crossover_invariant` (`:255-259`,
  `:272-276`); the construction errors in `chromosome.py:45-50` and
  `gene_collection.py:27-29`, `:84-92`; `__eq__` against something
  that is not a Chromosome, which raises `AttributeError`
  (`chromosome.py:97-116`). (MED, S)
- [ ] The `min_population_size` stop of `fit` in
  `algorithms/base.py` has no Python test; the no-improvement stop
  has one since 0.7.11, and `callback_func` and `exit_condition`
  since 0.13.1. In
  Rust the `min_population_size` stop and the stalled-mean stop
  (`algorithm.rs:213-219`, `:401-406`) have none either. (MED, M)
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
  (`tests/unit/test_binary_algs.py:21`); `get_best` and `get_bests`;
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

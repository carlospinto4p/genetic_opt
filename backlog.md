# Backlog - Genetic-Opt

### 2026.10.12 (found while fixing parallel scoring and removing `cpinto`)

- [ ] The Rust crate does not save the plot `fit_plots.jpg` that the
  Python package saves with each generation.
- [ ] `space_points` in the saved `fit_metrics` is the number of
  different genes (2 for a binary problem), not the number of
  possible chromosomes, so `exploration_percentage` is not a
  percentage: a knapsack run of 10 objects reports 7500. Both
  implementations do it.

### 2026.10.12 (`/scan`: security, performance, refactoring, test coverage)

Read from the code by four scanners. Nothing was built and neither
test suite was run. Two items are marked "checked by running"; every
other one is from reading the cited lines. Timings come from one
micro-timing run on a loaded machine and are orders of magnitude.

**Security**

- [ ] `crates/genetic_opt/src/algorithm.rs:390`: `population_size = 0`
  with `min_population_size = 0` passes `fit_parameters()` (line 240)
  and `measure` then indexes `self.population[0]`, so `fit` panics
  instead of returning `Error::Validation`. `crossovers_prop`,
  `besties_prop` and `mutate_prob` are not range-checked in either
  implementation (Python checks only the two sizes and `n_jobs`,
  `algorithms/__init__.py:423-433`). (MED, S)
- [ ] `.gitlab-ci.yml`: the `publish-package` job that holds
  `CI_JOB_TOKEN` installs `build` and `twine` with no version, and
  `hatchling` has no version bound (`pyproject.toml:23`). The file
  is the `python-base` skeleton since 0.4.1, so the pin belongs in
  `programme`. GitLab CI is disabled across the fleet
  (`~/.claude/rules/publish-on-demand.md`), so the job rarely runs.
  (LOW, S)
- [ ] `src/genetic_opt/files.py:217-219`: `save_yaml` uses `yaml.dump`
  with the full `Dumper`, so an object that is not plain data in
  `experiment_config()` is written as a `!!python/object` tag that
  only an unsafe loader can read back. Line 217 also replaces
  `Dumper.ignore_aliases` on the shared PyYAML class, which changes
  YAML output for the whole process and for every later test. Use
  `safe_dump` with a local Dumper subclass. `ignore_aliases=False`
  has no test. (LOW, S)
- [ ] `src/genetic_opt/algorithms/__init__.py:175-178` and
  `crates/genetic_opt/src/algorithm.rs:173-176`: the save folder is
  `save_path` + `experiment_name` + timestamp, and the name is not
  checked. A name with `../` writes outside `save_path`; in Rust an
  absolute name discards `save.path`. Matters only when the name
  comes from untrusted input. (LOW, S)
- [ ] `src/genetic_opt/functions.py:60` and
  `crates/genetic_opt/src/algorithm.rs:174`: the run folder name is a
  UTC timestamp to the second. Two runs with one experiment name
  started in the same second share the folder and overwrite each
  other's `fit_data_<n>` files. (LOW, S)
- [ ] `src/genetic_opt/utils.py:162-218`, `files.py:110-129`:
  `load_fit_result` cannot execute code (`bson.decode` and
  `json.load` only), but it reads each file whole with no size
  limit and passes the dicts unchecked into `Score(**s)`,
  `Metric(**d)` and `Chromosome(...)`, so a malformed file raises a
  raw `KeyError` or `TypeError` and unknown keys are accepted.
  (LOW, M)
- [ ] `src/genetic_opt/exceptions.py:17-22`: every
  `GeneticOptException` logs at ERROR level in its constructor, so
  a caught exception still prints an error. Three raise sites pass
  `locals()` (`chromosome.py:49`, `gene_collection.py:29`, `:226`),
  which prints every local, including the genes and the gene space.
  `algorithms/__init__.py:257-259` and `:274-276` print whole
  chromosomes. (LOW, S)
- [ ] `src/genetic_opt/chromosome.py:112-116` with
  `algorithms/__init__.py:926-943`: `_chromosome_cache` is keyed by
  `Chromosome.id` alone, an md5 of the `repr` cut to 30 digits. Two
  different chromosomes with one id would share a score. Written
  from recall, unchecked: `md5()` without `usedforsecurity=False`
  raises on a FIPS build of Python. (LOW, S)
- [ ] `crates/genetic_opt/src/problems.rs:58-62` and `:78`: `Knapsack`
  adds weights and sums values as `u32`. Large inputs panic in a
  debug build and wrap in a release build, where a wrapped weight
  passes the capacity check. Use `checked_add` or `u64`. (LOW, S)
- [ ] `pyproject.toml:14` and `:19-20`: `pyyaml>=6.0.3`,
  `pytest>=9.1.1` and `ruff>=0.16.4` have no upper bound, unlike
  the other five runtime dependencies. (LOW, S)
- [ ] **[manual]** `pyproject.toml:5`: the `authors` field carries a
  personal name and a personal email address, published as package
  metadata with every wheel. Decide whether that is wanted.

**Performance**

- [ ] `src/genetic_opt/algorithms/__init__.py:881-890` with
  `utils.py:309-315`: with a `save_path`, every generation
  serializes the whole history of populations and
  `_save_fit_result` then keeps only the last one. The work grows
  with the square of the generations. Serialize `historial[-1]`
  only. (HIGH, S)
- [ ] `src/genetic_opt/algorithms/__init__.py:898-904`: with a
  `save_path` and `plot_metrics=True` (the default) a 13x15 inch
  matplotlib figure is built and written to `fit_plots.jpg` after
  every generation; the `fit` docstring (line 354) says "after
  finishing the training". `plots.py:88-93` re-applies every
  `other_metrics_to_plot` function to every generation each time.
  Plot once at the end or every N generations. (HIGH, S)
- [ ] `src/genetic_opt/chromosome.py:63-64`: every Chromosome builds
  its own `RandomState`, about 217 microseconds of the 214-220 a
  10-gene Chromosome takes to build, and about 3 KB in each pickled
  Chromosome. Since 0.2.13 `fit` passes the algorithm's own state
  (`algorithms/__init__.py:237-241`), so it is only a fallback
  (`chromosome.py:159`). Build it on first use. (HIGH, S)
- [ ] `src/genetic_opt/examples/binary.py:43-82`: `decode_bag` and
  `fit_bag` close over `self`, so sending the fitness function to a
  worker pickles the whole `GeneticBag` with its population,
  history and caches: 8,857 bytes before a `fit`, 634,581 after 9
  generations of 50. Close over `weights`, `values` and `capacity`.
  `changelog.md:94-96` says only the fitness function travels,
  which does not hold for a bound method or such a closure; say so
  in the `fit` docstring. (HIGH, S)
- [ ] `src/genetic_opt/algorithms/__init__.py:488-490` and `:787-793`:
  `_get_fitted_data` runs after every generation and decodes the
  whole population each time, also with no `save_path`, where every
  result but the last is thrown away. (MED, S)
- [ ] `src/genetic_opt/chromosome.py:97-116`: `Chromosome.id` is
  recomputed on every call (`repr`, md5, decimal string, int: 2.9
  microseconds for 10 genes, 13.9 for 200); `__hash__` calls it
  once and `__eq__` twice, many times a generation. Keep it on the
  instance and clear it in `random_mutate`. (MED, S)
- [ ] `src/genetic_opt/gene_collection.py:114-117`, `:188-193`,
  `:228-229` with `gene_space.py:54`: mutation and gene picking
  loop in Python with one random draw per gene; a replacement gene
  costs about 10 microseconds because `choice([0, 1])` builds an
  array each call. One mask and one batched draw would do it.
  Changes what a seed produces, as 0.2.13 did. (MED, M)
- [ ] `src/genetic_opt/algorithms/__init__.py:934-937`:
  `Parallel(n_jobs=n_jobs)` is called every generation, also when
  no Chromosome is new, and the default `n_jobs=-2` starts worker
  processes for a fitness function that takes microseconds. Skip
  the call when `new_population` is empty. Effect not measured.
  (MED, S)
- [ ] `src/genetic_opt/algorithms/__init__.py:14`, `plots.py:6`,
  `files.py:8-11`: importing `genetic_opt.algorithms` imports
  `matplotlib.pyplot`, `bson` and `yaml` whether or not anything is
  saved: 0.88 seconds on top of numpy's 0.19, paid again by each
  worker process. 0.3.0 moved these imports to the top
  (`changelog.md:55-56`). Import them inside the save and plot
  functions. (MED, S)
- [ ] `tests/unit/test_binary_algs.py:13-19`: `test_genetic_bag` uses the
  default `n_jobs=-2`, which starts 15 worker processes on a
  16-core machine for a 10-gene knapsack. The same `fit` with
  `n_jobs=1` took 0.12 seconds. Line 46-48 already covers two
  processes. Pass `n_jobs=1`. (MED, S)
- [ ] `tests/integration/test_rust_layout.py:15-36`: the Python suite runs
  `cargo run --example knapsack` twice. With no `target/` folder
  that compiles the crate and 102 dependencies inside pytest, needs
  the network, and writes to `crates/genetic_opt/target/`. The test
  is skipped without a word when `cargo` is missing, so a machine
  without Rust reports green. It carries the `integration` marker
  since 0.4.1. Build once in a session fixture. (MED, S)
- [ ] `src/genetic_opt/utils.py:79-94` and `:200-207`:
  `load_fit_result` parses every generation file in full, and each
  file holds the metrics of all generations so far, so loading
  grows with the square of the generations. Only `population` is
  needed from every file but the last. (MED, S)
- [ ] `src/genetic_opt/utils.py:316-322`,
  `crates/genetic_opt/src/save.rs:39` and `algorithm.rs:460`: each
  `fit_data_<n>` file repeats the metrics of every earlier
  generation, in both implementations. Changing it touches both
  writers and the reader. (LOW, M)
- [ ] `historial` and `_chromosome_cache`
  (`algorithms/__init__.py:198-207`, `:972-977`) and the Rust
  `history` and `scores` (`algorithm.rs:112`, `:114`) grow for the
  whole run. `historial` is part of what `fit` returns, so a limit
  is an API decision. (LOW, M)
- [ ] `crates/genetic_opt/src/algorithm.rs:345-388`: each new
  chromosome has its genes cloned twice (lines 355, 364-365) and
  hashed three to four times with SipHash, and `measure` hashes the
  whole population again each generation to count the different
  ones. Equal chromosomes already share one `Arc<Individual>` (line
  369), so key the map by it and count by pointer. (LOW, S)
- [ ] Small costs in the Python loop: three `logger.info` calls per
  generation build a `pformat` of the whole `Metric` even with the
  level off (`algorithms/__init__.py:468-477`);
  `_get_iteration_improvement()` runs twice a generation (lines 472
  and 317); each save does one extra `stat` to log the file size
  (`files.py:144-147`, `:171-174`, `:194-197`); `random_state.choice`
  over a list of Chromosomes builds an object array each generation
  (lines 670-674; drawing indices changes what a seed produces).
  (LOW, S)
- [ ] Small costs in the Rust crate: `median` copies and sorts
  scores that are already sorted and `variance` recomputes the mean
  (`metrics.rs:64-76`); with saving on, `decode` runs one by one
  over the population while the thread pool is idle
  (`algorithm.rs:454-458`); `chrono` is used for one timestamp with
  its default features on, and `bson` and `serde_norway` are needed
  only when saving (`Cargo.toml:9-17`, 102 crates in the lock
  file). (LOW, S)
- [ ] The repo records no wall-clock time for the Python suite, the
  Rust suite or a cargo build. Run `pytest --durations=10` and
  `cargo test` once and write the date beside the result. (LOW, S)

**Refactoring**

- [ ] Bug, checked by running:
  `src/genetic_opt/algorithms/binary.py:57` calls
  `randint(1, self.chromosome_length - 1)`, whose upper bound is
  excluded. For length 5 the cut is only ever 1, 2 or 3, and for
  length 2 it raises `ValueError: low >= high`. The Rust
  `single_point_crossover` uses `1..length`
  (`crates/genetic_opt/src/problem.rs:124`). Lines 60-61 build the
  children without `is_gene_set` or `random_seed`. Fix with a
  regression test; it changes what a seed produces. (HIGH, S)
- [ ] `src/genetic_opt/algorithms/__init__.py:57-983`: the whole
  `GeneticAlgorithm` class, about 930 lines, lives in a package
  `__init__.py` and does evolution, validation, statistics,
  serialization, saving and plotting. Move it to
  `algorithms/base.py` and put saving and plotting behind a saver,
  as `save.rs` does. (HIGH, M)
- [ ] Bug, checked by running:
  `src/genetic_opt/gene_collection.py:208-209`:
  `GeneSet.select_random` does `genes = gene_space` when the size
  equals the size of the gene space, so the genes become the
  `BinaryGeneSpace` object instead of a set. (MED, S)
- [ ] Bug, from reading: `src/genetic_opt/algorithms/__init__.py:428-433`
  turns the default `n_jobs=-2` into `cpu_count() - 1`, which is 0
  on a one-core machine and raises `ValidationException`. The Rust
  crate guards it with `.max(1)` (`algorithm.rs:234`).
  `tests/unit/test_binary_algs.py:13`, `:47` and
  `crates/genetic_opt/tests/algorithm.rs:139`, `:161` ask for 2
  jobs and fail on one core too. (MED, S)
- [ ] `src/genetic_opt/algorithms/__init__.py:308-317` with `:831-839`:
  `_get_iteration_improvement` returns the raw metrics for the
  first generation and differences afterwards, under the same keys,
  so a run whose first population has mean score 0 stops at once.
  `README.md:58` documents it as a difference from the Rust crate.
  Lines 843-850 depend on the field order of `Metric.__dict__`. No
  test pins either behaviour. (MED, S)
- [ ] `crates/genetic_opt/src/algorithm.rs:213`:
  `self.metrics[generation]` assumes `metrics` is empty when `fit`
  starts. A second `fit` on the same object reads the first run's
  metrics and mixes in the old population (lines 191, 201-203). In
  Python `historial` and `metrics` keep growing across calls. Reset
  the state or consume `self`. (MED, S)
- [ ] `src/genetic_opt/chromosome.py:133-164`,
  `gene_collection.py:114-118`, `:187-196`: `random_mutate` changes
  the genes in place and returns `self` without clearing
  `self.score`, while `__hash__` comes from the genes. A mutated
  object that is already a dict key or already scored is then
  inconsistent. The Rust `Problem::mutate` returns a new `Vec`.
  (MED, M)
- [ ] `src/genetic_opt/logs.py:26-49`, `:58`: the library calls
  `logging.config.dictConfig` at import, adds a stdout handler and
  sets `propagate: False`, and reads `LOG_FORMAT` and
  `LOG_DATEFORMAT`, which nothing documents. A library should only
  call `logging.getLogger("genetic_opt")`
  (`~/.claude/rules/logger-format.md`). (MED, S)
- [ ] `src/genetic_opt/algorithms/__init__.py:108-128` and `:320-336`:
  `__init__` takes 15 parameters and `fit` 12; `binary.py:17-22`
  lists 8 again. The Rust crate groups them as `FitConfig` and
  `SaveConfig`. Two dataclasses would replace the hand-built
  `fit_parameters` dict at lines 434-443. (MED, M)
- [ ] The shape of the fit result is pasted into eight docstrings
  (`algorithms/__init__.py:373-416`, `:703-746`, `:955-967`,
  `utils.py:36-77`, `:115-157`, `:231-274`, `metrics.py:18-29`,
  `:140-151`) and has drifted: it names `self.fit_func`, which does
  not exist, and omits `min_population_size`, `n_jobs` and
  `genetic_opt_version`. A `FitResult` dataclass or TypedDict
  states it once, as the Rust `FitResult` does. (MED, M)
- [ ] `src/genetic_opt/utils.py:97-333`: `serialize_fit_result`
  writes `last_population` and `_save_fit_result` renames
  `historial[-1]` to `population` (`algorithms/__init__.py:887-890`),
  but `load_fit_result_file` never reads `last_population`, so a
  loaded result has a different shape from what `fit` returns. The
  name `utils` hides that the module only reads and writes fit
  results. (MED, M)
- [ ] `src/genetic_opt/algorithms/__init__.py:480-486` and `:511-524`:
  `fit` checks `hasattr(f, "__self__") and f.__self__ == self` to
  decide how to call `callback_func` and `exit_func`, and repeats
  the log-and-break block. Defaults of `lambda _: None` and
  `lambda _: False` remove both branches. (MED, S)
- [ ] The "genes or gene_space" check is written three times
  (`chromosome.py:43-50`, `gene_collection.py:84-87`, `:155-158`).
  `Chromosome` keeps `genes` and `size` as copies of its gene
  collection's and syncs them by hand (`chromosome.py:59-60`,
  `:163`). (MED, M)
- [ ] Argument checks raise the base `GeneticOptException` in
  `chromosome.py:46`, `gene_collection.py:28`, `:85`, `:156`, `:225`
  and `algorithms/__init__.py:919`, and `ValidationException` in
  `algorithms/__init__.py:193`, `:424`, `:431` and
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
  `get_best` and `get_bests` (`algorithms/__init__.py:541-565`),
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
  is a literal `5` (`algorithms/__init__.py:752`) where Rust has
  `N_BESTS`; `files.py:151` names a parameter `path` over
  `os.path`. Across the two implementations: `historial` and
  `history`, `opt_is_min` and `minimize`, `GeneticBag` and
  `Knapsack`, `fitness_func` stored as `algo_fitness_func`. Two
  docstring styles in `algorithms/__init__.py`. (LOW, M)
- [ ] Stale comments: the 2024 TODO at `utils.py:17` (the functions
  are tested now); notes from 2023 and 2024 at
  `algorithms/__init__.py:55-56`, `:186-187`, `:658-661`;
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
  `chromosome.py:54`, `:82-83`, `:106-108` never run, including the
  bug filed above. Rust has `set_chromosomes_stay_sets...`
  (`tests/algorithm.rs:201`). (HIGH, M)
- [ ] `opt_is_min=True` is used by no Python test, so the ascending
  sort at `algorithms/__init__.py:945-948` never runs. Rust has
  `minimize_keeps_the_lowest_scores`. (HIGH, S)
- [ ] `tests/unit/test_binary_algs.py:50`:
  `len(calls) == len(set(calls))` holds for an empty file, so the
  test passes if the logging wrapper is never called. Add
  `assert calls`. (MED, S)
- [ ] `tests/unit/test_fit_save.py:49` checks the loaded history by length
  only, not its content, its order or `fit_metrics`. The run has at
  most 4 files, so the ordering of `fit_data_10` after `fit_data_2`
  that `utils.py:89` handles never runs. (MED, S)
- [ ] Python error paths with no test: the three
  `ValidationException` cases (`algorithms/__init__.py:423-433`,
  `:192-196`) and `examples/binary.py:38-41`; `InvariantException`
  from `mutation_invariant` and `crossover_invariant` (`:255-259`,
  `:272-276`); the construction errors in `chromosome.py:45-50` and
  `gene_collection.py:27-29`, `:84-92`; `__eq__` against something
  that is not a Chromosome, which raises `AttributeError`
  (`chromosome.py:97-116`). (MED, S)
- [ ] `callback_func`, `exit_condition` and the `min_population_size`
  stop (`algorithms/__init__.py:480-486`, `:497-524`) have no
  Python test; the no-improvement stop runs only by accident. In
  Rust the `min_population_size` stop and the stalled-mean stop
  (`algorithm.rs:213-219`, `:401-406`) have none either. (MED, M)
- [ ] `load_fit_result` (`utils.py:79-94`) on an empty or missing
  folder reaches `fit_data_list[-1]` and raises `IndexError`; a
  folder with another file in it and a corrupt BSON or JSON file
  are untested. `remove_duplicates` (`:192-198`),
  `load_decoded_chromosome_func` and `load_gene_func` are never
  passed. (MED, M)
- [ ] Mutation with probability 0 and 1 is untested in both
  implementations (`chromosome.py:133-164`,
  `gene_collection.py:95-118`, `crates/genetic_opt/src/problem.rs:67-81`);
  only 0.05 and 0.5 are used. (MED, S)
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
  error (`algorithms/__init__.py:918-919`) and `n_generations=0`;
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
- [ ] The project has no `AGENTS.md`, so Codex and OpenCode do not
  get `CLAUDE.md` and `.claude/rules/`
  (`~/.claude/rules/claude-opencode-sync.md`). `downstream` has none
  either.

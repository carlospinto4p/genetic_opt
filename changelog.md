
## Changelog - Genetic-Opt


### v0.13.1 - 13th October 2026

- `src/genetic_opt/algorithms/base.py`: `fit` always calls
  `callback_func` and `exit_condition` with the algorithm. It looked
  at `__self__` to call a method of the algorithm with no argument,
  and wrote the lines that end the run twice. Without a
  `callback_func` it still calls the method `default_fit_callback`,
  which a subclass overrides. A method of the algorithm passed as
  `callback_func` or `exit_condition` now gets the algorithm as an
  argument, as any other function does.
- Added two tests to `tests/unit/test_binary_algs.py`: the callback
  and the exit condition get the algorithm, and a subclass that
  overrides `default_fit_callback` has it called in each generation.

### v0.13.0 - 13th October 2026

- Renamed the module `genetic_opt.utils` to `genetic_opt.fit_result_io`.
  It holds `load_fit_result`, `load_fit_result_file` and
  `serialize_fit_result` and nothing else, which the old name did not
  say. Code that imports `genetic_opt.utils` has to import
  `genetic_opt.fit_result_io`.
- The docstrings, `README.md`, `CLAUDE.md`, `backlog.md` and two
  comments of the Rust crate name the module by its new name.

### v0.12.0 - 13th October 2026

- `src/genetic_opt/utils.py`: `load_fit_result` returns
  `last_population` too, read from the file of the last generation, so
  a loaded run has the keys `GeneticAlgorithm.fit` returns. The files
  always held it and nothing read it. `load_fit_result_file` returns
  what it did: the `last_population` of a file is its `population`,
  decoded.
- `src/genetic_opt/fit_result.py`: removed `LoadedFitResult`.
  `load_fit_result` returns a `FitResult`.
- `tests/unit/test_fit_save.py`: the loaded `last_population` and the
  keys of the loaded run are compared with those `fit` returns, and a
  `Score` of `last_population` with an unknown key is refused.
- `README.md`: says that a loaded run has the keys of `fit`.

### v0.11.1 - 13th October 2026

- `CLAUDE.md`: a change that breaks the code of `downstream` gets an
  item in the backlog of `downstream` in the same task. The changes of
  0.9.0 and 0.11.0 were only reported, and the item was filed
  afterwards.

### v0.11.0 - 13th October 2026

- Added `src/genetic_opt/algorithms/config.py`, with the two classes
  that replace loose arguments, as `FitConfig` and `SaveConfig` do in
  the Rust crate. `genetic_opt.algorithms` exports both. Code that
  calls `fit` or saves its runs has to be changed.
  - `FitConfig`: `n_generations`, `population_size`,
    `crossovers_prop`, `besties_prop`, `mutate_prob`,
    `min_population_size` and `n_jobs`, with the defaults `fit` had.
  - `SaveConfig`: `path`, `serialize_decoded_chromosome_func`,
    `as_bson` and `serialize_gene_func`.
- `src/genetic_opt/algorithms/base.py`:
  - `GeneticAlgorithm.fit` takes a `FitConfig` in place of those seven
    arguments. `exit_condition`, `plot_metrics`,
    `other_metrics_to_plot`, `callback_func` and `iter_func` stay as
    they were.
  - `GeneticAlgorithm` takes `save`, a `SaveConfig`, in place of
    `save_path`, `save_as_bson`, `serialize_decoded_chromosome_func`
    and `serialize_gene_func`. The attribute `save_path` still holds
    the folder of the run.
  - `fit_parameters` is built from the `FitConfig`, and not key by
    key.
- `src/genetic_opt/algorithms/save.py`: `FitSaver` takes a
  `SaveConfig`. A `SaveConfig` can not be built without
  `serialize_decoded_chromosome_func`, so the `ValidationException`
  for a `save_path` without one is gone.
- `README.md`: added an example of each class.
- Added `test_fit_parameters_are_the_config_with_the_seed_and_the_jobs`
  to `tests/unit/test_binary_algs.py`. The other tests and
  `sketches/genetic_bag.py` call `fit` the new way.

### v0.10.0 - 13th October 2026

- Added `src/genetic_opt/fit_result.py`, which states once the keys of
  what `GeneticAlgorithm.fit` returns and of a loaded run. They are
  typed dictionaries, so the results stay plain dictionaries:
  - `FitResult`: what `fit` returns.
  - `LoadedFitResult`: what `utils.load_fit_result` returns.
  - `FitResultFile`: what `utils.load_fit_result_file` returns.
  - `Bests`, `FitMetrics`, `FitnessFuncCalls`, `TotalFitTime`,
    `FitParameters` and `FitSummary`: their parts.
- The description of those keys was pasted into eight docstrings of
  `algorithms/base.py`, `utils.py`, `metrics.py` and
  `algorithms/plots.py`, which name the type now. The copies left out
  `min_population_size`, `n_jobs` and `genetic_opt_version`, and said
  that `population_idx` starts with 0, where it starts with 1.
- `fit`, the two load functions, `serialize_fit_result`, `FitSaver` and
  `plot_genetic_algo_metrics` are annotated with the new types.
- `metrics.py`: the docstring of `Metric` lists `size`.
- Added `test_the_fit_result_types_name_the_keys_of_each_result` to
  `tests/unit/test_fit_save.py`: the keys of each result are the ones
  its type names.

### v0.9.0 - 13th October 2026

- `src/genetic_opt/logs.py` no longer sets up logging when the
  package is imported. It added a handler on the standard output to
  the logger `genetic_opt`, set its level to `INFO` and stopped it
  passing records to the root logger. Now `logger` is
  `logging.getLogger("genetic_opt")` and nothing else, so a program
  that wants the progress of a run configures logging itself.
  - Removed `get_app_logger`, `LOG_FORMAT` and `LOG_DATEFORMAT`, and
    with them the environment variables `LOG_FORMAT` and
    `LOG_DATEFORMAT`, which the package read and nothing documented.
- `README.md`: added the section "Logs", with how to see the progress
  of a run.
- Added `test_the_package_leaves_logging_to_the_application` to
  `tests/unit/test_functions.py`. The two tests that attached `caplog`
  to the package logger by hand (there and in
  `tests/unit/test_files.py`) read it through the root logger.

### v0.8.1 - 13th October 2026

- A second `fit` on the same `GeneticAlgorithm` keeps the scores of
  the first, so a chromosome met again is not scored again. Since
  0.7.13 it cleared them, and scoring is the costly part of a run.
  `fitness_func_calls.processed` still counts the current run only:
  the times the fitness function ran in it.
  - `crates/genetic_opt/src/algorithm.rs`: `GeneticAlgorithm` counts
    the chromosomes each run scores.
  - `src/genetic_opt/algorithms/base.py`: `fit` notes how many scores
    the cache held when the run started.
- The tests `a_second_fit_is_the_same_run_again`
  (`crates/genetic_opt/tests/algorithm.rs`) and
  `test_a_second_fit_starts_a_new_run`
  (`tests/unit/test_binary_algs.py`) check that nothing is scored
  twice.

### v0.8.0 - 13th October 2026

- `Chromosome.random_mutate` in `src/genetic_opt/chromosome.py`
  returns a new Chromosome and leaves the one it is called on as it
  was. Before, it changed the genes in place and returned the same
  object, which kept its old score and changed its hash while it
  could be the key of a dictionary. Code that calls it and does not
  use what it returns has to be changed.
  - The new Chromosome has no score and shares the random state of
    the first.
  - `GeneList.random_mutate` and `GeneSet.random_mutate` in
    `src/genetic_opt/gene_collection.py` return a new collection
    too.
  - A `mutation_invariant` of `GeneticAlgorithm` got the same object
    twice, so it compared the mutated Chromosome with itself. It
    gets the one before and the one after now.
- `tests/unit/test_binary_algs.py`:
  - Added `test_mutation_leaves_the_chromosome_as_it_was`.
  - Added
    `test_the_mutation_invariant_gets_the_chromosome_before_and_after`.
  - The other mutation tests read the Chromosome that is returned.

### v0.7.13 - 13th October 2026

- Fixed a second `fit` on the same `GeneticAlgorithm`, which mixed
  the first run into the second. Each `fit` is a new run now:
  - `crates/genetic_opt/src/algorithm.rs`: `fit_with` clears the
    population, the history, the metrics and the scores, and starts
    from the seed again. The second run read the metrics of the
    first to decide when to stop, and joined the old population to
    the new one.
  - `src/genetic_opt/algorithms/base.py`: `fit` clears the same, and
    `self.random_state` starts from the seed again. `historial`,
    `metrics` and the counts of `fit_metrics` kept growing.
  - `README.md`: the gene space of the Python package keeps its own
    random state, so its second run draws other genes. Listed in
    the differences with the crate.
- Added `a_second_fit_is_the_same_run_again` to
  `crates/genetic_opt/tests/algorithm.rs` and
  `test_a_second_fit_starts_a_new_run` to
  `tests/unit/test_binary_algs.py`.

### v0.7.12 - 13th October 2026

- `.claude/rules/00-rule-index.md`: regenerated with
  `programme.merge.rule_index`, so it lists the path-scoped
  `testing-areas` rule added in v0.7.7.


### v0.7.11 - 13th October 2026

- Fixed `GeneticAlgorithm.fit` in
  `src/genetic_opt/algorithms/base.py`: a run whose first population
  has a mean score of 0 stopped at once, as if it had not improved.
  `_get_iteration_improvement` returned the metrics of the first
  generation under the keys of the differences. It returns an empty
  dictionary for it now, and reads the two metrics by name.
- `tests/unit/test_binary_algs.py`:
  - Added `test_fit_goes_on_after_a_first_generation_with_mean_score_0`.
  - Added `test_fit_stops_when_the_mean_score_does_not_change`.
- `README.md`: removed this from the differences with the Rust crate.

### v0.7.10 - 13th October 2026

- Fixed `GeneticAlgorithm.fit` in
  `src/genetic_opt/algorithms/base.py`: a negative `n_jobs` that
  leaves no core gives one job. The default, -2, raised
  `ValidationException` on a machine with one core. The Rust crate
  already did this for its default.
- `tests/unit/test_binary_algs.py`:
  - Added `test_fit_uses_one_job_when_fewer_are_left`.
  - Added `test_fit_refuses_no_jobs_and_more_jobs_than_cores`.
  - `test_fit_scores_each_chromosome_once` asks for two jobs or for
    the one that a machine with one core allows.
- `crates/genetic_opt/tests/algorithm.rs`: the two tests that asked
  for two threads do the same, through `two_jobs`.

### v0.7.9 - 13th October 2026

- Fixed `GeneSet.select_random` in
  `src/genetic_opt/gene_collection.py`: a set Chromosome built from
  a gene space of its own size got the gene space object as its
  genes, where it now gets a set with every gene of the space.
- `tests/unit/test_binary_algs.py`: added
  `test_a_set_as_large_as_its_gene_space_holds_every_gene`.

### v0.7.8 - 13th October 2026

- Moved the `GeneticAlgorithm` class from
  `src/genetic_opt/algorithms/__init__.py` to
  `src/genetic_opt/algorithms/base.py`. The package file keeps the
  names other projects import from it: `GeneticAlgorithm`,
  `Chromosome` and `Score`.
- Added `src/genetic_opt/algorithms/save.py` with `FitSaver`, which
  creates the folder of a run and writes `experiment_config.yml`,
  the files of `fit_data/` and `fit_plots.jpg`, as `save.rs` does in
  the Rust crate. `GeneticAlgorithm` holds one when it gets a
  `save_path`. The files are the same as before.
- Removed from `GeneticAlgorithm` the attributes `save_as_bson`,
  `serialize_decoded_chromosome_func` and `serialize_gene_func`,
  which `FitSaver` holds now, and the method `_save_fit_result`.
  `save_path` stays.
- `tests/unit/test_imports.py`: added
  `test_the_algorithms_package_keeps_the_names_other_projects_import`.

### v0.7.7 - 13th October 2026

- Added `.claude/rules/testing-areas.md` with the measured times
  that 0.7.5 put in `.claude/rules/testing.md`, which is as it was
  before 0.7.5 again. `programme` pushes `testing.md` to every
  Python project, so an addition there would be overwritten.

### v0.7.6 - 13th October 2026

- Fixed `BinaryGeneticAlgorithm.crossover_func` in
  `src/genetic_opt/algorithms/binary.py`:
  - The cut can fall before the last gene. It never did, because
    `randint` leaves its upper bound out: with 5 genes the cut was
    1, 2 or 3 and is now 1 to 4, as in the Rust
    `single_point_crossover`.
  - Chromosomes of 2 genes are crossed, where the call raised
    `ValueError: low >= high`. With 1 gene the children are copies
    of the parents.
  - The children carry the seed of the run as `random_seed`, where
    they carried 442, and `is_gene_set` from the algorithm.
- A seed gives another run than before 0.7.6, since the cuts are
  drawn from one more position.
- `tests/unit/test_binary_algs.py`:
  - `test_crossover_cuts_at_every_position_between_two_genes`.
  - `test_crossover_of_two_genes_swaps_the_second_one`.
  - `test_crossover_of_one_gene_returns_the_same_genes`.
  - `test_crossover_children_carry_the_seed_of_the_run`.
- `README.md`: the note on `random_seed` says what the Python
  package does.

### v0.7.5 - 13th October 2026

- `.claude/rules/testing.md`: added the section "Measured times",
  with one run of each suite and of a `cargo build` from nothing,
  dated 13th October 2026. The Python unit suite takes 5.2 seconds
  and the Rust build 12.7.

### v0.7.4 - 13th October 2026

- `crates/genetic_opt/src/metrics.rs`:
  - `median` reads the middle of scores that are already sorted,
    in either direction. It copied them and sorted the copy.
  - `variance` takes the mean, which the caller has, where it
    computed it again.
  - Test `median_of_values_sorted_in_either_direction`.
- `crates/genetic_opt/Cargo.toml`: `chrono` is built with its `now`
  feature alone, which is what the name of a run folder needs. The
  lock file went from 102 crates to 89.
- Nothing was timed.

### v0.7.3 - 13th October 2026

- With the level of the `genetic_opt` logger above `INFO`, `fit` and
  the save functions no longer do the work of the lines they do not
  log. The logger starts at `INFO`, so a run that leaves it there
  logs the same lines and does the same work as before.
  - `GeneticAlgorithm.fit` in `src/genetic_opt/algorithms/__init__.py`
    does not format the metrics of each generation, and calls
    `_get_iteration_improvement` once a generation where it called it
    twice.
  - `save_bson`, `save_json`, `save_yaml` and `save_current_figure` in
    `src/genetic_opt/files.py` do not read the size of the file they
    wrote.
- `next_generation_selection` draws the positions of the random
  parents, where it handed the Chromosomes to `RandomState.choice`,
  which copied them into an array each generation. A seed gives the
  same run: on 13th October 2026 six knapsack runs, of seeds 442, 7
  and 2026 with populations of 50 and 31, kept every population of
  every generation.
- Nothing was timed.
- Tests:
  - Added `tests/conftest.py` with the fixture `set_log_level`.
  - `tests/unit/test_binary_algs.py`:
    `test_fit_formats_the_metrics_only_when_they_are_logged`.
  - `tests/unit/test_files.py`:
    `test_a_save_reads_the_file_size_only_when_it_is_logged`.

### v0.7.2 - 13th October 2026

- `crates/genetic_opt/src/algorithm.rs`:
  - The scores already computed are a set of `Individual`, found by
    its chromosome, where they were a map from a copy of the
    chromosome. `score` moves each new chromosome into its
    `Individual`: its genes were copied twice and are not copied now.
  - `score` hashes a new chromosome three times where it hashed it
    four, and one scored before once where it hashed it twice.
  - `measure` and `summary` tell the different chromosomes apart by
    the address of their `Individual`, which equal chromosomes share,
    so the genes of the population are not hashed each generation.
- Nothing was timed. The results of a run do not change.
- Added `the_metrics_count_the_different_chromosomes` to
  `crates/genetic_opt/tests/algorithm.rs`: `n_uniques` of each
  generation against the different chromosomes of its population.
- The crate's version is equal to the package's again: 0.7.1 changed
  `pyproject.toml` alone.

### v0.7.1 - 13th October 2026

- `CLAUDE.md` `## Core Rules`: removed "Update CLAUDE.md Each
  Iteration". Self-Improvement already says to update the file
  when a rule changes. Periodic Reviews is now rule 3. Pushed from
  `programme` v4.159.10.

### v0.7.0 - 13th October 2026

- Each `fit_data_<n>` file holds the metrics of its own generation
  alone, as a list of one under the same key `metrics`. Before, it
  held those of every generation up to its own, so the files of a run
  grew with the square of its generations. Both implementations write
  it: `GeneticAlgorithm._save_fit_result` in
  `src/genetic_opt/algorithms/__init__.py` and `save_generation` in
  `crates/genetic_opt/src/algorithm.rs`.
- `utils.load_fit_result` takes the last of the `metrics` of each
  file, which is the metrics of that file's generation in both
  layouts, so it loads a run saved by any version. A file with an
  empty `metrics` is refused.
- `utils.load_fit_result_file` returns the `metrics` the file holds:
  one for a file saved since this version.
- A version before this one that loads a run saved since gets the
  metrics of the last generation only, with no error. So does
  `downstream`'s own `load_fit_result`, which takes the metrics from
  the last file; an item to change it is in its backlog.
- Measured on 13th October 2026 on a machine in use, a run of 147
  generations of 50 Chromosomes of 300 genes, three loads each. As
  JSON it takes 15.7 MiB where it took 37.5, and loads in 0.51 to
  0.57 seconds; the run saved by 0.6.14 loads in 1.02 to 1.08. As
  BSON it takes 42.4 MiB where it took 98.6, and loads in 0.33 to
  0.37 seconds; the one saved by 0.6.14 loads in 0.64 to 1.37.
- `README.md` says which version changed the files and what an
  earlier version reads from them.
- Tests:
  - `tests/unit/test_fit_save.py`:
    `test_each_file_holds_the_metrics_of_its_generation_alone` and
    `test_load_fit_result_reads_a_run_saved_before_0_7_0`.
  - `crates/genetic_opt/tests/algorithm.rs`:
    `a_run_is_saved_one_file_per_generation` expects one metric in
    the last file, the one of the last generation.

### v0.6.14 - 13th October 2026

- `utils.load_fit_result` reads the bests, the metrics, the fit
  metrics and the fit parameters from the file of the last generation
  only. From every other file it reads the population. Before, it
  built all of them from every file and kept the last.
- A malformed `bests` or `metrics` in a file that is not the last one
  is no longer refused, since it is not read. A missing `population`
  or `population_idx`, and a Score of a population with an unknown
  key, are refused in every file as before.
- `utils.load_fit_result_file` returns what it did.
- Timed on 13th October 2026 on a machine in use, a run of 147
  generations of 50 Chromosomes of 300 genes, three loads each: as
  JSON (37.5 MiB) 1.62 to 1.68 seconds before and 1.20 to 1.24 after;
  as BSON (98.6 MiB) 1.20 to 1.46 before and 0.66 to 0.86 after. The
  rest is parsing the files, each of which repeats the metrics of
  the generations before it.
- `tests/unit/test_fit_save.py`:
  `test_load_fit_result_refuses_a_score_with_an_unknown_key` puts the
  unknown key in a population Score of each file and in a best Score
  of the last file. It put it in a best Score of the first file.

### v0.6.13 - 13th October 2026

- `test_genetic_bag` in `tests/unit/test_binary_algs.py` passes
  `n_jobs=1`. With the default it started one worker process for
  each core but one, for a knapsack of 10 genes.
  `test_fit_scores_each_chromosome_once` still runs with two
  processes.
- `tests/integration/test_rust_layout.py` builds the crate's knapsack
  example once, in the session fixture `knapsack_example`, and both
  tests run the built program. Before, each test called `cargo run`.
  The first build on a machine still compiles the crate and its
  dependencies inside pytest, and the tests are still skipped when
  `cargo` is missing.

### v0.6.12 - 13th October 2026

- `import genetic_opt.algorithms` no longer imports `matplotlib`,
  `bson` and `yaml`. Each is imported by the function that uses it:
  - `src/genetic_opt/files.py`: `load_bson`, `save_bson`,
    `save_current_figure` and `save_yaml`.
  - `src/genetic_opt/algorithms/plots.py`: `set_pyplot_config` and
    `plot_genetic_algo_metrics`.
  - `src/genetic_opt/utils.py`: `load_fit_result_file`, for
    `BSONError`.
- A run that saves and plots nothing imports none of the three, and
  neither does a worker process.
- Timed on 13th October 2026, three runs on a machine in use: the
  import after `numpy` took 0.55 to 0.62 seconds before and 0.10 to
  0.11 after.
- Removed `_NoAliasSafeDumper` from `files.py`; `save_yaml` builds the
  class itself.
- Added `tests/unit/test_imports.py`: 2 tests that import the package
  in a new interpreter and check none of the three is loaded.

### v0.6.11 - 13th October 2026

- `GeneticAlgorithm._sort_population` in
  `src/genetic_opt/algorithms/__init__.py` no longer calls `joblib`'s
  `Parallel` when every Chromosome waiting for a score is already in
  the cache. `iter_func` is not called for that step either.
- Timed on 13th October 2026, one run on a machine in use: a
  `Parallel` call over an empty list took about 5 milliseconds the
  first time and 0.4 to 1 after that with `n_jobs=-2`, and 0.05 with
  `n_jobs=1`. No `fit` was timed.
- Added `test_sorting_starts_no_workers_when_no_chromosome_is_new` to
  `tests/unit/test_binary_algs.py`.

### v0.6.10 - 13th October 2026

- `AbstractGeneSpace.select_random` in `src/genetic_opt/gene_space.py`
  states what it returns: one gene with no `n`, a collection of `n`
  genes for an `int`, also for `n=1`, and a nested collection with
  the shape `n` for a tuple. `BinaryGeneSpace` already did this.
- `_draw_genes` in `gene_collection.py` still asks for one gene with
  no `n`, so a gene space that returns a single gene for `n=1` keeps
  working.
- Added `tests/unit/test_gene_space.py`: 7 tests of the three cases
  on `BinaryGeneSpace`.

### v0.6.9 - 13th October 2026

- `src/genetic_opt/gene_collection.py`:
  - `GeneList.random_mutate` and `GeneSet.random_mutate` decide which
    genes mutate with one draw for the whole collection, and get the
    new genes with one call, `gene_space.select_random(n=<count>)`,
    instead of one call for each gene.
  - `GeneList.select_random` and `GeneSet._complete_genes` draw the
    genes they need with one call too.
  - Added `_draw_genes`, which all four use. For one gene it calls
    `select_random()` with no `n`. With a `gene_space_func` it still
    calls that function once for each gene.
- A gene space used this way must return `n` genes from
  `select_random(n=<int>)`, as the docstring of `AbstractGeneSpace`
  already says. One that returns a single gene for every `n` worked
  before and now fails.
- Timed on 13th October 2026, one run on a machine in use. Mutating a
  list of 200 genes at probability 0.05: 168 microseconds before, 42
  after. A list of 10 genes: 9 before, 13 after. A knapsack `fit` of
  60 generations, 200 Chromosomes of 200 genes, one process: 2.3
  seconds before, 0.9 after.
- What a seed produces did not change with `BinaryGeneSpace` and
  `numpy` 1.26.4: the same two runs give the same history before and
  after. Nothing checks that for another gene space.
- Added six tests to `tests/unit/test_binary_algs.py`: list mutation
  with one call, with probability 0 and 1, set mutation, a Chromosome
  built from a gene space, and mutation through a `gene_space_func`.

### v0.6.8 - 13th October 2026

- `GeneticAlgorithm.fit` with no `save_path` builds its result once,
  when the run ends, instead of after every generation. Building it
  decodes the whole population, and every result but the last was
  thrown away. With a `save_path` nothing changes: each generation is
  still saved.
- `Chromosome.id` is computed on first use and kept; `random_mutate`
  clears it. `__hash__` and `__eq__` no longer hash the genes on every
  call. Code that changes `genes` some other way must build a new
  Chromosome to get a new id.
- Neither change alters what a seed produces: a knapsack run of 61
  generations gives the same history before and after.
- Added to `tests/unit/test_binary_algs.py`:
  `test_fit_without_a_save_path_decodes_the_population_once` and
  `test_a_mutated_chromosome_gets_a_new_id`.
- The crate's version had stayed at 0.6.6 when v0.6.7 bumped
  `pyproject.toml` alone. `Cargo.toml` and `Cargo.lock` now read 0.6.8.

### v0.6.7 - 13th October 2026

- Rotated changelog: archived 18 entries to `changelog/2023.md`, `changelog/2024.md`.


### v0.6.6 - 13th October 2026

- Added `.claude/rules/00-rule-index.md`, generated by
  `programme.merge.rule_index`: the list of this project's rules
  that load only when a matching file is read. It names one rule,
  `testing`.


### v0.6.5 - 12th October 2026

- Version lines brought back in step: v0.6.4 bumped `pyproject.toml`
  alone, leaving `crates/genetic_opt/Cargo.toml`, its `Cargo.lock`
  and `uv.lock` at 0.6.3. All four now read 0.6.5. No code change.


### v0.6.4 - 12th October 2026

- `.gitlab-ci.yml`: the publish job installs `build==1.6.1` and
  `twine==7.0.0` instead of whatever version is newest that day. The
  job holds `CI_JOB_TOKEN`. Versions are the latest on
  https://pypi.org/pypi/build/json and
  https://pypi.org/pypi/twine/json, read 12th October 2026. Same
  line as the shared `python-base` copy in `market_wrapper` v7.25.2.


### v0.6.3 - 12th October 2026

- `algorithms/__init__.py`:
  - With a `save_path`, `fit` serializes only the last population
    after each generation. It serialized every earlier population
    again and wrote the last one, so the work grew with the square of
    the generations. The saved files are unchanged.
  - With a `save_path` and `plot_metrics`, `fit` writes
    `fit_plots.jpg` once, when the run ends, as its docstring says.
    It built and wrote the figure after every generation. A run that
    is interrupted now leaves no plot.
  - The `fit` docstring says that a fitness function which is a bound
    method, or uses `self`, takes the whole algorithm to each worker
    process.
- `Chromosome.random_state` is built on first use. `fit` passes the
  algorithm's own state, so a Chromosome of a run no longer builds
  one or carries it when pickled.
- `examples/binary.py`: the decode and fitness functions of
  `GeneticBag` use `weights`, `values` and `capacity` and not `self`,
  so the bag with its population and history is no longer sent to the
  worker processes.
- Added tests: 1 in `tests/unit/test_fit_save.py`, which also compares
  the loaded history with the one `fit` returns, and 2 in
  `tests/unit/test_binary_algs.py`.
- `backlog.md`: removed the four items above.


### v0.6.2 - 12th October 2026

- `GeneticOptException` and its subclasses no longer log their
  message at ERROR level when they are created, so a caught exception
  prints nothing. The message is unchanged for the code that catches
  it.
- The errors raised when a Chromosome is built no longer carry
  `locals()` as `processing_object`, which put the genes and the gene
  space in the message. The two size errors name both sizes instead.
- `GeneticAlgorithm` keeps the scores already computed by the `repr`
  of the Chromosome, not by `Chromosome.id`. Two different
  Chromosomes with one id shared a score.
- `Chromosome.id` calls `md5` with `usedforsecurity=False`.
- `crates/genetic_opt/src/problems.rs`: `Knapsack` adds weights and
  values as `u64`. A sum over `u32::MAX` panicked in a debug build
  and wrapped in a release build, where a wrapped weight passed the
  capacity check.
- `pyproject.toml`: `pyyaml`, `pytest` and `ruff` are held below
  their next major version, as the other dependencies are.
- Added tests: 2 in `tests/unit/test_functions.py`, 1 in
  `tests/unit/test_binary_algs.py` and 1 in
  `crates/genetic_opt/tests/algorithm.rs`.
- `backlog.md`: removed the four items above.


### v0.6.1 - 12th October 2026

- `files.py`:
  - `save_yaml` writes with PyYAML's `SafeDumper`, so
    `experiment_config.yml` is read back by a safe loader. An object
    that is not plain data in `experiment_config()` now raises
    `yaml.representer.RepresenterError` and no file is written. It
    was written as a `!!python/object` tag.
  - `save_yaml` no longer replaces `ignore_aliases` on PyYAML's shared
    `Dumper` class, which changed the YAML output of the whole
    process.
  - Added `create_new_folder`: it creates a folder that did not
    exist, adding `_2`, `_3` and so on to the name while one exists.
- The folder of a run is created when the run is set up, in
  `GeneticAlgorithm.__init__` and at the start of the crate's `fit`.
  Two runs with one experiment name started in the same second
  shared a folder and overwrote each other's files. The second one
  now gets `<UTC date and time>_2`.
- An `experiment_name` that is an absolute path or holds `..` is
  refused when saving, with `ValidationException` in Python and
  `Error::Validation` in the crate. It wrote outside the save path.
  A name with folders in it, such as `group/name`, is still accepted.
- `utils.py`:
  - `load_fit_result` and `load_fit_result_file` raise
    `ValidationException` naming the file when its content is not the
    one of a fit result file. They raised a raw `KeyError`,
    `TypeError` or decoding error.
  - Added the parameter `max_file_bytes` to both: a larger file is
    refused without being read. There is no limit by default.
- Added tests: 5 in `tests/unit/test_files.py`, 6 in
  `tests/unit/test_fit_save.py` and 2 in
  `crates/genetic_opt/tests/algorithm.rs`.
- `backlog.md`: removed the four items above and added one to decide
  whether the loader refuses unknown keys.


### v0.6.0 - 12th October 2026

- Fixed `space_points` and `exploration_percentage` in
  `fit_metrics.fitness_func_calls`, in both implementations.
  `space_points` was the number of different genes, so a knapsack run
  of 10 objects reported 2 and an exploration of 7500. It is now the
  number of different chromosomes: every list of that length, or every
  set of that many different genes. The same run reports 1024 and
  17.29.
- `space_points` is now a decimal number, not an integer: `f64` in the
  crate's `FitnessCalls` and `float` in the Python fit result. A count
  too large for one is infinite, with an exploration of 0. A JSON file
  written by the crate holds `null` for it.
- Added `get_space_points` to `metrics.py`.
- Added tests: `space_points_counts_lists_and_sets` in
  `crates/genetic_opt/src/algorithm.rs`,
  `test_get_space_points_counts_lists_and_sets` in
  `tests/unit/test_binary_algs.py`, and checks of the count in three
  existing tests, one of them the Rust run loaded by Python.
- `backlog.md`: removed the item about the Rust crate not saving
  `fit_plots.jpg`. The crate stays without the plot.


### v0.5.2 - 12th October 2026

- `pyproject.toml`: the build backend is now `hatchling>=1.32.4,<2.0.0`.
  It had no version bound. 1.32.4 was the newest release on PyPI on
  12th October 2026.
- `backlog.md`: removed the item about the `publish-package` job of
  `.gitlab-ci.yml` installing `build` and `twine` with no version.
  The file is the shared `python-base` one, so the item moved to the
  backlog of `programme`.


### v0.5.1 - 12th October 2026

- Fixed a panic in the Rust crate: `fit` with `population_size = 0`
  and `min_population_size = 0` read the first chromosome of an empty
  population. It now returns `Error::Validation`.
- `fit` refuses a `crossovers_prop`, `besties_prop` or `mutate_prob`
  outside 0 to 1, a NaN included, in both implementations:
  `Error::Validation` in the crate and `ValidationException` in the
  Python package, which also refuses a `population_size` under 1.
  Before, no value of the three was checked.
- Added tests for these cases: `bad_parameters_are_refused` in
  `crates/genetic_opt/tests/algorithm.rs` and
  `test_fit_refuses_parameters_out_of_range` in
  `tests/unit/test_binary_algs.py`.


### v0.5.0 - 12th October 2026

- The package now needs Python 3.14 or later: `requires-python` in
  `pyproject.toml` went from `>=3.11` to `>=3.14`. `uv.lock` is
  resolved for that range. `downstream`, the one project that installs
  this package, already needs 3.14.
- Removed the quotes from the 9 type hints that name their own class,
  in `algorithms/__init__.py`, `chromosome.py`, `gene_collection.py`
  and `metrics.py`. Python 3.14 reads a type hint only when asked for
  it, so they are no longer needed.
- `.gitlab-ci.yml`: the `publish-package` job runs on
  `python:3.14-slim`, from `python:3.12-slim`.


### v0.4.3 - 12th October 2026

- Decided that the Python package gets no binding to the Rust crate
  (PyO3, maturin). The crate stays as a Rust library and the package
  stays pure Python. `roadmap.md` records the reasons under "What NOT
  to do", and `README.md` says it in the section on the crate.
- `backlog.md`: removed the two items this settles, the binding and
  whether to keep the crate.


### v0.4.2 - 12th October 2026

- Fixed `fit_metrics.fitness_func_calls` in the fit result of the
  Python package. `total` was the number of hits of a method cache and
  `percent_processed` divided the misses by the hits. Now `total` is
  the number of Chromosomes that needed a score, `processed` the times
  the fitness function ran, `cached` their difference and
  `percent_processed` is `100 * processed / total`, as in the Rust
  crate. `README.md` no longer lists it as a difference.
- `GeneticAlgorithm.get_chromosome_score` is no longer wrapped in
  `functools.cache`, which kept every Chromosome and the algorithm
  itself alive. It reads and fills `_chromosome_cache`, which already
  held the same scores. The sort of the population and the fit result
  read `Chromosome.score` directly.
- `tests/unit/test_binary_algs.py`: 3 tests, for the counters, for
  `get_chromosome_score` and for the algorithm being freed.
- `ruff check src tests` reports nothing, from 56 findings. The commit
  hook checks every line of a changed file, so this could not be a
  release of its own. No behaviour changes in it:
  - A parameter with the default `None` is now typed `X | None` (45
    places).
  - Import order, `collections.abc` imports, three `pass` statements
    after a docstring, and the two nested `if` of the invariant
    checks in `algorithms/__init__.py`.
  - Removed `from __future__ import annotations` from `gene_space.py`
    and `gene_collection.py`.
  - Every file under `src` and `tests` has been through `ruff format`.


### v0.4.1 - 12th October 2026

- Registered the project in `programme` and added the files its
  projects carry:
  - `CLAUDE.md`, and `.claude/` with `settings.json` and the rules
    `committing`, `testing` and `versioning`.
  - `roadmap.md`, as a stub with no direction in it.
  - `.pre-commit-config.yaml`, `.pre-commit-scripts/` and
    `scripts/changelog-add.sh`. A commit now runs `ruff`, the
    changelog and version guards, and `cargo fmt --check` and
    `cargo clippy -D warnings` when a file of the crate changes.
  - `.python-version`: 3.14.
  - `.gitattributes`.
- `.gitignore` and `.gitlab-ci.yml` replaced by the `python-base`
  ones. `.gitignore` keeps `/.run/`, `*/data/` and `target/`, and now
  covers `.venv/` and `.env*`. The package is published by the manual
  job `publish-package`, offered only on a `vX.Y.Z` tag that matches
  the version; `build-wheel` is gone.
- Removed the dependency on `bson`. It does not build on Python 3.14,
  and `files.py` already used the `bson` module that `pymongo`
  installs in the same folder.
- Tests moved to `tests/unit/` and `tests/integration/`.
  `test_rust_layout.py` is the integration suite and carries the
  `integration` marker, registered in `pyproject.toml` with
  `testpaths`.
- `changelog.md`: version headers now start with `v`, which the
  changelog guards need.


### v0.4.0 - 12th October 2026

- Added the Rust crate `crates/genetic_opt`: the algorithm of this
  package written in Rust. The Python package does not use it yet.
  - `Problem`: trait a problem implements. Its genes, fitness
    function, crossover and decoding, with defaults for the first
    population and for the mutation.
  - `GeneticAlgorithm`: runs a `Problem` with the selection of
    `algorithms.GeneticAlgorithm`. The fitness function runs on
    several threads, once per different chromosome.
  - `FitConfig`, `FitResult`, `Metric`, `FitMetrics`, `Score`,
    `Chromosome`: the parameters and the results of a run.
  - `SaveConfig`: saves a run as `experiment_config.yml` and one
    `fit_data/fit_data_<n>` file per generation, BSON or JSON, in the
    layout `utils.load_fit_result` reads. No plot is saved.
  - `problems::Knapsack` and the example program `knapsack`: the
    problem of `examples.binary.GeneticBag`.
  - 12 tests.
- The version of the crate is kept equal to this package's.
- Added `tests/test_rust_layout.py`: the example program saves a run
  as BSON and as JSON, and `utils.load_fit_result` loads it. Skipped
  without `cargo`.
- `README.md`: added the section "Rust crate", with the differences
  between the two implementations.
- `.gitignore`: added `target/`.


### v0.3.0 - 12th October 2026

- Removed the dependency on `cpinto`, and the `gitlab_cpinto` index
  with it. The functions used from it were copied from `cpinto`
  0.3.11 into this package:
  - Added `files.py`: `ensure_folder_format`, `get_file_extension`,
    `get_files_inside_folder`, `load_bson`, `load_json`, `save_bson`,
    `save_json`, `save_yaml`, `save_current_figure`, and the helpers
    they call.
  - Added `functions.py`: `identity_func`, `format_bytes`,
    `format_seconds`, `now_for_file_path`, `time_it_with_logger`.
  - `logs.py`: added `get_app_logger` and `log_format`.
  - `algorithms/plots.py`: added `set_pyplot_config`.
- `exceptions.py`:
  - `GeneticOptException` is a direct subclass of `Exception`, no
    longer of `CPintoException`. It keeps the message format and the
    error log, and loses the parameters `logger` and `logger_level`.
  - Added `ValidationException`, raised where `cpinto`'s was.
- Differences with the `cpinto` functions:
  - `get_app_logger` configures its own logger only, not the root
    logger.
  - `now_for_file_path` is always UTC. The `TIMEZONE` environment
    variable is no longer read.
  - `bson`, `matplotlib` and `yaml` are imported at the top of
    `files.py`, not inside each function.
- Added `pyyaml` as a dependency. `fit` with a `save_path` needed it
  and failed without it, since `cpinto` did not install it.
- Added `[tool.ruff]` to `pyproject.toml`. Without it, `ruff` run from
  another folder took that folder's settings and removed the quotes
  from type hints, which Python 3.11 to 3.13 cannot import.
- Removed `from __future__ import annotations` from
  `algorithms/__init__.py`, `chromosome.py` and `metrics.py`.
- Added unit tests:
  - `tests/test_files.py`: 12 tests.
  - `tests/test_functions.py`: 15 tests.
  - `tests/test_fit_save.py`: a `fit` saved as BSON and as JSON, then
    read back with `utils.load_fit_result`.


### v0.2.13 - 12th October 2026

- Fixed `algorithms.GeneticAlgorithm.mutate`: every Chromosome mutated
  in the same positions. Each one drew from its own `RandomState`, and
  they all shared one seed (442 from `BinaryGeneticAlgorithm`'s
  crossover, the algorithm's seed from `init_population`). The draws
  now come from the algorithm's `random_state`.
- `chromosome.Chromosome.random_mutate`: added the parameter
  `random_state`. Default to the Chromosome's own, as before.
- Added the test `test_mutation_differs_between_chromosomes`.
- A `fit` with a given seed no longer gives the populations it gave
  before this version.
- `chromosome.py` was reformatted by the pinned `ruff`.


### v0.2.12 - 12th October 2026

- Fixed `algorithms.GeneticAlgorithm._sort_population`: with `n_jobs`
  above 1, the scores computed by the worker processes were discarded
  and the main process computed every one again, one at a time. A `fit`
  of the `GeneticBag` example with 4 jobs called the fitness function
  267 times for 132 Chromosomes. The workers' scores are now kept, and
  equal Chromosomes in one generation are scored once.
- Added `algorithms._score_chromosome`, the function sent to the
  workers. Only the fitness function travels with it, not the whole
  `GeneticAlgorithm`.
- `__version__` is read from the installed package. It was fixed at
  `0.2.9`, which is what `fit` wrote as `genetic_opt_version`.
- Added `pytest` to `dev`, and the test
  `test_fit_scores_each_chromosome_once`.
- `algorithms/__init__.py` was reformatted by the pinned `ruff`.


### v0.2.11 - 25th August 2026

- Migrated `pyproject.toml` from Poetry to uv (PEP 621 `[project]` +
  `[dependency-groups]`, `hatchling` build backend). The old Poetry
  setup had no dev dependencies and no pinned formatter, so every
  file was reformatted by whichever `ruff` was newest on the day it
  was last touched.
- Added `ruff>=0.16.4` to `dev` so the per-edit formatter is pinned.
- Removed `poetry.lock` (superseded by `uv.lock`).


### v0.2.10 - 23rd August 2026

- `.gitlab-ci.yml`: publish job now uploads to `${CI_PROJECT_ID}`
  instead of the hardcoded shared `cpinto` registry project
  (42232103) — own-registry publish direction, programme
  backlog 2026-08-22.
- Copied all 14 previously published releases (0.1.0 through
  0.2.9) from the shared registry to `genetic-opt`'s own GitLab
  package registry (project 48069240), sha256-verified against
  the source before and after.


### v0.2.9 - 14th September 2024

- Fix in `chromosome.Chromosome.__repr__` when `self.is_gene_set`: previous
  representation of the object was not unique, and thus, all Chromosome 
  comparisons broken, even the `Chromosome.id` method.


### v0.2.8 - 11th September 2024

- Changes in `utils`:
  - Added the parameter `remove_duplicates` in the functions 
  `load_fit_result` and `load_fit_result_file`.


### v0.2.7 - 10th August 2024

- Changes in `algorithms.GeneticAlgorithm.fit`:
  - Added the parameter `min_population_size`. 
  - Removed an unreachable check about Chromosomes with no scores. 


### v0.2.6 - 30th July 2024

- Changes in `algorithms.GeneticAlgorithm`:
  - Added the parameters `mutation_invariant` and `crossover_invariant`.
  - Added the inner functions `_crossover` and `_mutate`.
  - Methods `no_improvement_condition` and `no_exit_condition` are not
    static anymore. They take the self instance as a parameter, not the
    improvement dict.
  - Added Some documentation for the method `no_improvement_condition`.
- Added the exception `InvariantException`.


### v0.2.5 - 25th July 2024

- Changes in `algorithms.GeneticAlgorithm`:
  - Added the parameter `save_as_bson`, default to `True`.
  - Method `_save_fit_result` will save a file for each population instead of
    one big, single file.
    - Changed the format of these files. Removed the key `historial`, that
      will be generated by appending the different `population`s.
- Module `utils`:
  - Added the function `load_fit_result_file`.
  - Changed the function `load_fit_result`.
- Added dependencies:
  - `cpinto ^0.3.9`.
  - `bson ^0.5.10`.
  - `pymongo ^4.8.0`.


### v0.2.4 - 6th June 2024

- Fixes in `GeneticAlgorithm`: 
  - Fix in the way `self._chromosome_cache` is handled.
  - Method `_sort_population` will prevent having non-calculated scores.
  - Removed the parameter `fitness_timeout`.
- `README.md` updated.


### v0.2.3 - 1st June 2024

- Fixes in `gene_collection`: `GeneList` and `GeneSet` were randomly setting
  the `genes` ignoring the values received.


### v0.2.2 - 31st May 2024

- Changes in `GeneticAlgorithm`:
  - Added the method `get_init_population`, allowing manipulating the
    functions used to get this population from the `GeneSpace`.
  - Inner method `_get_fitted_data` returns the key 
    `fit_metrics.total_fit_time.raw` rounded to two decimals.


### v0.2.1 - 29th May 2024

- Added logs when initializing `GeneticAlgorithm`. It will log the size
  of the `GeneSpace` used.
- Fix in the output type of `BinaryGeneSpace.select_random`.


### v0.2.0 - 27th May 2024

- Removed the `core` module. Scripts inside it moved outside.
- Class `core.gene_space.GeneSpace` doesn't inherit from `set` anymore.
  It isn't a generator either. It is an ABC now, and the methods 
  `select_random` and `__len__` have to be overwritten.
  - Original class renamed to `AbstractGeneSpace`.
  - Added class `BinaryGeneSpace`.
- Class `BinaryGeneticAlgorithm` moved from `algorithms.core` to 
  `algorithms.binary`.
- Tests updated. No test was added.

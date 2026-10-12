
## Changelog - Genetic-Opt


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


### v0.1.17 - 14th May 2024

- Class `GeneticAlgorithm`:
  - Added the parameter `fitness_timeout`.
  - Added the method `experiment_config`.
  - Method `fit` will save a `experiment_config.yml` file with the fit 
    configuration.


### v0.1.16 - 11th May 2024

- Python version updated to `^3.11`
- `Score` key `extra_metrics` also allow `list` as type.
- Added documentation for `GeneticAlgorithm.no_improvement_condition`.


### v0.1.15 - 20th April 2024

- Changes in `GeneticAlgorithm`:
  - Added the method `default_fit_callback`.
  - Added the static methods `no_exit_condition` and `no_improvement_condition`.


### v0.1.14 - 20th March 2024

- Dependency on `cpinto` updated to `0.3.4`.
- Removed the module `utils`.


### v0.1.13 - 12th March 2024

- Changes in the `Metrics` object:
  - Key `best` is not a tuple anymore. Now it is a dictionary with keys
    `score`, `result`, `encoded`.
- Changes in all the objects that use `Metrics` due to this change:
  - Minor inner changes in `GeneticAlgorithm`.
  - Changes in the functions of `core.algorithms.utils`.
  - Changes in `core.algorithms.plots` when handling those `Metrics`.


### v0.1.12 - 11th March 2024

- Changes in `Geneticalgorithm._get_fitted_data`:
  - Added the keys `space_points` and `exploration_percentage` in the
    `fit_metrics` dictionary.
  - Changes in the documentation and the `utils` functions due to this.
  - Changes in `plots.plot_genetic_algo_metrics` to show these new keys.


### v0.1.11 - 10th March 2024

- Changes in `GeneticAlgorithm`:
  - Method `fit` will save each iteration result after calculating it.
  - Changed the response of this `fit`: key `result` changed to `bests`.
  - Changes all functions in the `utils` module to save and load this 
    dictionary.
- Fix in `Chromosome.from_dict`: it wasn't using properly the 
  argument `is_gene_set`.


### v0.1.10 - 9th March 2024 

- Module `core`:
  - Added the parameter `size` to `metrics.Metric`.
  - Changes in `algorithms.plots.plot_genetic_algo_metrics`:
    - Parameter `other_keys` type change: it is now a dictionary instead 
      of a list of tuples.
    - It shows the populations size.


### v0.1.9 - 8th March 2024 

- Changes in `core.algorithms`:
  - Added the function `plots.plot_genetic_algo_metrics`.
  - Added the parameters `plot_metrics` and `other_metrics_to_plot` to the 
    function `GeneticAlgorithm.fit`.
- Dependency on `cpinto` updated to `v0.3.2`.


### v0.1.8 - 6th March 2024

- Change in the `Score` object: added the key `name`.
- Removed the parameter `score_name` from `GeneticAlgorithm`.
- Added a dependency on `matplotlib`, but it is not used for now.


### v0.1.7 - 5th March 2024

- Added the method `from_dict` to the classes `Chromosome` and `Metrics`.
- Added the function `utils.load_fit_result`.
- Fix saving the `historial` key in the function `utils.serialize_fit_result`.


### v0.1.6 - 4th March 2024

- Added the method `to_dict` to the classes `Chromosome`, `Score` and `Metrics`.  
- Dependency on `cpinto` updated to `v0.3.0`.
- Class `GeneticAlgorithm`: 
  - Added the parameters `save_path` and `serialize_decoded_chromosome_func`.
  - Added the method `_save_fit_result`.
  - Some documentation updated.
- Added the function `utils.serialize_fit_result`.


### v0.1.5 - 29th February 2024

- Class `GeneticAlgorithm`: 
  - Method `init_population`:
    - Bug fixed: all chromosomes of the initial population were the 
    same when using joblib.
    - Initial population pick is now faster.
  - Added the value `genetic_opt_version` in the metrics returned, inside 
    the section `fit_metrics`.
- Added the parameter `n` to `GeneSpace.select_random`. 
- Classes `Chromosome` and `GeneCollection`s are compatible with numpy arrays
  when receiving the `genes` parameter.


### v0.1.4 - 21st February 2024

- Class `GeneticAlgorithm`: 
  - Changes in the method `_get_fitted_data`:
    - Added the parameter `n_jobs`. Now it appears in the metrics data.
    - Within the result dictionary of the summary, the part of `bests_5`
    now includes only non-unique chromosomes.
- Function `metrics.get_population_metrics` rounds up the received 
  `fitting_seconds` to 2 decimals.


### v0.1.3 - 14th February 2024

- Added `joblib` dependency.
- Class `GeneticAlgorithm`: 
  - Added the parameter `n_jobs` with a default value of `-2` to the methods:
    - `fit`.
    - `init_population`.
    - `next_generation_selection`.
    - `_sort_population`.
- `Chromosome.__hash__` maximum length reduced to 30. 


### v0.1.2 - 13th February 2024

- Class `GeneticAlgorithm`: 
  - Included the parameter `iter_func` inside the main iterations:
    - Added the parameter in the methods `init_population`, 
    `next_generation_selection` and `_sort_population`.
  - Method `init_population` is measured better internally.
  - Added the inner parameter `_chromosome_cache`.
  - Functions `identity_func`, `no_exit_condition` and 
    `no_improvement_condition` are now outside of this class.
- `Chromosome.__hash__` has a maximum length of 100 instead of 15. 


### v0.1.1 - 12th February 2024

- Class `GeneticAlgorithm`: 
  - Added the parameter `extra_config`.
  - Inner `fitness_func` renamed to `algo_fitness_func`.
- Value of `Score` changed to float instead of integer.
- Fix in the `init` method of `GeneSet` and `GeneList`.
- Improved the documentation of `core.gene_space.GeneSpace`.


### v0.1.0 - 27th July 2023

- First release.

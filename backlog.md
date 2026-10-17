# Backlog - Genetic-Opt

### 2026.10.16 (v1.0.0 scan)

#### Refactoring

- [ ] (LOW, S) `src/genetic_opt/algorithms/base.py:306-315,466`: `plot_metrics` and `other_metrics_to_plot` only apply with a `SaveConfig`; move them into it.
- [ ] (LOW, S) Repeated defaults: `next_generation_selection` (`base.py:561-568`) repeats 0.7/0.6/0.05 from `FitConfig`; `n_jobs=-2` repeated at `base.py:506,567,714`; `fit_result.py:205` hard-codes "at most 5" instead of citing `N_BESTS`.
- [ ] (LOW, S) `src/genetic_opt/files.py:143-170`: `save_current_figure` (matplotlib) belongs beside `algorithms/plots.py`; its `clear_fig`/`close_fig` arguments are never passed.
- [ ] (LOW, S) `src/genetic_opt/algorithms/plots.py:71-135`: the legend keyword arguments are copied four times.
- [ ] (LOW, S) `src/genetic_opt/gene_collection.py:130,206`: `self.size` set before `super().__init__` sets it again; class docstrings at 52-56, 104-108, 178-182 are near copies.
- [ ] (LOW, S) `crates/genetic_opt/examples/knapsack.rs:19-38` and `numbers.rs:115-134`: argument parsing and printing copied; an unknown format (`jsno`) silently saves BSON instead of being refused.
- [ ] (LOW, M) `crates/genetic_opt/tests/algorithm.rs:70-133`: the test `Numbers` problem repeats `examples/numbers.rs:58-107`; five `Problem` impls share boilerplate.
- [ ] (LOW, S) `src/genetic_opt/algorithms/base.py:240`: crossover-invariant error says "mutated to"; should say "crossed to".
- [ ] (LOW, S) `src/genetic_opt/files.py:75-81`: `get_file_size` returns `None` by falling off the end.
- [ ] (LOW, S) Google-style `Args:`/`Returns:` docstrings where the project uses Sphinx: `fit_result_io.py:30,101,240`, `metrics.py:64,109,143`, `chromosome.py:86,189`, `algorithms/plots.py:47-56`.
- [ ] (LOW, S) Type hints: `score.py:9-10` and `chromosome.py:156` need `| None`; missing annotations in `functions.py:10,69`, `files.py:131,173`, `chromosome.py:110`, `algorithms/binary.py:28`, and `-> None` on `__init__`s.
- [ ] (LOW, S) `chromosome.py:99` and `metrics.py:88`: `from_dict` builds the base class instead of `cls(...)`.
- [ ] (LOW, S) Stale docstrings: `gene_collection.py:1` ("Gene Space submodule"), `chromosome.py:142-144` (Score as a tuple), `chromosome.py:188` (missing `is_gene_set`); no module docstring in `fit_result_io.py`, `algorithms/binary.py`, `examples/binary.py`, `score.py`; no class docstrings in `exceptions.py:8,29,33`; `base.py:613` `_get_fitted_data` returns a `FitResult` and could be named so.
- [ ] (LOW, S) Dead parameters: `exceptions.py:9-23` `processing_object` and `functions.py:28` `format_seconds(only_hours=...)` are used only by tests.
- [ ] (LOW, S) `README.md:40-41,47,65-66,98-102,126-127`: "Before 0.x.0" history notes belong in the changelog now that the version is 1.0.0.

#### Test coverage

- [ ] (HIGH, S) `tests/integration/test_rust_layout.py:74-86`: a Rust run loaded in Python checks only a few fields. Check every key and value type against the `FitResult` TypedDicts (as `tests/unit/test_fit_result.py` does for Python runs): the other `fit_parameters` keys, `total_fit_time`, `genetic_opt_version`, `percent_processed`, `cached`, `exploration_percentage`, `last_population`, every Metric field, and each chromosome's `score_time` and `random_seed`.
- [ ] (MED, S) `tests/integration/test_rust_layout.py:63-118`: no Rust run with `extra_config` is loaded, `load_fit_result_file` is never called on a Rust file, and `experiment_config.yml` is only checked to exist.
- [ ] (MED, S) Infinite `space_points` is written as JSON `null` by Rust (`algorithm.rs:583`) and `Infinity` by Python (`metrics.py:192`); Python then loads `None` where its type says float. Decide one form and test it.
- [ ] (MED, S) NaN fitness is untested in both: Python leaves NaN scores mid-population after sorting (`base.py:753-756`); Rust's reversed `total_cmp` (`algorithm.rs:255-262`) would rank NaN best; `no_improvement_condition` (`base.py:303`) never fires on a NaN mean. Decide the behaviour, then test it.
- [ ] (MED, S) `src/genetic_opt/gene_collection.py:230`: `GeneSet.random_mutate` iterates `list(self.genes)`, whose order for string genes changes between interpreter launches (hash randomization), so a seed may not reproduce a set-chromosome run. The seed test (`_bag_run_genes` in `tests/unit/algorithms/test_base.py`) covers only int lists.
- [ ] (MED, S) Python `fit` is never run with `population_size=1`, `crossovers_prop=0`, or `crossovers_prop=besties_prop=1` (`base.py:587-599`); the crate covers these at `tests/algorithm.rs:407`.
- [ ] (MED, S) `iter_func` (`base.py:348,408,744`) is never passed in any test.
- [ ] (MED, S) `ones_algorithm` in `tests/unit/conftest.py`: the unit suite saves and loads only list chromosomes; set chromosomes are covered only by the cargo-gated integration suite.
- [ ] (MED, S) `load_fit_result_file` (`tests/unit/test_fit_result.py`, `tests/unit/algorithms/test_save.py`) is tested only on JSON, never with `remove_duplicates`, `max_file_bytes`, BSON or a malformed file.
- [ ] (MED, S) `test_fit_saves_each_generation_and_loads_it_back` in `tests/unit/algorithms/test_save.py`: history equality relies on `Chromosome.__eq__` (genes only), so losing `score_time` or `random_seed` on save would pass. Add a direct `Chromosome.to_dict`/`from_dict` round-trip test.
- [ ] (LOW, S) No test for a fitness function that raises inside a worker process (`base.py:742-745`, `n_jobs > 1`).
- [ ] (LOW, S) `fit_result_io.py:66-74`: two files with the same `population_idx` (`fit_data_1.json` and `fit_data_1.bson`) put a generation twice in `history`; untested and not refused.
- [ ] (LOW, S) `score.py:23-26`: `Score.to_dict` drops an empty `name` or `extra_metrics`, so `Score(value=1, extra_metrics={})` does not round-trip equal. Untested.
- [ ] (LOW, S) `algorithms/plots.py:138`: plot title without a score name is untested.
- [ ] (LOW, S) Rust gaps: no `n_generations = 0` test (Python has one in `tests/unit/algorithms/test_base.py`); no saved-chromosome `score_time` check (`tests/algorithm.rs:795-798`); `format.rs:37-44` omits the 0, 60 and 3600 s cases the Python test checks.
- [ ] (LOW, S) Weak assertions: `test_load_fit_result_refuses_a_file_over_the_size_limit` in `test_fit_result_io.py` (truthy `bests`), `test_files.py:170` (only `endswith(" B")`), `test_now_for_file_path_format` in `test_functions.py` (format only, not UTC), `test_a_chromosome_builds_its_random_state_on_first_use` in `test_chromosome.py` (depends on numpy's RandomState pickle size).

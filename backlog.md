# Backlog - Genetic-Opt

### 2026.10.16 (v1.0.0 scan)

#### Performance

- [ ] (MED, M) `src/genetic_opt/algorithms/base.py:435-439,662-665`, `algorithms/save.py:98-107`, `crates/genetic_opt/src/algorithm.rs:556-560`: every generation file holds the population twice (`population` and decoded `last_population`), but the loader reads `last_population` only from the last file. Dropping it changes the file format and how a crashed run is read: needs a decision.
- [ ] (MED, M) `src/genetic_opt/algorithms/base.py:742-745`: a new `joblib.Parallel` is built each generation and `self.fitness_func` is pickled again per batch. Keep one `Parallel` open for the whole `fit` (not timed).
- [ ] (LOW, S) `src/genetic_opt/algorithms/base.py:736,750`: `repr(chromosome)` computed twice per unscored chromosome (and sorts the genes for a set). Keep the key from the first loop.
- [ ] (LOW, S) `src/genetic_opt/metrics.py:164-166`: `mean`, `median` and `var` each convert the same list to a numpy array. Convert once.
- [ ] (LOW, S) `crates/genetic_opt/src/algorithm.rs:425-437`: `score` hashes each new chromosome twice and sorts a `Vec` collected from a `HashMap` to restore order. Use a `Vec` plus an index map.
- [ ] (LOW, S) `tests/unit/test_fit_save.py:74-77`: the save-and-load tests also draw the full metrics JPEG (about 4.2 s of the 8.95 s unit suite across the plot tests). Pass `plot_metrics=False` where the plot is not under test.
- [ ] (LOW, S) `crates/genetic_opt/Cargo.toml`: no `[profile.dev]`; `debug = "line-tables-only"` (or no debug info for dependencies) would cut build time. Not measured.
- [ ] (LOW, S) `tests/integration/test_rust_layout.py:24-60`: two session fixtures each run `cargo build --example <name>`; one `cargo build --examples` would do.
- [ ] (LOW, S) `.claude/rules/testing-areas.md` "Recorded times": measured at v0.7.4 (89 unit tests, 5.2 s); now 177 unit tests in 8.95 s, 5 integration tests, 40 Rust tests. Re-measure all four rows and the slowest-tests note.

#### Refactoring

- [ ] (MED, S) `src/genetic_opt/fit_result_io.py:61-74,120-131,136-152`: `_refuse_malformed` catches `AttributeError`/`TypeError`/`ValueError`/`KeyError` around the caller's `load_gene_func` and `load_decoded_chromosome_func`, so a bug in those is reported as "not a fit result file". Narrow the catch to the parsing.
- [ ] (MED, S) `src/genetic_opt/gene_collection.py:133-134,209-211`: `GeneList`/`GeneSet` built with fewer genes than `size` and no `gene_space` crash with `AttributeError`/`TypeError` instead of `ValidationException`. Add the check and a regression test.
- [ ] (MED, S) `src/genetic_opt/algorithms/base.py:355-388`: `fit` validates `FitConfig` and resolves `n_jobs` inline (~35 lines). Move into `FitConfig.__post_init__` or a helper, like the crate's `fit_parameters()`.
- [ ] (MED, S) `src/genetic_opt/algorithms/base.py:470-490,731-751`: the score-cache lookup by `repr(chromosome)` is written twice; `get_chromosome_score` is called only by tests.
- [ ] (MED, S) `src/genetic_opt/algorithms/base.py:290-303`: no counterpart to the crate's `FitConfig.stop_without_improvement`; tests turn it off by replacing `no_improvement_condition` on the instance (`tests/unit/test_binary_algs.py:663,690,714`).
- [ ] (MED, M) Python/crate settings placement differs: `random_seed`, `extra_config`, `experiment_name`, `save` are constructor arguments in Python (`base.py:111-114`, `config.py:131-148`) but `FitConfig`/`SaveConfig` fields in the crate (`algorithm.rs:29-51`, `save.rs:19-24`); `as_bson: bool` vs `format: SaveFormat`. Public API change: decide, then check `downstream`.
- [ ] (MED, M) `init_population` means different things: Python (`base.py:502`) builds and scores the first population, the crate (`problem.rs:169`) only returns genes, like Python's `get_init_population`. Public API change: decide, then check `downstream`.
- [ ] (MED, M) Test files do not mirror source modules (`.claude/rules/testing.md`): `tests/unit/test_binary_algs.py` (890 lines) tests chromosome, gene collections, base, examples and metrics; `test_functions.py:95-131` tests exceptions and gene collections; `test_fit_save.py` covers save, fit_result_io and plots. Split into `test_chromosome.py`, `test_gene_collection.py`, `test_fit_result_io.py`, `test_plots.py`, `test_score.py`, `test_exceptions.py`, and add the `# ── Module ──` headers missing in four files.
- [ ] (LOW, S) v1.0.0 rename leftovers: `tests/unit/test_binary_algs.py:24` `test_genetic_bag` and ~80 `genetic_bag` locals; `decode_bag`/`fit_bag` in `src/genetic_opt/examples/binary.py:46,73`; `FitnessFuncCalls` (`fit_result.py:216`) vs the crate's `FitnessCalls` (`metrics.rs:38`); gitignored `sketches/genetic_bag.py` still imports `GeneticBag`.
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

- [ ] (HIGH, S) `tests/integration/test_rust_layout.py:74-86`: a Rust run loaded in Python checks only a few fields. Check every key and value type against the `FitResult` TypedDicts (as `tests/unit/test_fit_save.py:132-153` does for Python runs): the other `fit_parameters` keys, `total_fit_time`, `genetic_opt_version`, `percent_processed`, `cached`, `exploration_percentage`, `last_population`, every Metric field, and each chromosome's `score_time` and `random_seed`.
- [ ] (MED, S) `tests/integration/test_rust_layout.py:63-118`: no Rust run with `extra_config` is loaded, `load_fit_result_file` is never called on a Rust file, and `experiment_config.yml` is only checked to exist.
- [ ] (MED, S) Infinite `space_points` is written as JSON `null` by Rust (`algorithm.rs:583`) and `Infinity` by Python (`metrics.py:192`); Python then loads `None` where its type says float. Decide one form and test it.
- [ ] (MED, S) NaN fitness is untested in both: Python leaves NaN scores mid-population after sorting (`base.py:753-756`); Rust's reversed `total_cmp` (`algorithm.rs:255-262`) would rank NaN best; `no_improvement_condition` (`base.py:303`) never fires on a NaN mean. Decide the behaviour, then test it.
- [ ] (MED, S) `src/genetic_opt/gene_collection.py:230`: `GeneSet.random_mutate` iterates `list(self.genes)`, whose order for string genes changes between interpreter launches (hash randomization), so a seed may not reproduce a set-chromosome run. The seed test (`test_binary_algs.py:674`) covers only int lists.
- [ ] (MED, S) Python `fit` is never run with `population_size=1`, `crossovers_prop=0`, or `crossovers_prop=besties_prop=1` (`base.py:587-599`); the crate covers these at `tests/algorithm.rs:407`.
- [ ] (MED, S) `iter_func` (`base.py:348,408,744`) is never passed in any test.
- [ ] (MED, S) `tests/unit/test_fit_save.py:39-59`: the unit suite saves and loads only list chromosomes; set chromosomes are covered only by the cargo-gated integration suite.
- [ ] (MED, S) `load_fit_result_file` (`test_fit_save.py:145,166`) is tested only on JSON, never with `remove_duplicates`, `max_file_bytes`, BSON or a malformed file.
- [ ] (MED, S) `tests/unit/test_fit_save.py:93-98`: history equality relies on `Chromosome.__eq__` (genes only), so losing `score_time` or `random_seed` on save would pass. Add a direct `Chromosome.to_dict`/`from_dict` round-trip test.
- [ ] (LOW, S) No test for a fitness function that raises inside a worker process (`base.py:742-745`, `n_jobs > 1`).
- [ ] (LOW, S) `fit_result_io.py:66-74`: two files with the same `population_idx` (`fit_data_1.json` and `fit_data_1.bson`) put a generation twice in `history`; untested and not refused.
- [ ] (LOW, S) `score.py:23-26`: `Score.to_dict` drops an empty `name` or `extra_metrics`, so `Score(value=1, extra_metrics={})` does not round-trip equal. Untested.
- [ ] (LOW, S) `algorithms/plots.py:138`: plot title without a score name is untested.
- [ ] (LOW, S) Rust gaps: no `n_generations = 0` test (Python has one at `test_binary_algs.py:82`); no saved-chromosome `score_time` check (`tests/algorithm.rs:795-798`); `format.rs:37-44` omits the 0, 60 and 3600 s cases the Python test checks.
- [ ] (LOW, S) Weak assertions: `test_fit_save.py:476` (truthy `bests`), `test_files.py:170` (only `endswith(" B")`), `test_functions.py:73-74` (format only, not UTC), `test_binary_algs.py:447` (depends on numpy's RandomState pickle size).

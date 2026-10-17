# Backlog - Genetic-Opt

### 2026.10.16 (v1.0.0 scan)

#### Test coverage

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

# Backlog - Genetic-Opt

### 2026.10.16 (v1.0.0 scan)

#### Test coverage

- [ ] (LOW, S) `fit_result_io.py:66-74`: two files with the same `population_idx` (`fit_data_1.json` and `fit_data_1.bson`) put a generation twice in `history`; untested and not refused.
- [ ] (LOW, S) `score.py:23-26`: `Score.to_dict` drops an empty `name` or `extra_metrics`, so `Score(value=1, extra_metrics={})` does not round-trip equal. Untested.
- [ ] (LOW, S) `algorithms/plots.py:138`: plot title without a score name is untested.
- [ ] (LOW, S) Rust gaps: no `n_generations = 0` test (Python has one in `tests/unit/algorithms/test_base.py`); no saved-chromosome `score_time` check (`tests/algorithm.rs:795-798`); `format.rs:37-44` omits the 0, 60 and 3600 s cases the Python test checks.
- [ ] (LOW, S) Weak assertions: `test_load_fit_result_refuses_a_file_over_the_size_limit` in `test_fit_result_io.py` (truthy `bests`), `test_files.py:170` (only `endswith(" B")`), `test_now_for_file_path_format` in `test_functions.py` (format only, not UTC), `test_a_chromosome_builds_its_random_state_on_first_use` in `test_chromosome.py` (depends on numpy's RandomState pickle size).

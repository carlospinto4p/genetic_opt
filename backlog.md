# Backlog - Genetic-Opt

### 2026.10.16 (v1.0.0 scan)

#### Test coverage

- [ ] (LOW, S) Rust gaps: no `n_generations = 0` test (Python has one in `tests/unit/algorithms/test_base.py`); no saved-chromosome `score_time` check (`tests/algorithm.rs:795-798`); `format.rs:37-44` omits the 0, 60 and 3600 s cases the Python test checks.
- [ ] (LOW, S) Weak assertions: `test_load_fit_result_refuses_a_file_over_the_size_limit` in `test_fit_result_io.py` (truthy `bests`), `test_files.py:170` (only `endswith(" B")`), `test_now_for_file_path_format` in `test_functions.py` (format only, not UTC), `test_a_chromosome_builds_its_random_state_on_first_use` in `test_chromosome.py` (depends on numpy's RandomState pickle size).

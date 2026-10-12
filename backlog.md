# Backlog - Genetic-Opt

### 2026.10.12 (found while fixing parallel scoring and removing `cpinto`)

- [ ] **[manual]** Publish 0.3.0 to the package registry. The
  `build-wheel` job in `.gitlab-ci.yml` is manual, so 0.2.12, 0.2.13
  and 0.3.0 are in `master` only. `downstream` asks for
  `genetic_opt>=0.2.9` and gets the parallel scoring fix only once a
  newer version is published.
- [ ] `pyproject.toml` depends on both `bson` and `pymongo`, and both
  install a `bson` folder: 6 files of `bson` 0.5.10 against 35 of
  `pymongo` 4.17.0 in the same place. Whichever is installed last
  wins. `files.py` calls `bson.BSON.encode` and `bson.decode`, which
  are `pymongo`'s. Drop the `bson` dependency, then reinstall
  `pymongo`, since removing `bson` deletes the files they share.
  `tests/test_files.py` and `tests/test_fit_save.py` cover the result.
- [ ] `ruff check src tests` reports 56 findings with the default
  rules of `ruff` 0.16.4: 45 `RUF013` (a parameter typed `str` with
  the default `None`), 3 `I001`, 3 `PIE790`, 2 `UP035`, 2 `SIM102`
  and 1 `B019`. Only `algorithms/__init__.py`, `chromosome.py`,
  `metrics.py` and the files added in 0.3.0 have been through the
  formatter.
- [ ] `B019`: `GeneticAlgorithm.get_chromosome_score` is cached with
  `functools.cache` on a method, so the cache keeps every Chromosome
  and the algorithm itself alive. `_chromosome_cache` already holds
  the same scores. Keep one of the two.
- [ ] `fit_metrics.fitness_func_calls` in `_get_fitted_data` is
  mislabelled: `total` is the number of cache hits, not of calls, and
  `percent_processed` divides the misses by the hits.
- [ ] Rewrite the library in Rust, as a Python package built with
  PyO3 and maturin so `downstream` keeps importing it. Second step of
  the plan agreed on 12th October 2026. On its own it gives little
  speed: the time goes into the fitness function, which stays in
  Python.
- [ ] Move `downstream`'s backtest, the fitness function of
  `RuleOptimizer`, to Rust. Third step of the same plan, and the one
  that makes the rewrite faster.

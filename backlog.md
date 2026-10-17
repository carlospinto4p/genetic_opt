# Backlog - Genetic-Opt

### 2026.10.17 (v5.10.2 /scan)

#### Performance

- [ ] `web/app.py:34-36` — the limits (300 gens, 400 chromosomes, 40 genes) allow a knapsack run of 18.1 s compute / 22.2 s over HTTP and a 96 MB response (function run: 9.9 s, 50.7 MB), which the comment says the limits should prevent; lower them and/or shrink the payload — HIGH — S
- [ ] `web/runs.py:200-207` — each parent is sent with full genes, value and score, all already in the previous generation at its `rank` (~25% of entries); send the rank only, update `BreedingView.svelte` and `Guide.svelte` — MED — M
- [ ] `frontend/src/lib/store.svelte.ts:29-38,68`, `pages/SavedRun.svelte:16` — runs live in deep `$state`, so every generation/gene array is proxied; runs are only replaced whole, so use `$state.raw` — MED — S
- [ ] `algorithms/config.py:59` + `base.py:901` — default `n_jobs=-2` sends every generation's few new chromosomes to worker processes; README knapsack takes 0.46 s at `n_jobs=1` vs 1.16-1.74 s at the default; score in-process when the batch is small (changing the default is a user decision) — MED — S
- [ ] `algorithms/base.py:473-477,814-817` — when saving, `_get_fit_result` decodes the whole population into `last_population` every generation, and `serialize_fit_result` (`fit_result_io.py:307-308`) discards it — MED — S
- [ ] `frontend/src/components/PopulationTable.svelte:83-102` + `GeneStrip.svelte:26-32,41-53` — every Play tick (700 ms) re-renders up to 16k gene squares, each building its `title` eagerly and scanning `changed`/`off` with `includes`; `off(row.member)` allocates per row (not measured in a browser) — MED — S
- [ ] `tests/unit/algorithms/test_plots.py`, `test_save.py` — the 6 plot tests take ~7.6 s of the 14 s unit run (~0.5 s per `savefig`, dpi barely matters) — MED — M
- [ ] `pyproject.toml` dev group — no `pytest-xdist`; the 10 slowest tests (~11 s of 14 s) are independent and could run with `-n auto` — MED — S
- [ ] `.claude/rules/testing-areas.md:36-39` — recorded times are stale (185 tests in 3.9 s, 5 integration tests in 0.5 s); measured 2026-10-17: unit 300 tests in 13.96 s (16.0 s wall), integration 21 in 2.96 s (crate built), `cargo test` warm 0.3 s, Vitest 4 tests 1.47 s; slowest are `test_a_saved_run_gets_the_plot_that_fit_saves` (~1.9 s ×2) and `test_one_seed_gives_the_same_set_run_with_any_hash_seed` (1.5-1.8 s); cold `cargo build` not re-measured — MED — S
- [ ] `web/runs.py:166-209` — `_breeding_record` spends 3.3 s self time at the limits on per-gene `int()` and the `changed` comprehension — LOW — S
- [ ] `gene_space.py:58` — `random_state.choice([0, 1], size=n)` gives identical draws to `randint(0, 2, size=n)` (checked values and dtype) at 6.5 µs vs 11.5 µs; 73k calls per limit-sized run — LOW — S
- [ ] `algorithms/base.py:341-358` (called at 498) — `stale_generations` walks all metrics each generation (quadratic); keep a running counter — LOW — S
- [ ] `chromosome.py:171`, `gene_collection.py:163,244` — `copy.copy` costs 2.0 µs vs 0.5 µs hand-built, two per mutation (~4% of mutation time) — LOW — S
- [ ] `frontend/src/components/PopulationTable.svelte:33,41` — `JSON.stringify(m.genes)` computed twice per member — LOW — S
- [ ] `tests/unit/algorithms/test_base.py:644-654` — the two hash-seed subprocesses run serially (~0.9 s each); start both, then wait — LOW — S
- [ ] `.pre-commit-config.yaml:105-117` — `cargo-test` and `frontend-test` use `always_run: true`; `files: ^crates/` / `^frontend/` would skip them (saves only ~1.8 s per push) — LOW — S

#### Refactoring

- [ ] `algorithms/base.py:479-520` — no single source for why a run stopped: Python checks five conditions inline, Rust builds its own chain (`algorithm.rs:386-405`), `web/runs.py:224-236` copies two of five, `runs.py:401-406` guesses for saved runs; so `_stop_reason` reports "completed" for runs stopped by `max_stale_generations`, `max_seconds` or `exit_condition`. Return the stop reason from `fit` in both implementations; this also shortens the ~170-line `fit` (`base.py:361-529`) — MED — M
- [ ] `gene_collection.py:411-413` — `GeneSet.__init__` fills the caller's own set in place via `_complete_genes` (`:482-483`); a tuple passes the `list`/`ndarray` conversion (`:406-409`) and fails on `.update` — MED — S
- [ ] `algorithms/base.py:731-732` — the crossed-parents / best-parents counts are computed in four places (also `web/runs.py:112-115`, `Guide.svelte:46-47`, `algorithm.rs:549-550`); one helper, and Guide reads `breeding.n_crossovers` — MED — S
- [ ] `algorithms/base.py:702-711` — `next_generation_selection` takes seven loose `FitConfig` fields plus `iter_func`/`n_jobs`; pass `config` (and the override at `web/runs.py:107`) — MED — M
- [ ] `web/runs.py:30-96` — `BinaryFunction`, `wavy_function`, `function_curve` live in the web layer while `Knapsack` is in `examples/binary.py`; `runs.py` also mixes the recorder mixin and the saved-run adapter; split — MED — M
- [ ] `frontend/src/components/LineChart.svelte:30-51` — padding, scaling and SVG path code duplicated in `FunctionPlot.svelte:14-33`; share a scale helper — MED — M
- [ ] `frontend/src/pages/Knapsack.svelte:58-62,173` — "server did not answer" block, "Loading the example…" line, `.explain`/`.row` CSS and `reset()` copied in `FunctionLab.svelte:43-47,107` and `Guide.svelte:63-67` — MED — S
- [ ] `algorithms/plots.py:500`, `algorithms/save.py` — saved-run code sits under `algorithms/`, apart from `fit_result.py`, `fit_result_io.py`, `files.py`; a `runs/` subpackage would group them, but `downstream` imports `genetic_opt.files` and `genetic_opt.fit_result_io` (needs shims or a downstream backlog item) — LOW — M
- [ ] `algorithms/__init__.py:3-14` — re-exports `Chromosome` and `Score` but not `BinaryGeneticAlgorithm`, which the README uses — LOW — S
- [ ] `algorithms/base.py:568-577` — Rust refuses a gene space too small for a set chromosome at run start (`algorithm.rs:461-469`); Python only fails when the first set chromosome is built (`gene_collection.py:477-481`) — LOW — S
- [ ] `pyproject.toml:56-57` — ruff has `line-length = 78` but no rule selection, so E501 is never checked although `CLAUDE.md` says it is enforced; 5 lines are over (`fit_result.py:13`, `fit_result_io.py:346`, `functions.py:69`, `base.py:601`, `tests/unit/algorithms/test_base.py:439`) — LOW — S
- [ ] `web/runs.py:408-409` — infinite-`space_points`-to-`None` repeats `fit_result_io.py:326-329` — LOW — S
- [ ] `algorithms/base.py:625-630` — the same `Chromosome(size=..., is_gene_set=..., random_seed=...)` call at `base.py:669-677` and `binary.py:80-85`; one `_new_chromosome(genes)` — LOW — S
- [ ] `web/app.py:49-50` — seeds 442 and 2 repeated at `web/runs.py:55-56` and `algorithms/binary.py:30-31` — LOW — S
- [ ] `web/runs.py:20-22` — README knapsack data copied at `crates/genetic_opt/examples/knapsack.rs:15-17` — LOW — S
- [ ] `algorithms/config.py:54-63` — `FitConfig` defaults duplicated in Rust (`algorithm.rs:102-117`) with no drift test (like `test_versions.py`) — LOW — S
- [ ] `crates/genetic_opt/src/algorithm.rs:524` — NaN-score error text built twice (also `:644`) — LOW — S
- [ ] `frontend/src/pages/SavedRun.svelte:9-22` — `open()` repeats `runLab`'s running/error try/finally (`store.svelte.ts:59-75`); `store.saved` (`:37`) hand-copies the `Lab` shape — LOW — S
- [ ] `frontend/src/pages/SavedRun.svelte:25-37` — parameter labels copied from `FitForm.svelte:22-84`; share one label map — LOW — S
- [ ] `frontend/src/pages/Knapsack.svelte:14-15` — `off` helper copied at `Guide.svelte:51-52` — LOW — S
- [ ] `frontend/src/components/PopulationTable.svelte:31-35` — duplicates keyed by `JSON.stringify(genes)` here, `genes.join('')` in `FunctionPlot.svelte:36-43` — LOW — S
- [ ] `web/app.py:125` — `_run(func: Any, ...)` should be `Callable[..., dict[str, Any]]` — LOW — S
- [ ] `frontend/src/lib/api.ts:83-91` — `SavedRun.fit_parameters` lacks `n_jobs`, `selection`, `tournament_size`, which both implementations save — LOW — S
- [ ] `frontend/src/components/Sidebar.svelte:12-17` — icons keyed by path string; move into `pages` in `router.svelte.ts`, typed by `PagePath` — LOW — S
- [ ] `frontend/src/components/BreedingView.svelte:20` — `n_random` is snake_case among camelCase — LOW — S
- [ ] `frontend/src/App.svelte:19` — `.catch(() => {})` hides a failed `/api/info`, so the sidebar silently shows no version — LOW — S
- [ ] `frontend/src/components/RunView.svelte:213-216` — `stopText` falls through to "mean stalled" for unknown stop reasons; make the switch over `StopReason` exhaustive — LOW — S
- [ ] `gene_collection.py:299-309` — abstract `select_random` and its two versions (`:370-380`, `:450-460`) are never called in src, tests or `downstream` — LOW — S
- [ ] `algorithms/base.py:339` — `no_improvement_condition` builds the whole improvement dict to read one key; Rust's `mean_stalled` (`algorithm.rs:718-723`) compares means directly — LOW — S

#### Test coverage

- [ ] `chromosome.py:121`, `gene_collection.py:234` — bug: a set chromosome with mixed gene types (e.g. `{1, "a"}` from `ValuesGeneSpace`) raises `TypeError` in `repr` and in mutation because `sorted()` cannot compare `str` with `int` (reproduced); fix (sort by `(type name, value)` as `web/runs.py:357` does) with a regression test — HIGH — S
- [ ] `frontend/src/lib/format.ts:16-35` — bug: `niceTicks` never ends on `Infinity`/`NaN` (reproduced in node); an empty series in `LineChart.svelte:34-37` passes ±Infinity from `Math.min()`/`Math.max()`; guard and test — MED — S
- [ ] `algorithms/base.py:782-785` — no Python test that `bests` are unique, at most `N_BESTS` (5) and best-first; the Rust test (`tests/algorithm.rs:517-518`) checks uniqueness but not the cap — MED — S
- [ ] `web/runs.py:408-409` — no test feeds `saved_run` (or `/api/runs/saved`) a run saved by the Rust crate, though `runs.py:361` promises it; `tests/integration/test_rust_layout.py` could — MED — S
- [ ] `web/runs.py:353-357` — `saved_run` untested for a set chromosome whose saved genes are dicts (how `downstream` saves rules); `test_runs.py:285` covers only a list chromosome — MED — S
- [ ] `algorithms/base.py:911` — only NaN scores are refused; an infinite score comes back from the API as `{"score": null}` with 200, untested (same for infinite variance) — MED — M
- [ ] `frontend/src/lib/api.ts:127-147` — `request()` error handling untested: string `detail`, Pydantic error list, non-JSON body — MED — S
- [ ] `frontend/src/lib/store.svelte.ts:133-165` — untested: `loadExamples` retry after failure (resets `loading`), `runLab` error path and `ran` snapshot — MED — M
- [ ] `frontend/src/components/*.svelte`, `pages/*.svelte` — ~2,500 lines with no component tests (Vitest has no DOM); extract and unit-test the tick/scale code (`LineChart.svelte:34-58`) and index clamping (`RunView.svelte:32`) — MED — M/L
- [ ] `web/app.py:69-78,86` — `MAX_GENES` limit on weights/values and the `n_bits` 2-40 range untested; `test_app.py:61` covers only the population limit — LOW — S
- [ ] `web/app.py:164-174` — `main()` and its reading of `GENETIC_OPT_WEB_PORT` untested — LOW — S
- [ ] `algorithms/base.py:581-582` — `cpu_count()` returning `None` makes the comparison raise `TypeError`; untested — LOW — S
- [ ] `frontend/src/lib/format.ts:2-13` — `fmt` and `pct` untested; a `null` score renders as the text "null" — LOW — S
- [ ] `frontend/src/lib/router.svelte.ts:11-14` — no test that an unknown hash falls back to `/` — LOW — S
- [ ] `tests/unit/algorithms/test_base.py:363` — `assert ...["bests"]["scores"]` only checks non-empty — LOW — S
- [ ] `tests/unit/algorithms/test_base.py:786` — `value > 0`; compare with the same run at `n_jobs=1` — LOW — S
- [ ] `tests/unit/algorithms/test_save.py:146-158` — parametrised on `other_metrics_to_plot` but only checks JPEG magic bytes, so the parameter is not verified — LOW — S
- [ ] `tests/unit/web/test_runs.py:262-266` — BSON run checked only by generation count; compare it to the JSON run — LOW — S
- [ ] `tests/integration/web/test_app.py:41-45,55-58` — checks only curve length and the 422 status, not the error text — LOW — S
- [ ] `tests/integration/web/test_app.py:7` — imports `ones_algorithm` from `tests.unit.conftest`; move the shared helper to `tests/conftest.py` — LOW — S
- [ ] `algorithms/plots.py:40-52` — `set_pyplot_config` changes global matplotlib style/`rcParams` and plot tests never restore them — LOW — S

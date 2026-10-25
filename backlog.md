# Backlog - Genetic-Opt

### 2026.10.17 (v5.10.2 /scan)

#### Performance

- [ ] **[manual]** Check the Knapsack page's breeding view after v5.10.8, which works out the parents and the crossed genes on the page: run `uv run python -m genetic_opt.web.app` and `corepack pnpm --dir frontend dev`, open `http://localhost:5208/#/knapsack`, click "Run the algorithm", stay on the breeding tab of a generation after 0. A pass: each pair shows Parent A and B with a score, a rank and a best/random chip; "crossed" rows have coloured bars under the genes; "mutated" rows ring the same genes that differ from the crossed row; ranks strip above shows picked squares. The "How it works" page was checked headless. Also after v5.10.9 (raw run state, tooltips built on hover): on the population tab, hover a gene square — its tooltip reads "gene N: 0/1", plus "turned off when decoded" on a crossed-out square; on a breeding child, "changed by the mutation" on a ringed square; press Play and the table steps every 700 ms; "Run the algorithm" again replaces the run; "Open a saved run" opens a folder — MED — S

#### Refactoring

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
- [ ] `frontend/src/components/*.svelte`, `pages/*.svelte` — ~2,500 lines with no component tests (Vitest has no DOM); extract and unit-test the index clamping (`RunView.svelte:32`); the chart scales moved to the tested `lib/chart.ts` in v7.0.1 — MED — M/L
- [ ] `web/app.py:69-78,86` — `MAX_GENES` limit on weights/values and the `n_bits` 2-40 range untested; `test_app.py:61` covers only the population limit — LOW — S
- [ ] `web/app.py:164-174` — `main()` and its reading of `GENETIC_OPT_WEB_PORT` untested — LOW — S
- [ ] `algorithms/base.py:581-582` — `cpu_count()` returning `None` makes the comparison raise `TypeError`; untested — LOW — S
- [ ] `frontend/src/lib/format.ts:2-13` — `fmt` and `pct` untested; a `null` score renders as the text "null" — LOW — S
- [ ] `frontend/src/lib/router.svelte.ts:11-14` — no test that an unknown hash falls back to `/` — LOW — S
- [ ] `tests/unit/algorithms/test_base.py:363` — `assert ...["bests"]["scores"]` only checks non-empty — LOW — S
- [ ] `tests/unit/algorithms/test_base.py:786` — `value > 0`; compare with the same run at `n_jobs=1` — LOW — S
- [ ] `tests/unit/web/test_runs.py:262-266` — BSON run checked only by generation count; compare it to the JSON run — LOW — S
- [ ] `tests/integration/web/test_app.py:41-45,55-58` — checks only curve length and the 422 status, not the error text — LOW — S
- [ ] `tests/integration/web/test_app.py:7` — imports `ones_algorithm` from `tests.unit.conftest`; move the shared helper to `tests/conftest.py` — LOW — S
- [ ] `runs/plots.py:40-52` — `set_pyplot_config` changes global matplotlib style/`rcParams` and plot tests never restore them — LOW — S

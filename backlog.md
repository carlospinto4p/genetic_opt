# Backlog - Genetic-Opt

### 2026.10.25 (v9.0.8)

- [ ] `frontend/src/components/LineChart.svelte` — a mean or median too large for a float reaches the explainer as `null` (decided in v9.0.8), and the chart reads `null` as 0: the line drops to 0 and the axis stretches to it. Reached with Knapsack values near 1e307. `Metrics` in `lib/api.ts` types them as `number`. Decide how the chart shows a missing value (a gap in the line?) — LOW — S

### 2026.10.17 (v5.10.2 /scan)

#### Performance

- [ ] **[manual]** Check the Knapsack page's breeding view after v5.10.8, which works out the parents and the crossed genes on the page: run `uv run python -m genetic_opt.web.app` and `corepack pnpm --dir frontend dev`, open `http://localhost:5208/#/knapsack`, click "Run the algorithm", stay on the breeding tab of a generation after 0. A pass: each pair shows Parent A and B with a score, a rank and a best/random chip; "crossed" rows have coloured bars under the genes; "mutated" rows ring the same genes that differ from the crossed row; ranks strip above shows picked squares. The "How it works" page was checked headless. Also after v5.10.9 (raw run state, tooltips built on hover): on the population tab, hover a gene square — its tooltip reads "gene N: 0/1", plus "turned off when decoded" on a crossed-out square; on a breeding child, "changed by the mutation" on a ringed square; press Play and the table steps every 700 ms; "Run the algorithm" again replaces the run; "Open a saved run" opens a folder — MED — S

#### Test coverage

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

# Backlog - Genetic-Opt

### 2026.10.17 (v5.10.2 /scan)

#### Performance

- [ ] **[manual]** Check the Knapsack page's breeding view after v5.10.8, which works out the parents and the crossed genes on the page: run `uv run python -m genetic_opt.web.app` and `corepack pnpm --dir frontend dev`, open `http://localhost:5208/#/knapsack`, click "Run the algorithm", stay on the breeding tab of a generation after 0. A pass: each pair shows Parent A and B with a score, a rank and a best/random chip; "crossed" rows have coloured bars under the genes; "mutated" rows ring the same genes that differ from the crossed row; ranks strip above shows picked squares. The "How it works" page was checked headless. Also after v5.10.9 (raw run state, tooltips built on hover): on the population tab, hover a gene square — its tooltip reads "gene N: 0/1", plus "turned off when decoded" on a crossed-out square; on a breeding child, "changed by the mutation" on a ringed square; press Play and the table steps every 700 ms; "Run the algorithm" again replaces the run; "Open a saved run" opens a folder. Since v9.0.11 the component tests in jsdom check each of these except how they look: what is left is that the bars, rings, crossed-out squares and chips are visible and in the right place — MED — S

#### Test coverage

- [ ] `tests/integration/web/test_app.py:7` — imports `ones_algorithm` from `tests.unit.conftest`; move the shared helper to `tests/conftest.py` — LOW — S
- [ ] `runs/plots.py:40-52` — `set_pyplot_config` changes global matplotlib style/`rcParams` and plot tests never restore them — LOW — S

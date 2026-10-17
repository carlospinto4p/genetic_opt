# Backlog - Genetic-Opt

### 2026.10.17 (v5.10.0 saved runs in the explainer)

- [ ] Give `frontend/` a test runner and a regression test for
  `niceTicks` in `frontend/src/lib/format.ts`. v5.10.0 fixed an endless
  loop there for a range of float noise (best and mean scores of a
  `downstream` run equal but for the last digit), found only by opening
  the real run. The front end has no tests at all, so the fix has none.
  Impact MEDIUM, effort Small.

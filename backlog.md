# Backlog - Genetic-Opt

### 2026.10.17 (v5.1.0 improvements review)

- [ ] Report progress from the Rust crate. It writes nothing during a
  run, where the Python package logs each generation's metrics to the
  `genetic_opt` logger. Use the `log` crate, which writes nothing until
  the program sets up a logger. Impact MEDIUM, effort Low.
- [ ] Stop a run after a number of seconds: a new `FitConfig` field in
  both implementations, checked after each generation. Impact MEDIUM,
  effort Low.
- [ ] Stop after a number of generations without a better best score.
  The default stop today is a mean score exactly equal to the one of the
  generation before: with integer scores (`Knapsack`) one flat generation
  ends the run, and with float scores it hardly ever fires. A new
  `FitConfig` field in both implementations. Impact MEDIUM, effort Medium.
- [ ] A Python gene space over any list of values given to it, beside
  `BinaryGeneSpace`. Today a problem whose genes are not 0 and 1 must
  write its own `AbstractGeneSpace` subclass. Impact LOW, effort Low.
- [ ] More ways to cross and to pick parents, in both implementations:
  uniform crossover, and tournament selection beside the current one.
  Impact LOW, effort Medium.
- [ ] Open a saved run in the explainer and step through its
  generations. The saved files hold each population and its scores, not
  the parents and crossovers, so the breeding view would be left out.
  Impact LOW, effort Medium.

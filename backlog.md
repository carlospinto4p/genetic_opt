# Backlog - Genetic-Opt

### 2026.10.17 (v5.1.0 improvements review)

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

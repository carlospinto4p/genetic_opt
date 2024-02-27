
## Changelog - Genetic-Opt


### 0.1.5 - 27th February 2024 - Not yet released!

- Class `GeneticAlgorithm`: 
  - Bug fixed in the `init_population` method: all chromosomes of this
  initial population were the same. 
  - Added the value `genetic_opt_version` in the metrics returned, inside 
  the section `fit_metrics`.


### 0.1.4 - 21st February 2024

- Class `GeneticAlgorithm`: 
  - Changes in the method `_get_fitted_data`:
    - Added the parameter `n_jobs`. Now it appears in the metrics data.
    - Within the result dictionary of the summary, the part of `bests_5`
    now includes only non-unique chromosomes.
- Function `metrics.get_population_metrics` rounds up the received 
  `fitting_seconds` to 2 decimals.


### 0.1.3 - 14th February 2024

- Added `joblib` dependency.
- Class `GeneticAlgorithm`: 
  - Added the parameter `n_jobs` with a default value of `-2` to the methods:
    - `fit`.
    - `init_population`.
    - `next_generation_selection`.
    - `_sort_population`.
- `Chromosome.__hash__` maximum length reduced to 30. 


### 0.1.2 - 13th February 2024

- Class `GeneticAlgorithm`: 
  - Included the parameter `iter_func` inside the main iterations:
    - Added the parameter in the methods `init_population`, 
    `next_generation_selection` and `_sort_population`.
  - Method `init_population` is measured better internally.
  - Added the inner parameter `_chromosome_cache`.
  - Functions `identity_func`, `no_exit_condition` and 
    `no_improvement_condition` are now outside of this class.
- `Chromosome.__hash__` has a maximum length of 100 instead of 15. 


### 0.1.1 - 12th February 2024

- Class `GeneticAlgorithm`: 
  - Added the parameter `extra_config`.
  - Inner `fitness_func` renamed to `algo_fitness_func`.
- Value of `Score` changed to float instead of integer.
- Fix in the `init` method of `GeneSet` and `GeneList`.
- Improved the documentation of `core.gene_space.GeneSpace`.


### 0.1.0 - 27th July 2023

- First release.


## Changelog - Genetic-Opt


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

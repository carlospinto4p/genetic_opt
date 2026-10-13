
# Genetic Opt

Genetic algorithm optimizers package.

This package provides two base classes, `algorithms.GeneticAlgorithm` and 
`algorithms.binary.BinaryGeneticAlgorithm` to formulate genetic optimization
methodologies in order to tackle different optimization problems.

There is an example of optimization problem tackled with these classes
in `examples.binary.GeneticBag`.

## Rust crate

`crates/genetic_opt` is the same algorithm written in Rust. The Python
package does not use it and has no binding to it: they are two
implementations side by side. A Rust project uses the crate as a
dependency. `roadmap.md` has the reasons.

A problem implements the trait `Problem` (its genes, its fitness
function, its crossover) and `GeneticAlgorithm` runs it. The fitness
function runs on several threads at once. `problems::Knapsack` is the
example, the same problem as `examples.binary.GeneticBag`:

```rust
use genetic_opt::problems::Knapsack;
use genetic_opt::{FitConfig, GeneticAlgorithm};

let knapsack = Knapsack::new(
    vec![23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
    vec![92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
    165,
)?;
let result = GeneticAlgorithm::new(knapsack, FitConfig::new(100, 50)).fit()?;
println!("{}", result.bests[0].score.value);
```

With `FitConfig::save` set, a run is saved in the layout of the Python
package: `experiment_config.yml` and one `fit_data/fit_data_<n>` file
per generation, as BSON or JSON. `utils.load_fit_result` reads them. It
does not save the plot `fit_plots.jpg`.

Since 0.7.0 each `fit_data_<n>` file holds the metrics of its own
generation, in both implementations. Before, it held those of every
generation up to its own. `utils.load_fit_result` reads both. A
version before 0.7.0 that loads a run saved since gets the metrics of
the last generation only.

```bash
# Tests
cargo test --manifest-path crates/genetic_opt/Cargo.toml

# Run the example, saving it in a folder
cargo run --manifest-path crates/genetic_opt/Cargo.toml \
    --example knapsack -- <folder> bson
```

Differences with the Python package:

- A seed does not give the same run in both: they draw their random
  numbers differently.
- A run does not stop when the mean score of the first generation is 0.
- Every saved chromosome carries the seed of the run as `random_seed`.

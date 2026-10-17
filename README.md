
# Genetic Opt

Genetic algorithm optimizers package.

This package provides two base classes, `algorithms.GeneticAlgorithm` and 
`algorithms.binary.BinaryGeneticAlgorithm` to formulate genetic optimization
methodologies in order to tackle different optimization problems.

There is an example of optimization problem tackled with these classes
in `examples.binary.Knapsack`.

The parameters of a run go in a `FitConfig`. To save the runs, the
algorithm gets a `SaveConfig`:

```python
from genetic_opt.algorithms import FitConfig, SaveConfig
from genetic_opt.examples.binary import Knapsack

bag = Knapsack(
    weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
    values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
    capacity=165,
)
result = bag.fit(FitConfig(n_generations=100, population_size=50))
print(result["bests"]["scores"][0].value)
```

```python
BinaryGeneticAlgorithm(
    ...,
    save=SaveConfig(
        path="<folder>",
        serialize_decoded_chromosome_func=list,
        serialize_gene_func=int,
    ),
)
```

A saved run also gets a plot of its metrics, `fit_plots.jpg`.
`SaveConfig(plot_metrics=False)` leaves it out, and
`other_metrics_to_plot` adds the functions of the best Chromosome
of each population to it.

Before 0.11.0 these were loose arguments of `fit` and of the
algorithm: `n_generations`, `save_path` and the rest.

`fit` returns a dictionary, and `fit_result_io.load_fit_result`
returns one with the same keys for a saved run. Those keys, and the
ones of a single file loaded with `fit_result_io.load_fit_result_file`,
are written once, in `fit_result.py`: `FitResult` and `FitResultFile`.
Before 0.13.0 the module `fit_result_io` was named `utils`.

The saved files hold each population once, as genes. The
`last_population` of a loaded run is the last population decoded
again, so `load_fit_result` takes the `decode_func` of the algorithm:

```python
from genetic_opt.fit_result_io import load_fit_result

loaded = load_fit_result("<folder>/fit_data", bag.decode_func)
```

Before 2.0.0 every file also held its population decoded, and
`load_fit_result` took no `decode_func`. It still reads those files.

## Logs

The package writes the progress of a run to the logger `genetic_opt`
at level `INFO` and sets up no handler. A program that wants to see it
configures logging itself:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s-%(name)s: %(message)s",
    datefmt="%Y.%m.%d %H:%M:%S",
)
```

Before 0.9.0 the package added a handler on the standard output when
it was imported.

## Rust crate

`crates/genetic_opt` is the same algorithm written in Rust. The Python
package does not use it and has no binding to it: they are two
implementations side by side. A Rust project uses the crate as a
dependency. `roadmap.md` has the reasons.

A problem implements the trait `Problem` (its genes, its fitness
function, its crossover) and `GeneticAlgorithm` runs it. The fitness
function runs on several threads at once. `examples::Knapsack` is the
example, the same problem as `examples.binary.Knapsack`:

```rust
use genetic_opt::examples::Knapsack;
use genetic_opt::{AlgorithmConfig, FitConfig, GeneticAlgorithm};

let knapsack = Knapsack::new(
    vec![23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
    vec![92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
    165,
)?;
let mut algorithm = GeneticAlgorithm::new(knapsack, AlgorithmConfig::default());
let result = algorithm.fit(&FitConfig::new(100, 50))?;
println!("{}", result.bests[0].score.value);
```

The settings sit where the Python package has them.
`AlgorithmConfig` holds what the Python algorithm takes when it is
created: `experiment_name`, `random_seed`, `extra_config` and `save`.
`FitConfig` holds the parameters of a run, given to `fit`.

With `AlgorithmConfig::save` set, a run is saved in the layout of the
Python package: `experiment_config.yml` and one
`fit_data/fit_data_<n>` file per generation, as BSON or JSON.
`fit_result_io.load_fit_result` reads them. It does not save the plot
`fit_plots.jpg`.

Since 0.7.0 each `fit_data_<n>` file holds the metrics of its own
generation, in both implementations. Before, it held those of every
generation up to its own. `fit_result_io.load_fit_result` reads both.
A version before 0.7.0 that loads a run saved since gets the metrics of
the last generation only.

```bash
# Tests
cargo test --manifest-path crates/genetic_opt/Cargo.toml

# Run the example, saving it in a folder
cargo run --manifest-path crates/genetic_opt/Cargo.toml \
    --example knapsack -- <folder> bson
```

The `numbers` example runs `examples::Numbers`, which picks 3 different
numbers under 12 with the highest sum, or the lowest with `minimize`
set. Its chromosomes are sets and its scores have a name and extra
metrics. It takes the same arguments. A format other than `json` or
`bson` stops either example with an error.

Differences with the Python package:

- A seed does not give the same run in both: they draw their random
  numbers differently.
- A second `fit` on the same object is a new run in both. In the crate
  it is the same run again. In the Python package the gene space keeps
  its own random state, so the genes drawn differ.
- Every saved chromosome carries the seed of the run as `random_seed`.
  In the Python package a child carries the seed its `crossover_func`
  gives it: `BinaryGeneticAlgorithm` gives the seed of the run since
  0.7.6, and gave 442 before.

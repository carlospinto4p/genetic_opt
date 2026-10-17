
# Genetic Opt

Genetic algorithm optimizers package.

This package provides two base classes, `algorithms.GeneticAlgorithm` and
`algorithms.BinaryGeneticAlgorithm` to formulate genetic optimization
methodologies in order to tackle different optimization problems.

There is an example of optimization problem tackled with these classes
in `examples.binary.Knapsack`.

`GeneticAlgorithm` takes the genes it draws from a gene space.
`gene_space.BinaryGeneSpace` holds 0 and 1, and
`gene_space.ValuesGeneSpace` holds any values it is given, each one
once:

```python
from genetic_opt.gene_space import ValuesGeneSpace

gene_space = ValuesGeneSpace(["red", "green", "blue"], random_seed=5)
```

`BinaryGeneticAlgorithm` crosses two parents with
`crossover.single_point_crossover`, which cuts both at one random
position and swaps their tails. `crossover=uniform_crossover` gives
each gene of a child from one parent or the other, with even odds:

```python
from genetic_opt.crossover import uniform_crossover

BinaryGeneticAlgorithm(..., crossover=uniform_crossover)
```

A subclass of `GeneticAlgorithm` can call either function in its
`crossover_func`. The crate has both, `single_point_crossover` and
`uniform_crossover`, for `Problem::crossover`.

The parents of each generation are the best Chromosomes, a share
`besties_prop` of them, and others picked from the rest. By default
those are picked at random. With `selection="tournament"` each one is
the best of `tournament_size` Chromosomes drawn at random from the
rest, 3 by default. Both are saved with the run. In the crate they are
`FitConfig::selection`, `Selection::Tournament`, and
`FitConfig::tournament_size`:

```python
bag.fit(
    FitConfig(
        n_generations=100,
        population_size=50,
        selection="tournament",
        tournament_size=4,
    )
)
```

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
from genetic_opt.algorithms import BinaryGeneticAlgorithm, SaveConfig

BinaryGeneticAlgorithm(
    ...,
    save=SaveConfig(
        path="<folder>",
        serialize_decoded_chromosome_func=list,
        serialize_gene_func=int,
    ),
)
```

A score whose value is NaN stops the run with a `ValidationException`
naming the Chromosome. The crate stops with `Error::Validation`.

A saved run also gets a plot of its metrics, `fit_plots.jpg`.
`SaveConfig(plot_metrics=False)` leaves it out, and
`other_metrics_to_plot` adds the functions of the best Chromosome
of each population to it. `runs.plots.save_fit_plots` draws it
later for a run saved without it, or by the Rust crate:

```python
from genetic_opt.runs.plots import save_fit_plots

save_fit_plots("<run folder>")
```

`fit` returns a dictionary, and `runs.fit_result_io.load_fit_result`
returns one with the same keys for a saved run. Those keys, and the
ones of a single file loaded with
`runs.fit_result_io.load_fit_result_file`, are written once, in
`runs/fit_result.py`: `FitResult` and `FitResultFile`.

Only the result of `fit` has `stop_reason`, which says why the run
ended: `completed`, `min_population`, `no_improvement`,
`stale_generations`, `max_seconds` or `exit_condition`. The saved files
do not hold it. In the crate it is `FitResult::stop_reason`, a
`StopReason`, where `OnGeneration` stands for `exit_condition`.

The saved files hold each population once, as genes. The
`last_population` of a loaded run is the last population decoded
again, so `load_fit_result` takes the `decode_func` of the algorithm:

```python
from genetic_opt.runs.fit_result_io import load_fit_result

loaded = load_fit_result("<folder>/fit_data", bag.decode_func)
```

It also reads files saved before 2.0.0, which held each population
decoded as well.

A run that stopped can go on from its last population. `fit` takes it
as `first_population`, instead of random Chromosomes, and their saved
scores are not computed again. A run saved by the Rust crate works
too:

```python
last = loaded["history"][-1]
result = bag.fit(
    FitConfig(n_generations=100, population_size=len(last)),
    first_population=last,
)
```

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

## Explainer

`frontend/` is a web page that explains how the algorithm works and
lets you step through real runs, generation by generation: the parents
picked, how each pair was crossed, which genes the mutation changed and
which children stayed. It shows the `Knapsack` example and
`genetic_opt.examples.binary.BinaryFunction`, which looks for the highest
point of `x · sin(10πx) + 1`. Its page "Open a saved run" steps through
a run saved by `fit` or by the crate, given the path of its folder: the
charts and each population, without the breeding, which the files do
not hold.

The runs are made by this package, through a small server in
`genetic_opt.web` that needs the `web` extra:

```bash
# The API, on http://localhost:5209
uv sync --all-extras
uv run python -m genetic_opt.web.app

# The page, on http://localhost:5208
corepack pnpm --dir frontend install
corepack pnpm --dir frontend dev
```

`GENETIC_OPT_WEB_PORT` moves the API to another port, for both.
`GENETIC_OPT_WEB_RUNS_ROOT`, when set, is the folder the saved runs the
page opens must be inside. A saved run over 4 GB (3.7 GiB) is refused.

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

`fit_from` starts a run from a population of genes with their scores,
the Python `first_population`. The scores are not computed again:

```rust
let first = algorithm
    .population()
    .iter()
    .map(|i| (i.chromosome.genes().to_vec(), i.score.clone()))
    .collect();
let result = algorithm.fit_from(&FitConfig::new(100, 50), Some(first), |_| false)?;
```

With `AlgorithmConfig::save` set, a run is saved in the layout of the
Python package: `experiment_config.yml` and one
`fit_data/fit_data_<n>` file per generation, as BSON or JSON.
`runs.fit_result_io.load_fit_result` reads them. It does not save the
plot `fit_plots.jpg`, which `runs.plots.save_fit_plots` draws from the
saved files.

Each `fit_data_<n>` file holds the metrics of its own generation, in
both implementations. `runs.fit_result_io.load_fit_result` also reads
runs
saved before 0.7.0, whose files held those of every generation up to
their own.

```bash
# Tests
cargo test --manifest-path crates/genetic_opt/Cargo.toml

# Run the example, saving it in a folder
cargo run --manifest-path crates/genetic_opt/Cargo.toml \
    --example knapsack -- <folder> bson
```

The `numbers` example runs `examples::Numbers`, which picks 3 different
numbers under 12 with the highest sum, or the lowest with `minimize`
set. Its chromosomes are sets, its scores have a name and extra
metrics, and its run has an `extra_config`. It takes the same
arguments. A format other than `json` or
`bson` stops either example with an error.

The crate writes the progress of a run through the `log` crate, at
level `info`: the parameters when it starts, the metrics of each
generation and why it stopped. As in the Python package, nothing is
written until the program sets up a logger.

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

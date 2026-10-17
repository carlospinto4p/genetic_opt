"""Genetic Opt runs that keep every step, for the explainer."""

import json
from math import isinf, pi, sin
from pathlib import Path
from typing import Any

from genetic_opt.algorithms.base import GeneticAlgorithm
from genetic_opt.algorithms.binary import BinaryGeneticAlgorithm
from genetic_opt.algorithms.config import FitConfig
from genetic_opt.chromosome import Chromosome
from genetic_opt.examples.binary import Knapsack
from genetic_opt.exceptions import ValidationException
from genetic_opt.files import get_files_inside_folder
from genetic_opt.fit_result_io import load_fit_result
from genetic_opt.functions import format_bytes, identity_func
from genetic_opt.metrics import Metric
from genetic_opt.score import Score

# The objects of the `Knapsack` example in the README
KNAPSACK_WEIGHTS = [23, 31, 29, 44, 53, 38, 63, 85, 89, 82]
KNAPSACK_VALUES = [92, 57, 49, 68, 60, 43, 67, 84, 87, 72]
KNAPSACK_CAPACITY = 165

# Interval and number of bits of `BinaryFunction` when none are given
FUNCTION_LOW, FUNCTION_HIGH, FUNCTION_BITS = -1.0, 2.0, 16
# Number of points of the curve `function_curve` draws
CURVE_POINTS = 401
# Size of the files of a saved run over which `saved_run` refuses it: a
# run is read whole into memory and sent in one response
MAX_SAVED_RUN_BYTES = 4 * 10**9


def wavy_function(x: float) -> float:
    """
    The function `BinaryFunction` maximizes: many peaks of growing
    height, so a search that climbs the nearest one ends on a low peak.
    :param x: point of the interval.
    :return: the value of the function at `x`.
    """
    return x * sin(10 * pi * x) + 1


class BinaryFunction(BinaryGeneticAlgorithm):
    """
    Problem: find the `x` of an interval with the highest
    `wavy_function(x)`.

    A Chromosome is a list of `n_bits` bits, read as a whole number
    from 0 to `2**n_bits - 1` (the first gene is the highest bit) and
    stretched over the interval: 0 is `low`, the largest is `high`.
    """

    def __init__(
        self,
        low: float = FUNCTION_LOW,
        high: float = FUNCTION_HIGH,
        n_bits: int = FUNCTION_BITS,
        random_seed: int = 442,
        gene_space_random_seed: int = 2,
    ) -> None:
        """
        :param low: lowest `x` of the interval.
        :param high: highest `x` of the interval.
        :param n_bits: number of genes of each Chromosome.
        :param random_seed: random seed for the algorithm.
        :param gene_space_random_seed: random seed for the genes drawn.
        """
        self.low, self.high, self.n_bits = low, high, n_bits
        largest = 2**n_bits - 1

        def decode(chromosome: Chromosome) -> float:
            """The `x` the bits of a Chromosome stand for."""
            number = int("".join(str(int(g)) for g in chromosome.genes), 2)
            return low + (high - low) * number / largest

        def fitness(chromosome: Chromosome) -> Score:
            return Score(value=wavy_function(decode(chromosome)), name="f(x)")

        super().__init__(
            chromosome_length=n_bits,
            chromosome_as_set=False,
            decode_func=decode,
            fitness_func=fitness,
            minimize=False,
            random_seed=random_seed,
            gene_space_random_seed=gene_space_random_seed,
        )


def function_curve(low: float, high: float) -> list[list[float]]:
    """
    Points of `wavy_function` over an interval, to draw it.
    :param low: lowest `x`.
    :param high: highest `x`.
    :return: `CURVE_POINTS` pairs `[x, f(x)]`.
    """
    step = (high - low) / (CURVE_POINTS - 1)
    xs = [low + i * step for i in range(CURVE_POINTS)]
    return [[x, wavy_function(x)] for x in xs]


class _Recorder:
    """
    Mixin that keeps what each generation of a run did: the parents
    picked, the pairs crossed, the genes the mutation changed and the
    children that stayed. It overrides the methods `GeneticAlgorithm`
    lets a subclass override, and calls them unchanged.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # What `shown` gave for each Chromosome, since one stays in the
        # population for many generations
        self._shown: dict[Chromosome, dict[str, Any]] = {}

    def shown(self, chromosome: Chromosome) -> dict[str, Any]:
        """
        A scored Chromosome as the explainer reads it, worked out once
        per run. Equal Chromosomes have the same genes and score.
        """
        if (record := self._shown.get(chromosome)) is None:
            record = self._shown[chromosome] = {
                "genes": [int(g) for g in chromosome.genes],
                "decoded": self.decode_func(chromosome),
                "score": chromosome.score.value,
            }
        return record

    def next_generation_selection(
        self, crossovers_prop: float, besties_prop: float, **kwargs: Any
    ) -> None:
        before = list(self.population)
        # As `GeneticAlgorithm.next_generation_selection` counts them
        n_crossovers = 2 * int((crossovers_prop * len(before)) // 2)
        self._breeding = {
            "n_crossovers": n_crossovers,
            "n_besties": int(n_crossovers * besties_prop),
            "ranks": {id(c): rank for rank, c in enumerate(before)},
            "parents": [],
            "crossovers": [],
            "mutations": [],
        }
        super().next_generation_selection(
            crossovers_prop=crossovers_prop,
            besties_prop=besties_prop,
            **kwargs,
        )

    def cross_parents(self, parents: list[Chromosome]) -> list[Chromosome]:
        self._breeding["parents"] = list(parents)
        return super().cross_parents(parents)

    def crossover_func(
        self, c1: Chromosome, c2: Chromosome
    ) -> tuple[Chromosome, Chromosome]:
        children = super().crossover_func(c1, c2)
        self._breeding["crossovers"].append(children)
        return children

    def mutate(self, chromosome: Chromosome, prob: float) -> Chromosome:
        mutated = super().mutate(chromosome, prob)
        self._breeding["mutations"].append(mutated)
        return mutated


def _breeding_record(algorithm: _Recorder) -> dict[str, Any]:
    """
    What `_Recorder` kept of the generation that just ended. Each parent
    is its rank in the last generation, and each child holds its genes
    after the mutation and the ones the mutation changed. The page
    works out the rest: the genes are bits, so a child's genes before
    the mutation are its changed ones flipped.
    """
    breeding = algorithm._breeding
    ranks = breeding["ranks"]
    stayed = {id(c) for c in algorithm.population}
    mutations = iter(breeding["mutations"])
    pairs = []
    for i, children in enumerate(breeding["crossovers"]):
        pair_children = []
        for crossed in children:
            mutated = next(mutations)
            pair_children.append(
                {
                    **algorithm.shown(mutated),
                    "changed": [
                        j
                        for j, (g, m) in enumerate(
                            zip(crossed.genes, mutated.genes)
                        )
                        if g != m
                    ],
                    "stayed": id(mutated) in stayed,
                }
            )
        pairs.append({"a": 2 * i, "b": 2 * i + 1, "children": pair_children})
    return {
        "n_crossovers": breeding["n_crossovers"],
        "n_besties": breeding["n_besties"],
        "parents": [ranks[id(parent)] for parent in breeding["parents"]],
        "pairs": pairs,
    }


def _metrics(metric: Metric) -> dict[str, Any]:
    """The metrics of a generation as the explainer reads them."""
    return {
        "best": metric.best.score.value,
        "mean": metric.mean,
        "median": metric.median,
        "var": metric.var,
        "n_uniques": metric.n_uniques,
        "percent_uniques": metric.percent_uniques,
    }


def _stop_reason(algorithm: GeneticAlgorithm, config: FitConfig) -> str:
    """
    Why the run ended, checked in the order `GeneticAlgorithm.fit`
    checks it after the last generation.
    """
    if algorithm.metrics[-1].n_uniques < config.min_population_size:
        return "min_population"
    if (
        config.stop_without_improvement
        and algorithm.no_improvement_condition()
    ):
        return "no_improvement"
    return "completed"


def record_run(
    algorithm_class: type[GeneticAlgorithm],
    config: FitConfig,
    **algorithm_kwargs: Any,
) -> dict[str, Any]:
    """
    Run an algorithm and keep every generation.
    :param algorithm_class: the class of the problem, such as `Knapsack`.
    :param config: the parameters of the run.
    :param algorithm_kwargs: what the class takes to be created.
    :return: a dictionary with keys `generations`, `stop_reason`,
        `fit_metrics`, `chromosome_length` and `minimize`. Each
        generation holds its sorted `population`, its `metrics`, and,
        after the first, the `breeding` that made it.
    :raises ValidationException: when the algorithm refuses a value.
    """
    recorded_class = type(
        f"Recorded{algorithm_class.__name__}",
        (_Recorder, algorithm_class),
        {},
    )
    algorithm = recorded_class(**algorithm_kwargs)
    generations = []

    def keep_generation(algo: GeneticAlgorithm) -> None:
        generation = {
            "population": [],
            "metrics": _metrics(algo.metrics[-1]),
            "breeding": None,
        }
        children = set()
        if generations:
            generation["breeding"] = _breeding_record(algo)
            children = {id(c) for c in algo._breeding["mutations"]}
        for chromosome in algo.population:
            generation["population"].append(
                {
                    **algo.shown(chromosome),
                    "origin": (
                        "initial"
                        if not generations
                        else "child"
                        if id(chromosome) in children
                        else "survivor"
                    ),
                }
            )
        generations.append(generation)

    result = algorithm.fit(config, callback_func=keep_generation)
    return {
        "chromosome_length": algorithm.chromosome_length,
        "minimize": algorithm.minimize,
        "generations": generations,
        "stop_reason": _stop_reason(algorithm, config),
        "fit_metrics": result["fit_metrics"]["fitness_func_calls"],
    }


def knapsack_run(
    weights: list[int],
    values: list[int],
    capacity: int,
    config: FitConfig,
    random_seed: int,
    gene_space_random_seed: int,
) -> dict[str, Any]:
    """A recorded run of the `Knapsack` example. See `record_run`."""
    return record_run(
        Knapsack,
        config,
        weights=weights,
        values=values,
        capacity=capacity,
        random_seed=random_seed,
        gene_space_random_seed=gene_space_random_seed,
    )


def function_run(
    low: float,
    high: float,
    n_bits: int,
    config: FitConfig,
    random_seed: int,
    gene_space_random_seed: int,
) -> dict[str, Any]:
    """
    A recorded run of `BinaryFunction`, with the `curve` of the
    function to draw. See `record_run`.
    """
    run = record_run(
        BinaryFunction,
        config,
        low=low,
        high=high,
        n_bits=n_bits,
        random_seed=random_seed,
        gene_space_random_seed=gene_space_random_seed,
    )
    return {**run, "curve": function_curve(low, high)}


def _shown_gene(gene: Any) -> Any:
    """
    A saved gene as the explainer shows it: a number or a text as it
    is, anything else, such as a dictionary, as JSON text. Either can
    go in a set, as the genes of a Chromosome saved as a set do.
    """
    if gene is None or isinstance(gene, int | float | str):
        return gene
    return json.dumps(gene, sort_keys=True, default=str)


def _saved_genes(chromosome: Chromosome) -> list:
    """The genes of a saved Chromosome, those of a set sorted."""
    if not chromosome.is_gene_set:
        return list(chromosome.genes)
    return sorted(chromosome.genes, key=lambda g: (type(g).__name__, g))


def saved_run(
    path: str,
    root: str | None = None,
    max_bytes: int = MAX_SAVED_RUN_BYTES,
) -> dict[str, Any]:
    """
    A run saved by `GeneticAlgorithm.fit`, or by the Rust crate, as the
    explainer shows it. The files hold each population and its scores,
    so there is no `breeding`, no `origin` and no decoded Chromosome.
    :param path: the folder of the run, or its `fit_data` folder.
    :param root: a folder `path` must be inside, links followed. Any
        folder by default.
    :param max_bytes: size of the files of the run over which it is
        refused without being read.
    :return: the keys of `record_run`, with `minimize` as `None`, since
        the files do not say it, and `stop_reason` as `stopped` when
        the run ended early for a reason the files do not hold. Also
        `folder`, the `fit_data` folder read, `fit_parameters` and
        `genetic_opt_version`, the version that saved it. An infinite
        `space_points` is `None`.
    :raises ValidationException: when `path` is outside `root`, is not
        a folder, does not hold a saved run, or its files have more than
        `max_bytes`.
    """
    folder = Path(path).expanduser()
    if root is not None and not folder.resolve().is_relative_to(
        Path(root).expanduser().resolve()
    ):
        raise ValidationException(f"`{path}` is not inside `{root}`")
    if (folder / "fit_data").is_dir():
        folder = folder / "fit_data"
    if not folder.is_dir():
        raise ValidationException(f"`{path}` is not a folder")
    files = get_files_inside_folder(str(folder), return_complete_path=True)
    if (size := sum(Path(file).stat().st_size for file in files)) > max_bytes:
        raise ValidationException(
            f"`{folder}` holds {format_bytes(size)}, more than the "
            f"{format_bytes(max_bytes)} the explainer opens"
        )
    result = load_fit_result(
        str(folder), decode_func=identity_func, load_gene_func=_shown_gene
    )
    generations = [
        {
            "population": [
                {
                    "genes": _saved_genes(chromosome),
                    "decoded": None,
                    "score": score.value,
                }
                for score, chromosome in population
            ],
            "metrics": _metrics(metric),
            "breeding": None,
        }
        for population, metric in zip(
            result["history"], result["metrics"], strict=True
        )
    ]
    parameters = result["fit_parameters"]
    # `load_fit_result` checks the files hold these keys, not what is
    # under them: a truncated run is refused here
    try:
        if len(generations) - 1 >= parameters["n_generations"]:
            stop_reason = "completed"
        elif (
            result["metrics"][-1].n_uniques
            < parameters["min_population_size"]
        ):
            stop_reason = "min_population"
        else:
            stop_reason = "stopped"
        calls = result["fit_metrics"]["fitness_func_calls"]
        if isinf(calls["space_points"]):
            calls = calls | {"space_points": None}
        chromosome_length = len(generations[0]["population"][0]["genes"])
        version = result["fit_metrics"]["genetic_opt_version"]
    except (IndexError, KeyError, TypeError) as error:
        raise ValidationException(
            f"`{folder}` is not a saved run: {error!r}"
        ) from error
    return {
        "chromosome_length": chromosome_length,
        "minimize": None,
        "generations": generations,
        "stop_reason": stop_reason,
        "fit_metrics": calls,
        "folder": str(folder),
        "fit_parameters": parameters,
        "genetic_opt_version": version,
    }

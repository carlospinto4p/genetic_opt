"""Genetic Opt runs that keep every step, for the explainer."""

from typing import Any

from genetic_opt.algorithms.base import GeneticAlgorithm, parent_counts
from genetic_opt.algorithms.config import FitConfig
from genetic_opt.chromosome import Chromosome
from genetic_opt.examples.binary import (
    BinaryFunction,
    Knapsack,
    wavy_function,
)
from genetic_opt.metrics import Metric

# The objects of the `Knapsack` example in the README
KNAPSACK_WEIGHTS = [23, 31, 29, 44, 53, 38, 63, 85, 89, 82]
KNAPSACK_VALUES = [92, 57, 49, 68, 60, 43, 67, 84, 87, 72]
KNAPSACK_CAPACITY = 165

# Number of points of the curve `function_curve` draws
CURVE_POINTS = 401


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
        self, config: FitConfig, **kwargs: Any
    ) -> None:
        before = list(self.population)
        n_crossovers, n_besties = parent_counts(
            len(before), config.crossovers_prop, config.besties_prop
        )
        self._breeding = {
            "n_crossovers": n_crossovers,
            "n_besties": n_besties,
            "ranks": {id(c): rank for rank, c in enumerate(before)},
            "parents": [],
            "crossovers": [],
            "mutations": [],
        }
        super().next_generation_selection(config, **kwargs)

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
            before, after = crossed.genes, mutated.genes
            pair_children.append(
                {
                    **algorithm.shown(mutated),
                    # Most children have no gene mutated, and comparing
                    # the whole lists is quicker than gene by gene
                    "changed": (
                        []
                        if before == after
                        else [
                            j
                            for j, (g, m) in enumerate(zip(before, after))
                            if g != m
                        ]
                    ),
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


def generation_metrics(metric: Metric) -> dict[str, Any]:
    """The metrics of a generation as the explainer reads them."""
    return {
        "best": metric.best.score.value,
        "mean": metric.mean,
        "median": metric.median,
        "var": metric.var,
        "n_uniques": metric.n_uniques,
        "percent_uniques": metric.percent_uniques,
    }


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
            "metrics": generation_metrics(algo.metrics[-1]),
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
        "stop_reason": result["stop_reason"],
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

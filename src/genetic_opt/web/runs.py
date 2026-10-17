"""Genetic Opt runs that keep every step, for the explainer."""

from math import pi, sin
from typing import Any

from genetic_opt.algorithms.base import GeneticAlgorithm
from genetic_opt.algorithms.binary import BinaryGeneticAlgorithm
from genetic_opt.algorithms.config import FitConfig
from genetic_opt.chromosome import Chromosome
from genetic_opt.examples.binary import Knapsack
from genetic_opt.score import Score

# The objects of the `Knapsack` example in the README
KNAPSACK_WEIGHTS = [23, 31, 29, 44, 53, 38, 63, 85, 89, 82]
KNAPSACK_VALUES = [92, 57, 49, 68, 60, 43, 67, 84, 87, 72]
KNAPSACK_CAPACITY = 165

# Interval and number of bits of `BinaryFunction` when none are given
FUNCTION_LOW, FUNCTION_HIGH, FUNCTION_BITS = -1.0, 2.0, 16
# Number of points of the curve `function_curve` draws
CURVE_POINTS = 401


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


def _gene_origins(child: list, a: list, b: list) -> list[str]:
    """
    Which parent each gene of a child came from: `a`, `b`, or `both`
    where the parents have the same gene.
    """
    return [
        "both" if ga == gb else "a" if g == ga else "b"
        for g, ga, gb in zip(child, a, b)
    ]


def _chromosome(
    algorithm: GeneticAlgorithm, chromosome: Chromosome
) -> dict[str, Any]:
    """A Chromosome as the explainer reads it."""
    return {
        "genes": [int(g) for g in chromosome.genes],
        "decoded": algorithm.decode_func(chromosome),
        "score": chromosome.score.value,
    }


def _breeding_record(algorithm: GeneticAlgorithm) -> dict[str, Any]:
    """What `_Recorder` kept of the generation that just ended."""
    breeding = algorithm._breeding
    ranks, n_besties = breeding["ranks"], breeding["n_besties"]
    stayed = {id(c) for c in algorithm.population}
    parents = breeding["parents"]
    mutations = iter(breeding["mutations"])
    pairs = []
    for i, children in enumerate(breeding["crossovers"]):
        a, b = parents[2 * i], parents[2 * i + 1]
        a_genes, b_genes = list(a.genes), list(b.genes)
        pair_children = []
        for crossed in children:
            mutated = next(mutations)
            crossed_genes = [int(g) for g in crossed.genes]
            pair_children.append(
                {
                    **_chromosome(algorithm, mutated),
                    "crossed": crossed_genes,
                    "origins": _gene_origins(crossed_genes, a_genes, b_genes),
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
        "n_besties": n_besties,
        "parents": [
            {
                **_chromosome(algorithm, parent),
                "rank": ranks[id(parent)],
                "kind": "best" if ranks[id(parent)] < n_besties else "random",
            }
            for parent in parents
        ],
        "pairs": pairs,
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
        metric = algo.metrics[-1]
        generation = {
            "population": [],
            "metrics": {
                "best": metric.best.score.value,
                "mean": metric.mean,
                "median": metric.median,
                "var": metric.var,
                "n_uniques": metric.n_uniques,
                "percent_uniques": metric.percent_uniques,
            },
            "breeding": None,
        }
        children = set()
        if generations:
            generation["breeding"] = _breeding_record(algo)
            children = {id(c) for c in algo._breeding["mutations"]}
        for chromosome in algo.population:
            generation["population"].append(
                {
                    **_chromosome(algo, chromosome),
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

import gc
import logging
import pickle
import weakref
from os import cpu_count

import pytest
from joblib import Parallel
from joblib.externals import cloudpickle

from genetic_opt.algorithms import FitConfig
from genetic_opt.algorithms import base as algorithms
from genetic_opt.algorithms.base import GeneticAlgorithm
from genetic_opt.algorithms.binary import BinaryGeneticAlgorithm
from genetic_opt.chromosome import Chromosome
from genetic_opt.examples.binary import GeneticBag
from genetic_opt.exceptions import InvariantException, ValidationException
from genetic_opt.fit_result import FitResult
from genetic_opt.gene_space import AbstractGeneSpace
from genetic_opt.metrics import Metric, get_space_points
from genetic_opt.score import Score


def test_genetic_bag():
    weights: list[int] = [23, 31, 29, 44, 53, 38, 63, 85, 89, 82]
    values: list[int] = [92, 57, 49, 68, 60, 43, 67, 84, 87, 72]
    capacity: int = 165
    genetic_bag = GeneticBag(
        weights=weights, values=values, capacity=capacity
    )
    opt_data = genetic_bag.fit(
        FitConfig(
            n_generations=100,
            population_size=50,
            crossovers_prop=0.7,
            besties_prop=0.6,
            mutate_prob=0.05,
            n_jobs=1,
        )
    )
    best_score = opt_data["bests"]["scores"][0].value
    assert best_score == 309
    best_bag = opt_data["bests"]["result"][0]
    assert best_bag == [1, 1, 1, 1, 0, 1, 0, 0, 0, 0]
    # There are different, tied best encodes for this problem, so only
    # the decoded bag is asserted.
    # The mean score stops changing long before the 100 generations.
    assert len(opt_data["metrics"]) == 9


class ZeroStartAlgorithm(BinaryGeneticAlgorithm):
    """Counts the ones of a Chromosome. Its first population has none."""

    def __init__(self):
        super().__init__(
            chromosome_length=10,
            chromosome_as_set=False,
            decode_func=lambda chromosome: list(chromosome.genes),
            fitness_func=lambda chromosome: Score(
                value=sum(chromosome.genes)
            ),
            opt_is_min=False,
        )

    def get_init_population(self, population_size: int) -> list[list[int]]:
        return [[0] * self.chromosome_length for _ in range(population_size)]


class EmptyStartAlgorithm(ZeroStartAlgorithm):
    """Its first population has no Chromosomes."""

    def get_init_population(self, population_size: int) -> list[list[int]]:
        return []


def test_fit_refuses_a_first_population_without_chromosomes():
    with pytest.raises(ValidationException, match="empty population"):
        EmptyStartAlgorithm().fit(
            FitConfig(n_generations=3, population_size=20, n_jobs=1),
            plot_metrics=False,
        )


def test_fit_with_0_generations_scores_the_first_population_only():
    algorithm = ZeroStartAlgorithm()
    result = algorithm.fit(
        FitConfig(n_generations=0, population_size=20, n_jobs=1),
        plot_metrics=False,
    )
    assert len(result["metrics"]) == 1
    assert len(algorithm.historial) == 1
    assert result["fit_parameters"]["n_generations"] == 0
    assert result["bests"]["scores"] == [Score(value=0)]
    assert len(result["last_population"]) == 20


class NumbersGeneSpace(AbstractGeneSpace):
    """Gene space of the numbers 0 to 11, as Python integers."""

    def __len__(self) -> int:
        return 12

    def select_random(self, n=None):
        genes = self.random_state.randint(12, size=n)
        return int(genes) if n is None else genes.tolist()


class NumbersAlgorithm(GeneticAlgorithm):
    """
    Pick 3 different numbers under 12 with the highest sum, or the
    lowest. A Chromosome is a set. The `Numbers` problem of the crate's
    `tests/algorithm.rs`.
    """

    def __init__(self, opt_is_min: bool):
        super().__init__(
            gene_space=NumbersGeneSpace(random_seed=5),
            chromosome_length=3,
            chromosome_as_set=True,
            decode_func=lambda chromosome: sum(chromosome.genes),
            fitness_func=lambda chromosome: Score(
                value=sum(chromosome.genes)
            ),
            opt_is_min=opt_is_min,
        )
        self.no_improvement_condition = self.no_exit_condition

    def crossover_func(
        self, c1: Chromosome, c2: Chromosome
    ) -> tuple[Chromosome, Chromosome]:
        """The lowest gene of one parent and the others of the other."""

        def mix(first: Chromosome, second: Chromosome) -> Chromosome:
            genes = sorted(first.genes)[:1] + sorted(second.genes)[1:]
            return Chromosome(
                size=self.chromosome_length,
                genes=set(genes),
                gene_space=self.gene_space,
                is_gene_set=True,
                random_seed=self.random_seed,
            )

        return mix(c1, c2), mix(c2, c1)


def _fit_numbers(opt_is_min: bool) -> tuple[NumbersAlgorithm, FitResult]:
    """Run `NumbersAlgorithm` for 60 generations of 30 Chromosomes."""
    algorithm = NumbersAlgorithm(opt_is_min=opt_is_min)
    result = algorithm.fit(
        FitConfig(
            n_generations=60,
            population_size=30,
            min_population_size=0,
            n_jobs=1,
        ),
        plot_metrics=False,
    )
    return algorithm, result


def test_set_chromosomes_stay_sets_and_the_best_never_gets_worse():
    algorithm, result = _fit_numbers(opt_is_min=False)
    bests = [metric.best["score"].value for metric in result["metrics"]]
    assert len(bests) > 1
    assert bests == sorted(bests)
    assert bests[-1] == 9 + 10 + 11
    # Every set of 3 numbers out of 12.
    space_points = result["fit_metrics"]["fitness_func_calls"]
    assert space_points["space_points"] == 220
    for population in algorithm.historial:
        for _, chromosome in population:
            assert isinstance(chromosome.genes, set)
            assert len(chromosome.genes) == 3
            assert chromosome.genes <= set(range(12))


def test_minimize_keeps_the_lowest_scores():
    algorithm, result = _fit_numbers(opt_is_min=True)
    bests = [metric.best["score"].value for metric in result["metrics"]]
    assert len(bests) > 1
    assert bests == sorted(bests, reverse=True)
    assert bests[-1] == 0 + 1 + 2
    assert result["bests"]["scores"][0].value == 3
    for population in algorithm.historial:
        scores = [score.value for score, _ in population]
        assert scores == sorted(scores)


def test_fit_goes_on_after_a_first_generation_with_mean_score_0():
    result = ZeroStartAlgorithm().fit(
        FitConfig(
            n_generations=3,
            population_size=20,
            mutate_prob=0.5,
            min_population_size=0,
            n_jobs=1,
        ),
        plot_metrics=False,
    )
    assert result["metrics"][0].mean == 0
    assert len(result["metrics"]) > 1


def test_fit_stops_when_the_mean_score_does_not_change():
    # Without mutations every child is all zeros too.
    result = ZeroStartAlgorithm().fit(
        FitConfig(
            n_generations=5,
            population_size=20,
            mutate_prob=0,
            min_population_size=0,
            n_jobs=1,
        ),
        plot_metrics=False,
    )
    assert len(result["metrics"]) == 2


@pytest.mark.parametrize(
    "min_population_size, generations", [(2, 1), (1, 6), (0, 6)]
)
def test_fit_stops_below_min_population_size(
    min_population_size, generations
):
    # Without mutations every Chromosome is all zeros: 1 different one.
    algorithm = ZeroStartAlgorithm()
    algorithm.no_improvement_condition = algorithm.no_exit_condition
    result = algorithm.fit(
        FitConfig(
            n_generations=5,
            population_size=20,
            mutate_prob=0,
            min_population_size=min_population_size,
            n_jobs=1,
        ),
        plot_metrics=False,
    )
    assert [metric.n_uniques for metric in result["metrics"]] == [1] * (
        generations
    )


def test_fit_scores_each_chromosome_once(tmp_path):
    # The fitness function runs in worker processes, so the calls are
    # counted through a file.
    calls_log = tmp_path / "calls.log"
    genetic_bag = GeneticBag(
        weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        capacity=165,
    )
    fit_bag = genetic_bag.algo_fitness_func

    def logged_fit_bag(chromosome):
        with open(calls_log, "a") as file:
            file.write(f"{chromosome!r}\n")
        return fit_bag(chromosome)

    genetic_bag.algo_fitness_func = logged_fit_bag
    # Two jobs, or the one that a machine with one core allows.
    result = genetic_bag.fit(
        FitConfig(
            n_generations=5, population_size=50, n_jobs=min(2, cpu_count())
        ),
        plot_metrics=False,
    )
    calls = calls_log.read_text().splitlines()
    assert calls
    assert len(calls) == len(set(calls))
    assert (
        len(calls) == result["fit_metrics"]["fitness_func_calls"]["processed"]
    )


def test_crossover_cuts_at_every_position_between_two_genes():
    size = 5
    genetic_bag = GeneticBag(
        weights=[1] * size, values=[1] * size, capacity=size
    )
    zeros = Chromosome(size=size, genes=[0] * size)
    ones = Chromosome(size=size, genes=[1] * size)
    cuts = set()
    for _ in range(200):
        first, second = genetic_bag.crossover_func(zeros, ones)
        cut = first.genes.index(1)
        assert first.genes == [0] * cut + [1] * (size - cut)
        assert second.genes == [1] * cut + [0] * (size - cut)
        cuts.add(cut)
    assert cuts == {1, 2, 3, 4}


def test_crossover_of_two_genes_swaps_the_second_one():
    genetic_bag = GeneticBag(weights=[1, 2], values=[3, 4], capacity=3)
    first, second = genetic_bag.crossover_func(
        Chromosome(size=2, genes=[0, 0]), Chromosome(size=2, genes=[1, 1])
    )
    assert first.genes == [0, 1]
    assert second.genes == [1, 0]


def test_crossover_of_one_gene_returns_the_same_genes():
    genetic_bag = GeneticBag(weights=[1], values=[3], capacity=3)
    first, second = genetic_bag.crossover_func(
        Chromosome(size=1, genes=[0]), Chromosome(size=1, genes=[1])
    )
    assert first.genes == [0]
    assert second.genes == [1]


def test_crossover_children_carry_the_seed_of_the_run():
    genetic_bag = GeneticBag(
        weights=[1] * 5, values=[1] * 5, capacity=5, random_seed=7
    )
    children = genetic_bag.crossover_func(
        Chromosome(size=5, genes=[0] * 5), Chromosome(size=5, genes=[1] * 5)
    )
    assert [child.random_seed for child in children] == [7, 7]
    assert [child.is_gene_set for child in children] == [False, False]


class OnesGeneSpace(AbstractGeneSpace):
    """Gene space of one symbol, so a mutated gene is always a 1."""

    def __len__(self) -> int:
        return 1

    def select_random(self, n=None) -> int | list[int]:
        return 1 if n is None else [1] * n


class RangeGeneSpace(AbstractGeneSpace):
    """Gene space of the numbers 0 to 19 that records how it is called."""

    def __init__(self):
        super().__init__(random_seed=7)
        self.calls: list[int | None] = []

    def __len__(self) -> int:
        return 20

    def select_random(self, n=None):
        self.calls.append(n)
        return self.random_state.choice(20, size=n)


def test_list_mutation_draws_its_new_genes_with_one_call():
    size = 40
    gene_space = RangeGeneSpace()
    chromosome = Chromosome(size=size, genes=[-1] * size).random_mutate(
        gene_space=gene_space, gene_mutate_prob=0.5
    )
    n_mutated = sum(gene != -1 for gene in chromosome.genes)
    assert 1 < n_mutated < size
    assert gene_space.calls == [n_mutated]
    assert all(type(gene) is int for gene in chromosome.genes)


@pytest.mark.parametrize("probability, n_mutated", [(0, 0), (1, 40)])
def test_list_mutation_with_probability_0_and_1(probability, n_mutated):
    gene_space = RangeGeneSpace()
    chromosome = Chromosome(size=40, genes=[-1] * 40).random_mutate(
        gene_space=gene_space, gene_mutate_prob=probability
    )
    assert sum(gene != -1 for gene in chromosome.genes) == n_mutated
    assert gene_space.calls == ([n_mutated] if n_mutated else [])


def test_set_mutation_with_probability_0_keeps_every_gene():
    gene_space = RangeGeneSpace()
    chromosome = Chromosome(
        size=8, genes=set(range(100, 108)), is_gene_set=True
    ).random_mutate(gene_space=gene_space, gene_mutate_prob=0)
    assert chromosome.genes == set(range(100, 108))
    assert gene_space.calls == []


def test_set_mutation_with_probability_1_replaces_every_gene():
    gene_space = RangeGeneSpace()
    chromosome = Chromosome(
        size=8, genes=set(range(100, 108)), is_gene_set=True
    ).random_mutate(gene_space=gene_space, gene_mutate_prob=1)
    assert isinstance(chromosome.genes, set)
    assert len(chromosome.genes) == 8
    assert chromosome.genes <= set(range(20))
    # Equal new genes are drawn again until the set has 8.
    assert gene_space.calls[0] == 8


def test_set_mutation_keeps_the_size_of_the_set():
    gene_space = RangeGeneSpace()
    unmutated = Chromosome(
        size=8, genes=set(range(100, 108)), is_gene_set=True
    )
    chromosome = unmutated.random_mutate(
        gene_space=gene_space, gene_mutate_prob=0.5
    )
    assert unmutated.genes == set(range(100, 108))
    assert isinstance(chromosome.genes, set)
    assert len(chromosome.genes) == 8
    kept = chromosome.genes & set(range(100, 108))
    assert 0 < len(kept) < 8
    assert chromosome.genes - kept <= set(range(20))


def test_a_set_as_large_as_its_gene_space_holds_every_gene():
    gene_space = RangeGeneSpace()
    chromosome = Chromosome(size=20, gene_space=gene_space, is_gene_set=True)
    assert isinstance(chromosome.genes, set)
    assert chromosome.genes == set(range(20))
    mutated = chromosome.random_mutate(
        gene_space=gene_space, gene_mutate_prob=0.5
    )
    assert mutated.genes == set(range(20))


def test_a_chromosome_built_from_a_gene_space_draws_with_one_call():
    gene_space = RangeGeneSpace()
    chromosome = Chromosome(size=12, gene_space=gene_space)
    assert gene_space.calls == [12]
    assert len(chromosome.genes) == 12
    assert set(chromosome.genes) <= set(range(20))


def test_mutation_differs_between_chromosomes():
    size = 40
    genetic_bag = GeneticBag(
        weights=[1] * size, values=[1] * size, capacity=10
    )
    genetic_bag.gene_space = OnesGeneSpace()
    chromosomes = [Chromosome(size=size, genes=[0] * size) for _ in range(2)]
    first, second = genetic_bag.mutate_chromosomes(
        chromosomes, mutate_prob=0.5
    )
    assert first.genes != second.genes


def test_a_chromosome_builds_its_random_state_on_first_use():
    size = 40
    unused = Chromosome(size=size, genes=[0] * size)
    unused_bytes = len(pickle.dumps(unused))
    # Two Chromosomes with one seed and no state given mutate alike.
    first, second = (
        Chromosome(size=size, genes=[0] * size).random_mutate(
            gene_space=OnesGeneSpace(), gene_mutate_prob=0.5
        )
        for _ in range(2)
    )
    assert 0 < sum(first.genes) < size
    assert first.genes == second.genes
    # The state is some 3 KB of a pickled Chromosome.
    assert unused_bytes < 1000 < len(pickle.dumps(first))


def test_a_mutated_chromosome_gets_a_new_id():
    size = 40
    unmutated = Chromosome(size=size, genes=[0] * size)
    unmutated_id = unmutated.id
    chromosome = unmutated.random_mutate(
        gene_space=OnesGeneSpace(), gene_mutate_prob=0.5
    )
    assert chromosome.id != unmutated_id
    same_genes = Chromosome(size=size, genes=list(chromosome.genes))
    assert chromosome.id == same_genes.id
    assert hash(chromosome) == hash(same_genes)
    assert chromosome == same_genes


def test_mutation_leaves_the_chromosome_as_it_was():
    size = 40
    chromosome = Chromosome(size=size, genes=[0] * size)
    chromosome.score, chromosome.score_time = Score(value=3), 0.5
    by_chromosome = {chromosome: "kept"}
    mutated = chromosome.random_mutate(
        gene_space=OnesGeneSpace(), gene_mutate_prob=0.5
    )
    assert mutated is not chromosome
    assert 0 < sum(mutated.genes) < size
    assert mutated.score is None
    assert mutated.score_time == 0
    assert chromosome.genes == [0] * size
    assert chromosome.score.value == 3
    assert by_chromosome[chromosome] == "kept"


def test_the_mutation_invariant_gets_the_chromosome_before_and_after():
    size = 40
    genetic_bag = GeneticBag(
        weights=[1] * size, values=[1] * size, capacity=10
    )
    genetic_bag.gene_space = OnesGeneSpace()
    pairs: list[tuple[list[int], list[int]]] = []

    def record(before: Chromosome, after: Chromosome) -> bool:
        pairs.append((list(before.genes), list(after.genes)))
        return True

    genetic_bag.mutation_invariant = record
    genetic_bag.mutate_chromosomes(
        [Chromosome(size=size, genes=[0] * size)], mutate_prob=0.5
    )
    ((before, after),) = pairs
    assert before == [0] * size
    assert 0 < sum(after) < size


@pytest.mark.parametrize(
    "invariant", ["mutation_invariant", "crossover_invariant"]
)
def test_a_broken_invariant_stops_the_run(invariant):
    genetic_bag, _ = _counting_bag()
    setattr(genetic_bag, invariant, lambda *_: False)
    with pytest.raises(InvariantException, match="mutated to"):
        genetic_bag.fit(
            FitConfig(
                n_generations=3,
                population_size=30,
                mutate_prob=0.5,
                n_jobs=1,
            ),
            plot_metrics=False,
        )


def test_the_bag_refuses_weights_and_values_of_different_lengths():
    with pytest.raises(ValidationException, match="must be the same"):
        GeneticBag(weights=[1, 2], values=[3], capacity=3)


# The same bags are decoded in `crates/genetic_opt/tests/algorithm.rs`,
# `knapsack_decodes_known_bags`.
KNOWN_BAGS = [
    ([0] * 10, [0] * 10, 0),
    ([1, 1, 1, 1, 0, 1, 0, 0, 0, 0], [1, 1, 1, 1, 0, 1, 0, 0, 0, 0], 309),
    ([1] * 10, [1, 1, 1, 1, 0, 0, 0, 0, 0, 0], 266),
    ([0, 0, 0, 0, 0, 0, 0, 1, 1, 0], [0, 0, 0, 0, 0, 0, 0, 1, 0, 0], 84),
]


@pytest.mark.parametrize("genes, decoded, value", KNOWN_BAGS)
def test_the_bag_decodes_and_scores_known_bags(genes, decoded, value):
    genetic_bag = GeneticBag(
        weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        capacity=165,
    )
    chromosome = Chromosome(size=10, genes=genes)
    assert genetic_bag.decode_func(chromosome) == decoded
    assert genetic_bag.algo_fitness_func(chromosome).value == value


def test_the_bag_takes_nothing_after_the_first_object_that_does_not_fit():
    genetic_bag = GeneticBag(
        weights=[5, 10, 1], values=[1, 1, 1], capacity=12
    )
    chromosome = Chromosome(size=3, genes=[1, 1, 1])
    assert genetic_bag.decode_func(chromosome) == [1, 0, 0]


def test_fit_without_a_save_path_decodes_the_population_once():
    genetic_bag, _ = _counting_bag()
    decode_bag = genetic_bag.decode_func
    decoded: list[str] = []

    def counted_decode_bag(chromosome):
        decoded.append(repr(chromosome))
        return decode_bag(chromosome)

    genetic_bag.decode_func = counted_decode_bag
    population_size = 50
    result = genetic_bag.fit(
        FitConfig(n_generations=5, population_size=population_size, n_jobs=1),
        plot_metrics=False,
    )
    generations = len(result["metrics"])
    assert generations > 1
    assert len(result["last_population"]) == population_size
    # The best of each generation for its metrics, then the bests and
    # the last population when the run ends.
    n_bests = len(result["bests"]["result"])
    assert len(decoded) == generations + n_bests + population_size


def test_the_fitness_function_of_the_bag_travels_without_the_bag():
    genetic_bag = GeneticBag(
        weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        capacity=165,
    )
    sent_bytes = len(cloudpickle.dumps(genetic_bag.algo_fitness_func))
    genetic_bag.fit(
        FitConfig(n_generations=5, population_size=50, n_jobs=1),
        plot_metrics=False,
    )
    assert len(cloudpickle.dumps(genetic_bag.algo_fitness_func)) == sent_bytes


def _counting_bag() -> tuple[GeneticBag, list[str]]:
    """A knapsack whose fitness function records each Chromosome it runs on."""
    genetic_bag = GeneticBag(
        weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        capacity=165,
    )
    fit_bag = genetic_bag.algo_fitness_func
    calls: list[str] = []

    def counted_fit_bag(chromosome):
        calls.append(repr(chromosome))
        return fit_bag(chromosome)

    genetic_bag.algo_fitness_func = counted_fit_bag
    return genetic_bag, calls


def test_fit_metrics_count_the_fitness_calls():
    # One process, so the fitness function runs here and `calls` fills.
    genetic_bag, calls = _counting_bag()
    result = genetic_bag.fit(
        FitConfig(n_generations=5, population_size=50, n_jobs=1),
        plot_metrics=False,
    )
    counted = result["fit_metrics"]["fitness_func_calls"]
    assert calls
    assert counted["processed"] == len(calls)
    # 50 Chromosomes in the first population and 34 children in each
    # later generation: 2 * int((0.7 * 50) // 2).
    later_generations = len(result["metrics"]) - 1
    assert later_generations > 0
    assert counted["total"] == 50 + 34 * later_generations
    assert counted["cached"] == counted["total"] - counted["processed"]
    assert counted["percent_processed"] == round(
        100 * counted["processed"] / counted["total"], 2
    )
    assert 0 < counted["percent_processed"] <= 100
    # Every list of 10 genes out of 2.
    assert counted["space_points"] == 1024
    assert counted["exploration_percentage"] == round(
        100 * counted["processed"] / 1024, 2
    )


def test_a_second_fit_starts_a_new_run():
    genetic_bag, calls = _counting_bag()
    config = FitConfig(n_generations=3, population_size=30, n_jobs=1)
    first = genetic_bag.fit(config, plot_metrics=False)
    first_calls = len(calls)
    assert first["fit_metrics"]["fitness_func_calls"]["processed"] == (
        first_calls
    )
    result = genetic_bag.fit(config, plot_metrics=False)
    generations = len(result["metrics"])
    assert 1 < generations <= 4
    assert len(result["historial"]) == generations
    # 30 Chromosomes in the first population and 20 children in each
    # later generation: 2 * int((0.7 * 30) // 2).
    counted = result["fit_metrics"]["fitness_func_calls"]
    assert counted["total"] == 30 + 20 * (generations - 1)
    # A Chromosome the first run scored is not scored again.
    assert len(calls) == len(set(calls))
    assert counted["processed"] == len(calls) - first_calls


def _bag_run_genes(n_jobs: int, **seeds: int) -> list[list[list[int]]]:
    """The genes of each population of a run of a new knapsack."""
    genetic_bag = GeneticBag(
        weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        capacity=165,
        **seeds,
    )
    genetic_bag.no_improvement_condition = genetic_bag.no_exit_condition
    result = genetic_bag.fit(
        FitConfig(n_generations=5, population_size=30, n_jobs=n_jobs),
        plot_metrics=False,
    )
    return [
        [list(chromosome.genes) for _, chromosome in population]
        for population in result["historial"]
    ]


def test_one_seed_gives_the_same_run_with_any_number_of_jobs():
    first = _bag_run_genes(n_jobs=1)
    assert len(first) == 6
    assert _bag_run_genes(n_jobs=1) == first
    # Two jobs, or the one that a machine with one core allows.
    assert _bag_run_genes(n_jobs=min(2, cpu_count())) == first


def test_another_seed_gives_another_run():
    assert _bag_run_genes(n_jobs=1) != _bag_run_genes(
        n_jobs=1, random_seed=7, gene_space_random_seed=8
    )


def test_fit_gives_the_algorithm_to_the_callback_and_the_exit_condition():
    genetic_bag, _ = _counting_bag()
    genetic_bag.no_improvement_condition = genetic_bag.no_exit_condition
    seen: list[GeneticBag] = []
    result = genetic_bag.fit(
        FitConfig(n_generations=5, population_size=30, n_jobs=1),
        plot_metrics=False,
        callback_func=seen.append,
        exit_condition=lambda algorithm: len(algorithm.metrics) == 2,
    )
    assert len(result["metrics"]) == 2
    assert len(seen) == 2
    assert all(algorithm is genetic_bag for algorithm in seen)


class CallbackCountingBag(GeneticBag):
    callbacks = 0

    def default_fit_callback(self) -> None:
        self.callbacks += 1


def test_fit_calls_the_callback_method_of_a_subclass_by_default():
    genetic_bag = CallbackCountingBag(
        weights=[23, 31, 29, 44], values=[92, 57, 49, 68], capacity=80
    )
    genetic_bag.no_improvement_condition = genetic_bag.no_exit_condition
    result = genetic_bag.fit(
        FitConfig(
            n_generations=2,
            population_size=10,
            min_population_size=2,
            n_jobs=1,
        ),
        plot_metrics=False,
    )
    assert genetic_bag.callbacks == len(result["metrics"]) == 3


def test_sorting_starts_no_workers_when_no_chromosome_is_new(monkeypatch):
    # Two genes give 4 Chromosomes, so the first population has them all.
    genetic_bag = GeneticBag(weights=[1, 2], values=[3, 4], capacity=3)
    fit_bag = genetic_bag.algo_fitness_func
    calls: list[str] = []

    def counted_fit_bag(chromosome):
        calls.append(repr(chromosome))
        return fit_bag(chromosome)

    genetic_bag.algo_fitness_func = counted_fit_bag
    parallel_calls: list[dict] = []

    def counted_parallel(**kwargs):
        parallel_calls.append(kwargs)
        return Parallel(**kwargs)

    monkeypatch.setattr(algorithms, "Parallel", counted_parallel)
    genetic_bag.init_population(population_size=50, n_jobs=1)
    assert len(calls) == 4
    genetic_bag.init_population(population_size=50, n_jobs=1)
    assert len(calls) == 4
    assert parallel_calls == [{"n_jobs": 1}]
    assert len(genetic_bag.population) == 50
    assert all(c.score is not None for c in genetic_bag.population)


@pytest.mark.parametrize(
    "level, logged", [(logging.INFO, True), (logging.WARNING, False)]
)
def test_fit_formats_the_metrics_only_when_they_are_logged(
    monkeypatch, set_log_level, level, logged
):
    genetic_bag = GeneticBag(
        weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        capacity=165,
    )
    formatted: list = []
    log_format = algorithms.log_format

    def counted_log_format(d, **kwargs):
        formatted.append(d)
        return log_format(d, **kwargs)

    monkeypatch.setattr(algorithms, "log_format", counted_log_format)
    set_log_level(level)
    result = genetic_bag.fit(
        FitConfig(n_generations=3, population_size=50, n_jobs=1)
    )
    metrics = [d for d in formatted if isinstance(d, Metric)]
    assert metrics == (result["metrics"] if logged else [])


def test_get_space_points_counts_lists_and_sets():
    assert get_space_points(2, 10, is_gene_set=False) == 1024
    assert get_space_points(12, 3, is_gene_set=True) == 220
    assert get_space_points(12, 12, is_gene_set=True) == 1
    assert get_space_points(2, 2000, is_gene_set=False) == float("inf")


@pytest.mark.parametrize(
    "parameters",
    [
        {"population_size": 0, "min_population_size": 0},
        {"crossovers_prop": 1.5},
        {"besties_prop": -0.1},
        {"mutate_prob": float("nan")},
        {"min_population_size": 31},
    ],
)
def test_fit_refuses_parameters_out_of_range(parameters):
    genetic_bag, calls = _counting_bag()
    fit_parameters = {"n_generations": 5, "population_size": 30, "n_jobs": 1}
    with pytest.raises(ValidationException):
        genetic_bag.fit(FitConfig(**(fit_parameters | parameters)))
    assert not calls


@pytest.mark.parametrize(
    "cores, parameters", [(1, {}), (1, {"n_jobs": -1}), (2, {"n_jobs": -4})]
)
def test_fit_uses_one_job_when_fewer_are_left(monkeypatch, cores, parameters):
    # Without `n_jobs` it is -2: every core but one.
    monkeypatch.setattr(algorithms, "cpu_count", lambda: cores)
    genetic_bag, _ = _counting_bag()
    result = genetic_bag.fit(
        FitConfig(n_generations=2, population_size=20, **parameters),
        plot_metrics=False,
    )
    assert result["fit_parameters"]["n_jobs"] == 1


def test_fit_parameters_are_the_config_with_the_seed_and_the_jobs():
    genetic_bag, _ = _counting_bag()
    result = genetic_bag.fit(
        FitConfig(n_generations=2, population_size=20, n_jobs=1),
        plot_metrics=False,
    )
    assert result["fit_parameters"] == {
        "n_generations": 2,
        "population_size": 20,
        "crossovers_prop": 0.7,
        "besties_prop": 0.6,
        "mutate_prob": 0.05,
        "min_population_size": 10,
        "n_jobs": 1,
        "random_seed": 666,
    }


@pytest.mark.parametrize("n_jobs", [0, 3])
def test_fit_refuses_no_jobs_and_more_jobs_than_cores(monkeypatch, n_jobs):
    monkeypatch.setattr(algorithms, "cpu_count", lambda: 2)
    genetic_bag, calls = _counting_bag()
    with pytest.raises(ValidationException, match="n_jobs"):
        genetic_bag.fit(
            FitConfig(n_generations=2, population_size=20, n_jobs=n_jobs)
        )
    assert not calls


def test_get_chromosome_score_runs_the_fitness_function_once():
    genetic_bag, calls = _counting_bag()
    genes = [1, 1, 1, 1, 0, 1, 0, 0, 0, 0]
    first = Chromosome(size=10, genes=list(genes))
    same_genes = Chromosome(size=10, genes=list(genes))
    assert genetic_bag.get_chromosome_score(first).value == 309
    assert genetic_bag.get_chromosome_score(first).value == 309
    assert genetic_bag.get_chromosome_score(same_genes).value == 309
    assert len(calls) == 1


def test_chromosomes_sharing_an_id_keep_their_own_scores(monkeypatch):
    genetic_bag, _ = _counting_bag()
    config = FitConfig(n_generations=5, population_size=30, n_jobs=1)
    expected = genetic_bag.fit(config, plot_metrics=False)["bests"]["scores"]

    # Every Chromosome gets one id, as two would after a hash collision.
    monkeypatch.setattr(Chromosome, "id", property(lambda self: 1))
    genetic_bag, calls = _counting_bag()
    in_bag = Chromosome(size=10, genes=[1, 1, 1, 1, 0, 1, 0, 0, 0, 0])
    empty = Chromosome(size=10, genes=[0] * 10)
    assert genetic_bag.get_chromosome_score(in_bag).value == 309
    assert genetic_bag.get_chromosome_score(empty).value == 0
    assert len(calls) == 2

    genetic_bag, _ = _counting_bag()
    scores = genetic_bag.fit(config, plot_metrics=False)["bests"]["scores"]
    assert [s.value for s in scores] == [s.value for s in expected]


def test_scoring_does_not_keep_the_algorithm_alive():
    genetic_bag, _ = _counting_bag()
    genetic_bag.fit(
        FitConfig(n_generations=2, population_size=20, n_jobs=1),
        plot_metrics=False,
    )
    reference = weakref.ref(genetic_bag)
    del genetic_bag
    gc.collect()
    assert reference() is None

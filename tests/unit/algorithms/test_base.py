import gc
import logging
import os
import subprocess
import sys
import time
import weakref
from os import cpu_count
from pathlib import Path
from typing import ClassVar

import pytest
from joblib import Parallel
from joblib.externals import cloudpickle

from genetic_opt.algorithms import FitConfig
from genetic_opt.algorithms import base as algorithms
from genetic_opt.algorithms.binary import BinaryGeneticAlgorithm
from genetic_opt.chromosome import Chromosome
from genetic_opt.examples.binary import Knapsack
from genetic_opt.exceptions import (
    InvariantException,
    ValidationException,
)
from genetic_opt.gene_space import ValuesGeneSpace
from genetic_opt.metrics import Metric
from genetic_opt.runs.fit_result import (
    FitResult,
)
from genetic_opt.runs.fit_result_io import load_fit_result
from genetic_opt.score import Score
from tests.unit.conftest import (
    NumbersAlgorithm,
    OnesGeneSpace,
    count_ones,
    decode_genes,
    ones_algorithm,
)

# ── GeneticAlgorithm Tests ─────────────────────────────────────────────


@pytest.fixture
def score_in_workers(monkeypatch):
    """Send every batch to the workers, however fast the scores are."""
    monkeypatch.setattr(algorithms, "IN_PROCESS_SECONDS", 0)


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
            minimize=False,
        )

    def init_population(self, population_size: int) -> list[list[int]]:
        return [[0] * self.chromosome_length for _ in range(population_size)]


class EmptyStartAlgorithm(ZeroStartAlgorithm):
    """Its first population has no Chromosomes."""

    def init_population(self, population_size: int) -> list[list[int]]:
        return []


def test_fit_refuses_a_first_population_without_chromosomes():
    with pytest.raises(ValidationException, match="empty population"):
        EmptyStartAlgorithm().fit(
            FitConfig(n_generations=3, population_size=20, n_jobs=1),
        )


class NotFiniteStartAlgorithm(ZeroStartAlgorithm):
    """Its first population has a Chromosome whose score is `value`."""

    def __init__(self, value: float):
        super().__init__()
        self.fitness_func = lambda chromosome: Score(
            value=value if sum(chromosome.genes) == 0 else 1.0
        )


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_fit_refuses_a_score_that_is_not_finite(value):
    algorithm = NotFiniteStartAlgorithm(float(value))
    config = FitConfig(
        n_generations=3, population_size=4, min_population_size=1, n_jobs=1
    )
    message = (
        rf"the fitness function gave a score that is not finite, {value}, "
        r"to the Chromosome \[0, 0, 0, 0, 0, 0, 0, 0, 0, 0\]"
    )
    # The score is not cached, so a second run is refused too
    for _ in range(2):
        with pytest.raises(ValidationException, match=message):
            algorithm.fit(config)


def test_fit_refuses_an_int_score_too_large_for_a_float():
    algorithm = NotFiniteStartAlgorithm(10**400)
    config = FitConfig(
        n_generations=3, population_size=4, min_population_size=1, n_jobs=1
    )
    with pytest.raises(ValidationException, match="not finite, 1000"):
        algorithm.fit(config)


def test_fit_with_0_generations_scores_the_first_population_only():
    algorithm = ZeroStartAlgorithm()
    result = algorithm.fit(
        FitConfig(n_generations=0, population_size=20, n_jobs=1),
    )
    assert len(result["metrics"]) == 1
    assert len(algorithm.history) == 1
    assert result["fit_parameters"]["n_generations"] == 0
    assert result["bests"]["scores"] == [Score(value=0)]
    assert len(result["last_population"]) == 20


class PairsStartAlgorithm(ZeroStartAlgorithm):
    """Its first population holds 0 to 9 ones, each twice."""

    def __init__(self, minimize: bool):
        super().__init__()
        self.minimize = minimize

    def init_population(self, population_size: int) -> list[list[int]]:
        return [
            [1] * ones + [0] * (self.chromosome_length - ones)
            for ones in range(10)
            for _ in range(2)
        ]


@pytest.mark.parametrize(
    ("minimize", "expected"),
    [(False, [9, 8, 7, 6, 5]), (True, [0, 1, 2, 3, 4])],
)
def test_bests_are_unique_at_most_n_bests_and_best_first(minimize, expected):
    result = PairsStartAlgorithm(minimize=minimize).fit(
        FitConfig(n_generations=0, population_size=20, n_jobs=1),
    )
    assert algorithms.N_BESTS == len(expected)
    assert [s.value for s in result["bests"]["scores"]] == expected
    assert [sum(genes) for genes in result["bests"]["result"]] == expected


def _fit_numbers(minimize: bool) -> tuple[NumbersAlgorithm, FitResult]:
    """Run `NumbersAlgorithm` for 60 generations of 30 Chromosomes."""
    algorithm = NumbersAlgorithm(minimize=minimize)
    result = algorithm.fit(
        FitConfig(
            n_generations=60,
            population_size=30,
            min_population_size=0,
            stop_without_improvement=False,
            n_jobs=1,
        ),
    )
    return algorithm, result


def test_set_chromosomes_stay_sets_and_the_best_never_gets_worse():
    algorithm, result = _fit_numbers(minimize=False)
    bests = [metric.best.score.value for metric in result["metrics"]]
    assert len(bests) > 1
    assert bests == sorted(bests)
    assert bests[-1] == 9 + 10 + 11
    # Every set of 3 numbers out of 12.
    space_points = result["fit_metrics"]["fitness_func_calls"]
    assert space_points["space_points"] == 220
    for population in algorithm.history:
        for _, chromosome in population:
            assert isinstance(chromosome.genes, set)
            assert len(chromosome.genes) == 3
            assert chromosome.genes <= set(range(12))


def test_minimize_keeps_the_lowest_scores():
    algorithm, result = _fit_numbers(minimize=True)
    bests = [metric.best.score.value for metric in result["metrics"]]
    assert len(bests) > 1
    assert bests == sorted(bests, reverse=True)
    assert bests[-1] == 0 + 1 + 2
    assert result["bests"]["scores"][0].value == 3
    for population in algorithm.history:
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
    )
    assert len(result["metrics"]) == 2
    assert result["stop_reason"] == "no_improvement"


def test_no_improvement_condition_is_not_met_before_two_generations():
    assert not ZeroStartAlgorithm().no_improvement_condition()


def test_fit_without_the_improvement_stop_breeds_every_generation():
    algorithm = ZeroStartAlgorithm()
    result = algorithm.fit(
        FitConfig(
            n_generations=5,
            population_size=20,
            mutate_prob=0,
            min_population_size=0,
            stop_without_improvement=False,
            n_jobs=1,
        ),
    )
    assert len(result["metrics"]) == 6
    assert result["stop_reason"] == "completed"
    assert algorithm.no_improvement_condition()
    assert "stop_without_improvement" not in result["fit_parameters"]


@pytest.mark.parametrize(
    "max_seconds, generations, stop_reason",
    [(0, 1, "max_seconds"), (3600, 6, "completed")],
)
def test_fit_stops_after_max_seconds(max_seconds, generations, stop_reason):
    result = ZeroStartAlgorithm().fit(
        FitConfig(
            n_generations=5,
            population_size=20,
            min_population_size=0,
            stop_without_improvement=False,
            n_jobs=1,
            max_seconds=max_seconds,
        ),
    )
    assert len(result["metrics"]) == generations
    assert result["stop_reason"] == stop_reason
    assert "max_seconds" not in result["fit_parameters"]


@pytest.mark.parametrize(
    "max_stale_generations, generations", [(2, 3), (0, 1)]
)
def test_fit_stops_after_max_stale_generations(
    max_stale_generations, generations
):
    # Without mutations every child is all zeros: no better best score.
    algorithm = ZeroStartAlgorithm()
    result = algorithm.fit(
        FitConfig(
            n_generations=5,
            population_size=20,
            mutate_prob=0,
            min_population_size=0,
            stop_without_improvement=False,
            n_jobs=1,
            max_stale_generations=max_stale_generations,
        ),
    )
    assert len(result["metrics"]) == generations
    assert result["stop_reason"] == "stale_generations"
    assert algorithm.stale_generations() == generations - 1
    assert "max_stale_generations" not in result["fit_parameters"]


@pytest.mark.parametrize("minimize", [False, True])
def test_a_better_best_score_ends_the_stale_generations(minimize):
    algorithm = NumbersAlgorithm(minimize=minimize)
    # A worse best score is stale too, as an equal one is.
    bests = [5, 3, 3, 6, 1, 1, 1] if minimize else [5, 7, 7, 4, 9, 9, 9]
    stale = []
    for value in bests:
        # A population of one, whose score is the best of the generation
        chromosome = Chromosome(size=1, genes={value}, is_gene_set=True)
        chromosome.score = Score(value=value)
        algorithm.population = [chromosome]
        algorithm._update_metrics(generation_fitting_time=0)
        stale.append(algorithm.stale_generations())
    assert stale == [0, 0, 1, 2, 0, 1, 2]


def test_fit_logs_that_max_stale_generations_stopped_it(
    caplog, set_log_level
):
    set_log_level(logging.INFO)
    ZeroStartAlgorithm().fit(
        FitConfig(
            n_generations=5,
            population_size=20,
            mutate_prob=0,
            min_population_size=0,
            stop_without_improvement=False,
            n_jobs=1,
            max_stale_generations=2,
        ),
    )
    assert (
        "the run stopped after generation 2: no better best score for 2 "
        "generations" in caplog.text
    )


def test_fit_logs_that_max_seconds_stopped_it(caplog, set_log_level):
    set_log_level(logging.INFO)
    ZeroStartAlgorithm().fit(
        FitConfig(
            n_generations=5,
            population_size=20,
            min_population_size=0,
            n_jobs=1,
            max_seconds=0,
        ),
    )
    assert (
        "the run stopped after generation 0: 0 seconds reached" in caplog.text
    )


@pytest.mark.parametrize(
    "min_population_size, generations, stop_reason",
    [(2, 1, "min_population"), (1, 6, "completed"), (0, 6, "completed")],
)
def test_fit_stops_below_min_population_size(
    min_population_size, generations, stop_reason
):
    # Without mutations every Chromosome is all zeros: 1 different one.
    result = ZeroStartAlgorithm().fit(
        FitConfig(
            n_generations=5,
            population_size=20,
            mutate_prob=0,
            min_population_size=min_population_size,
            stop_without_improvement=False,
            n_jobs=1,
        ),
    )
    assert [metric.n_uniques for metric in result["metrics"]] == [1] * (
        generations
    )
    assert result["stop_reason"] == stop_reason


def test_fit_scores_each_chromosome_once(tmp_path, score_in_workers):
    # The fitness function runs in worker processes, so the calls are
    # counted through a file.
    calls_log = tmp_path / "calls.log"
    knapsack = Knapsack(
        weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        capacity=165,
    )
    fitness = knapsack.fitness_func

    def logged_fitness(chromosome):
        with open(calls_log, "a") as file:
            file.write(f"{chromosome!r}\n")
        return fitness(chromosome)

    knapsack.fitness_func = logged_fitness
    # Two jobs, or the one that a machine with one core allows.
    result = knapsack.fit(
        FitConfig(
            n_generations=5, population_size=50, n_jobs=min(2, cpu_count())
        ),
    )
    calls = calls_log.read_text().splitlines()
    assert calls
    assert len(calls) == len(set(calls))
    assert (
        len(calls) == result["fit_metrics"]["fitness_func_calls"]["processed"]
    )


def broken_fitness(chromosome):
    raise ArithmeticError(f"a bug scoring {chromosome!r}")


@pytest.mark.parametrize("n_jobs", [1, min(2, cpu_count())])
def test_an_error_of_the_fitness_function_stops_the_run(
    tmp_path, n_jobs, score_in_workers
):
    algorithm = ones_algorithm(tmp_path)
    algorithm.fitness_func = broken_fitness
    config = FitConfig(n_generations=2, population_size=20, n_jobs=n_jobs)
    # Raised as it is, from the worker process that scored it.
    with pytest.raises(ArithmeticError, match="a bug scoring"):
        algorithm.fit(config)

    # The workers of the broken run do not stay in the way of the next.
    algorithm.fitness_func = count_ones
    assert algorithm.fit(config)["bests"]["scores"]


def test_mutation_differs_between_chromosomes():
    size = 40
    knapsack = Knapsack(weights=[1] * size, values=[1] * size, capacity=10)
    knapsack.gene_space = OnesGeneSpace()
    chromosomes = [Chromosome(size=size, genes=[0] * size) for _ in range(2)]
    first, second = knapsack.mutate_chromosomes(chromosomes, mutate_prob=0.5)
    assert first.genes != second.genes


def test_the_mutation_invariant_gets_the_chromosome_before_and_after():
    size = 40
    knapsack = Knapsack(weights=[1] * size, values=[1] * size, capacity=10)
    knapsack.gene_space = OnesGeneSpace()
    pairs: list[tuple[list[int], list[int]]] = []

    def record(before: Chromosome, after: Chromosome) -> bool:
        pairs.append((list(before.genes), list(after.genes)))
        return True

    knapsack.mutation_invariant = record
    knapsack.mutate_chromosomes(
        [Chromosome(size=size, genes=[0] * size)], mutate_prob=0.5
    )
    ((before, after),) = pairs
    assert before == [0] * size
    assert 0 < sum(after) < size


@pytest.mark.parametrize(
    "invariant, message",
    [
        ("mutation_invariant", "mutated to"),
        ("crossover_invariant", "crossed to"),
    ],
)
def test_a_broken_invariant_stops_the_run(invariant, message):
    knapsack, _ = _counting_bag()
    setattr(knapsack, invariant, lambda *_: False)
    with pytest.raises(InvariantException, match=message):
        knapsack.fit(
            FitConfig(
                n_generations=3,
                population_size=30,
                mutate_prob=0.5,
                n_jobs=1,
            ),
        )


def test_fit_without_a_save_path_decodes_the_population_once():
    knapsack, _ = _counting_bag()
    decode = knapsack.decode_func
    decoded: list[str] = []

    def counted_decode(chromosome):
        decoded.append(repr(chromosome))
        return decode(chromosome)

    knapsack.decode_func = counted_decode
    population_size = 50
    result = knapsack.fit(
        FitConfig(n_generations=5, population_size=population_size, n_jobs=1),
    )
    generations = len(result["metrics"])
    assert generations > 1
    assert len(result["last_population"]) == population_size
    # The best of each generation for its metrics, then the bests and
    # the last population when the run ends.
    n_bests = len(result["bests"]["result"])
    assert len(decoded) == generations + n_bests + population_size


def _counting_bag() -> tuple[Knapsack, list[str]]:
    """A knapsack whose fitness function records each Chromosome scored."""
    knapsack = Knapsack(
        weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        capacity=165,
    )
    fitness = knapsack.fitness_func
    calls: list[str] = []

    def counted_fitness(chromosome):
        calls.append(repr(chromosome))
        return fitness(chromosome)

    knapsack.fitness_func = counted_fitness
    return knapsack, calls


def test_fit_metrics_count_the_fitness_calls():
    # One process, so the fitness function runs here and `calls` fills.
    knapsack, calls = _counting_bag()
    result = knapsack.fit(
        FitConfig(n_generations=5, population_size=50, n_jobs=1),
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
    knapsack, calls = _counting_bag()
    config = FitConfig(n_generations=3, population_size=30, n_jobs=1)
    first = knapsack.fit(config)
    first_calls = len(calls)
    assert first["fit_metrics"]["fitness_func_calls"]["processed"] == (
        first_calls
    )
    result = knapsack.fit(config)
    generations = len(result["metrics"])
    assert 1 < generations <= 4
    assert len(result["history"]) == generations
    # 30 Chromosomes in the first population and 20 children in each
    # later generation: 2 * int((0.7 * 30) // 2).
    counted = result["fit_metrics"]["fitness_func_calls"]
    assert counted["total"] == 30 + 20 * (generations - 1)
    # A Chromosome the first run scored is not scored again.
    assert len(calls) == len(set(calls))
    assert counted["processed"] == len(calls) - first_calls


def test_fit_gives_iter_func_the_generations_and_the_chromosomes_to_score():
    # One process, so the fitness function runs here and `calls` fills.
    knapsack, calls = _counting_bag()
    wrapped: list[list] = []

    def record(items: list) -> list:
        wrapped.append(items)
        return items

    knapsack.fit(
        FitConfig(
            n_generations=3,
            population_size=30,
            stop_without_improvement=False,
            n_jobs=1,
        ),
        iter_func=record,
    )
    assert wrapped[0] == [0, 1, 2, 3]
    scored = [chromosome for items in wrapped[1:] for chromosome in items]
    assert all(isinstance(chromosome, Chromosome) for chromosome in scored)
    assert [repr(chromosome) for chromosome in scored] == calls


@pytest.mark.parametrize(
    ("crossovers_prop", "besties_prop", "children"),
    [(1.0, 1.0, 30), (1.0, 0.0, 30), (0.0, 1.0, 0)],
)
def test_proportions_at_0_and_1_breed_without_error(
    crossovers_prop, besties_prop, children
):
    # With both at 1 every Chromosome is a parent and the rest is empty.
    knapsack, _ = _counting_bag()
    result = knapsack.fit(
        FitConfig(
            n_generations=4,
            population_size=30,
            crossovers_prop=crossovers_prop,
            besties_prop=besties_prop,
            min_population_size=0,
            stop_without_improvement=False,
            n_jobs=1,
        ),
    )
    assert len(result["metrics"]) == 5
    assert [len(population) for population in result["history"]] == [30] * 5
    counted = result["fit_metrics"]["fitness_func_calls"]
    assert counted["total"] == 30 + children * 4


@pytest.mark.parametrize(
    ("population_size", "crossovers_prop", "besties_prop", "counts"),
    [
        # 21 parents, rounded down to an even 20; 20 * 0.6 = 12 best
        (30, 0.7, 0.6, (20, 12)),
        (30, 1.0, 1.0, (30, 30)),
        (31, 1.0, 0.5, (30, 15)),
        (30, 0.0, 1.0, (0, 0)),
        (1, 1.0, 1.0, (0, 0)),
    ],
)
def test_parent_counts_cross_an_even_number_of_parents(
    population_size, crossovers_prop, besties_prop, counts
):
    assert (
        algorithms.parent_counts(
            population_size, crossovers_prop, besties_prop
        )
        == counts
    )


def test_a_population_of_one_breeds_no_children():
    knapsack, _ = _counting_bag()
    result = knapsack.fit(
        FitConfig(
            n_generations=4,
            population_size=1,
            min_population_size=0,
            stop_without_improvement=False,
            n_jobs=1,
        ),
    )
    assert [len(population) for population in result["history"]] == [1] * 5
    assert result["fit_metrics"]["fitness_func_calls"]["total"] == 1
    assert len(result["bests"]["scores"]) == 1


def _bag_run_genes(n_jobs: int, **seeds: int) -> list[list[list[int]]]:
    """The genes of each population of a run of a new knapsack."""
    knapsack = Knapsack(
        weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        capacity=165,
        **seeds,
    )
    result = knapsack.fit(
        FitConfig(
            n_generations=5,
            population_size=30,
            stop_without_improvement=False,
            n_jobs=n_jobs,
        ),
    )
    return [
        [list(chromosome.genes) for _, chromosome in population]
        for population in result["history"]
    ]


def test_one_seed_gives_the_same_run_with_any_number_of_jobs(
    score_in_workers,
):
    first = _bag_run_genes(n_jobs=1)
    assert len(first) == 6
    assert _bag_run_genes(n_jobs=1) == first
    # Two jobs, or the one that a machine with one core allows.
    assert _bag_run_genes(n_jobs=min(2, cpu_count())) == first


def test_another_seed_gives_another_run():
    assert _bag_run_genes(n_jobs=1) != _bag_run_genes(
        n_jobs=1, random_seed=7, gene_space_random_seed=8
    )


WORDS = [f"w{number}" for number in range(40)]


class WordsAlgorithm(NumbersAlgorithm):
    """
    `NumbersAlgorithm` with 40 numbers written as words. Python orders a
    set of strings by a hash seed it draws at each launch.
    """

    def __init__(self):
        super().__init__(minimize=False)
        self.gene_space = ValuesGeneSpace(WORDS, random_seed=5)
        self.decode_func = lambda chromosome: sorted(chromosome.genes)
        self.fitness_func = lambda chromosome: Score(
            value=sum(int(word[1:]) for word in chromosome.genes)
        )


def _words_run_genes() -> list[list[list[str]]]:
    """The genes of each population of a run of `WordsAlgorithm`."""
    result = WordsAlgorithm().fit(
        FitConfig(
            n_generations=10,
            population_size=30,
            stop_without_improvement=False,
            n_jobs=1,
        ),
    )
    return [
        [sorted(chromosome.genes) for _, chromosome in population]
        for population in result["history"]
    ]


def test_one_seed_gives_the_same_set_run_with_any_hash_seed():
    code = (
        "from tests.unit.algorithms.test_base import _words_run_genes; "
        "print(_words_run_genes())"
    )
    # Both start before either is waited on, so they run at the same time
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", code],
            cwd=Path(__file__).parents[3],
            env={**os.environ, "PYTHONHASHSEED": hash_seed},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for hash_seed in ("1", "2")
    ]
    runs = []
    for process in processes:
        stdout, stderr = process.communicate()
        assert process.returncode == 0, stderr
        runs.append(stdout)
    assert runs[0].startswith("[[[")
    assert runs[0] == runs[1]


def test_fit_gives_the_algorithm_to_the_callback_and_the_exit_condition():
    knapsack, _ = _counting_bag()
    seen: list[Knapsack] = []
    result = knapsack.fit(
        FitConfig(
            n_generations=5,
            population_size=30,
            stop_without_improvement=False,
            n_jobs=1,
        ),
        callback_func=seen.append,
        exit_condition=lambda algorithm: len(algorithm.metrics) == 2,
    )
    assert len(result["metrics"]) == 2
    assert result["stop_reason"] == "exit_condition"
    assert len(seen) == 2
    assert all(algorithm is knapsack for algorithm in seen)


class CallbackCountingBag(Knapsack):
    callbacks = 0

    def default_fit_callback(self) -> None:
        self.callbacks += 1


def test_fit_calls_the_callback_method_of_a_subclass_by_default():
    knapsack = CallbackCountingBag(
        weights=[23, 31, 29, 44], values=[92, 57, 49, 68], capacity=80
    )
    result = knapsack.fit(
        FitConfig(
            n_generations=2,
            population_size=10,
            min_population_size=2,
            stop_without_improvement=False,
            n_jobs=1,
        ),
    )
    assert knapsack.callbacks == len(result["metrics"]) == 3


def test_sorting_starts_no_workers_when_no_chromosome_is_new(
    monkeypatch, score_in_workers
):
    # Two genes give 4 Chromosomes, so the first population has them all.
    knapsack = Knapsack(weights=[1, 2], values=[3, 4], capacity=3)
    fitness = knapsack.fitness_func
    calls: list[str] = []

    def counted_fitness(chromosome):
        calls.append(repr(chromosome))
        return fitness(chromosome)

    knapsack.fitness_func = counted_fitness
    parallel_calls: list[dict] = []

    def counted_parallel(**kwargs):
        parallel_calls.append(kwargs)
        return Parallel(**kwargs)

    monkeypatch.setattr(algorithms, "Parallel", counted_parallel)
    knapsack._start_population(population_size=50, n_jobs=1)
    assert len(calls) == 4
    knapsack._start_population(population_size=50, n_jobs=1)
    assert len(calls) == 4
    assert parallel_calls == [{"n_jobs": 1}]
    assert len(knapsack.population) == 50
    assert all(c.score is not None for c in knapsack.population)


def test_fit_keeps_one_pool_of_workers_for_the_whole_run(monkeypatch):
    knapsack = Knapsack(
        weights=list(range(1, 21)), values=list(range(20, 0, -1)), capacity=60
    )
    parallel_calls: list[dict] = []

    def counted_parallel(**kwargs):
        parallel_calls.append(kwargs)
        return Parallel(**kwargs)

    monkeypatch.setattr(algorithms, "Parallel", counted_parallel)
    result = knapsack.fit(
        FitConfig(
            n_generations=4,
            population_size=30,
            stop_without_improvement=False,
            n_jobs=1,
        )
    )
    assert len(result["metrics"]) == 5
    assert parallel_calls == [{"n_jobs": 1}]
    assert knapsack._parallel is None


class CountedParallel(Parallel):
    """A `Parallel` that counts the batches it is given."""

    batches: ClassVar[list[int]] = []

    def __call__(self, iterable):
        items = list(iterable)
        self.batches.append(len(items))
        return super().__call__(items)


def test_fast_scores_are_not_sent_to_the_workers(monkeypatch):
    monkeypatch.setattr(CountedParallel, "batches", [])
    monkeypatch.setattr(algorithms, "Parallel", CountedParallel)
    # A clock where scoring takes no time: timed for real, one slow
    # score on a busy machine sends the rest to the workers
    monkeypatch.setattr(algorithms, "perf_counter", lambda: 0.0)
    knapsack = Knapsack(
        weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        capacity=165,
    )
    result = knapsack.fit(
        FitConfig(
            n_generations=5, population_size=50, n_jobs=min(2, cpu_count())
        )
    )
    assert result["fit_metrics"]["fitness_func_calls"]["processed"] > 50
    assert CountedParallel.batches == []


def test_slow_scores_are_sent_to_the_workers_after_the_first(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(CountedParallel, "batches", [])
    monkeypatch.setattr(algorithms, "Parallel", CountedParallel)
    pids_log = tmp_path / "pids.log"

    def slow_ones(chromosome):
        with open(pids_log, "a") as file:
            file.write(f"{os.getpid()}\n")
        time.sleep(0.02)
        return count_ones(chromosome)

    algorithm = ones_algorithm(tmp_path)
    algorithm.fitness_func = slow_ones
    algorithm._start_population(
        population_size=10, n_jobs=min(2, cpu_count())
    )

    # The first is scored here, to time it, and the 9 others are
    # expected to take 0.18 s, more than `IN_PROCESS_SECONDS`
    pids = pids_log.read_text().splitlines()
    assert pids[0] == str(os.getpid())
    assert CountedParallel.batches == [len(pids) - 1]


def test_fit_lets_go_of_its_pool_of_workers_when_it_raises():
    knapsack = Knapsack(weights=[1, 2, 3], values=[3, 4, 5], capacity=4)

    def failing_callback(_):
        raise RuntimeError("callback failed")

    with pytest.raises(RuntimeError, match="callback failed"):
        knapsack.fit(
            FitConfig(n_generations=2, population_size=10, n_jobs=1),
            callback_func=failing_callback,
        )
    assert knapsack._parallel is None


def test_fit_runs_a_fitness_function_that_uses_the_algorithm(
    score_in_workers,
):
    # The function takes the whole algorithm to each worker process, so
    # the algorithm must pickle while its pool of workers is open.
    knapsack = Knapsack(
        weights=[23, 31, 29, 44, 53], values=[92, 57, 49, 68, 60], capacity=80
    )

    def fit_with_algorithm(chromosome: Chromosome) -> Score:
        return Score(
            value=sum(
                value * gene
                for value, gene in zip(knapsack.values, chromosome.genes)
            )
        )

    knapsack.fitness_func = fit_with_algorithm
    result = knapsack.fit(
        FitConfig(
            n_generations=2, population_size=20, n_jobs=min(2, cpu_count())
        )
    )
    assert result["bests"]["scores"][0].value > 0


def test_the_algorithm_pickles_without_its_run():
    # A fitness function that uses the algorithm takes it to each worker
    # process: what the run has built so far, which grows each
    # generation, is left behind.
    knapsack = Knapsack(
        weights=[23, 31, 29, 44, 53], values=[92, 57, 49, 68, 60], capacity=80
    )
    knapsack.fit(FitConfig(n_generations=5, population_size=20, n_jobs=1))
    sent = cloudpickle.loads(cloudpickle.dumps(knapsack))
    assert sent.population == []
    assert sent.history == []
    assert sent.metrics == []
    assert sent._chromosome_cache == {}
    assert knapsack.history != []


def last_saved_population(tmp_path) -> list[tuple[Score, Chromosome]]:
    """The last population of a run saved as JSON, loaded back."""
    saved = ones_algorithm(tmp_path / "saved", save_as_bson=False)
    saved.fit(
        FitConfig(
            n_generations=2,
            population_size=20,
            min_population_size=1,
            stop_without_improvement=False,
            n_jobs=1,
        ),
    )
    return load_fit_result(
        f"{saved.save_path}/fit_data",
        decode_func=decode_genes,
        load_gene_func=int,
    )["history"][-1]


def test_fit_starts_from_a_saved_population_without_scoring_it(tmp_path):
    last = last_saved_population(tmp_path)
    scored = []

    def counted_ones(chromosome: Chromosome) -> Score:
        scored.append(repr(chromosome))
        return count_ones(chromosome)

    algorithm = ones_algorithm(tmp_path)
    algorithm.fitness_func = counted_ones
    result = algorithm.fit(
        FitConfig(
            n_generations=3,
            population_size=20,
            min_population_size=1,
            stop_without_improvement=False,
            n_jobs=1,
        ),
        first_population=last,
    )
    assert [(s, list(c.genes)) for s, c in algorithm.history[0]] == [
        (s, list(c.genes)) for s, c in last
    ]
    assert not set(scored) & {repr(c) for _, c in last}
    calls = result["fit_metrics"]["fitness_func_calls"]
    assert calls["processed"] == len(scored)
    assert calls["cached"] >= len(last)


@pytest.mark.parametrize(
    "change, match",
    [
        (lambda last: [], "empty population"),
        (
            lambda last: [
                *last[:-1],
                (Score(value=float("nan")), last[-1][1]),
            ],
            "a score that is not finite, nan,",
        ),
        (
            lambda last: [
                *last[:-1],
                (Score(value=float("-inf")), last[-1][1]),
            ],
            "a score that is not finite, -inf,",
        ),
        (
            lambda last: [
                *last[:-1],
                (Score(value=10**400), last[-1][1]),
            ],
            "a score that is not finite, 1000",
        ),
        (
            lambda last: [
                *last[:-1],
                (last[-1][0], Chromosome(size=3, genes=[1, 1, 1])),
            ],
            "received 3 genes for a `size` of 12",
        ),
    ],
)
def test_fit_refuses_a_first_population_that_does_not_fit(
    tmp_path, change, match
):
    last = last_saved_population(tmp_path)
    algorithm = ones_algorithm(tmp_path)
    with pytest.raises(ValidationException, match=match):
        algorithm.fit(
            FitConfig(n_generations=1, population_size=20, n_jobs=1),
            first_population=change(last),
        )
    assert algorithm._chromosome_cache == {}


@pytest.mark.parametrize(
    "level, logged", [(logging.INFO, True), (logging.WARNING, False)]
)
def test_fit_formats_the_metrics_only_when_they_are_logged(
    monkeypatch, set_log_level, level, logged
):
    knapsack = Knapsack(
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
    result = knapsack.fit(
        FitConfig(n_generations=3, population_size=50, n_jobs=1)
    )
    metrics = [d for d in formatted if isinstance(d, Metric)]
    assert metrics == (result["metrics"] if logged else [])


@pytest.mark.parametrize(
    "parameters",
    [
        {"n_generations": -1},
        {"population_size": 0, "min_population_size": 0},
        {"crossovers_prop": 1.5},
        {"besties_prop": -0.1},
        {"mutate_prob": float("nan")},
        {"min_population_size": 31},
        {"max_seconds": -1},
        {"max_seconds": float("nan")},
        {"max_stale_generations": -1},
        {"selection": "roulette"},
        {"tournament_size": 0},
    ],
)
def test_fit_refuses_parameters_out_of_range(parameters):
    knapsack, calls = _counting_bag()
    fit_parameters = {"n_generations": 5, "population_size": 30, "n_jobs": 1}
    with pytest.raises(ValidationException):
        knapsack.fit(FitConfig(**(fit_parameters | parameters)))
    assert not calls


def test_fit_refuses_a_set_larger_than_the_gene_space():
    # The 12 numbers under 12 cannot fill a set of 13. The message is
    # that of `fit`, not the one of the first Chromosome built.
    algorithm = NumbersAlgorithm(minimize=False)
    algorithm.chromosome_length = 13
    with pytest.raises(ValidationException, match="a set of 13 genes"):
        algorithm.fit(
            FitConfig(n_generations=1, population_size=10, n_jobs=1)
        )


@pytest.mark.parametrize(
    "cores, parameters", [(1, {}), (1, {"n_jobs": -1}), (2, {"n_jobs": -4})]
)
def test_fit_uses_one_job_when_fewer_are_left(monkeypatch, cores, parameters):
    # Without `n_jobs` it is -2: every core but one.
    monkeypatch.setattr(algorithms, "cpu_count", lambda: cores)
    knapsack, _ = _counting_bag()
    result = knapsack.fit(
        FitConfig(n_generations=2, population_size=20, **parameters),
    )
    assert result["fit_parameters"]["n_jobs"] == 1


def test_fit_parameters_are_the_config_with_the_seed_and_the_jobs():
    knapsack, _ = _counting_bag()
    result = knapsack.fit(
        FitConfig(n_generations=2, population_size=20, n_jobs=1),
    )
    assert result["fit_parameters"] == {
        "n_generations": 2,
        "population_size": 20,
        "crossovers_prop": 0.7,
        "besties_prop": 0.6,
        "mutate_prob": 0.05,
        "min_population_size": 10,
        "n_jobs": 1,
        "selection": "random",
        "tournament_size": 3,
        "random_seed": 666,
    }


def _tournament_parents(
    tournament_size: int, n_besties: int = 0
) -> list[list[int]]:
    """
    The genes of the parents picked from a population of the genes 0 to
    19, scored by their own value and sorted best first, with no
    crossover nor mutation.
    """
    algorithm = NumbersAlgorithm(minimize=False)
    algorithm.population = []
    for value in range(19, -1, -1):
        chromosome = Chromosome(size=1, genes=[value])
        chromosome.score = Score(value=value)
        algorithm.population.append(chromosome)
    picked: list[list[int]] = []

    def keep_parents(parents):
        picked.extend(list(parent.genes) for parent in parents)
        return []

    algorithm.cross_parents = keep_parents
    algorithm.next_generation_selection(
        FitConfig(
            n_generations=1,
            population_size=20,
            crossovers_prop=1.0,
            besties_prop=n_besties / 20,
            selection="tournament",
            tournament_size=tournament_size,
        ),
        n_jobs=1,
    )
    return picked


def test_tournament_picks_the_best_of_the_chromosomes_drawn():
    one = sum(genes[0] for genes in _tournament_parents(1))
    five = sum(genes[0] for genes in _tournament_parents(5))
    # Each parent is the best of 5 drawn from 0 to 19: about 16 on
    # average, against about 9.5 for a random pick
    assert five > one
    assert five / 20 > 14


def test_tournament_draws_from_the_rest_after_the_besties():
    parents = _tournament_parents(20, n_besties=6)
    besties = sorted(genes[0] for genes in parents)[-6:]
    assert besties == list(range(14, 20))
    # Every other parent is drawn from 0 to 13
    assert all(genes[0] < 14 for genes in parents if genes[0] not in besties)


def test_a_tournament_run_is_saved_with_its_selection(tmp_path):
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    algorithm.fit(
        FitConfig(
            n_generations=3,
            population_size=20,
            n_jobs=1,
            selection="tournament",
            tournament_size=4,
        ),
    )
    loaded = load_fit_result(f"{algorithm.save_path}/fit_data", decode_genes)
    parameters = loaded["fit_parameters"]
    assert (parameters["selection"], parameters["tournament_size"]) == (
        "tournament",
        4,
    )


@pytest.mark.parametrize("n_jobs", [0, 3])
def test_fit_refuses_no_jobs_and_more_jobs_than_cores(monkeypatch, n_jobs):
    monkeypatch.setattr(algorithms, "cpu_count", lambda: 2)
    knapsack, calls = _counting_bag()
    with pytest.raises(ValidationException, match="n_jobs"):
        knapsack.fit(
            FitConfig(n_generations=2, population_size=20, n_jobs=n_jobs)
        )
    assert not calls


def test_chromosomes_sharing_an_id_keep_their_own_scores(monkeypatch):
    knapsack, _ = _counting_bag()
    config = FitConfig(n_generations=5, population_size=30, n_jobs=1)
    expected = knapsack.fit(config)["bests"]["scores"]

    # Every Chromosome gets one id, as two would after a hash collision.
    monkeypatch.setattr(Chromosome, "id", property(lambda self: 1))
    knapsack, _ = _counting_bag()
    scores = knapsack.fit(config)["bests"]["scores"]
    assert [s.value for s in scores] == [s.value for s in expected]


def test_scoring_does_not_keep_the_algorithm_alive():
    knapsack, _ = _counting_bag()
    knapsack.fit(
        FitConfig(n_generations=2, population_size=20, n_jobs=1),
    )
    reference = weakref.ref(knapsack)
    del knapsack
    gc.collect()
    assert reference() is None

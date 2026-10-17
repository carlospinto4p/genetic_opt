import gc
import logging
import weakref
from os import cpu_count

import pytest
from joblib import Parallel

from genetic_opt.algorithms import FitConfig
from genetic_opt.algorithms import base as algorithms
from genetic_opt.algorithms.base import GeneticAlgorithm
from genetic_opt.algorithms.binary import BinaryGeneticAlgorithm
from genetic_opt.chromosome import Chromosome
from genetic_opt.examples.binary import Knapsack
from genetic_opt.exceptions import (
    InvariantException,
    ValidationException,
)
from genetic_opt.fit_result import (
    FitResult,
)
from genetic_opt.gene_space import AbstractGeneSpace
from genetic_opt.metrics import Metric
from genetic_opt.score import Score
from tests.unit.conftest import OnesGeneSpace

# ── GeneticAlgorithm Tests ─────────────────────────────────────────────


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


class NanStartAlgorithm(ZeroStartAlgorithm):
    """Its first population has a Chromosome whose score is NaN."""

    def __init__(self):
        super().__init__()
        self.fitness_func = lambda chromosome: Score(
            value=float("nan") if sum(chromosome.genes) == 0 else 1.0
        )


def test_fit_refuses_a_nan_score():
    algorithm = NanStartAlgorithm()
    config = FitConfig(
        n_generations=3, population_size=4, min_population_size=1, n_jobs=1
    )
    message = (
        r"the fitness function gave a NaN score to the Chromosome "
        r"\[0, 0, 0, 0, 0, 0, 0, 0, 0, 0\]"
    )
    # The score is not cached, so a second run is refused too
    for _ in range(2):
        with pytest.raises(ValidationException, match=message):
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

    def __init__(self, minimize: bool):
        super().__init__(
            gene_space=NumbersGeneSpace(random_seed=5),
            chromosome_length=3,
            chromosome_as_set=True,
            decode_func=lambda chromosome: sum(chromosome.genes),
            fitness_func=lambda chromosome: Score(
                value=sum(chromosome.genes)
            ),
            minimize=minimize,
        )

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
    assert algorithm.no_improvement_condition()
    assert "stop_without_improvement" not in result["fit_parameters"]


@pytest.mark.parametrize(
    "min_population_size, generations", [(2, 1), (1, 6), (0, 6)]
)
def test_fit_stops_below_min_population_size(
    min_population_size, generations
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


def test_fit_scores_each_chromosome_once(tmp_path):
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
    """A knapsack whose fitness function records each Chromosome it runs on."""
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


def test_sorting_starts_no_workers_when_no_chromosome_is_new(monkeypatch):
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


def test_fit_runs_a_fitness_function_that_uses_the_algorithm():
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
    ],
)
def test_fit_refuses_parameters_out_of_range(parameters):
    knapsack, calls = _counting_bag()
    fit_parameters = {"n_generations": 5, "population_size": 30, "n_jobs": 1}
    with pytest.raises(ValidationException):
        knapsack.fit(FitConfig(**(fit_parameters | parameters)))
    assert not calls


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
        "random_seed": 666,
    }


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

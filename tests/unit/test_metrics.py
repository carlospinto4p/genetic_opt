import pytest

from genetic_opt.chromosome import Chromosome
from genetic_opt.metrics import get_population_metrics
from genetic_opt.score import Score

# ── get_population_metrics Tests ───────────────────────────────────────


def _population(
    scored_genes: list[tuple[float, list[int]]],
) -> list[tuple[Score, Chromosome]]:
    """A population, best first, from pairs of a score and the genes."""
    return [
        (Score(value=value), Chromosome(size=len(genes), genes=genes))
        for value, genes in scored_genes
    ]


def _sum_genes(chromosome: Chromosome) -> int:
    return sum(chromosome.genes)


def test_population_metrics_of_known_scores():
    population = _population(
        [(4, [1, 1]), (3, [1, 0]), (3, [1, 0]), (1, [0, 0])]
    )
    metric = get_population_metrics(
        population, decode_func=_sum_genes, fitting_seconds=1.234
    )
    assert metric.best["score"].value == 4
    assert metric.best["encoded"] is population[0][1]
    assert metric.best["result"] == 2
    assert metric.size == 4
    assert metric.mean == 2.75
    assert metric.median == 3
    # ((4 - 2.75)² + 2 * (3 - 2.75)² + (1 - 2.75)²) / 4
    assert abs(metric.var - 1.1875) < 1e-9
    assert metric.n_uniques == 3
    assert metric.percent_uniques == 75
    assert metric.fitting_seconds == 1.23


def test_population_metrics_of_an_even_count_take_the_middle_two():
    population = _population(
        [(8.5, [1, 1]), (3, [1, 0]), (2, [0, 1]), (0.25, [0, 0])]
    )
    metric = get_population_metrics(
        population, decode_func=_sum_genes, fitting_seconds=0
    )
    assert metric.median == 2.5


@pytest.mark.parametrize(
    "scored_genes, n_uniques",
    [
        ([(2.5, [1, 0]), (2.5, [0, 1]), (2.5, [1, 0])], 2),
        ([(2.5, [1, 0])], 1),
    ],
)
def test_population_metrics_of_equal_scores(scored_genes, n_uniques):
    population = _population(scored_genes)
    metric = get_population_metrics(
        population, decode_func=_sum_genes, fitting_seconds=0
    )
    assert metric.size == len(population)
    assert metric.mean == metric.median == 2.5
    assert metric.var == 0
    assert metric.n_uniques == n_uniques
    assert metric.percent_uniques == 100 * n_uniques / len(population)

from itertools import pairwise

import pytest

from genetic_opt.algorithms import FitConfig
from genetic_opt.chromosome import Chromosome
from genetic_opt.web.runs import (
    BinaryFunction,
    function_curve,
    function_run,
    knapsack_run,
    wavy_function,
)

WEIGHTS = [23, 31, 29, 44, 53, 38, 63, 85, 89, 82]
VALUES = [92, 57, 49, 68, 60, 43, 67, 84, 87, 72]


def run_knapsack(**config) -> dict:
    defaults = {
        "n_generations": 6,
        "population_size": 30,
        "mutate_prob": 0.2,
        "stop_without_improvement": False,
        "min_population_size": 0,
        "n_jobs": 1,
    }
    return knapsack_run(
        weights=WEIGHTS,
        values=VALUES,
        capacity=165,
        config=FitConfig(**{**defaults, **config}),
        random_seed=7,
        gene_space_random_seed=3,
    )


@pytest.fixture(scope="module")
def run() -> dict:
    return run_knapsack()


# ── BinaryFunction Tests ───────────────────────────────────────────────


@pytest.mark.parametrize(
    ("bits", "x"), [([0] * 8, -1.0), ([1] * 8, 2.0), ([1] + [0] * 7, 0.5)]
)
def test_binary_function_decodes_the_bits_over_the_interval(bits, x):
    problem = BinaryFunction(n_bits=8)
    chromosome = Chromosome(size=8, genes=bits)
    # 10000000 is 128 of 255
    expected = x if x != 0.5 else -1 + 3 * 128 / 255
    assert abs(problem.decode_func(chromosome) - expected) < 1e-12


def test_binary_function_scores_with_the_wavy_function():
    problem = BinaryFunction(n_bits=8)
    chromosome = Chromosome(size=8, genes=[0, 1, 1, 0, 1, 0, 0, 1])
    x = problem.decode_func(chromosome)
    assert problem.fitness_func(chromosome).value == wavy_function(x)


def test_function_curve_covers_the_interval():
    curve = function_curve(-1.0, 2.0)
    assert (curve[0][0], curve[-1][0]) == (-1.0, 2.0)
    assert curve[10][1] == wavy_function(curve[10][0])


# ── record_run Tests ───────────────────────────────────────────────────


def test_record_run_keeps_each_generation(run):
    assert len(run["generations"]) == 7
    assert run["stop_reason"] == "completed"
    assert all(len(g["population"]) == 30 for g in run["generations"])


def test_record_run_marks_the_first_population_as_initial(run):
    first = run["generations"][0]
    assert first["breeding"] is None
    assert {c["origin"] for c in first["population"]} == {"initial"}


def test_record_run_keeps_each_population_sorted_with_its_best(run):
    for generation in run["generations"]:
        scores = [c["score"] for c in generation["population"]]
        assert scores == sorted(scores, reverse=True)
        assert generation["metrics"]["best"] == scores[0]


def test_record_run_picks_the_besties_and_then_the_rest(run):
    # 30 * 0.7 = 21 crossed, rounded down to 20; 20 * 0.6 = 12 besties
    breeding = run["generations"][1]["breeding"]
    assert (breeding["n_crossovers"], breeding["n_besties"]) == (20, 12)
    parents = breeding["parents"]
    best_ranks = sorted(p["rank"] for p in parents if p["kind"] == "best")
    assert best_ranks == list(range(12))
    assert all(p["rank"] >= 12 for p in parents if p["kind"] == "random")


def test_record_run_takes_the_parents_scores_from_the_last_population(run):
    previous = run["generations"][0]["population"]
    for parent in run["generations"][1]["breeding"]["parents"]:
        assert parent["genes"] == previous[parent["rank"]]["genes"]
        assert parent["score"] == previous[parent["rank"]]["score"]


def test_record_run_gives_each_gene_of_a_child_its_parent(run):
    for generation in run["generations"][1:]:
        parents = generation["breeding"]["parents"]
        for pair in generation["breeding"]["pairs"]:
            a, b = parents[pair["a"]]["genes"], parents[pair["b"]]["genes"]
            for child in pair["children"]:
                for i, origin in enumerate(child["origins"]):
                    source = b if origin == "b" else a
                    assert child["crossed"][i] == source[i]
                    assert (origin == "both") == (a[i] == b[i])


def test_record_run_crosses_each_pair_at_one_point(run):
    # One child takes the start of `a` and the end of `b`, the other
    # the opposite, so neither switches parent twice.
    for pair in run["generations"][1]["breeding"]["pairs"]:
        for child in pair["children"]:
            switches = [o for o in child["origins"] if o != "both"]
            changes = sum(x != y for x, y in pairwise(switches))
            assert changes <= 1


def test_record_run_lists_the_genes_the_mutation_changed(run):
    n_changed = 0
    for generation in run["generations"][1:]:
        for pair in generation["breeding"]["pairs"]:
            for child in pair["children"]:
                flipped = [
                    1 - g if i in child["changed"] else g
                    for i, g in enumerate(child["crossed"])
                ]
                assert child["genes"] == flipped
                n_changed += len(child["changed"])
    # With a probability of 0.2, some genes change
    assert n_changed > 0


def test_record_run_marks_the_children_that_stayed(run):
    for generation in run["generations"][1:]:
        stayed = [
            child
            for pair in generation["breeding"]["pairs"]
            for child in pair["children"]
            if child["stayed"]
        ]
        children = [
            c for c in generation["population"] if c["origin"] == "child"
        ]
        assert len(stayed) == len(children)
        assert sorted(c["genes"] for c in stayed) == sorted(
            c["genes"] for c in children
        )


def test_record_run_counts_the_calls_to_the_fitness_function(run):
    calls = run["fit_metrics"]
    # The first population and the 20 children of each generation
    assert calls["total"] == 30 + 6 * 20
    assert calls["processed"] + calls["cached"] == calls["total"]


def test_record_run_stops_without_improvement():
    run = run_knapsack(
        n_generations=200, mutate_prob=0.0, stop_without_improvement=True
    )
    assert run["stop_reason"] == "no_improvement"
    assert len(run["generations"]) < 201
    last, before = run["generations"][-1], run["generations"][-2]
    assert last["metrics"]["mean"] == before["metrics"]["mean"]


def test_record_run_stops_at_the_minimum_population():
    run = run_knapsack(
        n_generations=200, mutate_prob=0.0, min_population_size=25
    )
    assert run["stop_reason"] == "min_population"
    assert run["generations"][-1]["metrics"]["n_uniques"] < 25


def test_function_run_sends_the_curve():
    run = function_run(
        low=0.0,
        high=1.0,
        n_bits=10,
        config=FitConfig(n_generations=2, population_size=20, n_jobs=1),
        random_seed=1,
        gene_space_random_seed=1,
    )
    assert run["chromosome_length"] == 10
    assert (run["curve"][0][0], run["curve"][-1][0]) == (0.0, 1.0)
    for chromosome in run["generations"][-1]["population"]:
        assert chromosome["score"] == wavy_function(chromosome["decoded"])

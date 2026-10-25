import re
from itertools import pairwise
from pathlib import Path

import pytest

from genetic_opt.algorithms import FitConfig
from genetic_opt.chromosome import Chromosome
from genetic_opt.examples.binary import BinaryFunction, wavy_function
from genetic_opt.web.runs import (
    KNAPSACK_CAPACITY,
    KNAPSACK_VALUES,
    KNAPSACK_WEIGHTS,
    function_curve,
    function_run,
    knapsack_run,
    record_run,
)

ROOT = Path(__file__).parents[3]
CRATE = ROOT / "crates" / "genetic_opt"
WEIGHTS, VALUES = KNAPSACK_WEIGHTS, KNAPSACK_VALUES


def numbers(text: str) -> list[int]:
    return [int(n) for n in re.findall(r"\d+", text)]


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


# ── function_curve Tests ───────────────────────────────────────────────


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
    ranks = breeding["parents"]
    assert sorted(r for r in ranks if r < 12) == list(range(12))


def _crossed_pairs(run: dict):
    """
    Each child with its genes before the mutation and the genes of its
    two parents, as the page works them out.
    """
    for previous, generation in pairwise(run["generations"]):
        population, breeding = previous["population"], generation["breeding"]
        for pair in breeding["pairs"]:
            a, b = (
                population[breeding["parents"][pair[p]]]["genes"]
                for p in ("a", "b")
            )
            for child in pair["children"]:
                crossed = [
                    1 - g if i in child["changed"] else g
                    for i, g in enumerate(child["genes"])
                ]
                yield child, crossed, a, b


def test_record_run_gives_each_gene_of_a_child_its_parent(run):
    for _, crossed, a, b in _crossed_pairs(run):
        assert all(g in (ga, gb) for g, ga, gb in zip(crossed, a, b))


def test_record_run_crosses_each_pair_at_one_point(run):
    # One child takes the start of `a` and the end of `b`, the other
    # the opposite, so neither switches parent twice.
    for _, crossed, a, b in _crossed_pairs(run):
        switches = [g == ga for g, ga, gb in zip(crossed, a, b) if ga != gb]
        assert sum(x != y for x, y in pairwise(switches)) <= 1


def test_record_run_lists_the_genes_the_mutation_changed(run):
    n_changed = 0
    for child, _, _, _ in _crossed_pairs(run):
        assert child["changed"] == sorted(set(child["changed"]))
        assert all(0 <= i < len(child["genes"]) for i in child["changed"])
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


def test_record_run_decodes_each_chromosome_once():
    decoded = []

    class CountedFunction(BinaryFunction):
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs)
            decode = self.decode_func

            def counted(chromosome: Chromosome) -> float:
                decoded.append(repr(chromosome))
                return decode(chromosome)

            self.decode_func = counted

    run = record_run(
        CountedFunction,
        FitConfig(
            n_generations=6,
            population_size=30,
            stop_without_improvement=False,
            n_jobs=1,
        ),
        n_bits=10,
    )
    shown = [c for g in run["generations"] for c in g["population"]]
    for generation in run["generations"][1:]:
        breeding = generation["breeding"]
        shown += [c for p in breeding["pairs"] for c in p["children"]]
    distinct = {tuple(c["genes"]) for c in shown}
    # Each distinct Chromosome once to be shown. The algorithm decodes
    # the best of each of the 7 generations for its metrics, and the 30
    # of the last population and the 5 bests when `fit` ends.
    assert len(shown) > 2 * len(distinct)
    assert len(decoded) <= len(distinct) + 7 + 30 + 5


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


# ── Knapsack Data Tests ────────────────────────────────────────────────

KNAPSACK = KNAPSACK_WEIGHTS, KNAPSACK_VALUES, [KNAPSACK_CAPACITY]


def test_the_readme_example_has_the_knapsack_of_the_explainer():
    readme = (ROOT / "README.md").read_text()
    call = re.search(r"Knapsack\(\s*weights=(.*?)\n\)", readme, re.DOTALL)
    weights, values, capacity = call.group(1).split("\n    ")
    assert tuple(map(numbers, (weights, values, capacity))) == KNAPSACK


# The source package holds the tests but not the crate.
@pytest.mark.skipif(not CRATE.is_dir(), reason="needs the Rust crate")
def test_the_rust_example_has_the_knapsack_of_the_explainer():
    example = (CRATE / "examples" / "knapsack.rs").read_text()
    call = re.search(r"Knapsack::new\((.*?)\)\?;", example, re.DOTALL)
    lines = [line for line in call.group(1).splitlines() if line.strip()]
    assert tuple(map(numbers, lines)) == KNAPSACK

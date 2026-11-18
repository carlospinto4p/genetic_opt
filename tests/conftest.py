import logging
import os
from collections.abc import Callable, Iterator

import pytest

from genetic_opt.algorithms import SaveConfig
from genetic_opt.algorithms.binary import BinaryGeneticAlgorithm
from genetic_opt.score import Score

# Plots are drawn to files only. With a display, matplotlib would pick
# Tk, whose objects can then be freed in the worker thread of a web
# test: Tk refuses there, and the test waited about 20 seconds.
os.environ.setdefault("MPLBACKEND", "Agg")


@pytest.fixture
def set_log_level() -> Iterator[Callable[[int], None]]:
    """Set the level of the package logger until the test ends."""
    logger = logging.getLogger("genetic_opt")
    level = logger.level
    yield logger.setLevel
    logger.setLevel(level)


# ── A run that counts ones, used by both levels ────────────────────────


def decode_genes(chromosome) -> list[int]:
    return [int(gene) for gene in chromosome.genes]


def count_ones(chromosome) -> Score:
    genes = decode_genes(chromosome)
    # The extra metrics go through every save and load of a Score.
    return Score(
        value=float(sum(genes)),
        name="ones",
        extra_metrics={"zeros": genes.count(0), "first": genes[:2]},
    )


def ones_algorithm(
    save_path,
    experiment_name: str = "ones",
    save_as_bson: bool = True,
    plot_metrics: bool = False,
    other_metrics_to_plot: dict | None = None,
    **kwargs,
) -> BinaryGeneticAlgorithm:
    return BinaryGeneticAlgorithm(
        chromosome_length=12,
        chromosome_as_set=False,
        decode_func=decode_genes,
        fitness_func=count_ones,
        minimize=False,
        experiment_name=experiment_name,
        save=SaveConfig(
            path=f"{save_path}/",
            serialize_decoded_chromosome_func=list,
            as_bson=save_as_bson,
            serialize_gene_func=int,
            plot_metrics=plot_metrics,
            other_metrics_to_plot=other_metrics_to_plot,
        ),
        **kwargs,
    )

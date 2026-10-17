import matplotlib.pyplot as plt
import pytest

from genetic_opt.algorithms.plots import plot_genetic_algo_metrics
from genetic_opt.fit_result_io import load_fit_result
from tests.unit.conftest import decode_genes

# ── plot_genetic_algo_metrics Tests ────────────────────────────────────


@pytest.mark.parametrize(
    "other_keys, titles",
    [
        (
            None,
            ["Summary", "Uniques in populations", "Fit times - Seconds"],
        ),
        (
            {"first gene": lambda chromosome: chromosome.genes[0]},
            [
                "Summary",
                "Other scores - Bests in each population",
                "Uniques in populations",
                "Fit times - Seconds",
            ],
        ),
    ],
)
def test_the_plot_has_a_panel_for_the_other_keys_when_given(
    saved_run, other_keys, titles
):
    loaded = load_fit_result(saved_run, decode_genes)
    plot_genetic_algo_metrics(
        loaded["metrics"], loaded["fit_metrics"], other_keys=other_keys
    )
    figure = plt.gcf()
    try:
        assert [axes.get_title() for axes in figure.axes] == titles
        assert figure.get_suptitle() == "Genetic Algorithm Metrics - Ones"
        if other_keys:
            legend = figure.axes[1].get_legend()
            assert [t.get_text() for t in legend.get_texts()] == [
                "first gene"
            ]
    finally:
        plt.close(figure)


@pytest.mark.parametrize(
    "score_name, title",
    [
        (None, "Genetic Algorithm Metrics"),
        ("", "Genetic Algorithm Metrics"),
        ("ones_left", "Genetic Algorithm Metrics - Ones Left"),
    ],
)
def test_the_plot_title_names_the_score_when_it_has_a_name(
    saved_run, score_name, title
):
    loaded = load_fit_result(saved_run, decode_genes)
    loaded["metrics"][0].best.score.name = score_name
    plot_genetic_algo_metrics(loaded["metrics"], loaded["fit_metrics"])
    figure = plt.gcf()
    try:
        assert figure.get_suptitle() == title
    finally:
        plt.close(figure)

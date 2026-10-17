from pathlib import Path

import matplotlib.pyplot as plt
import pytest

from genetic_opt.algorithms import FitConfig
from genetic_opt.algorithms.plots import (
    plot_genetic_algo_metrics,
    save_fit_plots,
)
from genetic_opt.fit_result_io import load_fit_result
from tests.unit.conftest import decode_genes, ones_algorithm

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


# ── save_fit_plots Tests ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "other_metrics_to_plot", [None, {"genes": lambda c: sum(c.genes)}]
)
def test_a_saved_run_gets_the_plot_that_fit_saves(
    tmp_path, other_metrics_to_plot
):
    algorithm = ones_algorithm(
        tmp_path,
        plot_metrics=True,
        other_metrics_to_plot=other_metrics_to_plot,
    )
    algorithm.fit(FitConfig(n_generations=3, population_size=20, n_jobs=1))
    plot_path = Path(algorithm.save_path) / "fit_plots.jpg"
    saved_by_fit = plot_path.read_bytes()
    # Every JPEG file starts with these bytes.
    assert saved_by_fit[:3] == b"\xff\xd8\xff"
    plot_path.unlink()

    drawn = save_fit_plots(
        algorithm.save_path,
        other_metrics_to_plot=other_metrics_to_plot,
        load_gene_func=int,
    )
    assert drawn == str(plot_path)
    assert plot_path.read_bytes() == saved_by_fit

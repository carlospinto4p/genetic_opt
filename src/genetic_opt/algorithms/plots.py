"""Genetic Opt plot functions for Algorithms training."""

from collections.abc import Callable
from operator import itemgetter
from pathlib import Path
from typing import Any

from genetic_opt.chromosome import Chromosome
from genetic_opt.files import (
    ensure_file_extension,
    ensure_folder_exists,
    log_saved,
)
from genetic_opt.fit_result import FitMetrics
from genetic_opt.fit_result_io import load_fit_result
from genetic_opt.functions import identity_func
from genetic_opt.metrics import Metric

# `matplotlib` is imported inside the functions that plot: it takes
# longer to import than the rest of the package.

PYPLOT_STYLE: str = "seaborn-v0_8"
PYPLOT_RC_PARAMS: dict = {
    "axes.titlesize": 18,
    "figure.figsize": (14, 10),
    "figure.titlesize": 20,
    "font.size": 16,
    "legend.fontsize": 14,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
}
# Keyword arguments of each legend of the metrics plot
LEGEND_PARAMS: dict = {
    "frameon": 1,
    "facecolor": "white",
    "edgecolor": "black",
    "framealpha": 0.3,
}


def set_pyplot_config() -> None:
    """
    Set default config for the library `matplotlib`.
    This function will:
        - Change default style to the one in `PYPLOT_STYLE`.
        - Change default plot parameters using the ones in
          `PYPLOT_RC_PARAMS`.
    """
    import matplotlib.pyplot as plt
    from matplotlib import rcParams

    plt.style.use(PYPLOT_STYLE)
    rcParams.update(PYPLOT_RC_PARAMS)


def plot_genetic_algo_metrics(
    metrics: list[Metric],
    fit_metrics: FitMetrics,
    other_keys: dict[str, Callable[[Chromosome], float]] | None = None,
) -> None:
    """
    Plot genetic algorithm training metrics summary.
    :param metrics: list of Metric objects, one for each algorithm
        population.
    :param fit_metrics: the `fit_metrics` of a `FitResult`.
    :param other_keys: dictionary with schema:
        - <metric name>: function
        where the functions are applied to the best Chromosome of each
        population.
    :return: None (but it creates a plt.Figure)
    """
    import matplotlib.pyplot as plt

    set_pyplot_config()
    population_idxs = [i for i, _ in enumerate(metrics)]
    if other_keys:
        fig, (ax1, ax2, ax3, ax4) = plt.subplots(nrows=4, figsize=(13, 17))
        ax_u, ax_t = ax3, ax4
    else:
        fig, (ax1, ax2, ax3) = plt.subplots(nrows=3, figsize=(13, 15))
        ax_u, ax_t = ax2, ax3
    ax1.set_title("Summary")
    ax1.plot(population_idxs, [m.best.score.value for m in metrics], lw=2.5)
    ax1.plot(population_idxs, [m.median for m in metrics], lw=1.4)
    ax1.plot(population_idxs, [m.mean for m in metrics], lw=1.4)
    ax1.legend(["Best", "Median", "Mean"], **LEGEND_PARAMS)
    if other_keys:
        ax2.set_title("Other scores - Bests in each population")
        for f in other_keys.values():
            ax2.plot(
                population_idxs,
                [f(m.best.encoded) for m in metrics],
                lw=1.6,
            )
        ax2.legend(list(other_keys), **LEGEND_PARAMS)

    ax_u.set_title("Uniques in populations")
    ax_u.plot(population_idxs, [m.percent_uniques for m in metrics], lw=2.5)
    ax_u.legend(["Percent uniques"], **LEGEND_PARAMS)

    ax_t.set_title("Fit times - Seconds")
    fitting_seconds = [m.fitting_seconds for m in metrics]
    n_jobs, raw_time = itemgetter("n_jobs", "formatted")(
        fit_metrics["total_fit_time"]
    )
    total_fits, fit_calls, percent_calls, space, exploration = itemgetter(
        "total",
        "processed",
        "percent_processed",
        "space_points",
        "exploration_percentage",
    )(fit_metrics["fitness_func_calls"])
    version = fit_metrics["genetic_opt_version"]
    ax_t.bar(population_idxs, fitting_seconds)
    # Create the legend
    handles = [plt.Line2D([], [], alpha=0)] * 5
    legend_labels = [
        f"Total fit time with {n_jobs} jobs: {raw_time}",
        f"Fitness_func calls: {fit_calls}/{total_fits} ({percent_calls} %)",
        f"Space exploration: {fit_calls}/{space} ({exploration} %)",
        f"Population size: {metrics[0].size}",
        f"`genetic_opt` version: {version}",
    ]
    ax_t.legend(
        handles,
        legend_labels,
        handlelength=0,
        **{**LEGEND_PARAMS, "framealpha": 0.4},
    )

    score_name_str = ""
    if score_name := getattr(metrics[0].best.score, "name", ""):
        score_name_str = " - " + score_name.replace("_", " ").title()

    fig.suptitle(f"Genetic Algorithm Metrics{score_name_str}")
    # Good if no `other keys`, let's see otherwise
    plt.subplots_adjust(top=0.94 if other_keys else 0.93)


def save_fit_plots(
    run_folder: str,
    other_metrics_to_plot: dict[str, Callable[[Chromosome], float]]
    | None = None,
    load_gene_func: Callable[[Any], Any] | None = None,
) -> str:
    """
    Plot the metrics of a saved run and save them in its folder as
    `fit_plots.jpg`, the plot `fit` saves when the run ends. For a run
    saved with `SaveConfig.plot_metrics` off, or by the Rust crate,
    which saves no plot.
    :param run_folder: folder of the run, which holds `fit_data/`.
    :param other_metrics_to_plot: as `SaveConfig.other_metrics_to_plot`.
    :param load_gene_func: function to load each saved gene, as
        `load_fit_result` takes it. It is needed when the saved genes
        can not be kept as they are, such as dictionaries in a set
        Chromosome, and for `other_metrics_to_plot` to get the genes it
        expects. The identity function by default.
    :return: path of the image.
    """
    loaded = load_fit_result(
        f"{run_folder}/fit_data",
        # The plot uses no decoded Chromosome
        decode_func=identity_func,
        load_gene_func=load_gene_func,
    )
    plot_genetic_algo_metrics(
        metrics=loaded["metrics"],
        fit_metrics=loaded["fit_metrics"],
        other_keys=other_metrics_to_plot,
    )
    path = f"{run_folder}/fit_plots"
    save_current_figure(path)
    return ensure_file_extension(path, "jpg")


def save_current_figure(path: str, extension: str = "jpg") -> None:
    """
    Save the current py-plot figure, then clear and close it, so the
    plots do not pile up in memory.
    :param path: output path.
    :param extension: image extension to use.
    """
    import matplotlib.pyplot as plt

    ensure_folder_exists(Path(path).parent)
    file_path = ensure_file_extension(path, extension)
    # Not `plt.savefig`, which draws the figure once more after saving
    plt.gcf().savefig(file_path, bbox_inches="tight")
    log_saved("image", file_path)
    plt.clf()
    plt.close()

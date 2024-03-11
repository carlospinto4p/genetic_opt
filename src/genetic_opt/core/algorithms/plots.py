""" Genetic Opt plot functions for Algorithms training. """

from operator import itemgetter
from typing import Callable

import matplotlib.pyplot as plt

from cpinto.plot.settings import set_pyplot_config

from genetic_opt.core.chromosome import Chromosome
from genetic_opt.core.metrics import Metric


def plot_genetic_algo_metrics(
        metrics: list[Metric], fit_metrics: dict,
        other_keys: dict[str, Callable[[Chromosome], float]] = None) -> None:
    """
    Plot genetic algorithm training metrics summary.
    Args:
        metrics: list of Metric objects, one for each algorithm population.
        fit_metrics: dictionary with keys:
            - fitness_func_calls: cached info:
                - cached
                - percent_processed
                - processed
                - total
                - space_points
                - exploration_percentage
            - total_fit_time:
                - raw
                - formatted
                - n_jobs
            - genetic_opt_version
        other_keys: dictionary with schema:
            - <metric name>: function
            where the functions are applied to the best Chromosome of each
            population.
    Returns:
        None (but it creates a plt.Figure)
    """
    set_pyplot_config()
    population_idxs = [i for i, _ in enumerate(metrics)]
    if other_keys:
        fig, (ax1, ax2, ax3, ax4) = plt.subplots(nrows=4, figsize=(13, 17))
        ax_u, ax_t = ax3, ax4
    else:
        fig, (ax1, ax2, ax3) = plt.subplots(nrows=3, figsize=(13, 15))
        ax_u, ax_t = ax2, ax3
    ax1.set_title('Summary')
    ax1.plot(population_idxs, [m.best[0].value for m in metrics], lw=2.5)
    ax1.plot(population_idxs, [m.median for m in metrics], lw=1.4)
    ax1.plot(population_idxs, [m.mean for m in metrics], lw=1.4)
    ax1.legend(['Best', 'Median', 'Mean'], frameon=1, facecolor='white',
               edgecolor='black', framealpha=.3)
    if other_keys:
        ax2.set_title('Other scores - Bests in each population')
        for f in other_keys.values():
            ax2.plot(population_idxs, [f(m.best[1]) for m in metrics], lw=1.6)
        ax2.legend([name for name in other_keys.keys()], frameon=1,
                   facecolor='white', edgecolor='black', framealpha=.3)

    ax_u.set_title('Uniques in populations')
    ax_u.plot(population_idxs, [m.percent_uniques for m in metrics], lw=2.5)
    ax_u.legend(['Percent uniques'], frameon=1, facecolor='white',
                edgecolor='black', framealpha=.3)

    ax_t.set_title('Fit times - Seconds')
    fitting_seconds = [m.fitting_seconds for m in metrics]
    n_jobs, raw_time = itemgetter('n_jobs', 'formatted')(
        fit_metrics['total_fit_time'])
    total_fits, fit_calls, percent_calls, space, exploration = itemgetter(
        'total', 'processed', 'percent_processed',
        'space_points', 'exploration_percentage')(
        fit_metrics['fitness_func_calls'])
    version = fit_metrics['genetic_opt_version']
    ax_t.bar(population_idxs, fitting_seconds)
    # Create the legend
    handles = [plt.Line2D([], [], alpha=0)] * 5
    legend_labels = [
        f'Total fit time with {n_jobs} jobs: {raw_time}',
        f'Fitness_func calls: {fit_calls}/{total_fits} ({percent_calls} %)',
        f'Space exploration: {fit_calls}/{space} ({exploration} %)',
        f'Population size: {metrics[0].size}',
        f'`genetic_opt` version: {version}']
    ax_t.legend(handles, legend_labels, handlelength=0, frameon=1,
                facecolor='white', edgecolor='black', framealpha=.5)

    score_name_str = ''
    if score_name := getattr(metrics[0].best[0], 'name', ''):
        score_name_str = ' - ' + score_name.replace('_', ' ').title()

    fig.suptitle(f'Genetic Algorithm Metrics{score_name_str}')
    # Good if no `other keys`, let's see otherwise
    plt.subplots_adjust(top=0.94 if other_keys else 0.93)

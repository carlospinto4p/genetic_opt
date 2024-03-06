""" Genetic Opt plot functions for Algorithms training. """

# import matplotlib.pyplot as plt
# import pandas as pd
#
# from cpinto.formatters import format_seconds
# from cpinto.plot.bar import add_value_labels
#
#
# def plot_genetic_algo_metrics(genetic_algo_metrics: dict,
#                               score_name: str) -> None:
#     """
#     Plot genetic algorithm training metrics summary.
#     :param genetic_algo_metrics: internal dictionary of the class.
#         This method uses the keys:
#         - 'population'
#         - 'best_score'
#         - 'median'
#         - 'mean'
#         - 'fitting_seconds'
#         and also plot other keys if they are present.
#     :param score_name: target score to optimize name.
#     :return: None (but it creates a plt.Figure)
#     """
#     population_idxs = [i - 1 for i in genetic_algo_metrics['population']]
#     fig, (ax1, ax2, ax3, ax4) = plt.subplots(nrows=4, figsize=(13, 17))
#     ax1.set_title('Summary')
#     ax1.plot(population_idxs, genetic_algo_metrics['best_score'], lw=2.5)
#     ax1.plot(population_idxs, genetic_algo_metrics['median'], lw=1.4)
#     ax1.plot(population_idxs, genetic_algo_metrics['mean'], lw=1.4)
#     ax1.legend(['Best', 'Median', 'Mean'], frameon=1, facecolor='white',
#                edgecolor='black', framealpha=.3)
#
#     ax2.set_title('Scores')
#     other_keys = []
#     for k in genetic_algo_metrics:
#         if k not in ['population', 'best_score', 'median', 'mean',
#                      'fitting_seconds', 'n_uniques', 'var', 'percent_uniques']:
#             other_keys.append(k)
#             ax2.plot(population_idxs, genetic_algo_metrics[k], lw=1.6)
#     ax2.legend(other_keys, frameon=1, facecolor='white', edgecolor='black',
#                framealpha=.3)
#
#     ax3.set_title('Uniques in populations')
#     ax3.plot(population_idxs, genetic_algo_metrics['percent_uniques'], lw=2.5)
#     ax3.legend(['Percent uniques'], frameon=1, facecolor='white',
#                edgecolor='black', framealpha=.3)
#
#     ax4.set_title('Fit times - Seconds')
#     ax4.bar(population_idxs, genetic_algo_metrics['fitting_seconds'])
#     total_seconds = genetic_algo_metrics['fitting_seconds'].sum()
#     ax4.legend([f'Total fit time: {format_seconds(total_seconds)}'], frameon=1,
#                facecolor='white', edgecolor='black', framealpha=.3)
#     plt.suptitle(f'Genetic Algorithm Metrics - '
#                  f'{score_name.replace("_", " ").title()}')

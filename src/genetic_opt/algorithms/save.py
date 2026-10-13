"""Genetic Opt submodule that saves a run to a folder."""

from collections.abc import Callable
from pathlib import PurePosixPath

from genetic_opt.algorithms.config import SaveConfig
from genetic_opt.algorithms.plots import plot_genetic_algo_metrics
from genetic_opt.chromosome import Chromosome
from genetic_opt.exceptions import ValidationException
from genetic_opt.files import (
    create_new_folder,
    ensure_folder_format,
    normalize_path,
    save_bson,
    save_current_figure,
    save_json,
    save_yaml,
)
from genetic_opt.fit_result import FitParameters, FitResult
from genetic_opt.fit_result_io import serialize_fit_result
from genetic_opt.functions import now_for_file_path


class FitSaver:
    """
    Saves a run of a `GeneticAlgorithm` to a folder of its own:
    `experiment_config.yml`, one file for each generation inside
    `fit_data/` and `fit_plots.jpg`. `fit_result_io.load_fit_result`
    reads the files of `fit_data/` back.
    """

    def __init__(self, save: SaveConfig, experiment_name: str):
        """
        Create the folder of a run that starts now, as
        `<save.path>/<experiment_name>/<UTC date and time>`, with `_2`,
        `_3` and so on added when it exists. It is created here, so two
        runs started in the same second do not share it.
        :param save: where and how to save the run.
        :param experiment_name: a path inside `save.path`: not an
            absolute one, and without `..`.
        :raises ValidationException: when `experiment_name` is not a
            path inside `save.path`.
        """
        name_path = PurePosixPath(normalize_path(experiment_name))
        if name_path.is_absolute() or ".." in name_path.parts:
            raise ValidationException(
                f"experiment_name = {experiment_name!r} must be "
                f"a path inside the save path"
            )
        self.save: SaveConfig = save
        self.folder: str = create_new_folder(
            f"{ensure_folder_format(save.path)}/"
            f"{experiment_name}/{now_for_file_path()}"
        )

    def save_experiment_config(
        self, fit_parameters: FitParameters, experiment_config: dict
    ) -> None:
        """
        Save `experiment_config.yml`.
        :param fit_parameters: fit parameters used in the experiment.
        :param experiment_config: extra config of the experiment. It is
            left out of the file when empty.
        """
        config = {"fit_parameters": fit_parameters}
        if experiment_config:
            config["experiment_config"] = experiment_config
        save_yaml(config, file_path=f"{self.folder}/experiment_config")

    def save_generation(self, fit_result: FitResult) -> None:
        """
        Save the last generation of a fit result as
        `fit_data/fit_data_<number of the generation>`.
        :param fit_result: what `GeneticAlgorithm.fit` returns, with every
            generation so far.
        """
        # The file holds the last population and its metrics only, so
        # the earlier ones are not serialized.
        n_population = len(fit_result["historial"])
        serialized_data = serialize_fit_result(
            fit_result
            | {
                "historial": fit_result["historial"][-1:],
                "metrics": fit_result["metrics"][-1:],
            },
            self.save.serialize_decoded_chromosome_func,
            serialize_gene_func=self.save.serialize_gene_func,
        )
        serialized_data["population_idx"] = n_population
        serialized_data["population"] = serialized_data.pop("historial")[-1]
        file_path = f"{self.folder}/fit_data/fit_data_{n_population}"

        if self.save.as_bson:
            save_bson(serialized_data, file_path)
        else:
            save_json(serialized_data, file_path)

    def save_plots(
        self,
        fit_result: FitResult,
        other_metrics_to_plot: dict[str, Callable[[Chromosome], float]]
        | None = None,
    ) -> None:
        """
        Plot the metrics of a fit result and save them as `fit_plots.jpg`.
        :param fit_result: what `GeneticAlgorithm.fit` returns.
        :param other_metrics_to_plot: functions applied to the best
            Chromosome of each population, by the name of their metric.
        """
        plot_genetic_algo_metrics(
            metrics=fit_result["metrics"],
            fit_metrics=fit_result["fit_metrics"],
            other_keys=other_metrics_to_plot,
        )
        save_current_figure(f"{self.folder}/fit_plots")

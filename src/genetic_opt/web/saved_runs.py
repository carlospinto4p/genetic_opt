"""Genetic Opt runs saved by `fit` or the Rust crate, for the explainer."""

import json
from math import isinf
from pathlib import Path
from typing import Any

from genetic_opt.chromosome import Chromosome
from genetic_opt.exceptions import ValidationException
from genetic_opt.functions import format_bytes, identity_func
from genetic_opt.runs.files import get_files_inside_folder
from genetic_opt.runs.fit_result_io import load_fit_result
from genetic_opt.web.runs import generation_metrics

# Size of the files of a saved run over which `saved_run` refuses it: a
# run is read whole into memory and sent in one response
MAX_SAVED_RUN_BYTES = 4 * 10**9


def _shown_gene(gene: Any) -> Any:
    """
    A saved gene as the explainer shows it: a number or a text as it
    is, anything else, such as a dictionary, as JSON text. Either can
    go in a set, as the genes of a Chromosome saved as a set do.
    """
    if gene is None or isinstance(gene, int | float | str):
        return gene
    return json.dumps(gene, sort_keys=True, default=str)


def _saved_genes(chromosome: Chromosome) -> list:
    """The genes of a saved Chromosome, those of a set sorted."""
    if not chromosome.is_gene_set:
        return list(chromosome.genes)
    return sorted(chromosome.genes, key=lambda g: (type(g).__name__, g))


def saved_run(
    path: str,
    root: str | None = None,
    max_bytes: int = MAX_SAVED_RUN_BYTES,
) -> dict[str, Any]:
    """
    A run saved by `GeneticAlgorithm.fit`, or by the Rust crate, as the
    explainer shows it. The files hold each population and its scores,
    so there is no `breeding`, no `origin` and no decoded Chromosome.
    :param path: the folder of the run, or its `fit_data` folder.
    :param root: a folder `path` must be inside, links followed. Any
        folder by default.
    :param max_bytes: size of the files of the run over which it is
        refused without being read.
    :return: the keys of `record_run`, with `minimize` as `None`, since
        the files do not say it, and `stop_reason` as `stopped` when
        the run ended early for a reason the files do not hold. Also
        `folder`, the `fit_data` folder read, `fit_parameters` and
        `genetic_opt_version`, the version that saved it. An infinite
        `space_points` is `None`.
    :raises ValidationException: when `path` is outside `root`, is not
        a folder, does not hold a saved run, or its files have more than
        `max_bytes`.
    """
    folder = Path(path).expanduser()
    if root is not None and not folder.resolve().is_relative_to(
        Path(root).expanduser().resolve()
    ):
        raise ValidationException(f"`{path}` is not inside `{root}`")
    if (folder / "fit_data").is_dir():
        folder = folder / "fit_data"
    if not folder.is_dir():
        raise ValidationException(f"`{path}` is not a folder")
    files = get_files_inside_folder(str(folder), return_complete_path=True)
    if (size := sum(Path(file).stat().st_size for file in files)) > max_bytes:
        raise ValidationException(
            f"`{folder}` holds {format_bytes(size)}, more than the "
            f"{format_bytes(max_bytes)} the explainer opens"
        )
    result = load_fit_result(
        str(folder), decode_func=identity_func, load_gene_func=_shown_gene
    )
    generations = [
        {
            "population": [
                {
                    "genes": _saved_genes(chromosome),
                    "decoded": None,
                    "score": score.value,
                }
                for score, chromosome in population
            ],
            "metrics": generation_metrics(metric),
            "breeding": None,
        }
        for population, metric in zip(
            result["history"], result["metrics"], strict=True
        )
    ]
    parameters = result["fit_parameters"]
    # `load_fit_result` checks the files hold these keys, not what is
    # under them: a truncated run is refused here
    try:
        if len(generations) - 1 >= parameters["n_generations"]:
            stop_reason = "completed"
        elif (
            result["metrics"][-1].n_uniques
            < parameters["min_population_size"]
        ):
            stop_reason = "min_population"
        else:
            stop_reason = "stopped"
        calls = result["fit_metrics"]["fitness_func_calls"]
        if isinf(calls["space_points"]):
            calls = calls | {"space_points": None}
        chromosome_length = len(generations[0]["population"][0]["genes"])
        version = result["fit_metrics"]["genetic_opt_version"]
    except (IndexError, KeyError, TypeError) as error:
        raise ValidationException(
            f"`{folder}` is not a saved run: {error!r}"
        ) from error
    return {
        "chromosome_length": chromosome_length,
        "minimize": None,
        "generations": generations,
        "stop_reason": stop_reason,
        "fit_metrics": calls,
        "folder": str(folder),
        "fit_parameters": parameters,
        "genetic_opt_version": version,
    }

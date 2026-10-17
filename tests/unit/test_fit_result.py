from genetic_opt.algorithms import FitConfig
from genetic_opt.fit_result import (
    Bests,
    FitMetrics,
    FitnessFuncCalls,
    FitParameters,
    FitResult,
    FitResultFile,
    TotalFitTime,
)
from genetic_opt.fit_result_io import load_fit_result, load_fit_result_file
from tests.unit.conftest import decode_genes, ones_algorithm

# ── FitResult Types Tests ──────────────────────────────────────────────


def test_the_fit_result_types_name_the_keys_of_each_result(tmp_path):
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    fit_result = algorithm.fit(
        FitConfig(n_generations=1, population_size=20, n_jobs=1),
    )
    folder = f"{algorithm.save_path}/fit_data"
    fit_metrics = fit_result["fit_metrics"]

    # Without an `extra_config` there is no `config`, and a loaded run has
    # no `stop_reason`. The other optional keys are left out only by runs
    # of older versions.
    for result, result_type, left_out in (
        (fit_result, FitResult, {"config"}),
        (
            load_fit_result(folder, decode_genes),
            FitResult,
            {"config", "stop_reason"},
        ),
        (
            load_fit_result_file(f"{folder}/fit_data_1.json"),
            FitResultFile,
            {"config"},
        ),
        (fit_result["bests"], Bests, set()),
        (fit_result["fit_parameters"], FitParameters, set()),
        (fit_metrics, FitMetrics, set()),
        (fit_metrics["fitness_func_calls"], FitnessFuncCalls, set()),
        (fit_metrics["total_fit_time"], TotalFitTime, set()),
    ):
        assert set(result) == result_type.__required_keys__ | (
            result_type.__optional_keys__ - left_out
        )
    assert FitResult.__optional_keys__ == {"config", "stop_reason"}
    assert FitParameters.__optional_keys__ == {
        "selection",
        "tournament_size",
    }

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from genetic_opt import __version__
from genetic_opt.algorithms import FitConfig
from genetic_opt.web.app import (
    MAX_GENERATIONS,
    MAX_GENES,
    MAX_INTERVAL_END,
    MAX_POPULATION,
    app,
)
from tests.unit.conftest import ones_algorithm


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, base_url="http://localhost:5209")


# ── API Tests ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("host", "status"),
    [
        ("127.0.0.1:5209", 200),
        # As the front-end's dev server sends it on
        ("localhost:5208", 200),
        ("rebound.example:5209", 400),
    ],
)
def test_api_answers_only_the_names_of_this_machine(client, host, status):
    response = client.get("/api/info", headers={"host": host})
    assert response.status_code == status


def test_info_gives_the_package_version(client):
    response = client.get("/api/info")
    assert response.json() == {"name": "genetic_opt", "version": __version__}


def test_examples_give_the_readme_knapsack(client):
    knapsack = client.get("/api/examples").json()["knapsack"]
    assert knapsack["capacity"] == 165
    assert knapsack["weights"][:2] == [23, 31]
    assert knapsack["fit"]["mutate_prob"] == 0.05


def test_run_knapsack_with_the_defaults(client):
    run = client.post("/api/runs/knapsack", json={}).json()
    best = run["generations"][-1]["population"][0]
    assert run["chromosome_length"] == 10
    # The bag the decoded genes stand for is worth the score
    values = [92, 57, 49, 68, 60, 43, 67, 84, 87, 72]
    assert best["score"] == sum(
        v * g for v, g in zip(values, best["decoded"])
    )


def test_run_function_sends_the_curve(client):
    body = {"n_bits": 8, "fit": {"n_generations": 3, "population_size": 20}}
    run = client.post("/api/runs/function", json=body).json()
    assert run["chromosome_length"] == 8
    assert len(run["curve"]) == 401


def test_run_knapsack_refuses_weights_and_values_of_two_lengths(client):
    body = {"weights": [1, 2], "values": [1]}
    response = client.post("/api/runs/knapsack", json=body)
    assert response.status_code == 422
    assert "len(weights) = 2" in response.json()["detail"]


def test_run_knapsack_refuses_a_minimum_over_the_population(client):
    body = {"fit": {"population_size": 5, "min_population_size": 10}}
    response = client.post("/api/runs/knapsack", json=body)
    assert response.status_code == 422


def test_run_refuses_a_population_over_the_limit(client):
    body = {"fit": {"population_size": MAX_POPULATION + 1}}
    assert client.post("/api/runs/knapsack", json=body).status_code == 422


def test_run_refuses_generations_over_the_limit(client):
    body = {"fit": {"n_generations": MAX_GENERATIONS + 1}}
    assert client.post("/api/runs/function", json=body).status_code == 422


def test_examples_give_the_limits_of_a_run(client):
    limits = client.get("/api/examples").json()["limits"]
    assert limits == {
        "n_generations": MAX_GENERATIONS,
        "population_size": MAX_POPULATION,
        "genes": MAX_GENES,
    }


def test_run_function_refuses_an_empty_interval(client):
    body = {"low": 1.0, "high": 1.0}
    assert client.post("/api/runs/function", json=body).status_code == 422


@pytest.mark.parametrize(
    "interval",
    [
        '{"low": NaN}',
        '{"high": Infinity}',
        f'{{"low": {-MAX_INTERVAL_END * 10}}}',
        # Their difference is infinite
        '{"low": -1e308, "high": 1e308}',
    ],
)
def test_run_function_refuses_an_interval_without_finite_ends(
    client, interval
):
    response = client.post(
        "/api/runs/function",
        content=interval,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "body",
    [
        {"weights": [10, -1], "values": [1, 2]},
        {"weights": [10, 20], "values": [1, -2]},
        {"fit": {"min_population_size": MAX_POPULATION + 1}},
    ],
    ids=["weight", "value", "min_population_size"],
)
def test_run_knapsack_refuses_values_out_of_range(client, body):
    response = client.post("/api/runs/knapsack", json=body)
    assert response.status_code == 422


def test_open_a_saved_run(client, tmp_path):
    algorithm = ones_algorithm(tmp_path, save_as_bson=True)
    algorithm.fit(FitConfig(n_generations=2, population_size=20, n_jobs=1))
    response = client.post(
        "/api/runs/saved", json={"path": algorithm.save_path}
    )
    assert response.status_code == 200
    run = response.json()
    assert run["genetic_opt_version"] == __version__
    assert len(run["generations"][0]["population"]) == 20


def test_open_a_saved_run_refuses_one_outside_the_runs_root(
    client, tmp_path, monkeypatch
):
    algorithm = ones_algorithm(tmp_path, save_as_bson=True)
    algorithm.fit(FitConfig(n_generations=1, population_size=20, n_jobs=1))
    (root := tmp_path / "runs").mkdir()
    monkeypatch.setenv("GENETIC_OPT_WEB_RUNS_ROOT", str(root))
    body = {"path": algorithm.save_path}
    response = client.post("/api/runs/saved", json=body)
    assert response.status_code == 422
    assert "is not inside" in response.json()["detail"]


def test_open_a_saved_run_refuses_a_truncated_run(client, tmp_path):
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    algorithm.fit(FitConfig(n_generations=1, population_size=20, n_jobs=1))
    for file in (Path(algorithm.save_path) / "fit_data").iterdir():
        raw = json.loads(file.read_text())
        del raw["fit_parameters"]["n_generations"]
        file.write_text(json.dumps(raw))
    body = {"path": algorithm.save_path}
    response = client.post("/api/runs/saved", json=body)
    assert response.status_code == 422
    assert "is not a saved run" in response.json()["detail"]


def test_open_a_saved_run_refuses_a_missing_folder(client, tmp_path):
    body = {"path": str(tmp_path / "missing")}
    response = client.post("/api/runs/saved", json=body)
    assert response.status_code == 422
    assert "is not a folder" in response.json()["detail"]

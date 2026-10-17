import pytest
from fastapi.testclient import TestClient

from genetic_opt import __version__
from genetic_opt.web.app import MAX_POPULATION, app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── API Tests ──────────────────────────────────────────────────────────


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


def test_run_function_refuses_an_empty_interval(client):
    body = {"low": 1.0, "high": 1.0}
    assert client.post("/api/runs/function", json=body).status_code == 422

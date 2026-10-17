"""
Genetic Opt web server: the API the explainer in `frontend/` calls.

Run it with `uv run python -m genetic_opt.web.app`.
"""

import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from genetic_opt import __version__
from genetic_opt.algorithms.config import FitConfig
from genetic_opt.exceptions import ValidationException
from genetic_opt.web.runs import (
    FUNCTION_BITS,
    FUNCTION_HIGH,
    FUNCTION_LOW,
    KNAPSACK_CAPACITY,
    KNAPSACK_VALUES,
    KNAPSACK_WEIGHTS,
    function_run,
    knapsack_run,
)

# Port of the API. The front-end's dev server sends `/api` to it.
DEFAULT_PORT = 5209

# Upper bounds of a run: every generation goes back in one response,
# so a large run would hold the server and send megabytes.
MAX_GENERATIONS = 300
MAX_POPULATION = 400
MAX_GENES = 40


class FitParams(BaseModel):
    """The `FitConfig` of a run, and the seeds of its algorithm."""

    n_generations: int = Field(100, ge=0, le=MAX_GENERATIONS)
    population_size: int = Field(50, ge=1, le=MAX_POPULATION)
    crossovers_prop: float = Field(FitConfig.crossovers_prop, ge=0, le=1)
    besties_prop: float = Field(FitConfig.besties_prop, ge=0, le=1)
    mutate_prob: float = Field(FitConfig.mutate_prob, ge=0, le=1)
    min_population_size: int = Field(FitConfig.min_population_size, ge=0)
    stop_without_improvement: bool = FitConfig.stop_without_improvement
    random_seed: int = Field(442, ge=0, lt=2**32)
    gene_space_random_seed: int = Field(2, ge=0, lt=2**32)

    def fit_config(self) -> FitConfig:
        """The `FitConfig` of these parameters, scored in one process."""
        return FitConfig(
            n_generations=self.n_generations,
            population_size=self.population_size,
            crossovers_prop=self.crossovers_prop,
            besties_prop=self.besties_prop,
            mutate_prob=self.mutate_prob,
            min_population_size=self.min_population_size,
            stop_without_improvement=self.stop_without_improvement,
            # The fitness functions take microseconds: worker processes
            # would cost more than they save.
            n_jobs=1,
        )


class KnapsackRequest(BaseModel):
    weights: list[int] = Field(
        default_factory=lambda: list(KNAPSACK_WEIGHTS),
        min_length=1,
        max_length=MAX_GENES,
    )
    values: list[int] = Field(
        default_factory=lambda: list(KNAPSACK_VALUES),
        min_length=1,
        max_length=MAX_GENES,
    )
    capacity: int = Field(KNAPSACK_CAPACITY, ge=0)
    fit: FitParams = Field(default_factory=FitParams)


class FunctionRequest(BaseModel):
    low: float = FUNCTION_LOW
    high: float = FUNCTION_HIGH
    n_bits: int = Field(FUNCTION_BITS, ge=2, le=MAX_GENES)
    fit: FitParams = Field(default_factory=FitParams)

    @model_validator(mode="after")
    def check_interval(self) -> FunctionRequest:
        if self.low >= self.high:
            raise ValueError(
                f"low ({self.low}) must be under high ({self.high})"
            )
        return self


app = FastAPI(title="genetic_opt explainer")


@app.get("/api/info")
def get_info() -> dict[str, str]:
    return {"name": "genetic_opt", "version": __version__}


@app.get("/api/examples")
def get_examples() -> dict[str, Any]:
    """The default problem and parameters of each example."""
    return {
        "knapsack": KnapsackRequest().model_dump(),
        "function": FunctionRequest().model_dump(),
        "limits": {
            "n_generations": MAX_GENERATIONS,
            "population_size": MAX_POPULATION,
            "genes": MAX_GENES,
        },
    }


def _run(func: Any, **kwargs: Any) -> dict[str, Any]:
    """Call a run function, turning what the algorithm refuses into 422."""
    try:
        return func(**kwargs)
    except ValidationException as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/runs/knapsack")
def run_knapsack(request: KnapsackRequest) -> dict[str, Any]:
    return _run(
        knapsack_run,
        weights=request.weights,
        values=request.values,
        capacity=request.capacity,
        config=request.fit.fit_config(),
        random_seed=request.fit.random_seed,
        gene_space_random_seed=request.fit.gene_space_random_seed,
    )


@app.post("/api/runs/function")
def run_function(request: FunctionRequest) -> dict[str, Any]:
    return _run(
        function_run,
        low=request.low,
        high=request.high,
        n_bits=request.n_bits,
        config=request.fit.fit_config(),
        random_seed=request.fit.random_seed,
        gene_space_random_seed=request.fit.gene_space_random_seed,
    )


def main() -> None:
    """Serve the API on `GENETIC_OPT_WEB_PORT`, or `DEFAULT_PORT`."""
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    port = int(os.environ.get("GENETIC_OPT_WEB_PORT", DEFAULT_PORT))
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()

import subprocess
import sys

import pytest

# ── Package Import Tests ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "module", ["genetic_opt.algorithms", "genetic_opt.examples.binary"]
)
def test_importing_the_package_leaves_the_save_libraries_out(module):
    # A new interpreter, because this one has imported them already.
    code = (
        f"import sys, {module}\n"
        "print([m for m in ('bson', 'matplotlib', 'yaml')"
        " if m in sys.modules])"
    )
    done = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    assert done.stdout.strip() == "[]"


def test_the_algorithms_package_keeps_the_names_other_projects_import():
    from genetic_opt import algorithms
    from genetic_opt.algorithms.base import GeneticAlgorithm
    from genetic_opt.algorithms.config import FitConfig, SaveConfig
    from genetic_opt.chromosome import Chromosome
    from genetic_opt.score import Score

    assert algorithms.GeneticAlgorithm is GeneticAlgorithm
    assert algorithms.FitConfig is FitConfig
    assert algorithms.SaveConfig is SaveConfig
    assert algorithms.Chromosome is Chromosome
    assert algorithms.Score is Score

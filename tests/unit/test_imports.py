import subprocess
import sys

import pytest


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

import logging

import pytest

from genetic_opt.exceptions import (
    GeneticOptException,
    InvariantException,
    ValidationException,
)

# ── GeneticOptException Tests ──────────────────────────────────────────


def test_exception_message_includes_the_processing_object():
    exception = GeneticOptException("bad size", {"size": 3})
    assert exception.message == "bad size"
    assert exception.processing_object == {"size": 3}
    assert str(exception) == (
        "GeneticOptException: bad size\n\tAt object:\n{'size': 3}"
    )


def test_exception_is_not_logged(caplog):
    with caplog.at_level(logging.DEBUG, logger="genetic_opt"):
        GeneticOptException("bad size", {"size": 3})
    assert caplog.records == []


@pytest.mark.parametrize(
    "exception_class", [InvariantException, ValidationException]
)
def test_exceptions_are_genetic_opt_exceptions(exception_class):
    with pytest.raises(GeneticOptException, match=exception_class.__name__):
        raise exception_class("failed")

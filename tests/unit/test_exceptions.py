import logging

import pytest

from genetic_opt.exceptions import (
    GeneticOptException,
    InvariantException,
    ValidationException,
)

# ── GeneticOptException Tests ──────────────────────────────────────────


def test_exception_message_is_prefixed_with_the_class_name():
    exception = GeneticOptException("bad size")
    assert exception.message == "bad size"
    assert str(exception) == "GeneticOptException: bad size"


def test_exception_is_not_logged(caplog):
    with caplog.at_level(logging.DEBUG, logger="genetic_opt"):
        GeneticOptException("bad size")
    assert caplog.records == []


@pytest.mark.parametrize(
    "exception_class", [InvariantException, ValidationException]
)
def test_exceptions_are_genetic_opt_exceptions(exception_class):
    with pytest.raises(GeneticOptException, match=exception_class.__name__):
        raise exception_class("failed")

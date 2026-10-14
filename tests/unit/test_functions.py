import logging
import re

import numpy as np
import pytest

from genetic_opt.chromosome import Chromosome
from genetic_opt.exceptions import (
    GeneticOptException,
    InvariantException,
    ValidationException,
)
from genetic_opt.functions import (
    format_bytes,
    format_seconds,
    identity_func,
    now_for_file_path,
    time_it_with_logger,
)
from genetic_opt.gene_space import BinaryGeneSpace


def test_identity_func_returns_its_input():
    value = [1, 2]
    assert identity_func(value) is value


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (12.345, "12.35 seconds"),
        (75, "1:15 minutes"),
        (3_725, "1:02:05 hours"),
        (90_000, "1 day, 1:00:00 hours"),
        (200_000, "2 days, 7:33:20 hours"),
    ],
)
def test_format_seconds(seconds, expected):
    assert format_seconds(seconds) == expected


def test_format_seconds_only_hours():
    assert format_seconds(200_000, only_hours=True) == "55:33:20"


@pytest.mark.parametrize(
    "num_bytes, expected",
    [(512, "512.0 B"), (1536, "1.5 KiB"), (3 * 1024**3, "3.0 GiB")],
)
def test_format_bytes(num_bytes, expected):
    assert format_bytes(num_bytes) == expected


def test_now_for_file_path_format():
    assert re.fullmatch(r"\d{8}_\d{6}", now_for_file_path())


def test_time_it_with_logger_logs_and_returns(caplog):
    logger = logging.getLogger("test_time_it")

    @time_it_with_logger(logger)
    def double(x):
        return 2 * x

    with caplog.at_level(logging.INFO, logger="test_time_it"):
        assert double(4) == 8
    assert [r.message for r in caplog.records] == [
        "`double` started...",
        "`double` took 0.00 seconds",
    ]


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


def test_the_package_leaves_logging_to_the_application():
    logger = logging.getLogger("genetic_opt")
    assert logger.handlers == []
    assert logger.propagate
    assert logger.level == logging.NOTSET


def test_construction_errors_name_the_sizes_and_nothing_else():
    with pytest.raises(GeneticOptException) as no_genes:
        Chromosome(size=3)
    assert no_genes.value.processing_object is None

    with pytest.raises(GeneticOptException) as wrong_size:
        Chromosome(size=2, genes=[1, 0, 1])
    assert wrong_size.value.processing_object is None
    assert wrong_size.value.message == (
        "Chromosome size (2) must match the length of the genes (3)"
    )

    with pytest.raises(GeneticOptException) as small_space:
        Chromosome(size=3, gene_space=BinaryGeneSpace(), is_gene_set=True)
    assert small_space.value.processing_object is None
    assert small_space.value.message == (
        "Chromosome received a `size` (3) greater than its `gene_space` (2)"
    )


@pytest.mark.parametrize("is_gene_set", [False, True])
def test_a_chromosome_needs_genes_or_a_gene_space(is_gene_set):
    with pytest.raises(GeneticOptException) as no_genes:
        Chromosome(size=3, genes=np.array([]), is_gene_set=is_gene_set)
    assert no_genes.value.message == (
        "Chromosome must be initialized with the `genes` parameter "
        "or using a `gene_space`"
    )


@pytest.mark.parametrize("is_gene_set", [False, True])
def test_chromosome_genes_and_size_follow_its_gene_collection(is_gene_set):
    chromosome = Chromosome(
        size=2, gene_space=BinaryGeneSpace(), is_gene_set=is_gene_set
    )
    mutated = chromosome.random_mutate(
        gene_space=BinaryGeneSpace(), gene_mutate_prob=1.0
    )
    assert mutated.genes is mutated.gene_collection.genes
    assert mutated.size == mutated.gene_collection.size == 2
    assert chromosome.genes is chromosome.gene_collection.genes


@pytest.mark.parametrize(
    "exception_class", [InvariantException, ValidationException]
)
def test_exceptions_are_genetic_opt_exceptions(exception_class):
    with pytest.raises(GeneticOptException, match=exception_class.__name__):
        raise exception_class("failed")

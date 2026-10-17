import pytest
from numpy import ndarray

from genetic_opt.chromosome import Chromosome
from genetic_opt.exceptions import ValidationException
from genetic_opt.gene_space import BinaryGeneSpace, ValuesGeneSpace

# ── BinaryGeneSpace Tests ──────────────────────────────────────────────


def test_select_random_with_no_n_returns_one_gene():
    gene = BinaryGeneSpace().select_random()
    assert not isinstance(gene, ndarray)
    assert gene in (0, 1)


@pytest.mark.parametrize("n", [1, 2, 25])
def test_select_random_with_an_int_returns_that_many_genes(n):
    genes = BinaryGeneSpace().select_random(n=n)
    assert genes.shape == (n,)
    assert set(genes.tolist()) <= {0, 1}


@pytest.mark.parametrize("n", [(1,), (3, 4), (2, 3, 5)])
def test_select_random_with_a_tuple_returns_genes_in_that_shape(n):
    genes = BinaryGeneSpace().select_random(n=n)
    assert genes.shape == n
    assert set(genes.flatten().tolist()) <= {0, 1}


# ── ValuesGeneSpace Tests ──────────────────────────────────────────────

VALUES = ["sun", 7, (2, 3), 0.5]


def test_values_gene_space_has_the_length_of_its_values():
    assert len(ValuesGeneSpace(VALUES)) == 4


def test_values_select_random_with_no_n_returns_one_value():
    gene = ValuesGeneSpace(VALUES).select_random()
    assert any(gene is value for value in VALUES)


@pytest.mark.parametrize("n", [1, 2, 25])
def test_values_select_random_with_an_int_returns_that_many_values(n):
    genes = ValuesGeneSpace(VALUES).select_random(n=n)
    assert genes.shape == (n,)
    assert all(gene in VALUES for gene in genes.tolist())


@pytest.mark.parametrize("n", [(1,), (3, 4), (2, 3, 5)])
def test_values_select_random_with_a_tuple_returns_values_in_that_shape(n):
    genes = ValuesGeneSpace(VALUES).select_random(n=n)
    assert genes.shape == n
    assert all(gene in VALUES for gene in genes.flatten().tolist())


def test_values_keep_their_types_when_drawn():
    genes = ValuesGeneSpace(VALUES, random_seed=3).select_random(n=200)
    assert {type(gene) for gene in genes.tolist()} == {
        str,
        int,
        tuple,
        float,
    }


def test_values_gene_space_draws_the_same_genes_with_a_seed():
    first = ValuesGeneSpace(VALUES, random_seed=9).select_random(n=30)
    second = ValuesGeneSpace(VALUES, random_seed=9).select_random(n=30)
    assert first.tolist() == second.tolist()


@pytest.mark.parametrize("is_gene_set", [False, True])
def test_values_gene_space_fills_a_chromosome(is_gene_set):
    chromosome = Chromosome(
        size=3,
        gene_space=ValuesGeneSpace(["a", "b", "c", "d"]),
        is_gene_set=is_gene_set,
    )
    assert len(chromosome.genes) == 3
    assert set(chromosome.genes) <= {"a", "b", "c", "d"}


@pytest.mark.parametrize("values", [[], ["a", "b", "a"]])
def test_values_gene_space_refuses_no_values_or_repeated_ones(values):
    with pytest.raises(ValidationException):
        ValuesGeneSpace(values)

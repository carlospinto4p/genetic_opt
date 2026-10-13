import pytest
from numpy import ndarray

from genetic_opt.gene_space import BinaryGeneSpace

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

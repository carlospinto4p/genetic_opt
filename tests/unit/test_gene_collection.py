import numpy as np
import pytest

from genetic_opt.chromosome import Chromosome
from genetic_opt.exceptions import (
    ValidationException,
)
from genetic_opt.gene_space import AbstractGeneSpace, BinaryGeneSpace

# ── GeneList and GeneSet Tests ─────────────────────────────────────────


class RangeGeneSpace(AbstractGeneSpace):
    """Gene space of the numbers 0 to 19 that records how it is called."""

    def __init__(self):
        super().__init__(random_seed=7)
        self.calls: list[int | None] = []

    def __len__(self) -> int:
        return 20

    def select_random(self, n=None):
        self.calls.append(n)
        return self.random_state.choice(20, size=n)


def test_list_mutation_draws_its_new_genes_with_one_call():
    size = 40
    gene_space = RangeGeneSpace()
    chromosome = Chromosome(size=size, genes=[-1] * size).random_mutate(
        gene_space=gene_space, gene_mutate_prob=0.5
    )
    n_mutated = sum(gene != -1 for gene in chromosome.genes)
    assert 1 < n_mutated < size
    assert gene_space.calls == [n_mutated]
    assert all(type(gene) is int for gene in chromosome.genes)


@pytest.mark.parametrize("probability, n_mutated", [(0, 0), (1, 40)])
def test_list_mutation_with_probability_0_and_1(probability, n_mutated):
    gene_space = RangeGeneSpace()
    chromosome = Chromosome(size=40, genes=[-1] * 40).random_mutate(
        gene_space=gene_space, gene_mutate_prob=probability
    )
    assert sum(gene != -1 for gene in chromosome.genes) == n_mutated
    assert gene_space.calls == ([n_mutated] if n_mutated else [])


def test_set_mutation_with_probability_0_keeps_every_gene():
    gene_space = RangeGeneSpace()
    chromosome = Chromosome(
        size=8, genes=set(range(100, 108)), is_gene_set=True
    ).random_mutate(gene_space=gene_space, gene_mutate_prob=0)
    assert chromosome.genes == set(range(100, 108))
    assert gene_space.calls == []


def test_set_mutation_with_probability_1_replaces_every_gene():
    gene_space = RangeGeneSpace()
    chromosome = Chromosome(
        size=8, genes=set(range(100, 108)), is_gene_set=True
    ).random_mutate(gene_space=gene_space, gene_mutate_prob=1)
    assert isinstance(chromosome.genes, set)
    assert len(chromosome.genes) == 8
    assert chromosome.genes <= set(range(20))
    # Equal new genes are drawn again until the set has 8.
    assert gene_space.calls[0] == 8


def test_set_mutation_keeps_the_size_of_the_set():
    gene_space = RangeGeneSpace()
    unmutated = Chromosome(
        size=8, genes=set(range(100, 108)), is_gene_set=True
    )
    chromosome = unmutated.random_mutate(
        gene_space=gene_space, gene_mutate_prob=0.5
    )
    assert unmutated.genes == set(range(100, 108))
    assert isinstance(chromosome.genes, set)
    assert len(chromosome.genes) == 8
    kept = chromosome.genes & set(range(100, 108))
    assert 0 < len(kept) < 8
    assert chromosome.genes - kept <= set(range(20))


def test_a_set_as_large_as_its_gene_space_holds_every_gene():
    gene_space = RangeGeneSpace()
    chromosome = Chromosome(size=20, gene_space=gene_space, is_gene_set=True)
    assert isinstance(chromosome.genes, set)
    assert chromosome.genes == set(range(20))
    mutated = chromosome.random_mutate(
        gene_space=gene_space, gene_mutate_prob=0.5
    )
    assert mutated.genes == set(range(20))


def test_a_chromosome_built_from_a_gene_space_draws_with_one_call():
    gene_space = RangeGeneSpace()
    chromosome = Chromosome(size=12, gene_space=gene_space)
    assert gene_space.calls == [12]
    assert len(chromosome.genes) == 12
    assert set(chromosome.genes) <= set(range(20))


@pytest.mark.parametrize("is_gene_set", [False, True])
def test_a_gene_drawn_alone_is_a_plain_python_value(is_gene_set):
    # A single gene is drawn without `n`, and `BinaryGeneSpace` returns
    # a numpy integer for it. numpy 2 prints that as `np.int64(1)`, so
    # it gave the Chromosome another `id` than the same genes as `int`.
    drawn = Chromosome(
        size=1, gene_space=BinaryGeneSpace(), is_gene_set=is_gene_set
    )
    (gene,) = drawn.genes
    assert type(gene) is int
    assert drawn == Chromosome(size=1, genes=[gene], is_gene_set=is_gene_set)


def test_a_set_chromosome_does_not_fill_the_set_it_is_given():
    genes = {100, 101}
    chromosome = Chromosome(
        size=5, genes=genes, gene_space=RangeGeneSpace(), is_gene_set=True
    )
    assert genes == {100, 101}
    assert len(chromosome.genes) == 5
    assert {100, 101} <= chromosome.genes


@pytest.mark.parametrize("given", [tuple, frozenset])
def test_a_set_chromosome_takes_any_collection_of_genes(given):
    chromosome = Chromosome(
        size=5,
        genes=given([100, 101]),
        gene_space=RangeGeneSpace(),
        is_gene_set=True,
    )
    assert isinstance(chromosome.genes, set)
    assert len(chromosome.genes) == 5
    assert {100, 101} <= chromosome.genes


@pytest.mark.parametrize("n_given", [2, 5])
def test_a_list_chromosome_takes_a_tuple_of_genes(n_given):
    genes = (1, 0, 1, 1, 0)[:n_given]
    chromosome = Chromosome(size=5, genes=genes, gene_space=RangeGeneSpace())
    assert isinstance(chromosome.genes, list)
    assert chromosome.genes[:n_given] == list(genes)
    assert len(chromosome.genes) == 5


def test_construction_errors_name_the_sizes():
    with pytest.raises(ValidationException) as wrong_size:
        Chromosome(size=2, genes=[1, 0, 1])
    assert wrong_size.value.message == (
        "Chromosome size (2) must match the length of the genes (3)"
    )

    with pytest.raises(ValidationException) as small_space:
        Chromosome(size=3, gene_space=BinaryGeneSpace(), is_gene_set=True)
    assert small_space.value.message == (
        "Chromosome received a `size` (3) greater than its `gene_space` (2)"
    )


@pytest.mark.parametrize("is_gene_set", [False, True])
def test_a_chromosome_needs_genes_or_a_gene_space(is_gene_set):
    with pytest.raises(ValidationException) as no_genes:
        Chromosome(size=3, genes=np.array([]), is_gene_set=is_gene_set)
    assert no_genes.value.message == (
        "Chromosome must be initialized with the `genes` parameter "
        "or using a `gene_space`"
    )


@pytest.mark.parametrize("is_gene_set", [False, True])
def test_a_chromosome_short_of_genes_needs_a_gene_space(is_gene_set):
    with pytest.raises(ValidationException) as short:
        Chromosome(size=3, genes=[1], is_gene_set=is_gene_set)
    assert short.value.message == (
        "Chromosome received 1 genes for a `size` of 3, and no "
        "`gene_space` to draw the rest from"
    )

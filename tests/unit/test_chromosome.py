import json
import pickle

import pytest

from genetic_opt.chromosome import Chromosome
from genetic_opt.gene_space import BinaryGeneSpace
from genetic_opt.score import Score
from tests.unit.conftest import OnesGeneSpace

# ── Chromosome Tests ───────────────────────────────────────────────────


def test_a_chromosome_builds_its_random_state_on_first_use():
    size = 40
    unused = Chromosome(size=size, genes=[0] * size)
    unused_bytes = len(pickle.dumps(unused))
    # Two Chromosomes with one seed and no state given mutate alike.
    first, second = (
        Chromosome(size=size, genes=[0] * size).random_mutate(
            gene_space=OnesGeneSpace(), gene_mutate_prob=0.5
        )
        for _ in range(2)
    )
    assert 0 < sum(first.genes) < size
    assert first.genes == second.genes
    # The state is some 3 KB of a pickled Chromosome.
    assert unused_bytes < 1000 < len(pickle.dumps(first))


def test_a_mutated_chromosome_gets_a_new_id():
    size = 40
    unmutated = Chromosome(size=size, genes=[0] * size)
    unmutated_id = unmutated.id
    chromosome = unmutated.random_mutate(
        gene_space=OnesGeneSpace(), gene_mutate_prob=0.5
    )
    assert chromosome.id != unmutated_id
    same_genes = Chromosome(size=size, genes=list(chromosome.genes))
    assert chromosome.id == same_genes.id
    assert hash(chromosome) == hash(same_genes)
    assert chromosome == same_genes


def test_mutation_leaves_the_chromosome_as_it_was():
    size = 40
    chromosome = Chromosome(size=size, genes=[0] * size)
    chromosome.score, chromosome.score_time = Score(value=3), 0.5
    by_chromosome = {chromosome: "kept"}
    mutated = chromosome.random_mutate(
        gene_space=OnesGeneSpace(), gene_mutate_prob=0.5
    )
    assert mutated is not chromosome
    assert 0 < sum(mutated.genes) < size
    assert mutated.score is None
    assert mutated.score_time == 0
    assert chromosome.genes == [0] * size
    assert chromosome.score.value == 3
    assert by_chromosome[chromosome] == "kept"


@pytest.mark.parametrize("other", [None, "[1, 0, 1]", [1, 0, 1]])
def test_a_chromosome_differs_from_what_is_not_a_chromosome(other):
    chromosome = Chromosome(size=3, genes=[1, 0, 1])
    assert chromosome != other
    assert (chromosome == other) is False


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
    "genes, is_gene_set", [([1, 0, 1], False), ({3, 7, 11}, True)]
)
@pytest.mark.parametrize("scored", [True, False])
def test_a_chromosome_comes_back_whole_from_its_dict(
    genes, is_gene_set, scored
):
    chromosome = Chromosome(
        size=3, genes=genes, random_seed=7, is_gene_set=is_gene_set
    )
    if scored:
        chromosome.score = Score(
            value=2.5, name="sum", extra_metrics={"zeros": 1}
        )
        chromosome.score_time = 0.25
    # Through JSON, as `fit` saves it.
    loaded = Chromosome.from_dict(
        json.loads(json.dumps(chromosome.to_dict(serialize_gene_func=str))),
        load_genes_func=int,
    )
    assert type(loaded.genes) is type(genes)
    assert (
        loaded.genes,
        loaded.is_gene_set,
        loaded.score,
        loaded.score_time,
        loaded.random_seed,
    ) == (
        genes,
        is_gene_set,
        chromosome.score,
        chromosome.score_time,
        7,
    )


def test_chromosome_from_dict_builds_the_subclass_it_is_called_on():
    class NamedChromosome(Chromosome):
        pass

    chromosome = Chromosome(size=2, genes=[1, 0])
    loaded = NamedChromosome.from_dict(chromosome.to_dict())
    assert type(loaded) is NamedChromosome

"""Genetic Opt crossover functions, over two lists of genes."""

from collections.abc import Callable, Sequence

from numpy.random import RandomState

# What `BinaryGeneticAlgorithm` takes as its `crossover`
CrossoverFunc = Callable[[Sequence, Sequence, RandomState], tuple[list, list]]


def single_point_crossover(
    genes_1: Sequence, genes_2: Sequence, random_state: RandomState
) -> tuple[list, list]:
    """
    Cut two lists of genes at the same random position and swap their
    tails.
    :param genes_1: genes of the first parent.
    :param genes_2: genes of the second parent.
    :param random_state: numpy RandomState object that draws the cut.
    :return: the genes of the two children. With fewer than two genes
        in the shorter parent, copies of the parents.
    """
    length = min(len(genes_1), len(genes_2))
    # A cut needs a gene on each side, and `randint` leaves its upper
    # bound out
    if length < 2:
        return list(genes_1), list(genes_2)
    cut = random_state.randint(1, length)
    return (
        list(genes_1[:cut]) + list(genes_2[cut:]),
        list(genes_2[:cut]) + list(genes_1[cut:]),
    )


def uniform_crossover(
    genes_1: Sequence, genes_2: Sequence, random_state: RandomState
) -> tuple[list, list]:
    """
    Give each child, at each position, the gene of one parent or the
    other, with even odds, and the other child the other gene.
    :param genes_1: genes of the first parent.
    :param genes_2: genes of the second parent.
    :param random_state: numpy RandomState object that draws the
        positions swapped.
    :return: the genes of the two children. Past the length of the
        shorter parent, each child keeps the genes of its own parent.
    """
    child_1, child_2 = list(genes_1), list(genes_2)
    length = min(len(genes_1), len(genes_2))
    swaps = (random_state.random(length) < 0.5).tolist()
    for position, swap in enumerate(swaps):
        if swap:
            child_1[position] = genes_2[position]
            child_2[position] = genes_1[position]
    return child_1, child_2

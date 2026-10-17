from numpy.random import RandomState

from genetic_opt.crossover import single_point_crossover, uniform_crossover

# ── single_point_crossover Tests ───────────────────────────────────────


def test_single_point_crossover_cuts_at_every_position_between_genes():
    random_state = RandomState(seed=1)
    cuts = set()
    for _ in range(200):
        first, second = single_point_crossover([0] * 5, [1] * 5, random_state)
        cut = first.index(1)
        assert first == [0] * cut + [1] * (5 - cut)
        assert second == [1] * cut + [0] * (5 - cut)
        cuts.add(cut)
    assert cuts == {1, 2, 3, 4}


def test_single_point_crossover_of_fewer_than_two_genes_copies_parents():
    random_state = RandomState(seed=1)
    assert single_point_crossover([0], [1], random_state) == ([0], [1])
    assert single_point_crossover([], [], random_state) == ([], [])


# ── uniform_crossover Tests ────────────────────────────────────────────


def test_uniform_crossover_gives_each_gene_to_either_child():
    random_state = RandomState(seed=1)
    swapped = [0] * 5
    for _ in range(200):
        first, second = uniform_crossover([0] * 5, [1] * 5, random_state)
        for position in range(5):
            # The two children share the genes of the parents out
            assert first[position] + second[position] == 1
            swapped[position] += first[position]
    # Each position is swapped about half of the times
    assert all(60 <= count <= 140 for count in swapped)


def test_uniform_crossover_of_different_lengths_keeps_the_longer_tail():
    random_state = RandomState(seed=1)
    for _ in range(50):
        first, second = uniform_crossover([0] * 2, [1] * 4, random_state)
        assert len(first) == 2
        assert second[2:] == [1, 1]
        assert [a + b for a, b in zip(first, second[:2])] == [1, 1]
    assert uniform_crossover([], [], random_state) == ([], [])


def test_uniform_crossover_keeps_the_parents_unchanged():
    genes_1, genes_2 = ["a", "b", "c"], ["x", "y", "z"]
    uniform_crossover(genes_1, genes_2, RandomState(seed=1))
    assert (genes_1, genes_2) == (["a", "b", "c"], ["x", "y", "z"])

use std::collections::BTreeSet;
use std::hash::Hash;

use rand::RngExt;
use serde::Serialize;

use crate::Score;

/// The random number generator handed to a [`Problem`]. Its output for a
/// given seed does not change between versions of the `rand` crates.
pub type Rng = rand_chacha::ChaCha8Rng;

/// An optimization problem a [`crate::GeneticAlgorithm`] can run.
///
/// A gene is a symbol, and a chromosome is a list or a set of genes that
/// encodes one candidate solution. The algorithm calls `fitness` from
/// several threads at once, and everything else from one.
pub trait Problem: Sync {
    type Gene: Clone + Ord + Hash + Send + Sync + Serialize;
    /// What a chromosome stands for in the terms of the problem.
    type Solution: Serialize;

    /// Number of genes in every chromosome.
    fn chromosome_length(&self) -> usize;

    /// Whether a chromosome is a set of distinct genes with no order.
    fn chromosome_as_set(&self) -> bool {
        false
    }

    /// Whether the best score is the lowest one, not the highest.
    fn minimize(&self) -> bool;

    /// Number of different genes there are.
    fn gene_space_size(&self) -> usize;

    fn random_gene(&self, rng: &mut Rng) -> Self::Gene;

    /// A score whose value is NaN stops the run with
    /// [`Error::Validation`](crate::Error::Validation).
    fn fitness(&self, genes: &[Self::Gene]) -> Score;

    fn decode(&self, genes: &[Self::Gene]) -> Self::Solution;

    /// Recombine two chromosomes into two new ones.
    fn crossover(
        &self,
        first: &[Self::Gene],
        second: &[Self::Gene],
        rng: &mut Rng,
    ) -> (Vec<Self::Gene>, Vec<Self::Gene>);

    /// The genes of each chromosome of the first population.
    fn init_population(&self, population_size: usize, rng: &mut Rng) -> Vec<Vec<Self::Gene>> {
        (0..population_size)
            .map(|_| {
                if self.chromosome_as_set() {
                    self.fill_set(BTreeSet::new(), rng)
                } else {
                    (0..self.chromosome_length())
                        .map(|_| self.random_gene(rng))
                        .collect()
                }
            })
            .collect()
    }

    /// Replace each gene by a random one with probability `prob`.
    fn mutate(&self, genes: &[Self::Gene], prob: f64, rng: &mut Rng) -> Vec<Self::Gene> {
        let mutated = genes.iter().map(|gene| {
            if rng.random::<f64>() < prob {
                self.random_gene(rng)
            } else {
                gene.clone()
            }
        });
        if self.chromosome_as_set() {
            let mutated = mutated.collect();
            self.fill_set(mutated, rng)
        } else {
            mutated.collect()
        }
    }

    /// Whether a mutation kept what the problem needs kept. The run stops
    /// with [`crate::Error::Invariant`] when it did not.
    fn mutation_invariant(&self, _before: &[Self::Gene], _after: &[Self::Gene]) -> bool {
        true
    }

    /// The same check, for a crossover.
    fn crossover_invariant(
        &self,
        _parents: (&[Self::Gene], &[Self::Gene]),
        _children: (&[Self::Gene], &[Self::Gene]),
    ) -> bool {
        true
    }

    /// Saved in `experiment_config.yml` beside the parameters of the run.
    fn experiment_config(&self) -> Option<serde_json::Value> {
        None
    }

    /// Add random genes to a set until it has `chromosome_length` of them.
    /// The gene space must hold at least that many, which the algorithm
    /// checks before it starts.
    fn fill_set(&self, mut genes: BTreeSet<Self::Gene>, rng: &mut Rng) -> Vec<Self::Gene> {
        while genes.len() < self.chromosome_length() {
            genes.insert(self.random_gene(rng));
        }
        genes.into_iter().collect()
    }
}

/// Cut two chromosomes at the same random position and swap their tails.
pub fn single_point_crossover<G: Clone>(
    first: &[G],
    second: &[G],
    rng: &mut Rng,
) -> (Vec<G>, Vec<G>) {
    let length = first.len().min(second.len());
    if length < 2 {
        return (first.to_vec(), second.to_vec());
    }
    let cut = rng.random_range(1..length);
    (
        [&first[..cut], &second[cut..]].concat(),
        [&second[..cut], &first[cut..]].concat(),
    )
}

/// Give each child, at each position, the gene of one parent or the other,
/// with even odds, and the other child the other gene. Past the length of
/// the shorter parent, each child keeps the genes of its own parent.
pub fn uniform_crossover<G: Clone>(first: &[G], second: &[G], rng: &mut Rng) -> (Vec<G>, Vec<G>) {
    let mut children = (first.to_vec(), second.to_vec());
    for position in 0..first.len().min(second.len()) {
        if rng.random::<bool>() {
            children.0[position] = second[position].clone();
            children.1[position] = first[position].clone();
        }
    }
    children
}

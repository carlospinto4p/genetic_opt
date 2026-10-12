use serde::{Serialize, Serializer};

use crate::Score;

/// A list or a set of genes, which encodes one candidate solution.
///
/// A set keeps its genes sorted and without duplicates, so two sets with
/// the same genes are equal whatever order they were built in.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct Chromosome<G> {
    genes: Vec<G>,
    is_gene_set: bool,
}

impl<G: Ord> Chromosome<G> {
    pub fn new(mut genes: Vec<G>, is_gene_set: bool) -> Self {
        if is_gene_set {
            genes.sort();
            genes.dedup();
        }
        Self { genes, is_gene_set }
    }
}

impl<G> Chromosome<G> {
    pub fn genes(&self) -> &[G] {
        &self.genes
    }

    pub fn is_gene_set(&self) -> bool {
        self.is_gene_set
    }
}

/// A chromosome with the score it got.
#[derive(Clone, Debug, PartialEq)]
pub struct Individual<G> {
    pub chromosome: Chromosome<G>,
    pub score: Score,
    /// Seconds the fitness function took, rounded to two decimals.
    pub score_time: f64,
    pub(crate) random_seed: u64,
}

/// The Python package's serialized `Chromosome`. Python gives each one a
/// seed and needs the key to load it; here it is the seed of the run.
#[derive(Serialize)]
struct EncodedChromosome<'a, G> {
    is_gene_set: bool,
    genes: &'a [G],
    score: &'a Score,
    score_time: f64,
    random_seed: u64,
}

impl<G: Serialize> Serialize for Individual<G> {
    fn serialize<S: Serializer>(&self, serializer: S) -> std::result::Result<S::Ok, S::Error> {
        EncodedChromosome {
            is_gene_set: self.chromosome.is_gene_set,
            genes: &self.chromosome.genes,
            score: &self.score,
            score_time: self.score_time,
            random_seed: self.random_seed,
        }
        .serialize(serializer)
    }
}

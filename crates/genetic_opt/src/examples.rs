//! Example problems.

use rand::RngExt;

use crate::{Error, Problem, Result, Rng, Score, single_point_crossover};

/// Given objects with a weight and a value each, and a bag with a
/// capacity, find the objects that give the highest total value without
/// their total weight going over the capacity.
///
/// A chromosome is a list with one gene per object: 1 when the object
/// goes into the bag, and 0 when it stays out.
pub struct Knapsack {
    weights: Vec<u32>,
    values: Vec<u32>,
    capacity: u32,
}

impl Knapsack {
    pub fn new(weights: Vec<u32>, values: Vec<u32>, capacity: u32) -> Result<Self> {
        if weights.len() != values.len() {
            return Err(Error::Validation(format!(
                "there are {} weights and {} values",
                weights.len(),
                values.len()
            )));
        }
        Ok(Self {
            weights,
            values,
            capacity,
        })
    }
}

impl Problem for Knapsack {
    type Gene = u8;
    type Solution = Vec<u8>;

    fn chromosome_length(&self) -> usize {
        self.weights.len()
    }

    fn minimize(&self) -> bool {
        false
    }

    fn gene_space_size(&self) -> usize {
        2
    }

    fn random_gene(&self, rng: &mut Rng) -> u8 {
        rng.random_range(0..=1)
    }

    fn fitness(&self, genes: &[u8]) -> Score {
        // Added as `u64`: a sum of `u32` values can pass `u32::MAX`.
        let value: u64 = self
            .decode(genes)
            .iter()
            .zip(&self.values)
            .map(|(gene, value)| u64::from(*gene) * u64::from(*value))
            .sum();
        Score::new(value as f64)
    }

    /// The bag the genes stand for: the objects are put in from the first
    /// one, and from the one that does not fit, no other goes in.
    fn decode(&self, genes: &[u8]) -> Vec<u8> {
        let capacity = u64::from(self.capacity);
        let mut weight: u64 = 0;
        let mut full = false;
        genes
            .iter()
            .zip(&self.weights)
            .map(|(gene, object_weight)| {
                let object_weight = u64::from(*object_weight);
                if *gene == 0 || full {
                    return 0;
                }
                if weight + object_weight > capacity {
                    full = true;
                    return 0;
                }
                weight += object_weight;
                1
            })
            .collect()
    }

    fn crossover(&self, first: &[u8], second: &[u8], rng: &mut Rng) -> (Vec<u8>, Vec<u8>) {
        single_point_crossover(first, second, rng)
    }
}

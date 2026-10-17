//! Example problems.

use std::collections::BTreeSet;

use rand::RngExt;
use serde_json::json;

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

/// Pick [`Numbers::PICKED`] different numbers under [`Numbers::NUMBERS`]
/// with the highest sum, or the lowest.
///
/// A chromosome is a set, and the score has a name and extra metrics, so
/// a saved run has the parts of the layout [`Knapsack`] leaves out.
pub struct Numbers {
    /// Whether the best pick is the one with the lowest sum.
    pub minimize: bool,
}

impl Numbers {
    /// The numbers are picked from 0 to one under this.
    pub const NUMBERS: u8 = 12;
    /// How many numbers a pick has.
    pub const PICKED: usize = 3;
}

impl Problem for Numbers {
    type Gene = u8;
    type Solution = Vec<u8>;

    fn chromosome_length(&self) -> usize {
        Self::PICKED
    }

    fn chromosome_as_set(&self) -> bool {
        true
    }

    fn minimize(&self) -> bool {
        self.minimize
    }

    fn gene_space_size(&self) -> usize {
        Self::NUMBERS.into()
    }

    fn random_gene(&self, rng: &mut Rng) -> u8 {
        rng.random_range(0..Self::NUMBERS)
    }

    fn fitness(&self, genes: &[u8]) -> Score {
        let sum: u32 = genes.iter().map(|gene| u32::from(*gene)).sum();
        Score {
            value: sum.into(),
            name: Some("sum".into()),
            extra_metrics: Some(json!({"largest": genes.iter().max()})),
        }
    }

    /// The numbers picked, lowest first.
    fn decode(&self, genes: &[u8]) -> Vec<u8> {
        genes.to_vec()
    }

    /// The first gene of one set with the others of the other.
    fn crossover(&self, first: &[u8], second: &[u8], rng: &mut Rng) -> (Vec<u8>, Vec<u8>) {
        let mix = |a: &[u8], b: &[u8]| -> BTreeSet<u8> {
            a[..1].iter().chain(&b[1..]).copied().collect()
        };
        (
            self.fill_set(mix(first, second), rng),
            self.fill_set(mix(second, first), rng),
        )
    }

    fn experiment_config(&self) -> Option<serde_json::Value> {
        Some(json!({"numbers": Self::NUMBERS, "picked": Self::PICKED}))
    }
}

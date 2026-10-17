//! Pick 3 different numbers under 12 with the highest sum, and print the
//! best pick found.
//!
//! A chromosome is a set, and the score has a name and extra metrics, so
//! a saved run has the parts of the layout the knapsack example leaves
//! out. `cargo run --example numbers -- [folder] [json|bson]` saves the
//! run in `folder`, in the layout the Python package reads.

use std::collections::BTreeSet;
use std::env::args;
use std::error::Error;

use rand::RngExt;
use serde_json::json;

use genetic_opt::{AlgorithmConfig, FitConfig, GeneticAlgorithm, Problem, Rng, SaveConfig, Score};

struct Numbers;

impl Problem for Numbers {
    type Gene = u8;
    type Solution = Vec<u8>;

    fn chromosome_length(&self) -> usize {
        3
    }

    fn chromosome_as_set(&self) -> bool {
        true
    }

    fn minimize(&self) -> bool {
        false
    }

    fn gene_space_size(&self) -> usize {
        12
    }

    fn random_gene(&self, rng: &mut Rng) -> u8 {
        rng.random_range(0..12)
    }

    fn fitness(&self, genes: &[u8]) -> Score {
        let sum: u32 = genes.iter().map(|gene| u32::from(*gene)).sum();
        Score {
            value: sum.into(),
            name: Some("sum".into()),
            extra_metrics: Some(json!({"largest": genes.iter().max()})),
        }
    }

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
}

fn main() -> Result<(), Box<dyn Error>> {
    let mut config = FitConfig::new(60, 30);
    // A population this small keeps fewer than 10 different sets, and
    // its mean score stops changing, before its best reaches 30.
    config.min_population_size = 0;
    config.stop_without_improvement = false;
    // The runs are saved in `folder/Numbers`, after the problem's type.
    let save = args().nth(1).map(|folder| SaveConfig {
        path: folder.into(),
        as_bson: args().nth(2).as_deref() != Some("json"),
    });
    let algorithm_config = AlgorithmConfig {
        save,
        ..AlgorithmConfig::default()
    };
    let result = GeneticAlgorithm::new(Numbers, algorithm_config).fit(&config)?;

    let best = &result.bests[0];
    println!("best sum: {}", best.score.value);
    println!("best numbers: {:?}", best.result);
    println!("generations: {}", result.metrics.len());
    if let Some(folder) = result.save_folder {
        println!("saved in: {}", folder.display());
    }
    Ok(())
}

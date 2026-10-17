//! Run the knapsack example and print the best bag found.
//!
//! `cargo run --example knapsack -- [folder] [json|bson]` saves the run
//! in `folder`, in the layout the Python package reads.

use std::env::args;
use std::error::Error;

use genetic_opt::examples::Knapsack;
use genetic_opt::{AlgorithmConfig, FitConfig, GeneticAlgorithm, SaveConfig};

fn main() -> Result<(), Box<dyn Error>> {
    let knapsack = Knapsack::new(
        vec![23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        vec![92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        165,
    )?;
    // The runs are saved in `folder/Knapsack`, after the problem's type.
    let save = args().nth(1).map(|folder| SaveConfig {
        path: folder.into(),
        as_bson: args().nth(2).as_deref() != Some("json"),
    });
    let config = AlgorithmConfig {
        save,
        ..AlgorithmConfig::default()
    };
    let result = GeneticAlgorithm::new(knapsack, config).fit(&FitConfig::new(100, 50))?;

    let best = &result.bests[0];
    println!("best value: {}", best.score.value);
    println!("best bag: {:?}", best.result);
    println!("generations: {}", result.metrics.len());
    if let Some(folder) = result.save_folder {
        println!("saved in: {}", folder.display());
    }
    Ok(())
}

//! Run the knapsack example and print the best bag found.
//!
//! `cargo run --example knapsack -- [folder] [json|bson]` saves the run
//! in `folder`, in the layout the Python package reads.

use std::env::args;
use std::error::Error;

use genetic_opt::problems::Knapsack;
use genetic_opt::{FitConfig, GeneticAlgorithm, SaveConfig, SaveFormat};

fn main() -> Result<(), Box<dyn Error>> {
    let knapsack = Knapsack::new(
        vec![23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        vec![92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        165,
    )?;
    let mut config = FitConfig::new(100, 50);
    if let Some(folder) = args().nth(1) {
        let format = match args().nth(2).as_deref() {
            Some("json") => SaveFormat::Json,
            _ => SaveFormat::Bson,
        };
        config.save = Some(SaveConfig {
            path: folder.into(),
            experiment_name: "Knapsack".into(),
            format,
        });
    }
    let result = GeneticAlgorithm::new(knapsack, config).fit()?;

    let best = &result.bests[0];
    println!("best value: {}", best.score.value);
    println!("best bag: {:?}", best.result);
    println!("generations: {}", result.metrics.len());
    if let Some(folder) = result.save_folder {
        println!("saved in: {}", folder.display());
    }
    Ok(())
}

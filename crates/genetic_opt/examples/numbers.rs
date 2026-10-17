//! Pick 3 different numbers under 12 with the highest sum, and print the
//! best pick found.
//!
//! A chromosome is a set, the score has a name and extra metrics, and the
//! run has an `extra_config`, so a saved run has the parts of the layout
//! the knapsack example leaves out. `cargo run --example numbers --
//! [folder] [json|bson]` saves the run in `folder`, in the layout the
//! Python package reads.

mod common;

use std::error::Error;

use genetic_opt::examples::Numbers;
use genetic_opt::{AlgorithmConfig, FitConfig, GeneticAlgorithm};
use serde_json::json;

fn main() -> Result<(), Box<dyn Error>> {
    let mut config = FitConfig::new(60, 30);
    // A population this small keeps fewer than 10 different sets, and
    // its mean score stops changing, before its best reaches 30.
    config.min_population_size = 0;
    config.stop_without_improvement = false;
    let problem = Numbers { minimize: false };
    // The runs are saved in `folder/Numbers`, after the problem's type.
    let algorithm_config = AlgorithmConfig {
        extra_config: Some(json!({"minimize": problem.minimize})),
        save: common::save_config()?,
        ..AlgorithmConfig::default()
    };
    let result = GeneticAlgorithm::new(problem, algorithm_config).fit(&config)?;
    common::print_run(&result, "sum", "numbers");
    Ok(())
}

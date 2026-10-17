//! Genetic algorithm optimizers.
//!
//! Describe an optimization problem by implementing [`Problem`], then run
//! it with [`GeneticAlgorithm`]. [`examples::Knapsack`] and
//! [`examples::Numbers`] are worked examples.
//!
//! A run can be saved to a folder, one file per generation, in the layout
//! of the Python package `genetic_opt`, whose
//! `fit_result_io.load_fit_result` reads it back.

mod algorithm;
mod chromosome;
mod error;
pub mod examples;
mod format;
mod metrics;
mod problem;
mod save;
mod score;

pub use algorithm::{AlgorithmConfig, FitConfig, FitParameters, FitResult, GeneticAlgorithm};
pub use chromosome::{Chromosome, Individual};
pub use error::{Error, Result};
pub use format::format_seconds;
pub use metrics::{Best, FitMetrics, FitnessFuncCalls, Metric, TotalFitTime};
pub use problem::{Problem, Rng, single_point_crossover};
pub use save::SaveConfig;
pub use score::Score;

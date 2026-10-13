//! Genetic algorithm optimizers.
//!
//! Describe an optimization problem by implementing [`Problem`], then run
//! it with [`GeneticAlgorithm`]. [`problems::Knapsack`] is a worked example.
//!
//! A run can be saved to a folder, one file per generation, in the layout
//! of the Python package `genetic_opt`, whose
//! `fit_result_io.load_fit_result` reads it back.

mod algorithm;
mod chromosome;
mod error;
mod format;
mod metrics;
mod problem;
pub mod problems;
mod save;
mod score;

pub use algorithm::{FitConfig, FitParameters, FitResult, GeneticAlgorithm};
pub use chromosome::{Chromosome, Individual};
pub use error::{Error, Result};
pub use format::format_seconds;
pub use metrics::{Best, FitMetrics, FitnessCalls, Metric, TotalFitTime};
pub use problem::{Problem, Rng, single_point_crossover};
pub use save::{SaveConfig, SaveFormat};
pub use score::Score;

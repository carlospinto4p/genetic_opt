use std::sync::Arc;

use serde::Serialize;

use crate::{Individual, Score};

/// A chromosome of a population, with what it stands for.
#[derive(Clone, Debug, Serialize)]
pub struct Best<G, S> {
    pub score: Score,
    pub encoded: Arc<Individual<G>>,
    pub result: S,
}

/// The measures of one generation.
#[derive(Clone, Debug, Serialize)]
pub struct Metric<G, S> {
    pub best: Best<G, S>,
    pub size: usize,
    pub mean: f64,
    pub median: f64,
    /// Variance of the scores over the whole population.
    pub var: f64,
    pub n_uniques: usize,
    pub percent_uniques: f64,
    /// Seconds it took to breed and score the generation.
    pub fitting_seconds: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct FitMetrics {
    pub fitness_func_calls: FitnessCalls,
    pub total_fit_time: TotalFitTime,
    pub genetic_opt_version: String,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct FitnessCalls {
    /// Chromosomes that needed a score.
    pub total: usize,
    /// Times the fitness function ran: once per different chromosome.
    pub processed: usize,
    /// `100 * processed / total`.
    pub percent_processed: f64,
    /// Scores taken from an earlier chromosome with the same genes.
    pub cached: usize,
    /// Number of different chromosomes the problem has. Infinite when it
    /// does not fit an `f64`, which a JSON file saves as `null`.
    pub space_points: f64,
    /// `100 * processed / space_points`.
    pub exploration_percentage: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct TotalFitTime {
    pub n_jobs: usize,
    pub raw: f64,
    pub formatted: String,
}

pub(crate) fn mean(values: &[f64]) -> f64 {
    values.iter().sum::<f64>() / values.len() as f64
}

/// The median of values sorted in either direction. Not a number when
/// there are none, as the mean and the variance are.
pub(crate) fn median(sorted: &[f64]) -> f64 {
    let middle = sorted.len() / 2;
    if sorted.is_empty() {
        f64::NAN
    } else if sorted.len().is_multiple_of(2) {
        (sorted[middle - 1] + sorted[middle]) / 2.0
    } else {
        sorted[middle]
    }
}

/// The variance of values whose mean is `mean`.
pub(crate) fn variance(values: &[f64], mean: f64) -> f64 {
    values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / values.len() as f64
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn statistics_of_a_population() {
        let values = [4.0, 1.0, 3.0, 2.0];
        assert_eq!(mean(&values), 2.5);
        assert_eq!(variance(&values, 2.5), 1.25);
    }

    #[test]
    fn median_of_values_sorted_in_either_direction() {
        assert_eq!(median(&[1.0, 2.0, 3.0, 5.0]), 2.5);
        assert_eq!(median(&[5.0, 3.0, 2.0, 1.0]), 2.5);
        assert_eq!(median(&[1.0, 3.0, 5.0]), 3.0);
        assert_eq!(median(&[5.0, 3.0, 1.0]), 3.0);
    }

    #[test]
    fn statistics_of_equal_values() {
        for values in [&[2.5, 2.5, 2.5][..], &[2.5]] {
            assert_eq!(mean(values), 2.5);
            assert_eq!(median(values), 2.5);
            assert_eq!(variance(values, 2.5), 0.0);
        }
    }

    #[test]
    fn statistics_of_no_values_are_not_numbers() {
        assert!(mean(&[]).is_nan());
        assert!(median(&[]).is_nan());
        assert!(variance(&[], 0.0).is_nan());
    }
}

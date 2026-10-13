use std::borrow::Borrow;
use std::collections::{HashMap, HashSet};
use std::hash::{Hash, Hasher};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::thread::available_parallelism;
use std::time::Instant;

use rand::SeedableRng;
use rand::seq::{IndexedRandom, SliceRandom};
use rayon::prelude::*;
use serde::Serialize;

use crate::format::{format_seconds, round2};
use crate::metrics::{mean, median, variance};
use crate::save::{
    BestsColumns, GenerationFile, create_run_folder, write_experiment_config, write_generation,
};
use crate::{
    Best, Chromosome, Error, FitMetrics, FitnessCalls, Individual, Metric, Problem, Result, Rng,
    SaveConfig, TotalFitTime,
};

/// Number of best chromosomes a [`FitResult`] reports.
const N_BESTS: usize = 5;

/// The parameters of a run.
#[derive(Clone, Debug)]
pub struct FitConfig {
    /// Generations to breed after the first population.
    pub n_generations: usize,
    pub population_size: usize,
    /// Proportion of the population that is crossed in each generation.
    pub crossovers_prop: f64,
    /// Proportion of the crossed chromosomes taken from the best ones.
    /// The others are picked at random from the rest.
    pub besties_prop: f64,
    /// Probability of each gene of a child to mutate.
    pub mutate_prob: f64,
    /// The run stops when a population has fewer different chromosomes.
    pub min_population_size: usize,
    /// The run stops when the mean score of a generation equals the one
    /// of the generation before.
    pub stop_without_improvement: bool,
    /// Threads that score chromosomes. `None` is every core but one.
    pub n_jobs: Option<usize>,
    pub random_seed: u64,
    /// Saved with every generation under the key `config`.
    pub extra_config: Option<serde_json::Value>,
    pub save: Option<SaveConfig>,
}

impl FitConfig {
    pub fn new(n_generations: usize, population_size: usize) -> Self {
        Self {
            n_generations,
            population_size,
            crossovers_prop: 0.7,
            besties_prop: 0.6,
            mutate_prob: 0.05,
            min_population_size: 10,
            stop_without_improvement: true,
            n_jobs: None,
            random_seed: 442,
            extra_config: None,
            save: None,
        }
    }
}

/// The parameters of a run as they are saved, with `n_jobs` resolved.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct FitParameters {
    pub n_generations: usize,
    pub population_size: usize,
    pub crossovers_prop: f64,
    pub besties_prop: f64,
    pub mutate_prob: f64,
    pub min_population_size: usize,
    pub random_seed: u64,
    pub n_jobs: usize,
}

/// What a run found. Every population it went through stays in
/// [`GeneticAlgorithm::history`].
#[derive(Clone, Debug)]
pub struct FitResult<G, S> {
    /// The best different chromosomes of the last population, best first.
    pub bests: Vec<Best<G, S>>,
    /// One per generation.
    pub metrics: Vec<Metric<G, S>>,
    pub fit_metrics: FitMetrics,
    pub fit_parameters: FitParameters,
    /// Folder the run was saved in, when it was.
    pub save_folder: Option<PathBuf>,
}

/// Number of different chromosomes a problem has: every list of `length`
/// genes, or every set of `length` different ones. A number too large
/// for an `f64` is infinite.
fn space_points(gene_space_size: usize, length: usize, as_set: bool) -> f64 {
    let genes = gene_space_size as f64;
    if !as_set {
        return genes.powi(length as i32);
    }
    // The binomial coefficient, one factor at a time.
    let picked = length.min(gene_space_size.saturating_sub(length));
    (1..=picked).fold(1.0, |count, i| {
        count * (genes - (picked - i) as f64) / i as f64
    })
}

type Population<G> = Vec<Arc<Individual<G>>>;
type Bests<P> = Vec<Best<<P as Problem>::Gene, <P as Problem>::Solution>>;

/// A scored chromosome, found among the others by its chromosome. The
/// set of them keeps each chromosome once, inside its `Individual`.
struct Scored<G>(Arc<Individual<G>>);

impl<G> Borrow<Chromosome<G>> for Scored<G> {
    fn borrow(&self) -> &Chromosome<G> {
        &self.0.chromosome
    }
}

impl<G: Hash> Hash for Scored<G> {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.0.chromosome.hash(state);
    }
}

impl<G: PartialEq> PartialEq for Scored<G> {
    fn eq(&self, other: &Self) -> bool {
        self.0.chromosome == other.0.chromosome
    }
}

impl<G: Eq> Eq for Scored<G> {}

/// Where the score of a chromosome asked for is.
enum Asked<G> {
    Scored(Arc<Individual<G>>),
    /// Position among the chromosomes to score.
    New(usize),
}

/// Runs a [`Problem`]:
///
/// - It starts from a random population and scores it.
/// - For each generation it picks parents, the best chromosomes plus a
///   random sample of the rest, crosses them in random pairs and mutates
///   the children.
/// - It joins the children to the population, sorts everything by score
///   and keeps as many as the population had.
///
/// A chromosome is scored once: an equal one met later takes its score.
pub struct GeneticAlgorithm<P: Problem> {
    problem: P,
    config: FitConfig,
    rng: Rng,
    population: Population<P::Gene>,
    history: Vec<Population<P::Gene>>,
    metrics: Vec<Metric<P::Gene, P::Solution>>,
    scores: HashSet<Scored<P::Gene>>,
    score_requests: usize,
}

impl<P: Problem> GeneticAlgorithm<P> {
    pub fn new(problem: P, config: FitConfig) -> Self {
        let rng = Rng::seed_from_u64(config.random_seed);
        Self {
            problem,
            config,
            rng,
            population: Vec::new(),
            history: Vec::new(),
            metrics: Vec::new(),
            scores: HashSet::new(),
            score_requests: 0,
        }
    }

    pub fn problem(&self) -> &P {
        &self.problem
    }

    /// The current population, best first.
    pub fn population(&self) -> &[Arc<Individual<P::Gene>>] {
        &self.population
    }

    /// Every population so far, each one best first.
    pub fn history(&self) -> &[Population<P::Gene>] {
        &self.history
    }

    /// The measures of every generation so far.
    pub fn metrics(&self) -> &[Metric<P::Gene, P::Solution>] {
        &self.metrics
    }

    /// Run the algorithm.
    pub fn fit(&mut self) -> Result<FitResult<P::Gene, P::Solution>>
    where
        P::Solution: Clone,
    {
        self.fit_with(|_| false)
    }

    /// Run the algorithm, calling `on_generation` after each generation is
    /// measured and before it is saved. The run stops after a generation
    /// for which it returns `true`.
    pub fn fit_with<F>(&mut self, mut on_generation: F) -> Result<FitResult<P::Gene, P::Solution>>
    where
        F: FnMut(&Self) -> bool,
        P::Solution: Clone,
    {
        let fit_parameters = self.fit_parameters()?;
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(fit_parameters.n_jobs)
            .build()
            .map_err(|e| Error::Validation(e.to_string()))?;
        let save_folder = match &self.config.save {
            Some(save) => Some(create_run_folder(save)?),
            None => None,
        };
        if let Some(folder) = &save_folder {
            write_experiment_config(folder, &fit_parameters, self.problem.experiment_config())?;
        }

        for generation in 0..=self.config.n_generations {
            let start = Instant::now();
            let candidates = if generation == 0 {
                self.first_chromosomes()?
            } else {
                self.breed()?
            };
            // The children go before the population they join, and the
            // sort keeps that order between equal scores.
            let mut population = self.score(candidates, &pool);
            population.append(&mut self.population);
            let minimize = self.problem.minimize();
            population.sort_by(|a, b| {
                let ordering = a.score.value.total_cmp(&b.score.value);
                if minimize {
                    ordering
                } else {
                    ordering.reverse()
                }
            });
            if let Some(previous) = self.history.last() {
                population.truncate(previous.len());
            }
            self.population = population;
            self.history.push(self.population.clone());
            self.metrics
                .push(self.measure(start.elapsed().as_secs_f64()));

            let stop = on_generation(self);
            if let (Some(folder), Some(save)) = (&save_folder, &self.config.save) {
                self.save_generation(folder, save, &fit_parameters)?;
            }
            let uniques = self.metrics[generation].n_uniques;
            if stop
                || uniques < self.config.min_population_size
                || (self.config.stop_without_improvement && self.mean_stalled())
            {
                break;
            }
        }
        let (bests, fit_metrics) = self.summary(&fit_parameters);
        Ok(FitResult {
            bests,
            metrics: self.metrics.clone(),
            fit_metrics,
            fit_parameters,
            save_folder,
        })
    }

    fn fit_parameters(&self) -> Result<FitParameters> {
        let config = &self.config;
        let cores = available_parallelism().map_or(1, |n| n.get());
        let n_jobs = config.n_jobs.unwrap_or((cores - 1).max(1));
        if n_jobs == 0 || n_jobs > cores {
            return Err(Error::Validation(format!(
                "n_jobs is {n_jobs}, and this machine has {cores} cores"
            )));
        }
        if config.population_size == 0 {
            return Err(Error::Validation("population_size is 0".into()));
        }
        for (name, value) in [
            ("crossovers_prop", config.crossovers_prop),
            ("besties_prop", config.besties_prop),
            ("mutate_prob", config.mutate_prob),
        ] {
            if !(0.0..=1.0).contains(&value) {
                return Err(Error::Validation(format!(
                    "{name} is {value}, and it must be between 0 and 1"
                )));
            }
        }
        if config.min_population_size > config.population_size {
            return Err(Error::Validation(format!(
                "min_population_size {} is greater than population_size {}",
                config.min_population_size, config.population_size
            )));
        }
        if self.problem.chromosome_as_set()
            && self.problem.gene_space_size() < self.problem.chromosome_length()
        {
            return Err(Error::Validation(format!(
                "a set of {} genes needs more than the {} genes there are",
                self.problem.chromosome_length(),
                self.problem.gene_space_size()
            )));
        }
        Ok(FitParameters {
            n_generations: config.n_generations,
            population_size: config.population_size,
            crossovers_prop: config.crossovers_prop,
            besties_prop: config.besties_prop,
            mutate_prob: config.mutate_prob,
            min_population_size: config.min_population_size,
            random_seed: config.random_seed,
            n_jobs,
        })
    }

    fn chromosome(&self, genes: Vec<P::Gene>) -> Result<Chromosome<P::Gene>> {
        let chromosome = Chromosome::new(genes, self.problem.chromosome_as_set());
        let length = self.problem.chromosome_length();
        if chromosome.genes().len() != length {
            return Err(Error::Validation(format!(
                "a chromosome has {} genes, and the problem asks for {length}",
                chromosome.genes().len()
            )));
        }
        Ok(chromosome)
    }

    fn first_chromosomes(&mut self) -> Result<Vec<Chromosome<P::Gene>>> {
        self.problem
            .init_population(self.config.population_size, &mut self.rng)
            .into_iter()
            .map(|genes| self.chromosome(genes))
            .collect()
    }

    /// Cross and mutate the parents of the next generation.
    fn breed(&mut self) -> Result<Vec<Chromosome<P::Gene>>> {
        let size = self.population.len();
        // The crossed chromosomes go in pairs.
        let n_crossovers = 2 * ((self.config.crossovers_prop * size as f64) as usize / 2);
        let n_besties = ((n_crossovers as f64 * self.config.besties_prop) as usize).min(size);
        let (besties, rest) = self.population.split_at(n_besties);
        let mut parents = besties.to_vec();
        for _ in n_besties..n_crossovers {
            let parent = rest.choose(&mut self.rng).ok_or_else(|| {
                Error::Validation(format!(
                    "{n_crossovers} parents were asked of a population \
                     with {n_besties} best chromosomes and no others"
                ))
            })?;
            parents.push(Arc::clone(parent));
        }
        parents.shuffle(&mut self.rng);

        let mut children = Vec::with_capacity(parents.len());
        for pair in parents.chunks_exact(2) {
            let first = pair[0].chromosome.genes();
            let second = pair[1].chromosome.genes();
            let (child_1, child_2) = self.problem.crossover(first, second, &mut self.rng);
            if !self
                .problem
                .crossover_invariant((first, second), (&child_1, &child_2))
            {
                return Err(Error::Invariant(
                    "a crossover broke the invariant of the problem".into(),
                ));
            }
            for child in [child_1, child_2] {
                let mutated = self
                    .problem
                    .mutate(&child, self.config.mutate_prob, &mut self.rng);
                if !self.problem.mutation_invariant(&child, &mutated) {
                    return Err(Error::Invariant(
                        "a mutation broke the invariant of the problem".into(),
                    ));
                }
                children.push(self.chromosome(mutated)?);
            }
        }
        Ok(children)
    }

    /// Score the chromosomes not seen before, in parallel and one of each,
    /// and pair every chromosome with its score.
    fn score(
        &mut self,
        chromosomes: Vec<Chromosome<P::Gene>>,
        pool: &rayon::ThreadPool,
    ) -> Population<P::Gene> {
        self.score_requests += chromosomes.len();
        let mut new: HashMap<Chromosome<P::Gene>, usize> = HashMap::new();
        let asked: Vec<Asked<P::Gene>> = chromosomes
            .into_iter()
            .map(|chromosome| match self.scores.get(&chromosome) {
                Some(scored) => Asked::Scored(Arc::clone(&scored.0)),
                None => {
                    let next = new.len();
                    Asked::New(*new.entry(chromosome).or_insert(next))
                }
            })
            .collect();
        let mut new: Vec<(Chromosome<P::Gene>, usize)> = new.into_iter().collect();
        new.sort_unstable_by_key(|(_, position)| *position);
        let problem = &self.problem;
        let random_seed = self.config.random_seed;
        let scored: Vec<Arc<Individual<P::Gene>>> = pool.install(|| {
            new.into_par_iter()
                .map(|(chromosome, _)| {
                    let start = Instant::now();
                    let score = problem.fitness(chromosome.genes());
                    Arc::new(Individual {
                        chromosome,
                        score,
                        score_time: round2(start.elapsed().as_secs_f64()),
                        random_seed,
                    })
                })
                .collect()
        });
        for individual in &scored {
            self.scores.insert(Scored(Arc::clone(individual)));
        }
        asked
            .into_iter()
            .map(|asked| match asked {
                Asked::Scored(individual) => individual,
                Asked::New(position) => Arc::clone(&scored[position]),
            })
            .collect()
    }

    fn best(&self, individual: &Arc<Individual<P::Gene>>) -> Best<P::Gene, P::Solution> {
        Best {
            score: individual.score.clone(),
            encoded: Arc::clone(individual),
            result: self.problem.decode(individual.chromosome.genes()),
        }
    }

    fn measure(&self, fitting_seconds: f64) -> Metric<P::Gene, P::Solution> {
        let values: Vec<f64> = self.population.iter().map(|i| i.score.value).collect();
        // Equal chromosomes share one `Individual`, so its address tells
        // the different ones apart.
        let n_uniques = self
            .population
            .iter()
            .map(Arc::as_ptr)
            .collect::<HashSet<_>>()
            .len();
        Metric {
            best: self.best(&self.population[0]),
            size: values.len(),
            mean: mean(&values),
            median: median(&values),
            var: variance(&values),
            n_uniques,
            percent_uniques: 100.0 * n_uniques as f64 / values.len() as f64,
            fitting_seconds: round2(fitting_seconds),
        }
    }

    fn mean_stalled(&self) -> bool {
        match self.metrics.as_slice() {
            [.., previous, last] => last.mean == previous.mean,
            _ => false,
        }
    }

    /// The best different chromosomes of the population and the counts
    /// of the run so far.
    fn summary(&self, fit_parameters: &FitParameters) -> (Bests<P>, FitMetrics) {
        let mut seen = HashSet::new();
        let bests = self
            .population
            .iter()
            .filter(|i| seen.insert(Arc::as_ptr(i)))
            .take(N_BESTS)
            .map(|i| self.best(i))
            .collect();
        let processed = self.scores.len();
        let space_points = space_points(
            self.problem.gene_space_size(),
            self.problem.chromosome_length(),
            self.problem.chromosome_as_set(),
        );
        let raw = round2(self.metrics.iter().map(|m| m.fitting_seconds).sum());
        let fit_metrics = FitMetrics {
            fitness_func_calls: FitnessCalls {
                total: self.score_requests,
                processed,
                percent_processed: round2(100.0 * processed as f64 / self.score_requests as f64),
                cached: self.score_requests - processed,
                space_points,
                exploration_percentage: round2(100.0 * processed as f64 / space_points),
            },
            total_fit_time: TotalFitTime {
                n_jobs: fit_parameters.n_jobs,
                raw,
                formatted: format_seconds(raw),
            },
            genetic_opt_version: env!("CARGO_PKG_VERSION").to_string(),
        };
        (bests, fit_metrics)
    }

    fn save_generation(
        &self,
        folder: &Path,
        save: &SaveConfig,
        fit_parameters: &FitParameters,
    ) -> Result<()> {
        let (bests, fit_metrics) = self.summary(fit_parameters);
        let generation = GenerationFile {
            bests: BestsColumns {
                scores: bests.iter().map(|b| &b.score).collect(),
                result: bests.iter().map(|b| &b.result).collect(),
                encoded: bests.iter().map(|b| &*b.encoded).collect(),
            },
            last_population: self
                .population
                .iter()
                .map(|i| (self.problem.decode(i.chromosome.genes()), &i.score))
                .collect(),
            fit_metrics: &fit_metrics,
            metrics: &self.metrics[self.metrics.len() - 1..],
            fit_parameters,
            config: self.config.extra_config.as_ref(),
            population_idx: self.history.len(),
            population: self.population.iter().map(|i| (&i.score, &**i)).collect(),
        };
        write_generation(folder, save.format, &generation)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn space_points_counts_lists_and_sets() {
        assert_eq!(space_points(2, 10, false), 1024.0);
        assert_eq!(space_points(12, 3, true), 220.0);
        assert_eq!(space_points(12, 12, true), 1.0);
        assert_eq!(space_points(2, 2000, false), f64::INFINITY);
        // What a JSON file of a run holds for an infinite count.
        assert!(serde_json::to_value(f64::INFINITY).unwrap().is_null());
    }
}

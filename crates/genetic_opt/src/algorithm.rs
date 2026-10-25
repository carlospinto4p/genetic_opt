use std::borrow::Borrow;
use std::collections::{HashMap, HashSet};
use std::hash::{Hash, Hasher};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::thread::available_parallelism;
use std::time::Instant;

use log::info;
use rand::seq::{IndexedRandom, SliceRandom};
use rand::{RngExt, SeedableRng};
use rayon::prelude::*;
use serde::Serialize;

use crate::format::{format_seconds, round2};
use crate::metrics::{mean, median, variance};
use crate::save::{
    BestsColumns, GenerationFile, create_run_folder, write_experiment_config, write_generation,
};
use crate::{
    Best, Chromosome, Error, FitMetrics, FitnessFuncCalls, Individual, Metric, Problem, Result,
    Rng, SaveConfig, Score, TotalFitTime,
};

/// Number of best chromosomes a [`FitResult`] reports.
const N_BESTS: usize = 5;

/// The settings of a [`GeneticAlgorithm`], which every run of it keeps.
#[derive(Clone, Debug)]
pub struct AlgorithmConfig {
    /// Names the folder of the runs inside the save path, so it must be a
    /// path inside it: not an absolute one, and without `..`. `None` is
    /// the name of the problem's type, without its module path.
    pub experiment_name: Option<String>,
    pub random_seed: u64,
    /// Saved with every generation under the key `config`.
    pub extra_config: Option<serde_json::Value>,
    /// Nothing is saved without it.
    pub save: Option<SaveConfig>,
}

impl Default for AlgorithmConfig {
    fn default() -> Self {
        Self {
            experiment_name: None,
            random_seed: 442,
            extra_config: None,
            save: None,
        }
    }
}

/// The parameters of a run, given to [`GeneticAlgorithm::fit`].
#[derive(Clone, Debug)]
pub struct FitConfig {
    /// Generations to breed after the first population.
    pub n_generations: usize,
    pub population_size: usize,
    /// Proportion of the population that is crossed in each generation.
    pub crossovers_prop: f64,
    /// Proportion of the crossed chromosomes taken from the best ones.
    /// The others are picked from the rest, as `selection` says.
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
    /// The run stops after the first generation that ends this many
    /// seconds or more after the run started. `None` is no limit. It is
    /// not saved with the run.
    pub max_seconds: Option<f64>,
    /// The run stops when this many generations in a row have bred no
    /// better best score than the generations before them. `None` is no
    /// limit. It is not saved with the run.
    pub max_stale_generations: Option<usize>,
    /// How the crossed chromosomes that are not among the best ones are
    /// picked from the rest.
    pub selection: Selection,
    /// Chromosomes drawn for each tournament, 1 or more. With 1, a
    /// tournament is a random pick.
    pub tournament_size: usize,
}

/// How the parents that are not among the best chromosomes are picked.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Selection {
    /// Each one at random from the rest.
    #[default]
    Random,
    /// Each one is the best of [`FitConfig::tournament_size`] chromosomes
    /// drawn at random from the rest.
    Tournament,
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
            max_seconds: None,
            max_stale_generations: None,
            selection: Selection::Random,
            tournament_size: 3,
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
    pub selection: Selection,
    pub tournament_size: usize,
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
    /// Why the run ended. It is not saved with the run.
    pub stop_reason: StopReason,
    /// Folder the run was saved in, when it was.
    pub save_folder: Option<PathBuf>,
}

/// Why a run ended: the first [`FitConfig`] condition a generation met,
/// in the order they are listed, or none of them.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum StopReason {
    /// It bred every generation asked.
    Completed,
    /// [`FitConfig::min_population_size`].
    MinPopulation,
    /// [`FitConfig::stop_without_improvement`].
    NoImprovement,
    /// [`FitConfig::max_stale_generations`].
    StaleGenerations,
    /// [`FitConfig::max_seconds`].
    MaxSeconds,
    /// `on_generation` returned `true`, in [`GeneticAlgorithm::fit_with`].
    OnGeneration,
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

/// The error of a score `value` that is not finite, given by `source` to
/// the chromosome of `genes`. `Gene` is not `Debug`, but it is
/// `Serialize`.
fn not_finite_score_error<G: Serialize>(source: &str, value: f64, genes: &[G]) -> Error {
    let genes = serde_json::to_string(genes).unwrap_or_default();
    Error::Validation(format!(
        "{source} a score that is not finite, {value}, to the chromosome {genes}"
    ))
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
///   sample of the rest, at random or by tournament, crosses them in
///   random pairs and mutates the children.
/// - It joins the children to the population, sorts everything by score
///   and keeps as many as the population had.
///
/// A chromosome is scored once: an equal one met later takes its score.
pub struct GeneticAlgorithm<P: Problem> {
    problem: P,
    config: AlgorithmConfig,
    experiment_name: String,
    rng: Rng,
    population: Population<P::Gene>,
    history: Vec<Population<P::Gene>>,
    metrics: Vec<Metric<P::Gene, P::Solution>>,
    scores: HashSet<Scored<P::Gene>>,
    score_requests: usize,
    /// Chromosomes scored by the current run.
    scored: usize,
}

impl<P: Problem> GeneticAlgorithm<P> {
    pub fn new(problem: P, config: AlgorithmConfig) -> Self {
        let rng = Rng::seed_from_u64(config.random_seed);
        let experiment_name = config.experiment_name.clone().unwrap_or_else(|| {
            let name = std::any::type_name::<P>();
            // `type_name` gives `module::Name<Parameters>`.
            let name = name.split('<').next().unwrap_or(name);
            name.rsplit("::").next().unwrap_or(name).to_string()
        });
        Self {
            problem,
            config,
            experiment_name,
            rng,
            population: Vec::new(),
            history: Vec::new(),
            metrics: Vec::new(),
            scores: HashSet::new(),
            score_requests: 0,
            scored: 0,
        }
    }

    pub fn problem(&self) -> &P {
        &self.problem
    }

    /// The name of the folder of the runs inside the save path.
    pub fn experiment_name(&self) -> &str {
        &self.experiment_name
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

    /// Run the algorithm. Each call is a new run: it starts from the seed
    /// again and keeps only the scores of the run before, so a chromosome
    /// met again is not scored again.
    pub fn fit(&mut self, config: &FitConfig) -> Result<FitResult<P::Gene, P::Solution>>
    where
        P::Solution: Clone,
    {
        self.fit_with(config, |_| false)
    }

    /// Run the algorithm, calling `on_generation` after each generation is
    /// measured and before it is saved. The run stops after a generation
    /// for which it returns `true`.
    pub fn fit_with<F>(
        &mut self,
        config: &FitConfig,
        on_generation: F,
    ) -> Result<FitResult<P::Gene, P::Solution>>
    where
        F: FnMut(&Self) -> bool,
        P::Solution: Clone,
    {
        self.fit_from(config, None, on_generation)
    }

    /// Run the algorithm as [`Self::fit_with`] does, from
    /// `first_population` when it is given: the genes of each chromosome
    /// of the first population with its score, instead of the ones of
    /// [`Problem::init_population`]. For example the last population of
    /// an earlier run, to go on with it. The scores are not computed
    /// again, and the time each one took is taken as 0. As with
    /// `init_population`, its length is the size of every population.
    pub fn fit_from<F>(
        &mut self,
        config: &FitConfig,
        first_population: Option<Vec<(Vec<P::Gene>, Score)>>,
        mut on_generation: F,
    ) -> Result<FitResult<P::Gene, P::Solution>>
    where
        F: FnMut(&Self) -> bool,
        P::Solution: Clone,
    {
        let fit_parameters = self.fit_parameters(config)?;
        let mut first_chromosomes = match first_population {
            Some(population) => Some(self.given_chromosomes(population)?),
            None => None,
        };
        // What an earlier run left would be mixed into this one.
        self.rng = Rng::seed_from_u64(self.config.random_seed);
        self.population.clear();
        self.history.clear();
        self.metrics.clear();
        // The scores stay: scoring is the costly part of a run.
        self.score_requests = 0;
        self.scored = 0;
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(fit_parameters.n_jobs)
            .build()?;
        let save_folder = match &self.config.save {
            Some(save) => Some(create_run_folder(save, &self.experiment_name)?),
            None => None,
        };
        if let Some(folder) = &save_folder {
            write_experiment_config(folder, &fit_parameters, self.problem.experiment_config())?;
        }
        info!(
            "starting a run of {}: {fit_parameters:?}",
            self.experiment_name
        );

        let run_start = Instant::now();
        let mut stop_reason = StopReason::Completed;
        for generation in 0..=config.n_generations {
            let start = Instant::now();
            let candidates = if generation == 0 {
                match first_chromosomes.take() {
                    Some(chromosomes) => chromosomes,
                    None => self.first_chromosomes(config.population_size)?,
                }
            } else {
                self.breed(config)?
            };
            // The children go before the population they join, and the
            // sort keeps that order between equal scores.
            let mut population = self.score(candidates, &pool)?;
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
            let metric = &self.metrics[generation];
            info!(
                "generation {generation}: best score {}, mean {}, median {}, \
                 {} different chromosomes, took {}",
                metric.best.score.value,
                metric.mean,
                metric.median,
                metric.n_uniques,
                format_seconds(metric.fitting_seconds)
            );

            let stop = on_generation(self);
            if let (Some(folder), Some(save)) = (&save_folder, &self.config.save) {
                self.save_generation(folder, save, &fit_parameters)?;
            }
            stop_reason = self.stop_reason(config, run_start, stop);
            if stop_reason != StopReason::Completed {
                break;
            }
        }
        let (bests, fit_metrics) = self.summary(&fit_parameters);
        Ok(FitResult {
            bests,
            metrics: self.metrics.clone(),
            fit_metrics,
            fit_parameters,
            stop_reason,
            save_folder,
        })
    }

    /// Whether the run stops after the generation just measured, checked
    /// in the order the Python package checks it. It logs why when it
    /// does.
    fn stop_reason(&self, config: &FitConfig, run_start: Instant, stop: bool) -> StopReason {
        let (reason, text) =
            if self.metrics[self.metrics.len() - 1].n_uniques < config.min_population_size {
                (
                    StopReason::MinPopulation,
                    format!(
                        "fewer than {} different chromosomes",
                        config.min_population_size
                    ),
                )
            } else if config.stop_without_improvement && self.mean_stalled() {
                (
                    StopReason::NoImprovement,
                    "the mean score did not change".to_string(),
                )
            } else if let Some(stale) = config.max_stale_generations
                && self.stale_generations() >= stale
            {
                (
                    StopReason::StaleGenerations,
                    format!("no better best score for {stale} generations"),
                )
            } else if let Some(seconds) = config.max_seconds
                && run_start.elapsed().as_secs_f64() >= seconds
            {
                (StopReason::MaxSeconds, format!("{seconds} seconds reached"))
            } else if stop {
                (
                    StopReason::OnGeneration,
                    "on_generation asked to stop".to_string(),
                )
            } else {
                return StopReason::Completed;
            };
        info!(
            "the run stopped after generation {}: {text}",
            self.metrics.len() - 1
        );
        reason
    }

    fn fit_parameters(&self, config: &FitConfig) -> Result<FitParameters> {
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
        if let Some(seconds) = config.max_seconds
            && (seconds.is_nan() || seconds < 0.0)
        {
            return Err(Error::Validation(format!(
                "max_seconds is {seconds}, and it must not be negative"
            )));
        }
        if config.tournament_size == 0 {
            return Err(Error::Validation(
                "tournament_size is 0, and it must be 1 or more".into(),
            ));
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
            random_seed: self.config.random_seed,
            n_jobs,
            selection: config.selection,
            tournament_size: config.tournament_size,
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

    fn first_chromosomes(&mut self, population_size: usize) -> Result<Vec<Chromosome<P::Gene>>> {
        let first = self.problem.init_population(population_size, &mut self.rng);
        if first.is_empty() {
            return Err(Error::Validation(
                "init_population returned no chromosomes".into(),
            ));
        }
        first
            .into_iter()
            .map(|genes| self.chromosome(genes))
            .collect()
    }

    /// The chromosomes of a first population given to [`Self::fit_from`].
    /// Their scores are kept, so they are not scored again.
    fn given_chromosomes(
        &mut self,
        population: Vec<(Vec<P::Gene>, Score)>,
    ) -> Result<Vec<Chromosome<P::Gene>>> {
        if population.is_empty() {
            return Err(Error::Validation(
                "the first population has no chromosomes".into(),
            ));
        }
        let mut individuals = Vec::with_capacity(population.len());
        for (genes, score) in population {
            let chromosome = self.chromosome(genes)?;
            if !score.value.is_finite() {
                return Err(not_finite_score_error(
                    "the first population gives",
                    score.value,
                    chromosome.genes(),
                ));
            }
            individuals.push(Individual {
                chromosome,
                score,
                score_time: 0.0,
                random_seed: self.config.random_seed,
            });
        }
        let chromosomes = individuals.iter().map(|i| i.chromosome.clone()).collect();
        // Once every chromosome is checked, so a refused population leaves
        // no score behind. A score kept already stays.
        for individual in individuals {
            self.scores.insert(Scored(Arc::new(individual)));
        }
        Ok(chromosomes)
    }

    /// Cross and mutate the parents of the next generation.
    fn breed(&mut self, config: &FitConfig) -> Result<Vec<Chromosome<P::Gene>>> {
        let size = self.population.len();
        // The crossed chromosomes go in pairs.
        let n_crossovers = 2 * ((config.crossovers_prop * size as f64) as usize / 2);
        let n_besties = ((n_crossovers as f64 * config.besties_prop) as usize).min(size);
        let (besties, rest) = self.population.split_at(n_besties);
        let mut parents = besties.to_vec();
        // Both proportions are at most 1, so `n_besties <= n_crossovers <=
        // size`. The rest is empty only when `n_besties` is the whole
        // population, and then no parent is drawn from it.
        for _ in n_besties..n_crossovers {
            let parent = match config.selection {
                Selection::Random => rest.choose(&mut self.rng),
                // The rest is sorted best first, so the lowest position
                // drawn wins the tournament.
                Selection::Tournament => (0..config.tournament_size)
                    .map(|_| self.rng.random_range(0..rest.len()))
                    .min()
                    .map(|position| &rest[position]),
            }
            .expect("the rest is not empty when parents are drawn from it");
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
                    .mutate(&child, config.mutate_prob, &mut self.rng);
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
    /// and pair every chromosome with its score. A score that is not
    /// finite is refused before it is kept, so a later run does not take it either.
    fn score(
        &mut self,
        chromosomes: Vec<Chromosome<P::Gene>>,
        pool: &rayon::ThreadPool,
    ) -> Result<Population<P::Gene>> {
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
        let mut by_position: Vec<Option<Chromosome<P::Gene>>> =
            (0..new.len()).map(|_| None).collect();
        for (chromosome, position) in new {
            by_position[position] = Some(chromosome);
        }
        let problem = &self.problem;
        let random_seed = self.config.random_seed;
        let scored: Vec<Arc<Individual<P::Gene>>> = pool.install(|| {
            by_position
                .into_par_iter()
                .flatten()
                .map(|chromosome| {
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
        if let Some(individual) = scored.iter().find(|i| !i.score.value.is_finite()) {
            return Err(not_finite_score_error(
                "the fitness function gave",
                individual.score.value,
                individual.chromosome.genes(),
            ));
        }
        self.scored += scored.len();
        for individual in &scored {
            self.scores.insert(Scored(Arc::clone(individual)));
        }
        Ok(asked
            .into_iter()
            .map(|asked| match asked {
                Asked::Scored(individual) => individual,
                Asked::New(position) => Arc::clone(&scored[position]),
            })
            .collect())
    }

    fn best(&self, individual: &Arc<Individual<P::Gene>>) -> Best<P::Gene, P::Solution> {
        Best {
            score: individual.score.clone(),
            encoded: Arc::clone(individual),
            result: self.problem.decode(individual.chromosome.genes()),
        }
    }

    fn measure(&self, fitting_seconds: f64) -> Metric<P::Gene, P::Solution> {
        // Sorted, as the population is.
        let values: Vec<f64> = self.population.iter().map(|i| i.score.value).collect();
        let mean = mean(&values);
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
            mean,
            median: median(&values),
            var: variance(&values, mean),
            n_uniques,
            percent_uniques: 100.0 * n_uniques as f64 / values.len() as f64,
            fitting_seconds: round2(fitting_seconds),
        }
    }

    /// The generations in a row, up to the last one, whose best score is
    /// no better than the best one of the generations before them: 0 when
    /// the last generation found a better one, or is the first one.
    pub fn stale_generations(&self) -> usize {
        let minimize = self.problem.minimize();
        let mut stale = 0;
        let mut best: Option<f64> = None;
        for metric in &self.metrics {
            let value = metric.best.score.value;
            let better = match best {
                None => true,
                Some(best) if minimize => value < best,
                Some(best) => value > best,
            };
            if better {
                stale = 0;
                best = Some(value);
            } else {
                stale += 1;
            }
        }
        stale
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
        let processed = self.scored;
        let space_points = space_points(
            self.problem.gene_space_size(),
            self.problem.chromosome_length(),
            self.problem.chromosome_as_set(),
        );
        let raw = round2(self.metrics.iter().map(|m| m.fitting_seconds).sum());
        let fit_metrics = FitMetrics {
            fitness_func_calls: FitnessFuncCalls {
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
            fit_metrics: &fit_metrics,
            metrics: &self.metrics[self.metrics.len() - 1..],
            fit_parameters,
            config: self.config.extra_config.as_ref(),
            population_idx: self.history.len(),
            population: self.population.iter().map(|i| (&i.score, &**i)).collect(),
        };
        write_generation(folder, save.as_bson, &generation)
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
    }
}

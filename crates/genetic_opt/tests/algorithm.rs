use std::cell::RefCell;
use std::collections::{BTreeSet, HashSet};
use std::fs::{File, read_dir};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::thread::{available_parallelism, sleep};
use std::time::Duration;

use log::{LevelFilter, Log, Metadata, Record};
use rand::SeedableRng;

use genetic_opt::examples::{Knapsack, Numbers};
use genetic_opt::{
    AlgorithmConfig, Chromosome, Error, FitConfig, GeneticAlgorithm, Problem, Rng, SaveConfig,
    Score, Selection, StopReason, single_point_crossover, uniform_crossover,
};

/// Two threads, or the one that a machine with one core allows.
fn two_jobs() -> usize {
    available_parallelism().map_or(1, |n| n.get()).min(2)
}

fn knapsack() -> Knapsack {
    Knapsack::new(
        vec![23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        vec![92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        165,
    )
    .unwrap()
}

const NUMBERS: u8 = Numbers::NUMBERS;
const PICKED: usize = Numbers::PICKED;

fn numbers(minimize: bool) -> Numbers {
    Numbers { minimize }
}

/// `problem`, counting the calls to its fitness function, which takes
/// at least `fitness_delay`, and with the mutation and crossover
/// invariants holding as asked.
struct Watched<P> {
    problem: P,
    fitness_calls: AtomicUsize,
    fitness_delay: Duration,
    keep_mutations: bool,
    keep_crossovers: bool,
}

fn watched<P>(problem: P, keep_mutations: bool, keep_crossovers: bool) -> Watched<P> {
    Watched {
        problem,
        fitness_calls: AtomicUsize::new(0),
        fitness_delay: Duration::ZERO,
        keep_mutations,
        keep_crossovers,
    }
}

impl<P: Problem> Problem for Watched<P> {
    type Gene = P::Gene;
    type Solution = P::Solution;

    fn chromosome_length(&self) -> usize {
        self.problem.chromosome_length()
    }

    fn chromosome_as_set(&self) -> bool {
        self.problem.chromosome_as_set()
    }

    fn minimize(&self) -> bool {
        self.problem.minimize()
    }

    fn gene_space_size(&self) -> usize {
        self.problem.gene_space_size()
    }

    fn random_gene(&self, rng: &mut Rng) -> P::Gene {
        self.problem.random_gene(rng)
    }

    fn fitness(&self, genes: &[P::Gene]) -> Score {
        self.fitness_calls.fetch_add(1, Ordering::Relaxed);
        sleep(self.fitness_delay);
        self.problem.fitness(genes)
    }

    fn decode(&self, genes: &[P::Gene]) -> P::Solution {
        self.problem.decode(genes)
    }

    fn crossover(
        &self,
        first: &[P::Gene],
        second: &[P::Gene],
        rng: &mut Rng,
    ) -> (Vec<P::Gene>, Vec<P::Gene>) {
        self.problem.crossover(first, second, rng)
    }

    fn mutation_invariant(&self, _before: &[P::Gene], _after: &[P::Gene]) -> bool {
        self.keep_mutations
    }

    fn crossover_invariant(
        &self,
        _parents: (&[P::Gene], &[P::Gene]),
        _children: (&[P::Gene], &[P::Gene]),
    ) -> bool {
        self.keep_crossovers
    }
}

/// 60 generations of 30 sets. Neither of the early stops is on: such a
/// population keeps fewer than 10 different sets, and its mean score
/// stops changing, before its best reaches the optimum.
fn numbers_config() -> FitConfig {
    let mut config = FitConfig::new(60, 30);
    config.min_population_size = 0;
    config.stop_without_improvement = false;
    config
}

/// A chromosome of 3 genes out of `gene_space_size`, whose first
/// population is `first_population`, whatever size is asked.
struct FirstGenes {
    first_population: Vec<Vec<u8>>,
    as_set: bool,
    gene_space_size: usize,
}

impl Problem for FirstGenes {
    type Gene = u8;
    type Solution = u32;

    fn chromosome_length(&self) -> usize {
        3
    }

    fn chromosome_as_set(&self) -> bool {
        self.as_set
    }

    fn minimize(&self) -> bool {
        false
    }

    fn gene_space_size(&self) -> usize {
        self.gene_space_size
    }

    fn random_gene(&self, rng: &mut Rng) -> u8 {
        rand::RngExt::random_range(rng, 0..12)
    }

    fn fitness(&self, genes: &[u8]) -> Score {
        Score::new(self.decode(genes).into())
    }

    fn decode(&self, genes: &[u8]) -> u32 {
        genes.iter().map(|gene| u32::from(*gene)).sum()
    }

    fn crossover(&self, first: &[u8], second: &[u8], _rng: &mut Rng) -> (Vec<u8>, Vec<u8>) {
        (first.to_vec(), second.to_vec())
    }

    fn init_population(&self, _population_size: usize, _rng: &mut Rng) -> Vec<Vec<u8>> {
        self.first_population.clone()
    }
}

/// The algorithm of `problem` with the default settings.
fn algorithm<P: Problem>(problem: P) -> GeneticAlgorithm<P> {
    GeneticAlgorithm::new(problem, AlgorithmConfig::default())
}

/// The message of the error a run of `algorithm` stops with.
fn fit_error<P: Problem>(mut algorithm: GeneticAlgorithm<P>, config: FitConfig) -> Error
where
    P::Solution: Clone,
{
    match algorithm.fit(&config) {
        Ok(_) => panic!("the run did not stop with an error"),
        Err(error) => error,
    }
}

#[test]
fn mutation_with_probability_0_keeps_every_gene() {
    let mut rng = Rng::seed_from_u64(1);
    assert_eq!(ZeroStart.mutate(&[5; 10], 0.0, &mut rng), [5; 10]);
    assert_eq!(
        numbers(false).mutate(&[20, 21, 22], 0.0, &mut rng),
        [20, 21, 22]
    );
}

#[test]
fn mutation_with_probability_1_replaces_every_gene() {
    let mut rng = Rng::seed_from_u64(1);
    let list = ZeroStart.mutate(&[5; 10], 1.0, &mut rng);
    assert_eq!(list.len(), 10);
    assert!(list.iter().all(|gene| *gene < 2));
    // Equal new genes are drawn again until the set has 3.
    let set = numbers(false).mutate(&[20, 21, 22], 1.0, &mut rng);
    assert_eq!(set.len(), PICKED);
    assert!(set.windows(2).all(|pair| pair[0] < pair[1]));
    assert!(set.iter().all(|gene| *gene < NUMBERS));
}

/// Counts the ones of a chromosome. Its first population has none.
struct ZeroStart;

impl Problem for ZeroStart {
    type Gene = u8;
    type Solution = Vec<u8>;

    fn chromosome_length(&self) -> usize {
        10
    }

    fn minimize(&self) -> bool {
        false
    }

    fn gene_space_size(&self) -> usize {
        2
    }

    fn random_gene(&self, rng: &mut Rng) -> u8 {
        rand::RngExt::random_range(rng, 0..2)
    }

    fn fitness(&self, genes: &[u8]) -> Score {
        Score::new(genes.iter().map(|gene| f64::from(*gene)).sum())
    }

    fn decode(&self, genes: &[u8]) -> Vec<u8> {
        genes.to_vec()
    }

    fn crossover(&self, first: &[u8], second: &[u8], rng: &mut Rng) -> (Vec<u8>, Vec<u8>) {
        single_point_crossover(first, second, rng)
    }

    fn init_population(&self, population_size: usize, _rng: &mut Rng) -> Vec<Vec<u8>> {
        vec![vec![0; 10]; population_size]
    }
}

/// Run `ZeroStart` for up to 6 generations without mutations, so every
/// chromosome is all zeros: 1 different one.
fn fit_zeros(min_population_size: usize, stop_without_improvement: bool) -> Vec<usize> {
    let mut config = FitConfig::new(5, 20);
    config.mutate_prob = 0.0;
    config.min_population_size = min_population_size;
    config.stop_without_improvement = stop_without_improvement;
    let result = algorithm(ZeroStart).fit(&config).unwrap();
    result
        .metrics
        .iter()
        .map(|metric| metric.n_uniques)
        .collect()
}

#[test]
fn the_run_stops_below_min_population_size() {
    assert_eq!(fit_zeros(2, false), [1]);
    assert_eq!(fit_zeros(1, false), [1; 6]);
    assert_eq!(fit_zeros(0, false), [1; 6]);
}

#[test]
fn the_run_stops_when_the_mean_score_does_not_change() {
    assert_eq!(fit_zeros(0, true), [1; 2]);
}

/// The number of generations of a run of `ZeroStart` with no other stop
/// than `max_seconds`.
fn generations_within(max_seconds: f64) -> usize {
    let mut config = FitConfig::new(5, 20);
    config.min_population_size = 0;
    config.stop_without_improvement = false;
    config.max_seconds = Some(max_seconds);
    algorithm(ZeroStart).fit(&config).unwrap().metrics.len()
}

/// A run of `ZeroStart` without mutations, so its best score never gets
/// better, with no other stop than `max_stale_generations`.
fn stale_run(max_stale_generations: usize) -> GeneticAlgorithm<ZeroStart> {
    let mut config = FitConfig::new(5, 20);
    config.mutate_prob = 0.0;
    config.min_population_size = 0;
    config.stop_without_improvement = false;
    config.max_stale_generations = Some(max_stale_generations);
    let mut algorithm = algorithm(ZeroStart);
    algorithm.fit(&config).unwrap();
    algorithm
}

#[test]
fn the_run_stops_after_max_stale_generations() {
    for (max_stale_generations, generations) in [(2, 3), (0, 1)] {
        let algorithm = stale_run(max_stale_generations);
        assert_eq!(algorithm.metrics().len(), generations);
        assert_eq!(algorithm.stale_generations(), generations - 1);
    }
}

#[test]
fn stale_generations_count_from_the_last_better_best_score() {
    for minimize in [false, true] {
        let mut algorithm = algorithm(numbers(minimize));
        algorithm.fit(&numbers_config()).unwrap();
        let bests: Vec<f64> = algorithm
            .metrics()
            .iter()
            .map(|metric| metric.best.score.value)
            .collect();
        // The best score never gets worse, so the stale ones are the
        // last ones equal to the last.
        let last = bests[bests.len() - 1];
        let stale = bests.iter().rev().take_while(|b| **b == last).count() - 1;
        assert!(bests.len() - 1 > stale, "the best never got better");
        assert_eq!(algorithm.stale_generations(), stale);
    }
}

#[test]
fn the_run_stops_after_max_seconds() {
    assert_eq!(generations_within(0.0), 1);
    assert_eq!(generations_within(3600.0), 6);
}

thread_local! {
    static LOGGED: RefCell<Vec<String>> = const { RefCell::new(Vec::new()) };
}

/// Keeps what each test's thread logs, apart from the other tests.
struct ThreadLogger;

impl Log for ThreadLogger {
    fn enabled(&self, _metadata: &Metadata) -> bool {
        true
    }

    fn log(&self, record: &Record) {
        let line = format!("{} {}", record.level(), record.args());
        LOGGED.with(|logged| logged.borrow_mut().push(line));
    }

    fn flush(&self) {}
}

/// The lines logged while `run` runs on this thread.
fn logged_by(run: impl FnOnce()) -> Vec<String> {
    static LOGGER: ThreadLogger = ThreadLogger;
    // Only the first test to get here sets it.
    if log::set_logger(&LOGGER).is_ok() {
        log::set_max_level(LevelFilter::Info);
    }
    LOGGED.with(|logged| logged.borrow_mut().clear());
    run();
    LOGGED.with(|logged| logged.take())
}

#[test]
fn a_run_logs_each_generation_and_why_it_stopped() {
    let lines = logged_by(|| {
        fit_zeros(0, true);
    });
    assert_eq!(lines.len(), 4, "{lines:?}");
    assert!(lines[0].starts_with("INFO starting a run of ZeroStart: "));
    assert!(lines[1].starts_with(
        "INFO generation 0: best score 0, mean 0, median 0, \
         1 different chromosomes, took "
    ));
    assert!(lines[2].starts_with("INFO generation 1: "));
    assert_eq!(
        lines[3],
        "INFO the run stopped after generation 1: the mean score did not change"
    );
}

#[test]
fn the_log_names_each_reason_to_stop() {
    let last_line = |run: &dyn Fn()| logged_by(run).pop().unwrap();
    assert_eq!(
        last_line(&|| {
            fit_zeros(2, false);
        }),
        "INFO the run stopped after generation 0: fewer than 2 different chromosomes"
    );
    assert_eq!(
        last_line(&|| {
            generations_within(0.0);
        }),
        "INFO the run stopped after generation 0: 0 seconds reached"
    );
    assert_eq!(
        last_line(&|| {
            stale_run(2);
        }),
        "INFO the run stopped after generation 2: no better best score for 2 generations"
    );
    assert_eq!(
        last_line(&|| {
            let mut config = FitConfig::new(5, 20);
            config.min_population_size = 0;
            algorithm(ZeroStart).fit_with(&config, |_| true).unwrap();
        }),
        "INFO the run stopped after generation 0: on_generation asked to stop"
    );
}

#[test]
fn the_result_says_why_the_run_stopped() {
    // `ZeroStart` without mutations: every chromosome is all zeros.
    let stop_reason = |change: &dyn Fn(&mut FitConfig), stop: bool| {
        let mut config = FitConfig::new(5, 20);
        config.mutate_prob = 0.0;
        config.min_population_size = 0;
        config.stop_without_improvement = false;
        change(&mut config);
        algorithm(ZeroStart)
            .fit_with(&config, |_| stop)
            .unwrap()
            .stop_reason
    };
    assert_eq!(stop_reason(&|_| {}, false), StopReason::Completed);
    assert_eq!(
        stop_reason(&|c| c.min_population_size = 2, false),
        StopReason::MinPopulation
    );
    assert_eq!(
        stop_reason(&|c| c.stop_without_improvement = true, false),
        StopReason::NoImprovement
    );
    assert_eq!(
        stop_reason(&|c| c.max_stale_generations = Some(2), false),
        StopReason::StaleGenerations
    );
    assert_eq!(
        stop_reason(&|c| c.max_seconds = Some(0.0), false),
        StopReason::MaxSeconds
    );
    assert_eq!(stop_reason(&|_| {}, true), StopReason::OnGeneration);
}

#[test]
fn knapsack_finds_the_best_bag() {
    let result = algorithm(knapsack()).fit(&FitConfig::new(100, 50)).unwrap();

    assert_eq!(result.bests[0].score.value, 309.0);
    assert_eq!(result.bests[0].result, [1, 1, 1, 1, 0, 1, 0, 0, 0, 0]);
}

#[test]
fn each_different_chromosome_is_scored_once() {
    let problem = watched(knapsack(), true, true);
    let mut config = FitConfig::new(5, 50);
    config.n_jobs = Some(two_jobs());
    let mut algorithm = algorithm(problem);
    let result = algorithm.fit(&config).unwrap();

    let fitness_calls = algorithm.problem().fitness_calls.load(Ordering::Relaxed);
    let calls = result.fit_metrics.fitness_func_calls;
    assert_eq!(calls.processed, fitness_calls);
    assert_eq!(calls.cached, calls.total - fitness_calls);
    assert!(calls.total > fitness_calls);
    // Every list of 10 genes out of 2.
    assert_eq!(calls.space_points, 1024.0);
    let explored = 100.0 * fitness_calls as f64 / 1024.0;
    assert!((calls.exploration_percentage - explored).abs() < 0.005);
    let kept: HashSet<_> = algorithm
        .history()
        .iter()
        .flatten()
        .map(|individual| &individual.chromosome)
        .collect();
    assert!(kept.len() <= fitness_calls);
}

#[test]
fn the_metrics_count_the_different_chromosomes() {
    let mut algorithm = algorithm(knapsack());
    let result = algorithm.fit(&FitConfig::new(5, 50)).unwrap();

    assert_eq!(result.metrics.len(), algorithm.history().len());
    let mut repeated = false;
    for (metric, population) in result.metrics.iter().zip(algorithm.history()) {
        let different: HashSet<_> = population.iter().map(|i| &i.chromosome).collect();
        assert_eq!(metric.n_uniques, different.len());
        repeated |= different.len() < population.len();
    }
    // Or the count was never asked to tell equal chromosomes apart.
    assert!(repeated);
}

/// The genes of each population of a knapsack run.
fn knapsack_run_genes(n_jobs: usize, random_seed: u64) -> Vec<Vec<Vec<u8>>> {
    let mut config = FitConfig::new(10, 30);
    config.n_jobs = Some(n_jobs);
    let settings = AlgorithmConfig {
        random_seed,
        ..AlgorithmConfig::default()
    };
    let mut algorithm = GeneticAlgorithm::new(knapsack(), settings);
    algorithm.fit(&config).unwrap();
    algorithm
        .history()
        .iter()
        .map(|population| {
            population
                .iter()
                .map(|i| i.chromosome.genes().to_vec())
                .collect()
        })
        .collect()
}

#[test]
fn a_seed_gives_the_same_run_with_any_number_of_threads() {
    assert_eq!(knapsack_run_genes(1, 7), knapsack_run_genes(two_jobs(), 7));
}

#[test]
fn another_seed_gives_another_run() {
    assert_ne!(knapsack_run_genes(1, 7), knapsack_run_genes(1, 8));
}

#[test]
fn the_population_keeps_its_size_and_is_sorted_best_first() {
    let mut config = FitConfig::new(4, 30);
    config.stop_without_improvement = false;
    let mut algorithm = algorithm(knapsack());
    let result = algorithm.fit(&config).unwrap();

    assert_eq!(algorithm.history().len(), 5);
    assert_eq!(result.metrics.len(), 5);
    for population in algorithm.history() {
        assert_eq!(population.len(), 30);
        assert!(
            population
                .windows(2)
                .all(|pair| pair[0].score.value >= pair[1].score.value)
        );
    }
    let bests: HashSet<_> = result.bests.iter().map(|b| &b.encoded.chromosome).collect();
    assert_eq!(bests.len(), result.bests.len());
    // Five of the thirty, best first
    assert_eq!(result.bests.len(), 5);
    assert!(
        result
            .bests
            .windows(2)
            .all(|pair| pair[0].score.value >= pair[1].score.value)
    );
}

#[test]
fn proportions_at_0_and_1_breed_without_error() {
    // With both at 1 every chromosome is a parent and the rest is empty.
    for (crossovers_prop, besties_prop) in [(1.0, 1.0), (1.0, 0.0), (0.0, 1.0)] {
        let mut config = FitConfig::new(4, 30);
        config.crossovers_prop = crossovers_prop;
        config.besties_prop = besties_prop;
        config.stop_without_improvement = false;
        config.min_population_size = 0;
        assert_eq!(algorithm(knapsack()).fit(&config).unwrap().metrics.len(), 5);
    }
}

#[test]
fn a_population_of_one_breeds_no_children() {
    let mut config = FitConfig::new(4, 1);
    config.stop_without_improvement = false;
    config.min_population_size = 0;
    let mut algorithm = algorithm(knapsack());
    let result = algorithm.fit(&config).unwrap();

    assert!(
        algorithm
            .history()
            .iter()
            .all(|population| population.len() == 1)
    );
    assert_eq!(algorithm.history().len(), 5);
    assert_eq!(result.fit_metrics.fitness_func_calls.total, 1);
    assert_eq!(result.bests.len(), 1);
}

#[test]
fn a_second_fit_is_the_same_run_again() {
    let mut config = FitConfig::new(4, 30);
    config.stop_without_improvement = false;
    let mut algorithm = algorithm(knapsack());
    let genes = |algorithm: &GeneticAlgorithm<Knapsack>| {
        algorithm
            .history()
            .iter()
            .map(|population| {
                population
                    .iter()
                    .map(|i| i.chromosome.genes().to_vec())
                    .collect::<Vec<_>>()
            })
            .collect::<Vec<_>>()
    };
    let first = algorithm.fit(&config).unwrap();
    let first_genes = genes(&algorithm);
    let second = algorithm.fit(&config).unwrap();

    assert_eq!(second.metrics.len(), 5);
    assert_eq!(algorithm.metrics().len(), 5);
    assert_eq!(genes(&algorithm), first_genes);
    let (first_calls, second_calls) = (
        first.fit_metrics.fitness_func_calls,
        second.fit_metrics.fitness_func_calls,
    );
    assert_eq!(second_calls.total, first_calls.total);
    // Every chromosome of the second run was scored by the first.
    assert!(first_calls.processed > 0);
    assert_eq!(second_calls.processed, 0);
    assert_eq!(second_calls.cached, second_calls.total);
}

#[test]
fn set_chromosomes_stay_sets_and_the_best_never_gets_worse() {
    let mut algorithm = algorithm(numbers(false));
    let result = algorithm.fit(&numbers_config()).unwrap();

    assert!(result.metrics.len() > 1);
    assert_eq!(result.bests[0].result, [9, 10, 11]);
    // Every set of 3 numbers out of 12.
    assert_eq!(result.fit_metrics.fitness_func_calls.space_points, 220.0);
    assert!(
        result
            .metrics
            .windows(2)
            .all(|pair| pair[0].best.score.value <= pair[1].best.score.value)
    );
    for individual in algorithm.history().iter().flatten() {
        let genes = individual.chromosome.genes();
        assert_eq!(genes.len(), PICKED);
        assert!(genes.windows(2).all(|pair| pair[0] < pair[1]));
    }
}

#[test]
fn minimize_keeps_the_lowest_scores() {
    let mut algorithm = algorithm(numbers(true));
    let result = algorithm.fit(&numbers_config()).unwrap();

    assert!(result.metrics.len() > 1);
    assert_eq!(result.bests[0].result, [0, 1, 2]);
    assert!(
        result
            .metrics
            .windows(2)
            .all(|pair| pair[0].best.score.value >= pair[1].best.score.value)
    );
    for population in algorithm.history() {
        assert!(
            population
                .windows(2)
                .all(|pair| pair[0].score.value <= pair[1].score.value)
        );
    }
}

#[test]
fn a_set_chromosome_is_sorted_without_repeated_genes() {
    let set = Chromosome::new(vec![3, 1, 3, 2], true);
    assert_eq!(set.genes(), [1, 2, 3]);
    assert!(set.is_gene_set());
    assert_eq!(set, Chromosome::new(vec![2, 3, 1], true));

    let list = Chromosome::new(vec![3, 1, 3, 2], false);
    assert_eq!(list.genes(), [3, 1, 3, 2]);
    assert!(!list.is_gene_set());
}

#[test]
fn fit_config_new_sets_the_defaults() {
    let config = FitConfig::new(7, 40);
    assert_eq!((config.n_generations, config.population_size), (7, 40));
    assert_eq!(config.crossovers_prop, 0.7);
    assert_eq!(config.besties_prop, 0.6);
    assert_eq!(config.mutate_prob, 0.05);
    assert_eq!(config.min_population_size, 10);
    assert!(config.stop_without_improvement);
    assert_eq!(config.n_jobs, None);
    assert_eq!(config.max_seconds, None);
    assert_eq!(config.max_stale_generations, None);
    assert_eq!(config.selection, Selection::Random);
    assert_eq!(config.tournament_size, 3);
}

#[test]
fn algorithm_config_default_sets_the_defaults() {
    let config = AlgorithmConfig::default();
    assert!(config.experiment_name.is_none());
    assert_eq!(config.random_seed, 442);
    assert!(config.extra_config.is_none());
    assert!(config.save.is_none());
}

#[test]
fn the_experiment_name_defaults_to_the_name_of_the_problem_type() {
    assert_eq!(algorithm(knapsack()).experiment_name(), "Knapsack");
    assert_eq!(algorithm(numbers(false)).experiment_name(), "Numbers");
    let settings = AlgorithmConfig {
        experiment_name: Some("bag".into()),
        ..AlgorithmConfig::default()
    };
    assert_eq!(
        GeneticAlgorithm::new(knapsack(), settings).experiment_name(),
        "bag"
    );
}

#[test]
fn the_algorithm_shows_the_last_population_and_the_metrics_of_the_run() {
    let mut config = FitConfig::new(4, 30);
    config.n_jobs = Some(1);
    let settings = AlgorithmConfig {
        random_seed: 9,
        ..AlgorithmConfig::default()
    };
    let mut algorithm = GeneticAlgorithm::new(knapsack(), settings);
    assert!(algorithm.population().is_empty());
    assert!(algorithm.metrics().is_empty());
    let result = algorithm.fit(&config).unwrap();

    assert_eq!(algorithm.population(), algorithm.history().last().unwrap());
    assert_eq!(
        serde_json::to_value(algorithm.metrics()).unwrap(),
        serde_json::to_value(&result.metrics).unwrap()
    );
    let parameters = &result.fit_parameters;
    assert_eq!(parameters.n_generations, 4);
    assert_eq!(parameters.population_size, 30);
    assert_eq!(parameters.crossovers_prop, 0.7);
    assert_eq!(parameters.besties_prop, 0.6);
    assert_eq!(parameters.mutate_prob, 0.05);
    assert_eq!(parameters.min_population_size, 10);
    assert_eq!(parameters.random_seed, 9);
    assert_eq!(parameters.n_jobs, 1);
    assert_eq!(parameters.selection, Selection::Random);
    assert_eq!(parameters.tournament_size, 3);
}

/// One gene from 0 to 19, scored by its value, whose crossover keeps the
/// genes of every parent it gets.
struct Parents(std::sync::Mutex<Vec<u8>>);

impl Problem for Parents {
    type Gene = u8;
    type Solution = u8;

    fn chromosome_length(&self) -> usize {
        1
    }

    fn minimize(&self) -> bool {
        false
    }

    fn gene_space_size(&self) -> usize {
        20
    }

    fn random_gene(&self, rng: &mut Rng) -> u8 {
        rand::RngExt::random_range(rng, 0..20)
    }

    fn fitness(&self, genes: &[u8]) -> Score {
        Score::new(f64::from(genes[0]))
    }

    fn decode(&self, genes: &[u8]) -> u8 {
        genes[0]
    }

    fn crossover(&self, first: &[u8], second: &[u8], _rng: &mut Rng) -> (Vec<u8>, Vec<u8>) {
        self.0.lock().unwrap().extend([first[0], second[0]]);
        (first.to_vec(), second.to_vec())
    }
}

/// The genes of the parents of one generation of [`Parents`], with no
/// besties.
fn tournament_parents(tournament_size: usize) -> Vec<u8> {
    let mut config = FitConfig::new(1, 100);
    config.crossovers_prop = 1.0;
    config.besties_prop = 0.0;
    config.mutate_prob = 0.0;
    config.min_population_size = 0;
    config.selection = Selection::Tournament;
    config.tournament_size = tournament_size;
    let mut algorithm = algorithm(Parents(std::sync::Mutex::new(Vec::new())));
    algorithm.fit(&config).unwrap();
    algorithm.problem().0.lock().unwrap().clone()
}

#[test]
fn a_tournament_picks_the_best_of_the_chromosomes_drawn() {
    let mean = |genes: &[u8]| genes.iter().map(|g| f64::from(*g)).sum::<f64>() / genes.len() as f64;
    let one = tournament_parents(1);
    let five = tournament_parents(5);
    assert_eq!((one.len(), five.len()), (100, 100));
    // The best of 5 drawn from 0 to 19 is about 16 on average, against
    // about 9.5 for a random pick.
    assert!(mean(&five) > 14.0);
    assert!(mean(&five) > mean(&one));
}

#[test]
fn a_tournament_run_is_saved_with_its_selection() {
    let folder = tempfile::tempdir().unwrap();
    let mut config = FitConfig::new(2, 20);
    config.selection = Selection::Tournament;
    config.tournament_size = 4;
    let result = saving_algorithm(knapsack(), folder.path(), "bag")
        .fit(&config)
        .unwrap();

    let file = File::open(result.save_folder.unwrap().join("experiment_config.yml")).unwrap();
    let saved: serde_json::Value = serde_norway::from_reader(file).unwrap();
    assert_eq!(saved["fit_parameters"]["selection"], "tournament");
    assert_eq!(saved["fit_parameters"]["tournament_size"], 4);
}

#[test]
fn a_run_of_0_generations_scores_the_first_population_only() {
    let mut algorithm = algorithm(knapsack());
    let result = algorithm.fit(&FitConfig::new(0, 20)).unwrap();

    assert_eq!(result.metrics.len(), 1);
    assert_eq!(algorithm.history().len(), 1);
    assert_eq!(result.fit_parameters.n_generations, 0);
    assert_eq!(algorithm.population().len(), 20);
}

#[test]
fn a_run_starts_from_a_given_population_without_scoring_it() {
    let mut saved = algorithm(knapsack());
    saved.fit(&FitConfig::new(3, 20)).unwrap();
    // Scores the fitness function would not give, to tell them apart.
    // Equal chromosomes get equal ones, as they share a score.
    let first: Vec<(Vec<u8>, Score)> = saved
        .population()
        .iter()
        .map(|individual| {
            let genes = individual.chromosome.genes().to_vec();
            (genes, Score::new(1000.0 + individual.score.value))
        })
        .collect();
    let mut algorithm = algorithm(watched(knapsack(), true, true));
    let result = algorithm
        .fit_from(&FitConfig::new(0, 20), Some(first.clone()), |_| false)
        .unwrap();

    let started: Vec<(Vec<u8>, Score)> = algorithm.history()[0]
        .iter()
        .map(|i| (i.chromosome.genes().to_vec(), i.score.clone()))
        .collect();
    assert_eq!(started, first);
    assert_eq!(algorithm.problem().fitness_calls.load(Ordering::Relaxed), 0);
    let calls = result.fit_metrics.fitness_func_calls;
    assert_eq!(calls.processed, 0);
    assert_eq!(calls.cached, 20);
}

#[test]
fn a_run_from_a_given_population_breeds_from_it() {
    let first: Vec<(Vec<u8>, Score)> = (0..4)
        .map(|i| (vec![i, i + 1, i + 2], Score::new(f64::from(3 * i + 3))))
        .collect();
    let mut config = FitConfig::new(3, 4);
    config.min_population_size = 0;
    config.stop_without_improvement = false;
    let problem = FirstGenes {
        first_population: vec![vec![9, 9, 9]; 4],
        as_set: false,
        gene_space_size: 12,
    };
    let mut algorithm = algorithm(problem);
    algorithm.fit_from(&config, Some(first), |_| false).unwrap();

    // The genes of `init_population` are never used.
    assert!(
        algorithm
            .history()
            .iter()
            .flatten()
            .all(|i| i.chromosome.genes() != [9, 9, 9])
    );
    assert_eq!(algorithm.history().len(), 4);
}

#[test]
fn a_given_population_that_does_not_fit_is_refused() {
    for (first, refused) in [
        (vec![], "the first population has no chromosomes"),
        (
            vec![
                (vec![0, 1, 2], Score::new(1000.0)),
                (vec![1, 2], Score::new(3.0)),
            ],
            "a chromosome has 2 genes",
        ),
        (
            vec![
                (vec![0, 1, 2], Score::new(1000.0)),
                (vec![4, 5, 6], Score::new(f64::NAN)),
            ],
            "the first population gives a NaN score to the chromosome [4,5,6]",
        ),
    ] {
        let problem = FirstGenes {
            first_population: vec![vec![0, 1, 2]],
            as_set: false,
            gene_space_size: 12,
        };
        let mut algorithm = algorithm(problem);
        let mut config = FitConfig::new(0, 1);
        config.min_population_size = 0;
        let error = algorithm
            .fit_from(&config, Some(first), |_| false)
            .unwrap_err();
        assert!(
            matches!(&error, Error::Validation(message) if message.starts_with(refused)),
            "{error:?}"
        );
        // No score of a refused population is kept: [0, 1, 2] is scored.
        algorithm.fit(&config).unwrap();
        assert_eq!(algorithm.population()[0].score.value, 3.0);
    }
}

#[test]
fn n_jobs_none_is_every_core_but_one() {
    let cores = available_parallelism().map_or(1, |n| n.get());
    let result = algorithm(knapsack()).fit(&FitConfig::new(1, 20)).unwrap();
    assert_eq!(result.fit_parameters.n_jobs, (cores - 1).max(1));
}

#[test]
fn on_generation_can_stop_the_run() {
    let mut config = FitConfig::new(50, 30);
    config.stop_without_improvement = false;
    let result = algorithm(knapsack())
        .fit_with(&config, |algorithm| algorithm.history().len() == 3)
        .unwrap();

    assert_eq!(result.metrics.len(), 3);
}

#[test]
fn a_broken_invariant_stops_the_run() {
    for (keep_mutations, keep_crossovers, broken) in
        [(false, true, "a mutation"), (true, false, "a crossover")]
    {
        let problem = watched(numbers(false), keep_mutations, keep_crossovers);
        let error = fit_error(algorithm(problem), FitConfig::new(5, 30));
        assert!(
            matches!(&error, Error::Invariant(message) if message.starts_with(broken)),
            "{error:?}"
        );
    }
}

#[test]
fn chromosomes_the_problem_cannot_hold_are_refused() {
    for (first_population, as_set, gene_space_size, refused) in [
        // A list of 2 genes.
        (vec![vec![1, 2]; 5], false, 12, "a chromosome has 2 genes"),
        // A set with a gene twice keeps 2.
        (vec![vec![1, 1, 2]; 5], true, 12, "a chromosome has 2 genes"),
        (vec![vec![0, 1, 2]; 5], true, 2, "a set of 3 genes"),
        (vec![], false, 12, "init_population returned no chromosomes"),
    ] {
        let problem = FirstGenes {
            first_population,
            as_set,
            gene_space_size,
        };
        let error = fit_error(algorithm(problem), FitConfig::new(5, 30));
        assert!(
            matches!(&error, Error::Validation(message) if message.starts_with(refused)),
            "{error:?}"
        );
    }
}

/// The sum of 3 genes, except for the genes `[4, 5, 6]`, whose score is
/// not a number. Its first population is those genes and `[1, 2, 3]`.
struct NanFor456;

impl Problem for NanFor456 {
    type Gene = u8;
    type Solution = u32;

    fn chromosome_length(&self) -> usize {
        3
    }

    fn minimize(&self) -> bool {
        false
    }

    fn gene_space_size(&self) -> usize {
        12
    }

    fn random_gene(&self, rng: &mut Rng) -> u8 {
        rand::RngExt::random_range(rng, 0..12)
    }

    fn fitness(&self, genes: &[u8]) -> Score {
        if genes == [4, 5, 6] {
            return Score::new(f64::NAN);
        }
        Score::new(self.decode(genes).into())
    }

    fn decode(&self, genes: &[u8]) -> u32 {
        genes.iter().map(|gene| u32::from(*gene)).sum()
    }

    fn crossover(&self, first: &[u8], second: &[u8], _rng: &mut Rng) -> (Vec<u8>, Vec<u8>) {
        (first.to_vec(), second.to_vec())
    }

    fn init_population(&self, _population_size: usize, _rng: &mut Rng) -> Vec<Vec<u8>> {
        vec![vec![1, 2, 3], vec![4, 5, 6]]
    }
}

#[test]
fn a_nan_score_stops_the_run() {
    let mut algorithm = algorithm(NanFor456);
    let mut config = FitConfig::new(5, 2);
    config.min_population_size = 0;
    // The score is not kept, so a second run is refused too.
    for _ in 0..2 {
        let error = algorithm.fit(&config).unwrap_err();
        assert!(
            matches!(
                &error,
                Error::Validation(message)
                    if message == "the fitness function gave a NaN score to the chromosome [4,5,6]"
            ),
            "{error:?}"
        );
    }
}

#[test]
fn more_threads_than_cores_are_refused() {
    let cores = available_parallelism().map_or(1, |n| n.get());
    let mut config = FitConfig::new(5, 30);
    config.n_jobs = Some(cores + 1);
    let error = fit_error(algorithm(knapsack()), config);
    assert!(
        matches!(&error, Error::Validation(message) if message.starts_with("n_jobs")),
        "{error:?}"
    );
}

#[test]
fn bad_parameters_are_refused() {
    let mut small_population = FitConfig::new(5, 5);
    small_population.min_population_size = 10;
    let mut no_threads = FitConfig::new(5, 30);
    no_threads.n_jobs = Some(0);

    let mut no_population = FitConfig::new(5, 0);
    no_population.min_population_size = 0;
    let mut crossovers_over_one = FitConfig::new(5, 30);
    crossovers_over_one.crossovers_prop = 1.5;
    let mut negative_besties = FitConfig::new(5, 30);
    negative_besties.besties_prop = -0.1;
    let mut mutate_not_a_number = FitConfig::new(5, 30);
    mutate_not_a_number.mutate_prob = f64::NAN;
    let mut negative_seconds = FitConfig::new(5, 30);
    negative_seconds.max_seconds = Some(-1.0);
    let mut seconds_not_a_number = FitConfig::new(5, 30);
    seconds_not_a_number.max_seconds = Some(f64::NAN);
    let mut empty_tournament = FitConfig::new(5, 30);
    empty_tournament.tournament_size = 0;

    for config in [
        small_population,
        no_threads,
        no_population,
        crossovers_over_one,
        negative_besties,
        mutate_not_a_number,
        negative_seconds,
        seconds_not_a_number,
        empty_tournament,
    ] {
        assert!(matches!(
            algorithm(knapsack()).fit(&config),
            Err(Error::Validation(_))
        ));
    }
    assert!(matches!(
        Knapsack::new(vec![1, 2], vec![1], 3),
        Err(Error::Validation(_))
    ));
}

#[test]
fn knapsack_sums_do_not_overflow() {
    let heavy = Knapsack::new(vec![u32::MAX, 2], vec![1, 1], u32::MAX).unwrap();
    assert_eq!(heavy.decode(&[1, 1]), vec![1, 0]);

    let valuable = Knapsack::new(vec![1, 1], vec![u32::MAX, u32::MAX], 2).unwrap();
    assert_eq!(valuable.fitness(&[1, 1]).value, 2.0 * f64::from(u32::MAX));
}

/// The same bags are decoded in `tests/unit/examples/test_binary.py`,
/// `KNOWN_BAGS`.
#[test]
fn knapsack_decodes_known_bags() {
    let bags: [([u8; 10], [u8; 10], f64); 4] = [
        ([0; 10], [0; 10], 0.0),
        (
            [1, 1, 1, 1, 0, 1, 0, 0, 0, 0],
            [1, 1, 1, 1, 0, 1, 0, 0, 0, 0],
            309.0,
        ),
        ([1; 10], [1, 1, 1, 1, 0, 0, 0, 0, 0, 0], 266.0),
        (
            [0, 0, 0, 0, 0, 0, 0, 1, 1, 0],
            [0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
            84.0,
        ),
    ];
    for (genes, decoded, value) in bags {
        assert_eq!(knapsack().decode(&genes), decoded);
        assert_eq!(knapsack().fitness(&genes).value, value);
    }
}

#[test]
fn knapsack_takes_nothing_after_the_first_object_that_does_not_fit() {
    let bag = Knapsack::new(vec![5, 10, 1], vec![1, 1, 1], 12).unwrap();
    assert_eq!(bag.decode(&[1, 1, 1]), vec![1, 0, 0]);
}

#[test]
fn single_point_crossover_cuts_at_every_position_between_two_genes() {
    let mut rng = Rng::seed_from_u64(1);
    let mut cuts = BTreeSet::new();
    for _ in 0..200 {
        let (first, second) = single_point_crossover(&[0; 5], &[1; 5], &mut rng);
        let cut = first.iter().position(|gene| *gene == 1).unwrap();
        assert_eq!(first, [vec![0; cut], vec![1; 5 - cut]].concat());
        assert_eq!(second, [vec![1; cut], vec![0; 5 - cut]].concat());
        cuts.insert(cut);
    }
    assert_eq!(cuts, BTreeSet::from([1, 2, 3, 4]));
}

#[test]
fn single_point_crossover_of_fewer_than_two_genes_returns_the_parents() {
    let mut rng = Rng::seed_from_u64(1);
    assert_eq!(
        single_point_crossover(&[0], &[1], &mut rng),
        (vec![0], vec![1])
    );
    assert_eq!(
        single_point_crossover::<u8>(&[], &[], &mut rng),
        (vec![], vec![])
    );
    // The shorter parent sets the length.
    assert_eq!(
        single_point_crossover(&[0], &[1, 1, 1], &mut rng),
        (vec![0], vec![1, 1, 1])
    );
}

#[test]
fn single_point_crossover_of_different_lengths_cuts_within_the_shorter() {
    let mut rng = Rng::seed_from_u64(1);
    let mut cuts = BTreeSet::new();
    for _ in 0..200 {
        let (first, second) = single_point_crossover(&[0; 3], &[1; 5], &mut rng);
        let cut = first.iter().position(|gene| *gene == 1).unwrap();
        // Each child keeps the tail, and so the length, of the other parent.
        assert_eq!(first, [vec![0; cut], vec![1; 5 - cut]].concat());
        assert_eq!(second, [vec![1; cut], vec![0; 3 - cut]].concat());
        cuts.insert(cut);
    }
    assert_eq!(cuts, BTreeSet::from([1, 2]));
}

#[test]
fn uniform_crossover_gives_each_gene_to_either_child() {
    let mut rng = Rng::seed_from_u64(1);
    let mut swapped = [0; 5];
    for _ in 0..200 {
        let (first, second) = uniform_crossover(&[0; 5], &[1; 5], &mut rng);
        for position in 0..5 {
            // The two children share the genes of the parents out.
            assert_eq!(first[position] + second[position], 1);
            swapped[position] += first[position];
        }
    }
    // Each position is swapped about half of the times.
    assert!(swapped.iter().all(|count| (60..=140).contains(count)));
}

#[test]
fn uniform_crossover_of_different_lengths_keeps_the_longer_tail() {
    let mut rng = Rng::seed_from_u64(1);
    for _ in 0..50 {
        let (first, second) = uniform_crossover(&[0; 2], &[1; 4], &mut rng);
        assert_eq!(first.len(), 2);
        assert_eq!(second[2..], [1, 1]);
        assert_eq!(first[0] + second[0], 1);
        assert_eq!(first[1] + second[1], 1);
    }
    assert_eq!(
        uniform_crossover::<u8>(&[], &[], &mut rng),
        (vec![], vec![])
    );
}

/// The knapsack, crossed with [`uniform_crossover`].
struct UniformKnapsack(Knapsack);

impl Problem for UniformKnapsack {
    type Gene = u8;
    type Solution = Vec<u8>;

    fn chromosome_length(&self) -> usize {
        self.0.chromosome_length()
    }

    fn minimize(&self) -> bool {
        self.0.minimize()
    }

    fn gene_space_size(&self) -> usize {
        self.0.gene_space_size()
    }

    fn random_gene(&self, rng: &mut Rng) -> u8 {
        self.0.random_gene(rng)
    }

    fn fitness(&self, genes: &[u8]) -> Score {
        self.0.fitness(genes)
    }

    fn decode(&self, genes: &[u8]) -> Vec<u8> {
        self.0.decode(genes)
    }

    fn crossover(&self, first: &[u8], second: &[u8], rng: &mut Rng) -> (Vec<u8>, Vec<u8>) {
        uniform_crossover(first, second, rng)
    }
}

#[test]
fn a_run_crossed_with_uniform_crossover_finds_the_best_bag() {
    let mut algorithm =
        GeneticAlgorithm::new(UniformKnapsack(knapsack()), AlgorithmConfig::default());
    let mut config = FitConfig::new(100, 50);
    config.n_jobs = Some(1);
    let result = algorithm.fit(&config).unwrap();
    assert_eq!(result.bests[0].score.value, 309.0);
}

#[test]
fn a_run_is_saved_one_file_per_generation() {
    for (as_bson, extension) in [(false, "json"), (true, "bson")] {
        let folder = tempfile::tempdir().unwrap();
        let mut config = FitConfig::new(3, 20);
        config.stop_without_improvement = false;
        let settings = AlgorithmConfig {
            experiment_name: Some("bag".into()),
            extra_config: Some(serde_json::json!({"note": "test"})),
            save: Some(SaveConfig {
                path: folder.path().to_path_buf(),
                as_bson,
            }),
            ..AlgorithmConfig::default()
        };
        let result = GeneticAlgorithm::new(knapsack(), settings)
            .fit(&config)
            .unwrap();

        let run_folder = result.save_folder.unwrap();
        assert_eq!(run_folder.parent().unwrap(), folder.path().join("bag"));
        assert!(run_folder.join("experiment_config.yml").is_file());
        let mut files: Vec<_> = read_dir(run_folder.join("fit_data"))
            .unwrap()
            .map(|entry| entry.unwrap().file_name().into_string().unwrap())
            .collect();
        files.sort();
        let expected: Vec<_> = (1..=4)
            .map(|n| format!("fit_data_{n}.{extension}"))
            .collect();
        assert_eq!(files, expected);

        let last = File::open(run_folder.join("fit_data").join(&files[3])).unwrap();
        let saved: serde_json::Value = if as_bson {
            serde_json::to_value(bson::Document::from_reader(last).unwrap()).unwrap()
        } else {
            serde_json::from_reader(last).unwrap()
        };
        assert_eq!(saved["population_idx"], 4);
        assert_eq!(saved["config"]["note"], "test");
        let metrics = saved["metrics"].as_array().unwrap();
        assert_eq!(metrics.len(), 1);
        assert_eq!(
            metrics[0]["best"]["score"]["value"],
            result.metrics[3].best.score.value
        );
        assert_eq!(saved["population"].as_array().unwrap().len(), 20);
        // The population is saved once, not decoded a second time.
        assert!(saved.get("last_population").is_none());
        assert_eq!(
            saved["bests"]["scores"][0]["value"],
            result.bests[0].score.value
        );
        let best = &saved["population"][0][1];
        assert_eq!(best["is_gene_set"], false);
        assert_eq!(best["genes"].as_array().unwrap().len(), 10);
        assert_eq!(best["random_seed"], 442);
    }
}

#[test]
fn a_saved_chromosome_keeps_the_time_its_score_took() {
    let folder = tempfile::tempdir().unwrap();
    let mut problem = watched(knapsack(), true, true);
    problem.fitness_delay = Duration::from_millis(20);
    let mut config = FitConfig::new(0, 3);
    config.min_population_size = 1;
    config.n_jobs = Some(1);
    let mut algorithm = saving_algorithm(problem, folder.path(), "bag");
    let result = algorithm.fit(&config).unwrap();

    let path = result.save_folder.unwrap().join("fit_data/fit_data_1.json");
    let saved: serde_json::Value = serde_json::from_reader(File::open(path).unwrap()).unwrap();
    let population = saved["population"].as_array().unwrap();
    assert_eq!(population.len(), algorithm.population().len());
    for (entry, individual) in population.iter().zip(algorithm.population()) {
        assert!(individual.score_time >= 0.02);
        assert_eq!(entry[1]["score_time"], individual.score_time);
    }
}

/// The algorithm of `problem`, saving its runs as JSON in
/// `path/experiment_name`.
fn saving_algorithm<P: Problem>(
    problem: P,
    path: &std::path::Path,
    experiment_name: &str,
) -> GeneticAlgorithm<P> {
    let settings = AlgorithmConfig {
        experiment_name: Some(experiment_name.into()),
        save: Some(SaveConfig {
            path: path.to_path_buf(),
            as_bson: false,
        }),
        ..AlgorithmConfig::default()
    };
    GeneticAlgorithm::new(problem, settings)
}

#[test]
fn two_runs_with_one_name_get_a_folder_each() {
    let folder = tempfile::tempdir().unwrap();
    // More runs than fit in the second a folder is named after.
    let run_folders: HashSet<_> = (0..5)
        .map(|_| {
            let result = saving_algorithm(knapsack(), folder.path(), "bag")
                .fit(&FitConfig::new(1, 20))
                .unwrap();
            result.save_folder.unwrap()
        })
        .collect();

    assert_eq!(run_folders.len(), 5);
    for run_folder in &run_folders {
        assert_eq!(run_folder.parent().unwrap(), folder.path().join("bag"));
        assert!(run_folder.join("experiment_config.yml").is_file());
    }
}

#[test]
fn the_experiment_config_of_the_problem_is_saved() {
    let folder = tempfile::tempdir().unwrap();
    let result = saving_algorithm(numbers(false), folder.path(), "numbers")
        .fit(&FitConfig::new(1, 20))
        .unwrap();

    let file = File::open(result.save_folder.unwrap().join("experiment_config.yml")).unwrap();
    let saved: serde_json::Value = serde_norway::from_reader(file).unwrap();
    assert_eq!(
        saved["experiment_config"],
        serde_json::json!({"numbers": 12, "picked": 3})
    );
    assert_eq!(saved["fit_parameters"]["population_size"], 20);
}

#[test]
fn a_save_path_that_cannot_be_created_stops_the_run() {
    let folder = tempfile::tempdir().unwrap();
    let file = folder.path().join("a_file");
    File::create(&file).unwrap();

    let error = fit_error(
        saving_algorithm(knapsack(), &file, "bag"),
        FitConfig::new(1, 20),
    );
    assert!(matches!(error, Error::Io(_)), "{error:?}");
}

#[test]
fn an_experiment_name_outside_the_save_path_is_refused() {
    let folder = tempfile::tempdir().unwrap();
    let save_path = folder.path().join("runs");
    let absolute = folder.path().join("elsewhere");

    for experiment_name in ["../elsewhere", "bag/../..", absolute.to_str().unwrap(), ""] {
        let mut algorithm = saving_algorithm(knapsack(), &save_path, experiment_name);
        assert!(matches!(
            algorithm.fit(&FitConfig::new(1, 20)),
            Err(Error::Validation(_))
        ));
    }
    assert!(!save_path.exists());
    assert!(!absolute.exists());
}

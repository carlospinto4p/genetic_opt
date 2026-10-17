use std::collections::{BTreeSet, HashSet};
use std::fs::{File, read_dir};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::thread::available_parallelism;

use rand::SeedableRng;

use genetic_opt::examples::Knapsack;
use genetic_opt::{
    AlgorithmConfig, Chromosome, Error, FitConfig, GeneticAlgorithm, Problem, Rng, SaveConfig,
    Score, single_point_crossover,
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

/// A knapsack that counts the calls to its fitness function.
struct CountedKnapsack {
    knapsack: Knapsack,
    fitness_calls: AtomicUsize,
}

impl Problem for CountedKnapsack {
    type Gene = u8;
    type Solution = Vec<u8>;

    fn chromosome_length(&self) -> usize {
        self.knapsack.chromosome_length()
    }

    fn minimize(&self) -> bool {
        false
    }

    fn gene_space_size(&self) -> usize {
        2
    }

    fn random_gene(&self, rng: &mut Rng) -> u8 {
        self.knapsack.random_gene(rng)
    }

    fn fitness(&self, genes: &[u8]) -> Score {
        self.fitness_calls.fetch_add(1, Ordering::Relaxed);
        self.knapsack.fitness(genes)
    }

    fn decode(&self, genes: &[u8]) -> Vec<u8> {
        self.knapsack.decode(genes)
    }

    fn crossover(&self, first: &[u8], second: &[u8], rng: &mut Rng) -> (Vec<u8>, Vec<u8>) {
        self.knapsack.crossover(first, second, rng)
    }
}

/// Pick `PICKED` different numbers under `NUMBERS` with the highest sum,
/// or the lowest. A chromosome is a set.
struct Numbers {
    minimize: bool,
    keep_mutations: bool,
    keep_crossovers: bool,
}

const NUMBERS: u8 = 12;
const PICKED: usize = 3;

impl Problem for Numbers {
    type Gene = u8;
    type Solution = u32;

    fn chromosome_length(&self) -> usize {
        PICKED
    }

    fn chromosome_as_set(&self) -> bool {
        true
    }

    fn minimize(&self) -> bool {
        self.minimize
    }

    fn gene_space_size(&self) -> usize {
        NUMBERS.into()
    }

    fn random_gene(&self, rng: &mut Rng) -> u8 {
        rand::RngExt::random_range(rng, 0..NUMBERS)
    }

    fn fitness(&self, genes: &[u8]) -> Score {
        Score::new(self.decode(genes).into())
    }

    fn decode(&self, genes: &[u8]) -> u32 {
        genes.iter().map(|gene| u32::from(*gene)).sum()
    }

    fn crossover(&self, first: &[u8], second: &[u8], rng: &mut Rng) -> (Vec<u8>, Vec<u8>) {
        let mix = |a: &[u8], b: &[u8]| -> BTreeSet<u8> {
            a[..1].iter().chain(&b[1..]).copied().collect()
        };
        (
            self.fill_set(mix(first, second), rng),
            self.fill_set(mix(second, first), rng),
        )
    }

    fn mutation_invariant(&self, _before: &[u8], _after: &[u8]) -> bool {
        self.keep_mutations
    }

    fn crossover_invariant(&self, _parents: (&[u8], &[u8]), _children: (&[u8], &[u8])) -> bool {
        self.keep_crossovers
    }

    fn experiment_config(&self) -> Option<serde_json::Value> {
        Some(serde_json::json!({"numbers": NUMBERS, "picked": PICKED}))
    }
}

fn numbers(minimize: bool) -> Numbers {
    Numbers {
        minimize,
        keep_mutations: true,
        keep_crossovers: true,
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

#[test]
fn knapsack_finds_the_best_bag() {
    let result = algorithm(knapsack()).fit(&FitConfig::new(100, 50)).unwrap();

    assert_eq!(result.bests[0].score.value, 309.0);
    assert_eq!(result.bests[0].result, [1, 1, 1, 1, 0, 1, 0, 0, 0, 0]);
}

#[test]
fn each_different_chromosome_is_scored_once() {
    let problem = CountedKnapsack {
        knapsack: knapsack(),
        fitness_calls: AtomicUsize::new(0),
    };
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
    assert_eq!(result.bests[0].result, 9 + 10 + 11);
    // Every set of 3 numbers out of 12.
    assert_eq!(result.fit_metrics.fitness_func_calls.space_points, 220.0);
    assert!(
        result
            .metrics
            .windows(2)
            .all(|pair| pair[0].best.result <= pair[1].best.result)
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
    // 0 + 1 + 2.
    assert_eq!(result.bests[0].result, 3);
    assert!(
        result
            .metrics
            .windows(2)
            .all(|pair| pair[0].best.result >= pair[1].best.result)
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
        let problem = Numbers {
            minimize: false,
            keep_mutations,
            keep_crossovers,
        };
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

    for config in [
        small_population,
        no_threads,
        no_population,
        crossovers_over_one,
        negative_besties,
        mutate_not_a_number,
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

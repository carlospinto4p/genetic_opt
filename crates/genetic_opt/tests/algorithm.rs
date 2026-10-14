use std::collections::{BTreeSet, HashSet};
use std::fs::{File, read_dir};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::thread::available_parallelism;

use genetic_opt::examples::Knapsack;
use genetic_opt::{
    Error, FitConfig, GeneticAlgorithm, Problem, Rng, SaveConfig, SaveFormat, Score,
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
}

fn numbers(minimize: bool) -> Numbers {
    Numbers {
        minimize,
        keep_mutations: true,
    }
}

#[test]
fn knapsack_finds_the_best_bag() {
    let mut algorithm = GeneticAlgorithm::new(knapsack(), FitConfig::new(100, 50));
    let result = algorithm.fit().unwrap();

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
    let mut algorithm = GeneticAlgorithm::new(problem, config);
    let result = algorithm.fit().unwrap();

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
    let mut algorithm = GeneticAlgorithm::new(knapsack(), FitConfig::new(5, 50));
    let result = algorithm.fit().unwrap();

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

#[test]
fn a_seed_gives_the_same_run_with_any_number_of_threads() {
    let run = |n_jobs| {
        let mut config = FitConfig::new(10, 30);
        config.n_jobs = Some(n_jobs);
        config.random_seed = 7;
        let mut algorithm = GeneticAlgorithm::new(knapsack(), config);
        algorithm.fit().unwrap();
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
    assert_eq!(run(1), run(two_jobs()));
}

#[test]
fn the_population_keeps_its_size_and_is_sorted_best_first() {
    let mut config = FitConfig::new(4, 30);
    config.stop_without_improvement = false;
    let mut algorithm = GeneticAlgorithm::new(knapsack(), config);
    let result = algorithm.fit().unwrap();

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
fn a_second_fit_is_the_same_run_again() {
    let mut config = FitConfig::new(4, 30);
    config.stop_without_improvement = false;
    let mut algorithm = GeneticAlgorithm::new(knapsack(), config);
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
    let first = algorithm.fit().unwrap();
    let first_genes = genes(&algorithm);
    let second = algorithm.fit().unwrap();

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
    let mut algorithm = GeneticAlgorithm::new(numbers(false), FitConfig::new(60, 30));
    let result = algorithm.fit().unwrap();

    assert!(result.metrics.len() > 1);
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
    let mut algorithm = GeneticAlgorithm::new(numbers(true), FitConfig::new(60, 30));
    let result = algorithm.fit().unwrap();

    assert!(result.metrics.len() > 1);
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
fn on_generation_can_stop_the_run() {
    let mut config = FitConfig::new(50, 30);
    config.stop_without_improvement = false;
    let mut algorithm = GeneticAlgorithm::new(knapsack(), config);
    let result = algorithm
        .fit_with(|algorithm| algorithm.history().len() == 3)
        .unwrap();

    assert_eq!(result.metrics.len(), 3);
}

#[test]
fn a_broken_invariant_stops_the_run() {
    let problem = Numbers {
        minimize: false,
        keep_mutations: false,
    };
    let mut algorithm = GeneticAlgorithm::new(problem, FitConfig::new(5, 30));

    assert!(matches!(algorithm.fit(), Err(Error::Invariant(_))));
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
        let mut algorithm = GeneticAlgorithm::new(knapsack(), config);
        assert!(matches!(algorithm.fit(), Err(Error::Validation(_))));
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

#[test]
fn a_run_is_saved_one_file_per_generation() {
    for (format, extension) in [(SaveFormat::Json, "json"), (SaveFormat::Bson, "bson")] {
        let folder = tempfile::tempdir().unwrap();
        let mut config = FitConfig::new(3, 20);
        config.stop_without_improvement = false;
        config.extra_config = Some(serde_json::json!({"note": "test"}));
        config.save = Some(SaveConfig {
            path: folder.path().to_path_buf(),
            experiment_name: "bag".into(),
            format,
        });
        let mut algorithm = GeneticAlgorithm::new(knapsack(), config);
        let result = algorithm.fit().unwrap();

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
        let saved: serde_json::Value = match format {
            SaveFormat::Json => serde_json::from_reader(last).unwrap(),
            SaveFormat::Bson => {
                serde_json::to_value(bson::Document::from_reader(last).unwrap()).unwrap()
            }
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
        assert_eq!(saved["last_population"].as_array().unwrap().len(), 20);
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

fn saving_config(path: &std::path::Path, experiment_name: &str) -> FitConfig {
    let mut config = FitConfig::new(1, 20);
    config.save = Some(SaveConfig {
        path: path.to_path_buf(),
        experiment_name: experiment_name.into(),
        format: SaveFormat::Json,
    });
    config
}

#[test]
fn two_runs_with_one_name_get_a_folder_each() {
    let folder = tempfile::tempdir().unwrap();
    // More runs than fit in the second a folder is named after.
    let run_folders: HashSet<_> = (0..5)
        .map(|_| {
            let config = saving_config(folder.path(), "bag");
            let result = GeneticAlgorithm::new(knapsack(), config).fit().unwrap();
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
fn an_experiment_name_outside_the_save_path_is_refused() {
    let folder = tempfile::tempdir().unwrap();
    let save_path = folder.path().join("runs");
    let absolute = folder.path().join("elsewhere");

    for experiment_name in ["../elsewhere", "bag/../..", absolute.to_str().unwrap(), ""] {
        let config = saving_config(&save_path, experiment_name);
        let mut algorithm = GeneticAlgorithm::new(knapsack(), config);
        assert!(matches!(algorithm.fit(), Err(Error::Validation(_))));
    }
    assert!(!save_path.exists());
    assert!(!absolute.exists());
}

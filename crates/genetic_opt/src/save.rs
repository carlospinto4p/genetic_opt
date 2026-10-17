use std::fs::{File, create_dir, create_dir_all};
use std::io::{BufWriter, ErrorKind, Write};
use std::path::{Component, Path, PathBuf};

use serde::Serialize;

use crate::{Error, FitMetrics, FitParameters, Individual, Metric, Result, Score};

/// Where and how a [`GeneticAlgorithm`](crate::GeneticAlgorithm) saves
/// its runs. The files of a run go to
/// `<path>/<experiment_name>/<UTC date and time of the start>/`, with
/// `_2`, `_3` and so on added to the last folder when it exists.
#[derive(Clone, Debug)]
pub struct SaveConfig {
    pub path: PathBuf,
    /// Whether each generation is saved as a BSON file instead of a
    /// JSON one.
    pub as_bson: bool,
}

/// Create the folder of a run of `experiment_name` that starts now, and
/// return it.
pub(crate) fn create_run_folder(save: &SaveConfig, experiment_name: &str) -> Result<PathBuf> {
    let name = Path::new(experiment_name);
    let inside = name
        .components()
        .all(|part| matches!(part, Component::Normal(_) | Component::CurDir));
    if experiment_name.is_empty() || !inside {
        return Err(Error::Validation(format!(
            "experiment_name is {experiment_name:?}, and it must be a path inside the save path"
        )));
    }
    let experiment = save.path.join(name);
    create_dir_all(&experiment)?;
    let now = chrono::Utc::now().format("%Y%m%d_%H%M%S").to_string();
    let mut folder = experiment.join(&now);
    let mut attempt = 1;
    // `create_dir` fails on a folder that exists, so two runs started in
    // the same second do not share one.
    loop {
        match create_dir(&folder) {
            Ok(()) => return Ok(folder),
            Err(error) if error.kind() == ErrorKind::AlreadyExists => {
                attempt += 1;
                folder = experiment.join(format!("{now}_{attempt}"));
            }
            Err(error) => return Err(error.into()),
        }
    }
}

#[derive(Serialize)]
struct ExperimentConfig<'a> {
    fit_parameters: &'a FitParameters,
    #[serde(skip_serializing_if = "Option::is_none")]
    experiment_config: Option<serde_json::Value>,
}

/// One file of `fit_data/`, as the Python
/// `fit_result_io.load_fit_result_file` reads it. It does not hold the
/// population decoded: the Python loader decodes `population` instead.
#[derive(Serialize)]
pub(crate) struct GenerationFile<'a, G: Serialize, S: Serialize> {
    pub bests: BestsColumns<'a, G, S>,
    pub fit_metrics: &'a FitMetrics,
    /// The metrics of this generation alone, as a list of one.
    pub metrics: &'a [Metric<G, S>],
    pub fit_parameters: &'a FitParameters,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub config: Option<&'a serde_json::Value>,
    /// Number of the generation, starting at 1.
    pub population_idx: usize,
    pub population: Vec<(&'a Score, &'a Individual<G>)>,
}

#[derive(Serialize)]
pub(crate) struct BestsColumns<'a, G: Serialize, S: Serialize> {
    pub scores: Vec<&'a Score>,
    pub result: Vec<&'a S>,
    pub encoded: Vec<&'a Individual<G>>,
}

pub(crate) fn write_experiment_config(
    folder: &Path,
    fit_parameters: &FitParameters,
    experiment_config: Option<serde_json::Value>,
) -> Result<()> {
    let file = File::create(folder.join("experiment_config.yml"))?;
    let config = ExperimentConfig {
        fit_parameters,
        experiment_config,
    };
    let mut writer = BufWriter::new(file);
    serde_norway::to_writer(&mut writer, &config)?;
    // Dropping a `BufWriter` writes out its buffer but drops the error.
    Ok(writer.flush()?)
}

pub(crate) fn write_generation<G: Serialize, S: Serialize>(
    folder: &Path,
    as_bson: bool,
    generation: &GenerationFile<G, S>,
) -> Result<()> {
    let folder = folder.join("fit_data");
    create_dir_all(&folder)?;
    let name = format!("fit_data_{}", generation.population_idx);
    if as_bson {
        let file = File::create(folder.join(format!("{name}.bson")))?;
        let mut writer = BufWriter::new(file);
        bson::serialize_to_document(generation)?.to_writer(&mut writer)?;
        Ok(writer.flush()?)
    } else {
        let file = File::create(folder.join(format!("{name}.json")))?;
        let mut writer = BufWriter::new(file);
        serde_json::to_writer(&mut writer, generation)?;
        Ok(writer.flush()?)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{FitnessFuncCalls, TotalFitTime};

    // `/dev/full` opens, but refuses every write. The files here are
    // smaller than the buffer, so the write fails only when the buffer is
    // written out at the end.
    #[cfg(target_os = "linux")]
    #[test]
    fn a_failed_write_is_returned() {
        use std::os::unix::fs::symlink;

        let folder = tempfile::tempdir().unwrap();
        let folder = folder.path();
        create_dir_all(folder.join("fit_data")).unwrap();
        for name in [
            "experiment_config.yml",
            "fit_data/fit_data_1.json",
            "fit_data/fit_data_1.bson",
        ] {
            symlink("/dev/full", folder.join(name)).unwrap();
        }
        let fit_parameters = FitParameters {
            n_generations: 1,
            population_size: 1,
            crossovers_prop: 0.7,
            besties_prop: 0.6,
            mutate_prob: 0.05,
            min_population_size: 1,
            random_seed: 442,
            n_jobs: 1,
        };
        let fit_metrics = FitMetrics {
            fitness_func_calls: FitnessFuncCalls {
                total: 0,
                processed: 0,
                percent_processed: 0.0,
                cached: 0,
                space_points: 1.0,
                exploration_percentage: 0.0,
            },
            total_fit_time: TotalFitTime {
                n_jobs: 1,
                raw: 0.0,
                formatted: String::new(),
            },
            genetic_opt_version: String::new(),
        };
        let generation = GenerationFile::<u8, u8> {
            bests: BestsColumns {
                scores: Vec::new(),
                result: Vec::new(),
                encoded: Vec::new(),
            },
            fit_metrics: &fit_metrics,
            metrics: &[],
            fit_parameters: &fit_parameters,
            config: None,
            population_idx: 1,
            population: Vec::new(),
        };

        assert!(write_experiment_config(folder, &fit_parameters, None).is_err());
        for as_bson in [false, true] {
            assert!(
                write_generation(folder, as_bson, &generation).is_err(),
                "as_bson: {as_bson}"
            );
        }
    }
}

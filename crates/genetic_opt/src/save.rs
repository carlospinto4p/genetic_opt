use std::fs::{File, create_dir, create_dir_all};
use std::io::{BufWriter, ErrorKind};
use std::path::{Component, Path, PathBuf};

use serde::Serialize;

use crate::{Error, FitMetrics, FitParameters, Individual, Metric, Result, Score};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SaveFormat {
    Bson,
    Json,
}

/// Where to save a run. Its files go to
/// `<path>/<experiment_name>/<UTC date and time of the start>/`, with
/// `_2`, `_3` and so on added to the last folder when it exists.
#[derive(Clone, Debug)]
pub struct SaveConfig {
    pub path: PathBuf,
    /// A path inside `path`: not an absolute one, and without `..`.
    pub experiment_name: String,
    pub format: SaveFormat,
}

/// Create the folder of a run that starts now, and return it.
pub(crate) fn create_run_folder(save: &SaveConfig) -> Result<PathBuf> {
    let name = Path::new(&save.experiment_name);
    let inside = name
        .components()
        .all(|part| matches!(part, Component::Normal(_) | Component::CurDir));
    if save.experiment_name.is_empty() || !inside {
        return Err(Error::Validation(format!(
            "experiment_name is {:?}, and it must be a path inside the save path",
            save.experiment_name
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
/// `fit_result_io.load_fit_result_file` reads it.
#[derive(Serialize)]
pub(crate) struct GenerationFile<'a, G: Serialize, S: Serialize> {
    pub bests: BestsColumns<'a, G, S>,
    /// Pairs of a decoded chromosome and its score.
    pub last_population: Vec<(S, &'a Score)>,
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
    Ok(serde_norway::to_writer(BufWriter::new(file), &config)?)
}

pub(crate) fn write_generation<G: Serialize, S: Serialize>(
    folder: &Path,
    format: SaveFormat,
    generation: &GenerationFile<G, S>,
) -> Result<()> {
    let folder = folder.join("fit_data");
    create_dir_all(&folder)?;
    let name = format!("fit_data_{}", generation.population_idx);
    match format {
        SaveFormat::Json => {
            let file = File::create(folder.join(format!("{name}.json")))?;
            Ok(serde_json::to_writer(BufWriter::new(file), generation)?)
        }
        SaveFormat::Bson => {
            let file = File::create(folder.join(format!("{name}.bson")))?;
            Ok(bson::serialize_to_document(generation)?.to_writer(BufWriter::new(file))?)
        }
    }
}

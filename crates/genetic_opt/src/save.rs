use std::fs::{File, create_dir_all};
use std::io::BufWriter;
use std::path::{Path, PathBuf};

use serde::Serialize;

use crate::{Error, FitMetrics, FitParameters, Individual, Metric, Result, Score};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SaveFormat {
    Bson,
    Json,
}

/// Where to save a run. Its files go to
/// `<path>/<experiment_name>/<UTC date and time of the start>/`.
#[derive(Clone, Debug)]
pub struct SaveConfig {
    pub path: PathBuf,
    pub experiment_name: String,
    pub format: SaveFormat,
}

#[derive(Serialize)]
struct ExperimentConfig<'a> {
    fit_parameters: &'a FitParameters,
    #[serde(skip_serializing_if = "Option::is_none")]
    experiment_config: Option<serde_json::Value>,
}

/// One file of `fit_data/`, as the Python `utils.load_fit_result_file`
/// reads it.
#[derive(Serialize)]
pub(crate) struct GenerationFile<'a, G: Serialize, S: Serialize> {
    pub bests: BestsColumns<'a, G, S>,
    /// Pairs of a decoded chromosome and its score.
    pub last_population: Vec<(S, &'a Score)>,
    pub fit_metrics: &'a FitMetrics,
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
    create_dir_all(folder)?;
    let file = File::create(folder.join("experiment_config.yml"))?;
    let config = ExperimentConfig {
        fit_parameters,
        experiment_config,
    };
    serde_norway::to_writer(BufWriter::new(file), &config)
        .map_err(|e| Error::Serialization(e.to_string()))
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
            serde_json::to_writer(BufWriter::new(file), generation)
                .map_err(|e| Error::Serialization(e.to_string()))
        }
        SaveFormat::Bson => {
            let file = File::create(folder.join(format!("{name}.bson")))?;
            bson::serialize_to_document(generation)
                .and_then(|document| document.to_writer(BufWriter::new(file)))
                .map_err(|e| Error::Serialization(e.to_string()))
        }
    }
}

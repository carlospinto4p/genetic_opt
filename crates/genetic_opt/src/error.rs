use thiserror::Error;

#[derive(Debug, Error)]
pub enum Error {
    /// A parameter of the run or of the problem is not valid.
    #[error("validation: {0}")]
    Validation(String),
    /// A crossover or a mutation broke an invariant of the problem.
    #[error("invariant: {0}")]
    Invariant(String),
    /// The threads that score chromosomes could not be started.
    #[error("thread pool: {0}")]
    ThreadPool(#[from] rayon::ThreadPoolBuildError),
    #[error(transparent)]
    Io(#[from] std::io::Error),
    /// A generation could not be written as JSON.
    #[error("JSON: {0}")]
    Json(#[from] serde_json::Error),
    /// The experiment configuration could not be written as YAML.
    #[error("YAML: {0}")]
    Yaml(#[from] serde_norway::Error),
    /// A generation could not be written as BSON.
    #[error("BSON: {0}")]
    Bson(#[from] bson::error::Error),
}

pub type Result<T> = std::result::Result<T, Error>;

use thiserror::Error;

#[derive(Debug, Error)]
pub enum Error {
    /// A parameter of the run or of the problem is not valid.
    #[error("validation: {0}")]
    Validation(String),
    /// A crossover or a mutation broke an invariant of the problem.
    #[error("invariant: {0}")]
    Invariant(String),
    #[error(transparent)]
    Io(#[from] std::io::Error),
    #[error("serialization: {0}")]
    Serialization(String),
}

pub type Result<T> = std::result::Result<T, Error>;

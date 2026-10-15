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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn each_error_names_its_kind() {
        let io = std::io::Error::new(std::io::ErrorKind::NotFound, "no folder");
        let json = serde_json::from_str::<u8>("[").unwrap_err();
        let yaml = serde_norway::from_str::<u8>("[").unwrap_err();
        let bson = bson::Document::from_reader(&[][..]).unwrap_err();
        let errors = [
            (Error::Validation("x is 0".into()), "validation: x is 0"),
            (
                Error::Invariant("a mutation".into()),
                "invariant: a mutation",
            ),
            (Error::from(io), "no folder"),
            (Error::from(json), "JSON: "),
            (Error::from(yaml), "YAML: "),
            (Error::from(bson), "BSON: "),
        ];
        for (error, text) in errors {
            assert!(error.to_string().starts_with(text), "{error}");
        }
    }
}

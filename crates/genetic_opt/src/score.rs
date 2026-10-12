use serde::Serialize;

/// The value a fitness function gives to a chromosome.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Score {
    pub value: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub extra_metrics: Option<serde_json::Value>,
}

impl Score {
    pub fn new(value: f64) -> Self {
        Self {
            value,
            name: None,
            extra_metrics: None,
        }
    }
}

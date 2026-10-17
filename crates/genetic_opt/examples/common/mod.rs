//! What the examples share: their command line, and what they print.
//!
//! Cargo builds `examples/*.rs` as examples, so this folder is a module
//! each of them includes, not an example of its own.

use std::env::args;
use std::fmt::Debug;

use genetic_opt::{FitResult, SaveConfig};

/// The save settings from the command line, `[folder] [json|bson]`: the
/// run is saved in `folder`, as BSON unless `json` is given, and not
/// saved without a folder.
pub fn save_config() -> Result<Option<SaveConfig>, String> {
    let mut args = args().skip(1);
    let Some(folder) = args.next() else {
        return Ok(None);
    };
    let as_bson = match args.next().as_deref() {
        None | Some("bson") => true,
        Some("json") => false,
        Some(other) => return Err(format!("unknown format `{other}`: use json or bson")),
    };
    Ok(Some(SaveConfig {
        path: folder.into(),
        as_bson,
    }))
}

/// Print the best score and what it stands for, under the names given,
/// the number of generations, and the folder the run was saved in.
pub fn print_run<G, S: Debug>(result: &FitResult<G, S>, score_name: &str, result_name: &str) {
    let best = &result.bests[0];
    println!("best {score_name}: {}", best.score.value);
    println!("best {result_name}: {:?}", best.result);
    println!("generations: {}", result.metrics.len());
    if let Some(folder) = &result.save_folder {
        println!("saved in: {}", folder.display());
    }
}

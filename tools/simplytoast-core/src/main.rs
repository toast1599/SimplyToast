use std::collections::HashMap;
use std::env;
use std::error::Error;
use std::io::{self, Read};

use serde::{Deserialize, Serialize};

//
// -------- Input structs --------
//

#[derive(Debug, Deserialize)]
struct ProcGroup {
    cpu: f64,
    mem: f64,
    count: u32,
}

#[derive(Debug, Deserialize)]
struct AutostartEntry {
    id: String,
    exec: String,
}

#[derive(Debug, Deserialize)]
struct Input {
    process_groups: HashMap<String, ProcGroup>,
    autostart: Vec<AutostartEntry>,
}

//
// -------- Output structs --------
//

#[derive(Debug, Serialize)]
struct ImpactResult {
    impact: f64,
    ratio: f64,
    label: String,
    color: String,
    sort_key: u8,
}

//
// -------- Logic --------
//

fn compute_impact(pg: &ProcGroup) -> f64 {
    pg.cpu * 2.0
        + pg.mem * 1.0
        + (pg.count.min(5) as f64) * 1.5
}

//
// -------- Commands --------
//

fn run_impact() -> Result<(), Box<dyn Error>> {
    // Read JSON from stdin
    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;
    let input: Input = serde_json::from_str(&input)?;

    let mut raw_impacts: HashMap<String, f64> = HashMap::new();
    let mut max_impact = 0.0;

    // Compute raw impact per autostart entry
    for entry in &input.autostart {
        let exe = entry
            .exec
            .split_whitespace()
            .next()
            .unwrap_or("")
            .rsplit('/')
            .next()
            .unwrap_or("");

        let impact = input
            .process_groups
            .get(exe)
            .map(compute_impact)
            .unwrap_or(0.0);

        raw_impacts.insert(entry.id.clone(), impact);
        if impact > max_impact {
            max_impact = impact;
        }
    }

    // Normalize + classify
    let mut output: HashMap<String, ImpactResult> = HashMap::new();

    for (id, impact) in raw_impacts {
        let (ratio, label, color, sort_key) = if max_impact <= 0.0 {
            (0.0, "None".to_string(), "gray".to_string(), 3)
        } else {
            let ratio = impact / max_impact;
            if ratio >= 0.7 {
                (ratio, "High".to_string(), "red".to_string(), 0)
            } else if ratio >= 0.3 {
                (ratio, "Medium".to_string(), "orange".to_string(), 1)
            } else if ratio > 0.0 {
                (ratio, "Low".to_string(), "green".to_string(), 2)
            } else {
                (0.0, "None".to_string(), "gray".to_string(), 3)
            }
        };

        output.insert(
            id,
            ImpactResult {
                impact,
                ratio,
                label,
                color,
                sort_key,
            },
        );
    }

    // Write JSON to stdout
    println!("{}", serde_json::to_string(&output)?);

    Ok(())
}

//
// -------- Main --------
//

fn main() -> Result<(), Box<dyn Error>> {
    let cmd = env::args().nth(1).unwrap_or_default();

    match cmd.as_str() {
        "impact" => run_impact()?,
        _ => {
            eprintln!("usage: simplytoast-core impact");
            std::process::exit(1);
        }
    }

    Ok(())
}

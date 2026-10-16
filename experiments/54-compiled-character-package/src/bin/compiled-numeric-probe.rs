//! Experimental signed target/helper/proxy package execution. No Blender invocation.
#[path = "../fit.rs"]
mod fit;
#[path = "../signed.rs"]
mod signed;
use serde::Deserialize;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    collections::{BTreeMap, BTreeSet},
    fs,
    io::Write,
    path::Path,
};
fn sha(b: &[u8]) -> String {
    format!("{:x}", Sha256::digest(b))
}
fn read(p: &Path) -> Result<Vec<u8>, String> {
    if fs::metadata(p).map_err(|e| e.to_string())?.len() > 32 * 1024 * 1024 {
        return Err("compiled input exceeds 32 MiB".into());
    }
    fs::read(p).map_err(|e| e.to_string())
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Package {
    schema_version: u32,
    sample_class: String,
    source_manifest_path: String,
    source_manifest_sha256: String,
    source_package_revision: String,
    compiler_provenance: Value,
    coordinate_convention: String,
    transform_identity: Value,
    bodies: Vec<Body>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Body {
    topology_id: String,
    node: String,
    mesh: String,
    primitive: String,
    positions: Vec<[f64; 3]>,
    signed_pairs: Vec<signed::SignedPair>,
    helper_rules: Vec<fit::MeanPoint>,
    bone_rules: Vec<fit::Bone>,
    garment_rules: Vec<fit::Garment>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Recipe {
    schema_version: u32,
    case_id: String,
    package_sha256: String,
    source_manifest_sha256: String,
    values: BTreeMap<String, f64>,
}
fn evaluate(package_path: &Path, recipe_path: &Path, command: &[String]) -> Result<Value, String> {
    let bytes = read(package_path)?;
    let p: Package = serde_json::from_slice(&bytes).map_err(|e| e.to_string())?;
    if p.schema_version != 2
        || ![
            "handwritten-numeric-control",
            "makehuman-approved-sample",
            "makehuman-approved-core-control",
        ]
        .contains(&p.sample_class.as_str())
        || p.coordinate_convention.is_empty()
        || p.source_package_revision.is_empty()
        || p.bodies.is_empty()
    {
        return Err("unsupported/incomplete compiled numeric package".into());
    }
    let manifest = read(
        &package_path
            .parent()
            .unwrap_or(Path::new("."))
            .join(&p.source_manifest_path),
    )?;
    if sha(&manifest) != p.source_manifest_sha256 {
        return Err("common source manifest hash mismatch".into());
    }
    let manifest_json: Value = serde_json::from_slice(&manifest).map_err(|e| e.to_string())?;
    if !(manifest_json["sample_class"] == p.sample_class
        || (p.sample_class == "makehuman-approved-core-control"
            && manifest_json["status"] == "core_smoke_passed"))
    {
        return Err("common manifest sample class mismatch".into());
    }
    let recipe_bytes = read(recipe_path)?;
    let r: Recipe = serde_json::from_slice(&recipe_bytes).map_err(|e| e.to_string())?;
    if r.schema_version != 2
        || r.case_id.is_empty()
        || r.package_sha256 != sha(&bytes)
        || r.source_manifest_sha256 != p.source_manifest_sha256
    {
        return Err("compiled recipe package/manifest identity mismatch".into());
    }
    let mut ids = BTreeSet::new();
    let mut output = Vec::new();
    for b in p.bodies {
        if b.topology_id.is_empty()
            || b.node.is_empty()
            || b.mesh.is_empty()
            || b.primitive.is_empty()
            || !ids.insert((b.node.clone(), b.mesh.clone(), b.primitive.clone()))
        {
            return Err("ambiguous/duplicate compiled node/mesh/primitive".into());
        }
        let positions = signed::evaluate(&b.positions, &b.signed_pairs, &r.values)?;
        let points = fit::mean_points(&positions, &b.helper_rules)?;
        let bones = fit::bones(&points, &b.bone_rules)?;
        let mut garments = BTreeMap::new();
        for g in &b.garment_rules {
            if garments
                .insert(g.id.clone(), fit::garment(&positions, g)?)
                .is_some()
            {
                return Err("duplicate compiled garment id".into());
            }
        }
        let mut packed = Vec::with_capacity(positions.len() * 24);
        for p in &positions {
            for v in p {
                packed.extend_from_slice(&v.to_le_bytes());
            }
        }
        output.push(json!({"topology_id":b.topology_id,"node":b.node,"mesh":b.mesh,"primitive":b.primitive,"vertex_count":positions.len(),"positions_f64le_sha256":sha(&packed),"positions":positions,"helper_points":points,"bones":bones,"garments":garments,"inverse_bind_matrices":null}));
    }
    Ok(
        json!({"schema_version":2,"route_id":"compiled-package","sample_class":p.sample_class,"case_id":r.case_id,"source_input_manifest_sha256":p.source_manifest_sha256,"package_sha256":sha(&bytes),"source_package_revision":p.source_package_revision,"compiler_provenance":p.compiler_provenance,"tool_version":env!("CARGO_PKG_VERSION"),"status":"passed","command":command,"exit_code":0,"artifact_paths":[command[3]],"log_paths":[],"actual_candidate_code_run":true,"native_graphical_execution_run":false,"web_graphical_execution_run":false,"reference_pipeline_run":false,"coordinate_convention":p.coordinate_convention,"transform_identity":p.transform_identity,"recipe":r.values,"bodies":output,"unsupported_fields":["bone rest matrices/inverse binds","skin weights and posed deformation","native/Web rendering and Work exchange"]}),
    )
}
fn run() -> Result<(), String> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 4 {
        return Err(
            "usage: compiled-numeric-probe PACKAGE.json RECIPE.json NEW-RESULT.json".into(),
        );
    }
    let result = evaluate(Path::new(&args[1]), Path::new(&args[2]), &args)?;
    let bytes = serde_json::to_vec(&result).map_err(|e| e.to_string())?;
    let mut file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&args[3])
        .map_err(|e| e.to_string())?;
    if let Err(e) = file.write_all(&bytes).and_then(|_| file.sync_all()) {
        drop(file);
        let _ = fs::remove_file(&args[3]);
        return Err(e.to_string());
    }
    println!(
        "{}",
        json!({"status":"passed","output":args[3],"sha256":sha(&bytes)})
    );
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("{}", json!({"status":"failed","error":e}));
        std::process::exit(2)
    }
}

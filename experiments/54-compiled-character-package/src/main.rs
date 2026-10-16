//! Bounded experimental POSITION evaluator. Does not render, skin or adapt a rig.
use serde::Deserialize;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    collections::{BTreeMap, BTreeSet},
    fs,
    io::Write,
    path::{Path, PathBuf},
};
type Result<T> = std::result::Result<T, String>;
fn hash(b: &[u8]) -> String {
    format!("{:x}", Sha256::digest(b))
}
fn read(p: &Path) -> Result<Vec<u8>> {
    if fs::metadata(p).map_err(|e| e.to_string())?.len() > 32 * 1024 * 1024 {
        return Err("input exceeds 32 MiB".into());
    }
    fs::read(p).map_err(|e| e.to_string())
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Package {
    schema_version: u32,
    sample_class: String,
    source_manifest_sha256: String,
    source_manifest_path: String,
    source_package_revision: String,
    asset_path: String,
    asset_sha256: String,
    profile_path: String,
    profile_sha256: String,
    profile_id: String,
    coordinate_convention: String,
    transform_policy: String,
    bindings: Vec<Binding>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Binding {
    parameter_id: String,
    node: usize,
    mesh: usize,
    primitive: usize,
    target: usize,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Recipe {
    schema_version: u32,
    profile_id: String,
    profile_sha256: String,
    case_id: String,
    values: BTreeMap<String, f64>,
}
#[derive(Deserialize)]
struct Profile {
    id: String,
    asset_sha256: String,
    parameters: Vec<Parameter>,
}
#[derive(Deserialize)]
struct Parameter {
    id: String,
    morph_index: usize,
    min: f64,
    max: f64,
    default: f64,
}
fn num(v: &Value, key: &str) -> Result<usize> {
    v[key]
        .as_u64()
        .and_then(|n| usize::try_from(n).ok())
        .ok_or_else(|| format!("missing/invalid integer {key}"))
}
fn indexed<'a>(v: &'a Value, key: &str, i: usize) -> Result<&'a Value> {
    v[key]
        .as_array()
        .and_then(|a| a.get(i))
        .ok_or_else(|| format!("missing {key}[{i}]"))
}
fn u32_at(b: &[u8], i: usize) -> Result<u32> {
    let bytes = b.get(i..i + 4).ok_or("truncated u32")?;
    Ok(u32::from_le_bytes(bytes.try_into().unwrap()))
}
struct Glb {
    json: Value,
    bin: Vec<u8>,
}
impl Glb {
    fn parse(b: &[u8]) -> Result<Self> {
        if b.get(..4) != Some(b"glTF") || u32_at(b, 4)? != 2 || u32_at(b, 8)? as usize != b.len() {
            return Err("invalid GLB header".into());
        }
        let n = u32_at(b, 12)? as usize;
        if u32_at(b, 16)? != 0x4e4f534a {
            return Err("missing JSON chunk".into());
        }
        let end = 20usize.checked_add(n).ok_or("JSON overflow")?;
        let json: Value = serde_json::from_slice(b.get(20..end).ok_or("truncated JSON")?)
            .map_err(|e| e.to_string())?;
        if json["asset"]["version"] != "2.0"
            || json
                .get("extensionsRequired")
                .is_some_and(|x| x.as_array().is_none_or(|a| !a.is_empty()))
        {
            return Err("unsupported asset version/required extensions".into());
        }
        let bn = u32_at(b, end)? as usize;
        if u32_at(b, end + 4)? != 0x004e4942 || end + 8 + bn != b.len() {
            return Err("unsupported GLB chunk layout".into());
        }
        let buffers = json["buffers"].as_array().ok_or("missing buffers")?;
        if buffers.len() != 1
            || buffers[0].get("uri").is_some()
            || num(&buffers[0], "byteLength")? > bn
        {
            return Err("only embedded buffer 0 supported".into());
        }
        Ok(Self {
            json,
            bin: b[end + 8..].to_vec(),
        })
    }
    fn floats(&self, index: usize, kind: &str, columns: usize) -> Result<Vec<Vec<f64>>> {
        let a = indexed(&self.json, "accessors", index)?;
        if a["componentType"] != 5126
            || a["type"] != kind
            || a.get("sparse").is_some()
            || a.get("normalized").is_some_and(|v| v != false)
        {
            return Err(format!("unsupported float accessor {index}"));
        }
        let v = indexed(&self.json, "bufferViews", num(a, "bufferView")?)?;
        if num(v, "buffer")? != 0 {
            return Err("external buffer unsupported".into());
        }
        let offset = v
            .get("byteOffset")
            .map(|_| num(v, "byteOffset"))
            .transpose()?
            .unwrap_or(0);
        let local = a
            .get("byteOffset")
            .map(|_| num(a, "byteOffset"))
            .transpose()?
            .unwrap_or(0);
        let width = columns * 4;
        let stride = v
            .get("byteStride")
            .map(|_| num(v, "byteStride"))
            .transpose()?
            .unwrap_or(width);
        if stride < width || stride % 4 != 0 || local % 4 != 0 || offset % 4 != 0 {
            return Err("invalid stride/alignment".into());
        }
        let count = num(a, "count")?;
        if count == 0 || count > 1_000_000 {
            return Err("invalid accessor count".into());
        }
        let length = (count - 1)
            .checked_mul(stride)
            .and_then(|n| n.checked_add(width))
            .ok_or("accessor overflow")?;
        let range_end = local.checked_add(length).ok_or("range overflow")?;
        if range_end > num(v, "byteLength")? {
            return Err("accessor outside bufferView".into());
        }
        let start = offset.checked_add(local).ok_or("offset overflow")?;
        if start.checked_add(length).ok_or("offset overflow")? > self.bin.len() {
            return Err("accessor outside BIN".into());
        }
        for key in ["min", "max"] {
            if let Some(bounds) = a.get(key) {
                let bounds = bounds.as_array().ok_or("invalid bounds")?;
                if bounds.len() != columns
                    || bounds
                        .iter()
                        .any(|x| x.as_f64().is_none_or(|n| !n.is_finite()))
                {
                    return Err("non-finite/invalid accessor bounds".into());
                }
            }
        }
        if let (Some(min), Some(max)) = (a["min"].as_array(), a["max"].as_array()) {
            if min
                .iter()
                .zip(max)
                .any(|(a, b)| a.as_f64().unwrap() > b.as_f64().unwrap())
            {
                return Err("inverted accessor bounds".into());
            }
        }
        let mut rows = Vec::with_capacity(count);
        for i in 0..count {
            let mut row = Vec::with_capacity(columns);
            for c in 0..columns {
                let p = start + i * stride + c * 4;
                let f = f32::from_le_bytes(self.bin[p..p + 4].try_into().unwrap()) as f64;
                if !f.is_finite() {
                    return Err("non-finite accessor value".into());
                }
                row.push(f);
            }
            rows.push(row);
        }
        Ok(rows)
    }
}
fn evaluate(package_path: &Path, recipe_path: &Path, command: &[String]) -> Result<Value> {
    let package_bytes = read(package_path)?;
    let p: Package = serde_json::from_slice(&package_bytes).map_err(|e| e.to_string())?;
    if p.schema_version != 1 || p.sample_class != "nvwa-existing-fixture-control" {
        return Err(
            "only existing-fixture preparation supported; approved MakeHuman sample NOT-RUN".into(),
        );
    }
    if p.transform_policy != "preserve-node-local-no-world-transform-no-skinning"
        || p.coordinate_convention != "glTF-local-right-handed-Y-up-meters"
    {
        return Err("unsupported coordinate/transform policy".into());
    }
    let root = package_path.parent().unwrap_or(Path::new("."));
    let manifest = read(&root.join(&p.source_manifest_path))?;
    if hash(&manifest) != p.source_manifest_sha256 {
        return Err("source manifest hash mismatch".into());
    }
    let asset = read(&root.join(&p.asset_path))?;
    let profile_bytes = read(&root.join(&p.profile_path))?;
    if hash(&asset) != p.asset_sha256 || hash(&profile_bytes) != p.profile_sha256 {
        return Err("asset/profile hash mismatch".into());
    }
    let manifest_json: Value = serde_json::from_slice(&manifest).map_err(|e| e.to_string())?;
    if manifest_json["sample_class"] != p.sample_class
        || manifest_json["asset_sha256"] != p.asset_sha256
        || manifest_json["profile_sha256"] != p.profile_sha256
    {
        return Err("manifest input identity mismatch".into());
    }
    let profile: Profile = serde_json::from_slice(&profile_bytes).map_err(|e| e.to_string())?;
    if profile.id != p.profile_id || profile.asset_sha256 != p.asset_sha256 {
        return Err("profile identity mismatch".into());
    }
    let r: Recipe = serde_json::from_slice(&read(recipe_path)?).map_err(|e| e.to_string())?;
    if r.schema_version != 1
        || r.profile_id != p.profile_id
        || r.profile_sha256 != p.profile_sha256
        || r.case_id.is_empty()
    {
        return Err("recipe profile/schema mismatch".into());
    }
    let mut specs = BTreeMap::new();
    let mut indices = BTreeSet::new();
    for s in &profile.parameters {
        if s.id.is_empty()
            || !s.min.is_finite()
            || !s.max.is_finite()
            || !s.default.is_finite()
            || s.min > s.max
            || !(s.min..=s.max).contains(&s.default)
            || specs.insert(s.id.as_str(), s).is_some()
            || !indices.insert(s.morph_index)
        {
            return Err("invalid/duplicate parameter bounds or target".into());
        }
    }
    if r.values.len() != specs.len()
        || r.values.iter().any(|(id, v)| {
            !v.is_finite()
                || specs
                    .get(id.as_str())
                    .is_none_or(|s| !(s.min..=s.max).contains(v))
        })
    {
        return Err("recipe missing/unknown/out-of-range/non-finite parameter".into());
    }
    let g = Glb::parse(&asset)?;
    let nodes = g.json["nodes"].as_array().ok_or("missing nodes")?;
    let mut binding_keys = BTreeSet::new();
    let mut covered = BTreeSet::new();
    for b in &p.bindings {
        let spec = specs
            .get(b.parameter_id.as_str())
            .ok_or("unknown binding parameter")?;
        if b.target != spec.morph_index
            || !binding_keys.insert((b.node, b.mesh, b.primitive, b.target))
        {
            return Err("duplicate/conflicting binding".into());
        }
        let n = nodes.get(b.node).ok_or("binding node absent")?;
        if num(n, "mesh")? != b.mesh {
            return Err("binding node/mesh mismatch".into());
        }
        let prim = indexed(
            indexed(&g.json, "meshes", b.mesh)?,
            "primitives",
            b.primitive,
        )?;
        indexed(prim, "targets", b.target)?;
        covered.insert(b.parameter_id.as_str());
    }
    if covered.len() != specs.len() {
        return Err("unbound profile parameter".into());
    }
    let mut output = Vec::new();
    for (ni, n) in nodes.iter().enumerate() {
        let Some(mi) = n.get("mesh") else { continue };
        let mi = mi.as_u64().ok_or("invalid mesh index")? as usize;
        let mesh = indexed(&g.json, "meshes", mi)?;
        for owner in [n, mesh] {
            if let Some(w) = owner.get("weights") {
                if w.as_array()
                    .ok_or("invalid default weights")?
                    .iter()
                    .any(|x| x.as_f64() != Some(0.0))
                {
                    return Err("nonzero default weights unsupported".into());
                }
            }
        }
        for (pi, prim) in mesh["primitives"]
            .as_array()
            .ok_or("missing primitives")?
            .iter()
            .enumerate()
        {
            let base = g.floats(num(&prim["attributes"], "POSITION")?, "VEC3", 3)?;
            let mut positions = base.clone();
            let targets = prim.get("targets").and_then(Value::as_array);
            if let Some(targets) = targets {
                for (ti, target) in targets.iter().enumerate() {
                    let binding = p
                        .bindings
                        .iter()
                        .find(|b| {
                            b.node == ni && b.mesh == mi && b.primitive == pi && b.target == ti
                        })
                        .ok_or("morph target lacks explicit node/primitive binding")?;
                    let delta = g.floats(num(target, "POSITION")?, "VEC3", 3)?;
                    if delta.len() != base.len() {
                        return Err("morph/base count mismatch".into());
                    }
                    let weight = r.values[&binding.parameter_id];
                    for (position, d) in positions.iter_mut().zip(delta) {
                        for c in 0..3 {
                            position[c] += weight * d[c];
                            if !position[c].is_finite() {
                                return Err("non-finite evaluated position".into());
                            }
                        }
                    }
                }
            }
            let mut packed = Vec::with_capacity(positions.len() * 24);
            let mut min = [f64::INFINITY; 3];
            let mut max = [f64::NEG_INFINITY; 3];
            let mut displacement: f64 = 0.0;
            let mut witness = None;
            for (vi, (position, original)) in positions.iter().zip(&base).enumerate() {
                let mut d = 0.;
                for c in 0..3 {
                    packed.extend_from_slice(&position[c].to_le_bytes());
                    min[c] = min[c].min(position[c]);
                    max[c] = max[c].max(position[c]);
                    d += (position[c] - original[c]).powi(2);
                }
                displacement = displacement.max(d.sqrt());
                if d > 0. && witness.is_none() {
                    witness = Some(json!({"vertex":vi,"basis":original,"evaluated":position}));
                }
            }
            output.push(json!({"node":ni,"mesh":mi,"primitive":pi,"vertex_count":positions.len(),"positions_f64le_sha256":hash(&packed),"bounds_local":{"min":min,"max":max},"max_displacement_local":displacement,"first_vertex":positions[0],"changed_witness":witness,"source_primitive":prim,"source_node":n}));
        }
    }
    let mut skins = Vec::new();
    if let Some(ss) = g.json["skins"].as_array() {
        for s in ss {
            let ib = g.floats(num(s, "inverseBindMatrices")?, "MAT4", 16)?;
            if ib.len() != s["joints"].as_array().ok_or("missing joints")?.len() {
                return Err("inverse-bind/joint count mismatch".into());
            }
            skins.push(json!({"source_skin":s,"inverse_bind_matrices":ib}));
        }
    }
    Ok(
        json!({"schema_version":1,"route_id":"compiled-package","sample_class":p.sample_class,"case_id":r.case_id,"source_input_manifest_sha256":p.source_manifest_sha256,"package_sha256":hash(&package_bytes),"asset_sha256":p.asset_sha256,"profile_sha256":p.profile_sha256,"source_package_revision":p.source_package_revision,"tool_version":env!("CARGO_PKG_VERSION"),"status":"passed","command":command,"exit_code":0,"artifact_paths":[command[3]],"log_paths":[],"actual_candidate_code_run":true,"native_graphical_execution_run":false,"web_graphical_execution_run":false,"reference_pipeline_run":false,"coordinate_convention":p.coordinate_convention,"transform_identity":p.transform_policy,"recipe":r.values,"measured_positions":output,"joint_rest_state":{"status":"preserved-source-metadata-only","nodes":nodes,"skins":skins},"garment_state":null,"unsupported_fields":["skinning and animation evaluation","joint relocation / inverse bind recomputation","garment fitting","normal/tangent morph evaluation","MakeHuman/MPFB rules","native/Web graphical verification"]}),
    )
}
fn run() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 4 {
        return Err(
            "usage: compiled-character-probe PACKAGE.json RECIPE.json NEW-RESULT.json".into(),
        );
    }
    let result = evaluate(Path::new(&args[1]), Path::new(&args[2]), &args)?;
    let output = PathBuf::from(&args[3]);
    if [&args[1], &args[2]].iter().any(|p| Path::new(p) == output) {
        return Err("output must differ from inputs".into());
    }
    let bytes = serde_json::to_vec(&result).map_err(|e| e.to_string())?;
    // Validation completes before output creation; create_new preserves existing files.
    let mut f = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&output)
        .map_err(|e| e.to_string())?;
    if let Err(e) = f.write_all(&bytes).and_then(|_| f.sync_all()) {
        drop(f);
        let _ = fs::remove_file(&output);
        return Err(e.to_string());
    }
    println!(
        "{}",
        json!({"status":"passed","output":output,"sha256":hash(&bytes)})
    );
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("{}", json!({"status":"failed","error":e}));
        std::process::exit(2);
    }
}

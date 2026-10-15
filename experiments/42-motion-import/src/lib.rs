use serde::de::{self, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Deserializer};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    collections::HashSet,
    fmt,
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    path::Path,
};

pub const JSON_LIMIT: u64 = 4 * 1024 * 1024;
pub const GLB_LIMIT: u64 = 32 * 1024 * 1024;
pub const BASE_SHA: &str = "f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6";
type R<T> = Result<T, String>;
pub fn sha(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
fn ensure(ok: bool, why: &str) -> R<()> {
    if ok { Ok(()) } else { Err(why.into()) }
}

// Value normally keeps the last duplicate key. This visitor rejects duplicates before typed parsing.
struct Strict(Value);
impl<'de> Deserialize<'de> for Strict {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        struct V;
        impl<'de> Visitor<'de> for V {
            type Value = Strict;
            fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
                f.write_str("strict JSON")
            }
            fn visit_bool<E: de::Error>(self, v: bool) -> Result<Strict, E> {
                Ok(Strict(v.into()))
            }
            fn visit_i64<E: de::Error>(self, v: i64) -> Result<Strict, E> {
                Ok(Strict(v.into()))
            }
            fn visit_u64<E: de::Error>(self, v: u64) -> Result<Strict, E> {
                Ok(Strict(v.into()))
            }
            fn visit_f64<E: de::Error>(self, v: f64) -> Result<Strict, E> {
                serde_json::Number::from_f64(v)
                    .map(|n| Strict(Value::Number(n)))
                    .ok_or_else(|| E::custom("nonfinite"))
            }
            fn visit_str<E: de::Error>(self, v: &str) -> Result<Strict, E> {
                Ok(Strict(v.into()))
            }
            fn visit_string<E: de::Error>(self, v: String) -> Result<Strict, E> {
                Ok(Strict(v.into()))
            }
            fn visit_unit<E: de::Error>(self) -> Result<Strict, E> {
                Ok(Strict(Value::Null))
            }
            fn visit_none<E: de::Error>(self) -> Result<Strict, E> {
                Ok(Strict(Value::Null))
            }
            fn visit_seq<A: SeqAccess<'de>>(self, mut a: A) -> Result<Strict, A::Error> {
                let mut v = Vec::new();
                while let Some(x) = a.next_element::<Strict>()? {
                    v.push(x.0)
                }
                Ok(Strict(Value::Array(v)))
            }
            fn visit_map<A: MapAccess<'de>>(self, mut a: A) -> Result<Strict, A::Error> {
                let mut m = serde_json::Map::new();
                while let Some((k, v)) = a.next_entry::<String, Strict>()? {
                    if m.insert(k, v.0).is_some() {
                        return Err(de::Error::custom("duplicate JSON key"));
                    }
                }
                Ok(Strict(Value::Object(m)))
            }
        }
        d.deserialize_any(V)
    }
}
pub fn strict_json(bytes: &[u8]) -> R<Value> {
    ensure(bytes.len() as u64 <= JSON_LIMIT, "JSON size limit")?;
    serde_json::from_slice::<Strict>(bytes)
        .map(|x| x.0)
        .map_err(|e| format!("JSON: {e}"))
}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Skeleton {
    pub identity: String,
    pub joint_names: Vec<String>,
    pub parent_indices: Vec<Option<usize>>,
    pub rest_local_translations_m: Vec<[f64; 3]>,
    pub rest_local_rotations_xyzw: Vec<[f64; 4]>,
    pub rest_local_scales_xyz: Vec<[f64; 3]>,
}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Convention {
    units: String,
    handedness: String,
    up_axis: String,
    rotation_order: String,
    transform_space: String,
    root_motion_mode: String,
}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Motion {
    schema_version: u32,
    pub provenance_kind: String,
    pub skeleton: Skeleton,
    convention: Convention,
    pub sample_times_seconds: Vec<f64>,
    pub local_rotations_xyzw: Vec<Vec<[f64; 4]>>,
    pub root_translations_m: Vec<[f64; 3]>,
}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Provenance {
    source_id: String,
    raw_format: String,
    raw_sha256: String,
    run_receipt_sha256: Option<String>,
    provider: Option<String>,
    code_revision: Option<String>,
    model_sha256: Option<String>,
}
fn vector(v: &[f64]) -> bool {
    v.iter().all(|n| n.is_finite() && (*n as f32).is_finite())
}
fn quat(v: &[f64; 4]) -> bool {
    vector(v) && (v.iter().map(|x| x * x).sum::<f64>() - 1.0).abs() <= 1e-4
}
impl Motion {
    pub fn validate(&self) -> R<()> {
        ensure(self.schema_version == 1, "schema_version")?;
        ensure(
            ["authored_control", "generated"].contains(&self.provenance_kind.as_str()),
            "provenance_kind",
        )?;
        let s = &self.skeleton;
        let n = match s.identity.as_str() {
            "nvwa18" => 18,
            "soma30" => 30,
            "soma77" => 77,
            _ => return Err("unknown skeleton identity".into()),
        };
        ensure(
            s.joint_names.len() == n
                && s.parent_indices.len() == n
                && s.rest_local_translations_m.len() == n
                && s.rest_local_rotations_xyzw.len() == n
                && s.rest_local_scales_xyz.len() == n,
            "joint array dimensions",
        )?;
        let names: HashSet<_> = s.joint_names.iter().collect();
        ensure(
            names.len() == n
                && s.joint_names
                    .iter()
                    .all(|s| !s.trim().is_empty() && s.len() <= 128),
            "joint names",
        )?;
        ensure(
            s.parent_indices.iter().filter(|p| p.is_none()).count() == 1,
            "exactly one root required",
        )?;
        for i in 0..n {
            let mut seen = HashSet::new();
            let mut k = Some(i);
            while let Some(j) = k {
                ensure(j < n && seen.insert(j), "invalid hierarchy or cycle")?;
                k = s.parent_indices[j];
            }
        }
        ensure(
            s.rest_local_translations_m.iter().all(|x| vector(x))
                && s.rest_local_rotations_xyzw.iter().all(quat)
                && s.rest_local_scales_xyz
                    .iter()
                    .all(|v| vector(v) && v.iter().all(|x| *x > 0.)),
            "invalid rest transform",
        )?;
        let c = &self.convention;
        ensure(
            c.units == "meters"
                && c.handedness == "right"
                && c.up_axis == "Y"
                && c.rotation_order == "xyzw"
                && c.transform_space == "local"
                && c.root_motion_mode == "absolute_translation",
            "unsupported units/axes/order/root mode",
        )?;
        let t = &self.sample_times_seconds;
        ensure(
            (2..=151).contains(&t.len())
                && t[0] == 0.0
                && t.last().unwrap() > &0.0
                && t.last().unwrap() <= &5.0
                && vector(t)
                && t.windows(2)
                    .all(|w| w[0] < w[1] && (w[0] as f32) < (w[1] as f32)),
            "invalid sample times",
        )?;
        ensure(
            self.local_rotations_xyzw.len() == t.len() && self.root_translations_m.len() == t.len(),
            "frame array dimensions",
        )?;
        ensure(
            self.local_rotations_xyzw
                .iter()
                .all(|f| f.len() == n && f.iter().all(quat))
                && self.root_translations_m.iter().all(|x| vector(x)),
            "frame joint dimensions or transforms",
        )
    }
}
fn hex(s: &str) -> bool {
    s.len() == 64
        && s.bytes()
            .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
}
pub fn validate_boundary(
    normalized: &[u8],
    raw: &[u8],
    receipt: Option<&[u8]>,
) -> R<(Motion, Value)> {
    let mut envelope = strict_json(normalized)?;
    let p = envelope
        .as_object_mut()
        .ok_or("envelope must be object")?
        .remove("provenance")
        .ok_or("missing provenance")?;
    let p: Provenance = serde_json::from_value(p).map_err(|e| format!("provenance: {e}"))?;
    ensure(
        !p.source_id.trim().is_empty()
            && p.source_id.len() <= 256
            && p.raw_format == "nvwa.motion.portable.v1"
            && hex(&p.raw_sha256)
            && p.raw_sha256 == sha(raw),
        "raw identity/hash/format",
    )?;
    let raw_value = strict_json(raw)?;
    ensure(
        raw_value == envelope,
        "raw motion differs from normalized motion",
    )?;
    let motion: Motion =
        serde_json::from_value(envelope).map_err(|e| format!("motion schema: {e}"))?;
    motion.validate()?;
    if motion.provenance_kind == "generated" {
        // No boolean or user-supplied manifest can establish genuine inference.
        // Receipt structure/hash alone is insufficient until an actual provider run is inspected.
        let r =
            receipt.ok_or("generated requires real raw-output/run provenance; receipt missing")?;
        ensure(
            p.run_receipt_sha256
                .as_ref()
                .is_some_and(|h| hex(h) && *h == sha(r))
                && p.provider.as_ref().is_some_and(|s| !s.is_empty())
                && p.code_revision.as_ref().is_some_and(|s| !s.is_empty())
                && p.model_sha256.as_ref().is_some_and(|s| hex(s)),
            "generated receipt identity",
        )?;
        strict_json(r)?;
        return Err("generated_evidence_unavailable: real provider process/run review has not been supplied".into());
    }
    ensure(
        p.run_receipt_sha256.is_none()
            && p.provider.is_none()
            && p.code_revision.is_none()
            && p.model_sha256.is_none()
            && receipt.is_none(),
        "authored control cannot carry generated claims",
    )?;
    Ok((motion, strict_json(normalized)?))
}
pub fn read_bounded(path: &Path, limit: u64) -> R<Vec<u8>> {
    let md = fs::symlink_metadata(path).map_err(|e| e.to_string())?;
    ensure(
        md.is_file() && !md.file_type().is_symlink(),
        "input must be regular non-symlink file",
    )?;
    ensure(md.len() <= limit, "input file size limit")?;
    let file = File::open(path).map_err(|e| e.to_string())?;
    let mut v = Vec::new();
    file.take(limit + 1)
        .read_to_end(&mut v)
        .map_err(|e| e.to_string())?;
    ensure(v.len() as u64 <= limit, "input file size limit")?;
    Ok(v)
}
fn u32at(b: &[u8], i: usize) -> R<u32> {
    b.get(i..i + 4)
        .ok_or_else(|| "truncated GLB".to_string())
        .map(|s| u32::from_le_bytes(s.try_into().unwrap()))
}
pub fn decode_glb(b: &[u8]) -> R<(Value, Vec<u8>)> {
    ensure(
        b.len() as u64 <= GLB_LIMIT && b.len() >= 28 && b.get(..4) == Some(b"glTF"),
        "GLB header/size",
    )?;
    ensure(
        u32at(b, 4)? == 2 && u32at(b, 8)? as usize == b.len(),
        "GLB version/length",
    )?;
    let n = u32at(b, 12)? as usize;
    ensure(n % 4 == 0 && u32at(b, 16)? == 0x4e4f534a, "GLB JSON chunk")?;
    let end = 20usize.checked_add(n).ok_or("GLB overflow")?;
    let doc = strict_json(b.get(20..end).ok_or("truncated GLB JSON")?)?;
    let len = u32at(b, end)? as usize;
    ensure(
        len % 4 == 0 && u32at(b, end + 4)? == 0x004e4942 && end + 8 + len == b.len(),
        "GLB binary chunk",
    )?;
    Ok((doc, b[end + 8..].to_vec()))
}
fn floats(value: &Value, default: &[f64]) -> R<Vec<f64>> {
    if value.is_null() {
        Ok(default.to_vec())
    } else {
        value
            .as_array()
            .ok_or("TRS array")?
            .iter()
            .map(|x| x.as_f64().ok_or("TRS number".into()))
            .collect()
    }
}
fn append_accessor(doc: &mut Value, bin: &mut Vec<u8>, rows: &[Vec<f64>], kind: &str) -> R<usize> {
    while bin.len() % 4 != 0 {
        bin.push(0)
    }
    let offset = bin.len();
    for row in rows {
        for v in row {
            bin.extend_from_slice(&(*v as f32).to_le_bytes())
        }
    }
    let views = doc["bufferViews"].as_array_mut().ok_or("bufferViews")?;
    let view = views.len();
    views.push(json!({"buffer":0,"byteOffset":offset,"byteLength":bin.len()-offset}));
    let accessors = doc["accessors"].as_array_mut().ok_or("accessors")?;
    let index = accessors.len();
    let mut a = json!({"bufferView":view,"componentType":5126,"count":rows.len(),"type":kind});
    if kind == "SCALAR" {
        a["min"] = json!([rows[0][0]]);
        a["max"] = json!([rows.last().unwrap()[0]]);
    }
    accessors.push(a);
    Ok(index)
}
pub fn export_same_rig(m: &Motion, base: &[u8]) -> R<Vec<u8>> {
    ensure(
        sha(base) == BASE_SHA,
        "base must be exact frozen Nvwa fixture",
    )?;
    ensure(
        m.skeleton.identity == "nvwa18",
        "retargeting required: only exact nvwa18 export supported",
    )?;
    let (mut d, mut bin) = decode_glb(base)?;
    let joints = d["skins"][0]["joints"]
        .as_array()
        .ok_or("skin joints")?
        .iter()
        .map(|v| v.as_u64().map(|n| n as usize).ok_or("joint index".into()))
        .collect::<R<Vec<_>>>()?;
    ensure(joints.len() == 18, "base joint count")?;
    let nodes = d["nodes"].as_array().ok_or("nodes")?;
    let s = &m.skeleton;
    for (i, &node) in joints.iter().enumerate() {
        let nd = &nodes[node];
        ensure(
            nd["name"].as_str() == Some(s.joint_names[i].as_str()),
            "joint order mismatch",
        )?;
        let parent = joints.iter().position(|&j| {
            nodes[j]["children"]
                .as_array()
                .is_some_and(|cs| cs.contains(&json!(node)))
        });
        ensure(parent == s.parent_indices[i], "base parent mismatch")?;
        let t = floats(&nd["translation"], &[0., 0., 0.])?;
        let q = floats(&nd["rotation"], &[0., 0., 0., 1.])?;
        let scale = floats(&nd["scale"], &[1., 1., 1.])?;
        ensure(
            t.len() == 3
                && q.len() == 4
                && scale.len() == 3
                && scale
                    .iter()
                    .zip(s.rest_local_scales_xyz[i])
                    .all(|(a, b)| (a - b).abs() < 1e-6)
                && t.iter()
                    .zip(s.rest_local_translations_m[i])
                    .all(|(a, b)| (a - b).abs() < 1e-6)
                && q.iter()
                    .zip(s.rest_local_rotations_xyzw[i])
                    .all(|(a, b)| (a - b).abs() < 1e-6),
            "base rest mismatch",
        )?;
    }
    let times = m
        .sample_times_seconds
        .iter()
        .map(|&t| vec![t])
        .collect::<Vec<_>>();
    let ti = append_accessor(&mut d, &mut bin, &times, "SCALAR")?;
    let mut samplers = vec![];
    let mut channels = vec![];
    for (i, &node) in joints.iter().enumerate() {
        let rows = m
            .local_rotations_xyzw
            .iter()
            .map(|f| f[i].to_vec())
            .collect::<Vec<_>>();
        let output = append_accessor(&mut d, &mut bin, &rows, "VEC4")?;
        channels.push(json!({"sampler":samplers.len(),"target":{"node":node,"path":"rotation"}}));
        samplers.push(json!({"input":ti,"output":output,"interpolation":"LINEAR"}));
    }
    let root = s.parent_indices.iter().position(|p| p.is_none()).unwrap();
    let rows = m
        .root_translations_m
        .iter()
        .map(|t| t.to_vec())
        .collect::<Vec<_>>();
    let output = append_accessor(&mut d, &mut bin, &rows, "VEC3")?;
    channels.push(
        json!({"sampler":samplers.len(),"target":{"node":joints[root],"path":"translation"}}),
    );
    samplers.push(json!({"input":ti,"output":output,"interpolation":"LINEAR"}));
    d["animations"] = json!([{"name":"imported_authored_control","samplers":samplers,"channels":channels,"extras":{"provenance_kind":m.provenance_kind,"experiment_only":true}}]);
    d["buffers"][0]["byteLength"] = json!(bin.len());
    let mut j = serde_json::to_vec(&d).map_err(|e| e.to_string())?;
    while j.len() % 4 != 0 {
        j.push(b' ')
    }
    while bin.len() % 4 != 0 {
        bin.push(0)
    }
    let total = 28 + j.len() + bin.len();
    ensure(total as u64 <= GLB_LIMIT, "output GLB size")?;
    let mut b = Vec::with_capacity(total);
    b.extend_from_slice(b"glTF");
    for v in [2, total as u32, j.len() as u32, 0x4e4f534a] {
        b.extend_from_slice(&v.to_le_bytes())
    }
    b.extend_from_slice(&j);
    b.extend_from_slice(&(bin.len() as u32).to_le_bytes());
    b.extend_from_slice(&0x004e4942u32.to_le_bytes());
    b.extend_from_slice(&bin);
    decode_glb(&b)?;
    Ok(b)
}
pub fn import_to(
    normalized: &Path,
    raw: &Path,
    base: &Path,
    out: &Path,
    receipt: Option<&Path>,
) -> R<Value> {
    let norm = read_bounded(normalized, JSON_LIMIT)?;
    let raw = read_bounded(raw, JSON_LIMIT)?;
    let receipt = receipt.map(|p| read_bounded(p, JSON_LIMIT)).transpose()?;
    let (m, envelope) = validate_boundary(&norm, &raw, receipt.as_deref())?;
    let base = read_bounded(base, GLB_LIMIT)?;
    let clip = export_same_rig(&m, &base)?;
    let normalized_output = serde_json::to_vec(&envelope).map_err(|e| e.to_string())?;
    ensure(
        normalized_output.len() as u64 <= JSON_LIMIT,
        "normalized output size limit",
    )?;
    let manifest = json!({"experiment_only":true,"ai_generated":false,"provenance_kind":m.provenance_kind,"raw_sha256":sha(&raw),"input_normalized_sha256":sha(&norm),"output_normalized_sha256":sha(&normalized_output),"base_sha256":sha(&base),"clip_sha256":sha(&clip),"joint_count":m.skeleton.joint_names.len(),"frame_count":m.sample_times_seconds.len(),"duration_seconds":m.sample_times_seconds.last(),"animation_index":0,"animation_name":"imported_authored_control","genuine_inference_verified":false,"runtime_playback":"NOT-RUN"});
    // Exclusive directory creation is the publication boundary. Never overwrite any existing target.
    fs::create_dir(out).map_err(|e| format!("new output directory required: {e}"))?;
    let write_result = (|| {
        for (name, bytes) in [
            ("clip.glb", clip),
            ("normalized.json", normalized_output),
            (
                "manifest.json",
                serde_json::to_vec_pretty(&manifest).unwrap(),
            ),
        ] {
            let mut f = OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(out.join(name))
                .map_err(|e| e.to_string())?;
            f.write_all(&bytes).map_err(|e| e.to_string())?;
            f.sync_all().map_err(|e| e.to_string())?;
        }
        Ok(())
    })();
    if let Err(e) = write_result {
        for name in ["clip.glb", "normalized.json", "manifest.json"] {
            let _ = fs::remove_file(out.join(name));
        }
        let _ = fs::remove_dir(out);
        return Err(e);
    }
    Ok(manifest)
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct F32Sidecar {
    source_format: String,
    code_revision: String,
    endianness: String,
    frame_count: usize,
    joint_count: usize,
    provenance_kind: String,
    skeleton: Value,
    convention: Value,
    sample_times_seconds: Vec<f64>,
}
pub fn adapt_f32(sidecar: &[u8], roots: &[u8], rotations: &[u8]) -> R<(Value, Value, Value)> {
    let s: F32Sidecar =
        serde_json::from_value(strict_json(sidecar)?).map_err(|e| format!("sidecar: {e}"))?;
    ensure(
        s.source_format == "kimodo.cpp.f32.v1"
            && s.code_revision == "5679ff19ba0a522c0b0516e9a9d402fe1af2c027"
            && s.endianness == "little",
        "unsupported F32 source revision/endianness",
    )?;
    ensure(
        (2..=151).contains(&s.frame_count) && [18, 30, 77].contains(&s.joint_count),
        "F32 count limits",
    )?;
    ensure(
        roots.len() == s.frame_count * 3 * 4
            && rotations.len() == s.frame_count * s.joint_count * 4 * 4,
        "F32 exact file size",
    )?;
    fn decode(bytes: &[u8]) -> R<Vec<f64>> {
        bytes
            .chunks_exact(4)
            .map(|b| {
                let n = f32::from_le_bytes(b.try_into().unwrap());
                ensure(n.is_finite(), "nonfinite F32")?;
                Ok(n as f64)
            })
            .collect()
    }
    let root_values = decode(roots)?;
    let rotation_values = decode(rotations)?;
    let raw = json!({"schema_version":1,"provenance_kind":s.provenance_kind,"skeleton":s.skeleton,"convention":s.convention,"sample_times_seconds":s.sample_times_seconds,"root_translations_m":root_values.chunks_exact(3).collect::<Vec<_>>(),"local_rotations_xyzw":rotation_values.chunks_exact(s.joint_count*4).map(|f|f.chunks_exact(4).collect::<Vec<_>>()).collect::<Vec<_>>()});
    let motion: Motion = serde_json::from_value(raw.clone()).map_err(|e| e.to_string())?;
    motion.validate()?;
    ensure(
        motion.skeleton.joint_names.len() == s.joint_count
            && motion.sample_times_seconds.len() == s.frame_count,
        "sidecar dimensions differ",
    )?;
    let bytes = serde_json::to_vec(&raw).map_err(|e| e.to_string())?;
    let mut envelope = raw.clone();
    envelope["provenance"] = json!({"source_id":format!("f32-adapter:{}",sha(sidecar)),"raw_format":"nvwa.motion.portable.v1","raw_sha256":sha(&bytes),"run_receipt_sha256":null,"provider":null,"code_revision":null,"model_sha256":null});
    let receipt = json!({"structural_conversion_only":true,"genuine_inference_verified":false,"provenance_kind":motion.provenance_kind,"sidecar_sha256":sha(sidecar),"root_positions_f32_sha256":sha(roots),"local_rotations_xyzw_f32_sha256":sha(rotations),"portable_raw_sha256":sha(&bytes),"endianness":"little","coordinate_conversion":"identity; explicit sidecar assertion, actual provider coordinate compatibility NOT-RUN","source_code_revision":s.code_revision});
    Ok((raw, envelope, receipt))
}
pub fn adapt_f32_to(sidecar: &Path, roots: &Path, rotations: &Path, out: &Path) -> R<Value> {
    let sidecar = read_bounded(sidecar, JSON_LIMIT)?;
    let roots = read_bounded(roots, JSON_LIMIT)?;
    let rotations = read_bounded(rotations, JSON_LIMIT)?;
    let (raw, envelope, receipt) = adapt_f32(&sidecar, &roots, &rotations)?;
    fs::create_dir(out).map_err(|e| format!("new output directory required: {e}"))?;
    let result = (|| {
        for (name, value) in [
            ("raw.json", raw),
            ("normalized.json", envelope),
            ("adapter-receipt.json", receipt.clone()),
        ] {
            let mut file = OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(out.join(name))
                .map_err(|e| e.to_string())?;
            file.write_all(&serde_json::to_vec(&value).unwrap())
                .map_err(|e| e.to_string())?;
            file.sync_all().map_err(|e| e.to_string())?;
        }
        Ok(())
    })();
    if let Err(e) = result {
        for name in ["raw.json", "normalized.json", "adapter-receipt.json"] {
            let _ = fs::remove_file(out.join(name));
        }
        let _ = fs::remove_dir(out);
        return Err(e);
    }
    Ok(receipt)
}

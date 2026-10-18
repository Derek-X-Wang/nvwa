//! Current published runtime cage -> full-positive accessory LBS -> actual CPU mesh upload.
use crate::hash;
use bevy::math::{DMat4, DVec3};
use bevy::{
    asset::RenderAssetUsages,
    image::{CompressedImageFormats, ImageSampler, ImageType},
    mesh::{Indices, PrimitiveTopology, VertexAttributeValues},
    prelude::*,
    render::render_resource::TextureFormat,
};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
const CAGE: usize = 19158;
const MANIFEST: &str = include_str!("../../62-b1-appearance-preview/assets/asset-manifest.json");
const WEIGHTS: &str =
    include_str!("../../../assets/characters/mpfb-b1-v1/weights.game_engine.json");
#[derive(Component)]
pub struct AccessoryTag;
#[derive(Clone, Debug)]
struct Row {
    helpers: Vec<usize>,
    coefficients: Vec<f64>,
    offset: [f64; 3],
}
#[derive(Clone, Debug)]
struct Mapping {
    rows: Vec<Row>,
    scales: [(usize, usize, f64); 3],
}
#[derive(Clone, Debug)]
struct Obj {
    count: usize,
    pairs: Vec<(usize, usize)>,
    uv: Vec<[f32; 2]>,
    indices: Vec<u32>,
}
struct Prepared {
    name: &'static str,
    mapping: Mapping,
    obj: Obj,
    png: &'static [u8],
    texture: &'static str,
    size: u32,
    hair: bool,
}
#[derive(Clone)]
struct Live {
    name: &'static str,
    entity: Entity,
    mesh: Handle<Mesh>,
    material: Handle<StandardMaterial>,
    image: Handle<Image>,
    rest: Vec<[f64; 3]>,
    weights: Vec<Vec<(usize, f64)>>,
    rest_normals: Vec<[f64; 3]>,
    obj: Obj,
    scales: [f64; 3],
    pixels_sha: String,
    texture: &'static str,
    hair: bool,
    image_size: u32,
}
#[derive(Default)]
pub struct State {
    live: Vec<Live>,
    key: Value,
    pub error: Option<String>,
    pub frame: Value,
    basis: Value,
    stream_frame: u64,
}
fn finite(v: &[f64]) -> Result<(), String> {
    if v.iter().all(|x| x.is_finite()) {
        Ok(())
    } else {
        Err("nonfinite accessory input".into())
    }
}
fn number(s: &str) -> Result<f64, String> {
    let x = s.parse::<f64>().map_err(|_| "invalid number")?;
    finite(&[x])?;
    Ok(x)
}
fn id(s: &str, limit: usize) -> Result<usize, String> {
    let n = s.parse::<usize>().map_err(|_| "invalid index")?;
    if n < limit {
        Ok(n)
    } else {
        Err("index outside declared domain".into())
    }
}
fn mapping(text: &str, count: usize) -> Result<Mapping, String> {
    let mut rows = vec![];
    let mut scales = [None; 3];
    let mut section = false;
    let mut obj = false;
    for line in text.lines() {
        let f: Vec<_> = line.split_whitespace().collect();
        if f.is_empty() || f[0].starts_with('#') {
            continue;
        }
        if f == ["verts", "0"] {
            if section {
                return Err("duplicate verts section".into());
            }
            section = true;
            continue;
        }
        if f[0] == "delete_verts" {
            return Err("accessory delete_verts unsupported".into());
        }
        if !section {
            if f[0] == "obj_file" {
                if f.len() != 2 || obj {
                    return Err("invalid obj_file".into());
                }
                obj = true;
            }
            if let Some(a) = ["x_scale", "y_scale", "z_scale"]
                .iter()
                .position(|k| *k == f[0])
            {
                if f.len() != 4 || scales[a].is_some() {
                    return Err("invalid scale rule".into());
                }
                let r = number(f[3])? * 0.1;
                if r.abs() < 1e-12 {
                    return Err("zero scale reference".into());
                }
                scales[a] = Some((id(f[1], CAGE)?, id(f[2], CAGE)?, r));
            }
            continue;
        }
        if f[0] == "material" {
            if f.len() != 2 {
                return Err("invalid material declaration".into());
            }
            continue;
        }
        let (helpers, mut coefficients, offset) = match f.len() {
            1 => (vec![id(f[0], CAGE)?], vec![1.], [0.; 3]),
            9 => (
                f[..3]
                    .iter()
                    .map(|x| id(x, CAGE))
                    .collect::<Result<Vec<_>, _>>()?,
                f[3..6]
                    .iter()
                    .map(|x| number(x))
                    .collect::<Result<Vec<_>, _>>()?,
                [
                    number(f[6])? * 0.1,
                    number(f[7])? * 0.1,
                    number(f[8])? * 0.1,
                ],
            ),
            _ => return Err("unsupported MHCLO row".into()),
        };
        let sum: f64 = coefficients.iter().sum();
        if sum.abs() <= 2f64.powi(-23) {
            return Err("zero coefficient sum".into());
        }
        for x in &mut coefficients {
            *x /= sum;
        }
        rows.push(Row {
            helpers,
            coefficients,
            offset,
        });
    }
    if rows.len() != count || !obj || scales.iter().any(Option::is_none) {
        return Err("incomplete mapping".into());
    }
    Ok(Mapping {
        rows,
        scales: scales.map(Option::unwrap),
    })
}
fn obj(text: &str, count: usize) -> Result<Obj, String> {
    let mut vertices = 0;
    let mut tex = vec![];
    let mut pairs = vec![];
    let mut lookup = BTreeMap::new();
    let mut indices = vec![];
    let mut used = BTreeSet::new();
    for line in text.lines() {
        let f: Vec<_> = line.split_whitespace().collect();
        if f.is_empty() || f[0].starts_with('#') {
            continue;
        }
        match f[0] {
            "v" => {
                if f.len() != 4 {
                    return Err("invalid OBJ position".into());
                }
                for v in &f[1..] {
                    number(v)?;
                }
                vertices += 1;
            }
            "vt" => {
                if f.len() != 3 {
                    return Err("invalid OBJ UV".into());
                }
                tex.push([number(f[1])? as f32, 1. - number(f[2])? as f32]);
            }
            "f" => {
                if f.len() < 4 {
                    return Err("invalid OBJ face".into());
                }
                let mut face = vec![];
                for token in &f[1..] {
                    let p: Vec<_> = token.split('/').collect();
                    if p.len() != 2 {
                        return Err("OBJ requires position/UV corner; supplied normals unsupported for pinned assets".into());
                    }
                    let v = id(p[0], vertices + 1)?
                        .checked_sub(1)
                        .ok_or("OBJ zero index")?;
                    let t = id(p[1], tex.len() + 1)?
                        .checked_sub(1)
                        .ok_or("OBJ zero UV")?;
                    used.insert(v);
                    let next = pairs.len() as u32;
                    let i = *lookup.entry((v, t)).or_insert_with(|| {
                        pairs.push((v, t));
                        next
                    });
                    face.push(i);
                }
                for i in 1..face.len() - 1 {
                    indices.extend([face[0], face[i], face[i + 1]]);
                }
            }
            "o" | "g" | "s" | "usemtl" | "mtllib" => {}
            _ => return Err(format!("unsupported OBJ directive {}", f[0])),
        }
    }
    if vertices != count || used != (0..count).collect() || indices.is_empty() {
        return Err("OBJ missing source coverage".into());
    }
    let uv = pairs.iter().map(|(_, t)| tex[*t]).collect();
    Ok(Obj {
        count,
        pairs,
        uv,
        indices,
    })
}
fn authenticated(path: &str, bytes: &[u8]) -> Result<(), String> {
    let m: Value = serde_json::from_str(MANIFEST).map_err(|e| e.to_string())?;
    if m["outputs"][path]["sha256"] != format!("{:x}", Sha256::digest(bytes))
        || m["outputs"][path]["size"].as_u64() != Some(bytes.len() as u64)
    {
        return Err(format!("fixed asset hash/size mismatch {path}"));
    }
    Ok(())
}
fn prepare() -> Result<Vec<Prepared>, String> {
    let mut out = vec![];
    macro_rules! asset {
        ($name:literal,$stem:literal,$texture:literal,$count:literal,$size:literal,$hair:literal) => {{
            let map = include_str!(concat!(
                "../../62-b1-appearance-preview/assets/",
                $stem,
                ".mhclo"
            ));
            let geometry = include_str!(concat!(
                "../../62-b1-appearance-preview/assets/",
                $stem,
                ".obj"
            ));
            let png = include_bytes!(concat!("../../62-b1-appearance-preview/assets/", $texture));
            authenticated(concat!($stem, ".mhclo"), map.as_bytes())?;
            authenticated(concat!($stem, ".obj"), geometry.as_bytes())?;
            authenticated($texture, png)?;
            out.push(Prepared {
                name: $name,
                mapping: mapping(map, $count)?,
                obj: obj(geometry, $count)?,
                png,
                texture: $texture,
                size: $size,
                hair: $hair,
            });
        }};
    }
    asset!(
        "eyes",
        "eyes/low-poly/low-poly",
        "eyes/materials/brown_eye.png",
        96,
        1024,
        false
    );
    asset!(
        "hair",
        "hair/short04/short04",
        "hair/short04/short04_diffuse.png",
        865,
        2048,
        true
    );
    Ok(out)
}
fn cage(body: &Value) -> Result<Vec<[f64; 3]>, String> {
    let ids: Vec<usize> =
        serde_json::from_value(body["source_ids"].clone()).map_err(|e| e.to_string())?;
    let rest: Vec<[f64; 3]> =
        serde_json::from_value(body["rest_positions"].clone()).map_err(|e| e.to_string())?;
    if ids.len() != rest.len() {
        return Err("cage coverage mismatch".into());
    }
    let mut cage = vec![None; CAGE];
    for (i, p) in ids.into_iter().zip(rest) {
        finite(&p)?;
        let slot = cage.get_mut(i).ok_or("cage ID outside domain")?;
        if slot.is_some_and(|old| old != p) {
            return Err("conflicting duplicate cage position".into());
        }
        *slot = Some(p);
    }
    cage.into_iter()
        .map(|x| x.ok_or("missing full19158 cage position".into()))
        .collect()
}
fn weights(names: &[String]) -> Result<Vec<Vec<f64>>, String> {
    if names.len() != 53 || names.iter().collect::<BTreeSet<_>>().len() != 53 {
        return Err("exact53 unique bones required".into());
    }
    if format!("{:x}", Sha256::digest(WEIGHTS.as_bytes()))
        != "9f4a773e74ce5ba08415b4f30070338e9f75bae5971b5075b10cd6b9caa58473"
    {
        return Err("source weights hash mismatch".into());
    }
    let w: Value = serde_json::from_str(WEIGHTS).map_err(|e| e.to_string())?;
    let w = w["weights"].as_object().ok_or("source weights missing")?;
    if w.len() != 53 {
        return Err("source bone coverage".into());
    }
    let mut result = vec![];
    for name in names {
        let entries = w
            .get(name)
            .and_then(Value::as_array)
            .ok_or("actual bone not in fixed source weights")?;
        let mut row = vec![0.; CAGE];
        let mut used = BTreeSet::new();
        for e in entries {
            let i = e[0].as_u64().ok_or("weight source index")? as usize;
            let v = e[1].as_f64().ok_or("weight number")?;
            if i >= CAGE || !v.is_finite() || v < 0. || !used.insert(i) {
                return Err("invalid source weights".into());
            }
            row[i] = v;
        }
        result.push(row);
    }
    Ok(result)
}
fn transfer(mapping: &Mapping, source: &[Vec<f64>]) -> Result<Vec<Vec<(usize, f64)>>, String> {
    mapping
        .rows
        .iter()
        .map(|r| {
            let mut row = vec![];
            for (j, weights) in source.iter().enumerate() {
                let v: f64 = r
                    .helpers
                    .iter()
                    .zip(&r.coefficients)
                    .map(|(h, c)| weights[*h] * c)
                    .sum();
                finite(&[v])?;
                if v > 0. {
                    row.push((j, v));
                }
            }
            let sum: f64 = row.iter().map(|x| x.1).sum();
            if sum <= 0. || !sum.is_finite() {
                return Err("no final-positive weight".into());
            }
            for (_, w) in &mut row {
                *w /= sum;
            }
            Ok(row)
        })
        .collect()
}
fn fit(mapping: &Mapping, cage: &[[f64; 3]]) -> Result<(Vec<[f64; 3]>, [f64; 3]), String> {
    let mut scales = [0.; 3];
    for (a, (lo, hi, reference)) in mapping.scales.iter().enumerate() {
        scales[a] = (cage[*hi][a] - cage[*lo][a]) / reference;
    }
    finite(&scales)?;
    let mut rest = vec![];
    for row in &mapping.rows {
        let mut p = [0.; 3];
        for a in 0..3 {
            p[a] = row
                .helpers
                .iter()
                .zip(&row.coefficients)
                .map(|(h, c)| cage[*h][a] * c)
                .sum::<f64>()
                + scales[a] * row.offset[a];
        }
        finite(&p)?;
        rest.push(p);
    }
    Ok((rest, scales))
}
fn source_normals(rest: &[[f64; 3]], obj: &Obj) -> Result<Vec<[f64; 3]>, String> {
    let mut n = vec![DVec3::ZERO; rest.len()];
    for t in obj.indices.chunks_exact(3) {
        let a = obj.pairs[t[0] as usize].0;
        let b = obj.pairs[t[1] as usize].0;
        let c = obj.pairs[t[2] as usize].0;
        let normal = (DVec3::from_array(rest[b]) - DVec3::from_array(rest[a]))
            .cross(DVec3::from_array(rest[c]) - DVec3::from_array(rest[a]));
        if !normal.is_finite() || normal.length_squared() < 1e-24 {
            return Err("degenerate fitted accessory triangle".into());
        }
        for i in [a, b, c] {
            n[i] += normal;
        }
    }
    n.into_iter()
        .map(|n| {
            let n = n.try_normalize().ok_or("invalid fitted normal")?;
            Ok(n.to_array())
        })
        .collect()
}
fn skin(
    rest: &[[f64; 3]],
    normals: &[[f64; 3]],
    weights: &[Vec<(usize, f64)>],
    bones: &[DMat4],
) -> Result<(Vec<[f32; 3]>, Vec<[f32; 3]>), String> {
    let normal_matrices: Vec<_> = bones.iter().map(|m| m.inverse().transpose()).collect();
    let mut positions = vec![];
    let mut outn = vec![];
    for ((p, n), row) in rest.iter().zip(normals).zip(weights) {
        let mut q = DVec3::ZERO;
        let mut normal = DVec3::ZERO;
        for (j, w) in row {
            q += bones[*j].transform_point3(DVec3::from_array(*p)) * *w;
            normal += normal_matrices[*j].transform_vector3(DVec3::from_array(*n)) * *w;
        }
        if !q.is_finite() {
            return Err("nonfinite posed accessory".into());
        }
        let normal = normal.try_normalize().ok_or("nonfinite posed normal")?;
        positions.push(q.as_vec3().to_array());
        outn.push(normal.as_vec3().to_array());
    }
    Ok((positions, outn))
}
pub fn dispose(world: &mut World, state: &mut State) {
    for live in state.live.drain(..) {
        let _ = world.despawn(live.entity);
        if let Some(mut assets) = world.get_resource_mut::<Assets<Mesh>>() {
            assets.remove(live.mesh.id());
        }
        if let Some(mut assets) = world.get_resource_mut::<Assets<StandardMaterial>>() {
            assets.remove(live.material.id());
        }
        if let Some(mut assets) = world.get_resource_mut::<Assets<Image>>() {
            assets.remove(live.image.id());
        }
    }
    state.key = Value::Null;
    state.frame = Value::Null;
}
fn transform(value: &Value) -> Result<Mat4, String> {
    let a: [f32; 16] = serde_json::from_value(value.clone()).map_err(|e| e.to_string())?;
    if !a.iter().all(|x| x.is_finite()) {
        return Err("nonfinite placement".into());
    }
    let matrix = Mat4::from_cols_array(&a);
    if matrix.determinant().abs() < 1e-10 {
        return Err("singular display placement".into());
    }
    Ok(matrix)
}
pub fn sync(
    world: &mut World,
    state: &mut State,
    snapshot: &Value,
    enabled: bool,
) -> Result<(), String> {
    if !enabled {
        dispose(world, state);
        state.error = None;
        return Ok(());
    }
    let result = update(world, state, snapshot, true);
    if let Err(e) = &result {
        dispose(world, state);
        state.error = Some(e.clone());
    } else {
        state.error = None;
    }
    result
}
fn update(
    world: &mut World,
    state: &mut State,
    snapshot: &Value,
    capture: bool,
) -> Result<(), String> {
    require_asset_resources(world)?;
    let body = snapshot["parts"]
        .as_array()
        .and_then(|v| v.iter().find(|v| v["name"] == "body"))
        .ok_or("actual body missing")?;
    let bones = snapshot["bones"].as_array().ok_or("bones absent")?;
    let names: Vec<String> = bones
        .iter()
        .map(|b| {
            b["name"]
                .as_str()
                .map(String::from)
                .ok_or("bone name absent".to_string())
        })
        .collect::<Result<_, _>>()?;
    if names.len() != 53 {
        return Err("exact53 bones required".into());
    }
    let mut matrices = vec![];
    for b in bones {
        let m: [f64; 16] = serde_json::from_value(b["skin"].clone()).map_err(|e| e.to_string())?;
        finite(&m)?;
        let m = DMat4::from_cols_array(&m);
        if !m.determinant().is_finite() || m.determinant().abs() < 1e-12 {
            return Err("singular actual skin matrix".into());
        }
        matrices.push(m);
    }
    let placement = transform(&body["display_transform"])?;
    let key = json!({"generation":snapshot["generation"],"revision":snapshot["revision"],"character":snapshot["character_entity"],"body":body["mesh_handle"],"parameters":snapshot["parameters"]});
    if state.key != key || state.live.len() != 2 {
        dispose(world, state);
        let cage = cage(body)?;
        let source = weights(&names)?;
        // Prepare and validate both before spawning, so no partial asset success can render.
        let mut prepared = vec![];
        for p in prepare()? {
            let (rest, scales) = fit(&p.mapping, &cage)?;
            let rows = transfer(&p.mapping, &source)?;
            let normals = source_normals(&rest, &p.obj)?;
            let image = Image::from_buffer(
                p.png,
                ImageType::Extension("png"),
                CompressedImageFormats::NONE,
                true,
                ImageSampler::default(),
                RenderAssetUsages::default(),
            )
            .map_err(|e| e.to_string())?;
            if image.width() != p.size
                || image.height() != p.size
                || image.texture_descriptor.format != TextureFormat::Rgba8UnormSrgb
                || image
                    .data
                    .as_ref()
                    .is_none_or(|d| d.len() != p.size as usize * p.size as usize * 4)
            {
                return Err("fixed decoded accessory image domain".into());
            }
            prepared.push((p, rest, scales, rows, normals, image));
        }
        for (p, rest, scales, rows, normals, image) in prepared {
            let pixels_sha = format!("{:x}", Sha256::digest(image.data.as_ref().unwrap()));
            let image = world.resource_mut::<Assets<Image>>().add(image);
            let material = world
                .resource_mut::<Assets<StandardMaterial>>()
                .add(StandardMaterial {
                    base_color: Color::WHITE,
                    base_color_texture: Some(image.clone()),
                    perceptual_roughness: 0.7,
                    metallic: 0.,
                    alpha_mode: AlphaMode::Mask(0.5),
                    cull_mode: if p.hair {
                        None
                    } else {
                        Some(bevy::render::render_resource::Face::Back)
                    },
                    double_sided: p.hair,
                    ..default()
                });
            let (positions, posed_normals) = skin(&rest, &normals, &rows, &matrices)?;
            let mut mesh = Mesh::new(
                PrimitiveTopology::TriangleList,
                RenderAssetUsages::default(),
            );
            mesh.insert_attribute(
                Mesh::ATTRIBUTE_POSITION,
                p.obj
                    .pairs
                    .iter()
                    .map(|(i, _)| positions[*i])
                    .collect::<Vec<_>>(),
            );
            mesh.insert_attribute(
                Mesh::ATTRIBUTE_NORMAL,
                p.obj
                    .pairs
                    .iter()
                    .map(|(i, _)| posed_normals[*i])
                    .collect::<Vec<_>>(),
            );
            mesh.insert_attribute(Mesh::ATTRIBUTE_UV_0, p.obj.uv.clone());
            mesh.insert_indices(Indices::U32(p.obj.indices.clone()));
            let mesh = world.resource_mut::<Assets<Mesh>>().add(mesh);
            let entity = world
                .spawn((
                    AccessoryTag,
                    Name::new(format!("64-{}-unsaved", p.name)),
                    Mesh3d(mesh.clone()),
                    MeshMaterial3d(material.clone()),
                    Transform::from_matrix(placement),
                    GlobalTransform::from(placement),
                ))
                .id();
            state.live.push(Live {
                name: p.name,
                entity,
                mesh,
                material,
                image,
                rest,
                weights: rows,
                rest_normals: normals,
                obj: p.obj,
                scales,
                pixels_sha,
                texture: p.texture,
                hair: p.hair,
                image_size: p.size,
            });
        }
        state.key = key;
        state.basis = json!({"generation":snapshot["generation"],"revision":snapshot["revision"],"character_entity":snapshot["character_entity"],"parameters":snapshot["parameters"],"parts":[{"name":"body","mesh_handle":body["mesh_handle"],"display_entity":body["display_entity"],"model_to_world":body["model_to_world"]}]});
    }
    let mut records = vec![];
    for live in &state.live {
        let (positions, normals) = skin(&live.rest, &live.rest_normals, &live.weights, &matrices)?;
        let render_positions: Vec<_> = live.obj.pairs.iter().map(|(i, _)| positions[*i]).collect();
        let render_normals: Vec<_> = live.obj.pairs.iter().map(|(i, _)| normals[*i]).collect();
        let mut meshes = world.resource_mut::<Assets<Mesh>>();
        let mut mesh = meshes
            .get_mut(&live.mesh)
            .ok_or("accessory mesh disappeared")?;
        mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, render_positions);
        mesh.insert_attribute(Mesh::ATTRIBUTE_NORMAL, render_normals);
        drop(mesh);
        drop(meshes);
        world
            .get_entity_mut(live.entity)
            .map_err(|_| "accessory entity disappeared before transform update")?
            .insert((
                Transform::from_matrix(placement),
                GlobalTransform::from(placement),
            ));
        // Read the actual asset arrays back through the same handle used by Mesh3d.
        let entity = world
            .get_entity(live.entity)
            .map_err(|_| "accessory entity disappeared")?;
        if entity.get::<Mesh3d>().is_none_or(|m| m.0 != live.mesh)
            || entity
                .get::<MeshMaterial3d<StandardMaterial>>()
                .is_none_or(|m| m.0 != live.material)
        {
            return Err("accessory entity binding changed".into());
        }
        if !capture {
            observe_material(world, live, false)?;
            continue;
        }
        let meshes = world.resource::<Assets<Mesh>>();
        let mesh = meshes.get(&live.mesh).ok_or("uploaded accessory absent")?;
        let actual = match mesh.attribute(Mesh::ATTRIBUTE_POSITION) {
            Some(VertexAttributeValues::Float32x3(v)) => v,
            _ => return Err("actual accessory POSITION absent".into()),
        };
        let actual_normals = match mesh.attribute(Mesh::ATTRIBUTE_NORMAL) {
            Some(VertexAttributeValues::Float32x3(v)) => v,
            _ => return Err("actual accessory NORMAL absent".into()),
        };
        let uv = match mesh.attribute(Mesh::ATTRIBUTE_UV_0) {
            Some(VertexAttributeValues::Float32x2(v)) => v,
            _ => return Err("actual accessory UV absent".into()),
        };
        if uv != &live.obj.uv {
            return Err("accessory UV changed".into());
        }
        let indices: Vec<_> = mesh
            .indices()
            .ok_or("accessory indices missing")?
            .iter()
            .collect();
        if indices
            != live
                .obj
                .indices
                .iter()
                .map(|i| *i as usize)
                .collect::<Vec<_>>()
        {
            return Err("accessory indices changed".into());
        }
        let material = observe_material(world, live, capture)?;
        let actual_transform = entity
            .get::<GlobalTransform>()
            .ok_or("accessory placement absent")?
            .to_matrix()
            .to_cols_array();
        if actual_transform != placement.to_cols_array() {
            return Err("accessory placement mismatch".into());
        }
        records.push(json!({"name":live.name,"entity":format!("{:?}",live.entity),"mesh_handle":format!("{:?}",live.mesh.id()),"source_vertices":live.obj.count,"source_uv_pairs":live.obj.pairs,"rest_model_m":live.rest,"rest_normals":live.rest_normals,"full_normalized_positive_influences":live.weights,"axis_scales":live.scales,"positions":actual,"normals":actual_normals,"uv_0":uv,"indices":indices,"display_transform":actual_transform,"model_to_world_record_only":body["model_to_world"],"material":material,"tangents":"NOT-EXPORTED; no normal map in simple material","posed_model_bounds_m":bounds(actual,Mat4::IDENTITY)?,"posed_stage_bounds_m":bounds(actual,placement)?,"actual_cpu_upload_sha256":hash(actual)?,"observation":"CPU Assets<Mesh> through actual entity handles; NOT GPU readback","not_saved":true}));
    }
    if capture {
        state.frame = json!({"identity":state.key,"generation":snapshot["generation"],"revision":snapshot["revision"],"sample":snapshot["sample"],"bone_names":names,"actual_skin_matrices":bones,"accessories":records,"material_conversion":"simple diffuse sRGB ×white; cutout Mask(0.5); no legacyshader parity"});
    }
    Ok(())
}
pub fn stream(world: &mut World, state: &mut State) -> Result<(), String> {
    let result = stream_current(world, state);
    if let Err(e) = &result {
        dispose(world, state);
        state.error = Some(e.clone());
    }
    result
}
fn stream_current(world: &mut World, state: &mut State) -> Result<(), String> {
    if state.live.is_empty() {
        let snapshot = nvwa_runtime::b1_frame_snapshot(world)?;
        return sync(world, state, &snapshot, true);
    }
    let character = world
        .iter_entities()
        .find(|e| format!("{:?}", e.id()) == state.basis["character_entity"].as_str().unwrap_or(""))
        .map(|e| e.id())
        .ok_or("current character entity lost")?;
    let frames = nvwa_b1_adapter::bone_frames(world, character)?;
    let body_entity = world
        .iter_entities()
        .find(|e| {
            format!("{:?}", e.id())
                == state.basis["parts"][0]["display_entity"]
                    .as_str()
                    .unwrap_or("")
        })
        .ok_or("current body entity lost")?;
    if body_entity.get::<Mesh3d>().is_none_or(|m| {
        format!("{:?}", m.0.id())
            != state.basis["parts"][0]["mesh_handle"]
                .as_str()
                .unwrap_or("")
    }) {
        return Err("stream body mesh identity changed".into());
    }
    let display = body_entity
        .get::<GlobalTransform>()
        .ok_or("current body placement lost")?
        .to_matrix()
        .to_cols_array();
    let t = world
        .get_resource::<nvwa_runtime::Playback>()
        .ok_or("current playback resource missing")?;
    state.stream_frame += 1;
    let mut basis = state.basis.clone();
    basis["parts"][0]["display_transform"] = json!(display);
    basis["bones"] = serde_json::to_value(frames).map_err(|e| e.to_string())?;
    basis["sample"] = json!({"clip_id":t.clip_id,"position_seconds":t.position_seconds,"playing":t.playing,"stream_frame":state.stream_frame,"serial":null,"scope":"live actual bone transforms; published serial checked by requested full capture"});
    update(world, state, &basis, false)
}

fn bounds(positions: &[[f32; 3]], transform: Mat4) -> Result<Value, String> {
    if positions.is_empty() {
        return Err("empty accessory bounds".into());
    }
    let mut min = Vec3::splat(f32::INFINITY);
    let mut max = Vec3::splat(f32::NEG_INFINITY);
    for p in positions {
        let p = transform.transform_point3(Vec3::from_array(*p));
        if !p.is_finite() {
            return Err("nonfinite actual upload bounds".into());
        }
        min = min.min(p);
        max = max.max(p);
    }
    Ok(json!({"min":min.to_array(),"max":max.to_array()}))
}
fn require_asset_resources(world: &World) -> Result<(), String> {
    if world.get_resource::<Assets<Mesh>>().is_none()
        || world.get_resource::<Assets<StandardMaterial>>().is_none()
        || world.get_resource::<Assets<Image>>().is_none()
    {
        return Err("current accessory mesh/material/image resource missing".into());
    }
    Ok(())
}
/// Production-called readback seam: current entity material -> actual texture -> image bytes.
fn observe_material(world: &World, live: &Live, pixels: bool) -> Result<Value, String> {
    require_asset_resources(world)?;
    let handle = &world
        .get::<MeshMaterial3d<StandardMaterial>>(live.entity)
        .ok_or("actual accessory material component missing")?
        .0;
    if handle != &live.material {
        return Err("actual entity material binding mismatch".into());
    }
    let material = world
        .resource::<Assets<StandardMaterial>>()
        .get(handle)
        .ok_or("actual accessory material asset missing")?;
    let texture = material
        .base_color_texture
        .as_ref()
        .ok_or("actual accessory texture absent")?;
    if texture != &live.image
        || material.base_color != Color::WHITE
        || material.alpha_mode != AlphaMode::Mask(0.5)
        || material.perceptual_roughness != 0.7
        || material.metallic != 0.
        || material.double_sided != live.hair
        || material.cull_mode
            != if live.hair {
                None
            } else {
                Some(bevy::render::render_resource::Face::Back)
            }
    {
        return Err("actual accessory material policy/binding mismatch".into());
    }
    let image = world
        .resource::<Assets<Image>>()
        .get(texture)
        .ok_or("actual bound accessory image missing")?;
    if image.width() != live.image_size
        || image.height() != live.image_size
        || image.texture_descriptor.format != TextureFormat::Rgba8UnormSrgb
    {
        return Err("actual accessory image domain changed".into());
    }
    let data = image
        .data
        .as_ref()
        .ok_or("actual bound image CPU pixels absent")?;
    if data.len() != live.image_size as usize * live.image_size as usize * 4 {
        return Err("actual accessory pixel coverage changed".into());
    }
    let actual_hash = if pixels {
        let hash = format!("{:x}", Sha256::digest(data));
        if hash != live.pixels_sha {
            return Err("actual bound image pixels differ from authenticated decode".into());
        }
        Some(hash)
    } else {
        None
    };
    Ok(
        json!({"handle":format!("{:?}",handle.id()),"base_color":format!("{:?}",material.base_color),"roughness":material.perceptual_roughness,"metallic":material.metallic,"alpha":format!("{:?}",material.alpha_mode),"double_sided":material.double_sided,"cull_mode":format!("{:?}",material.cull_mode),"texture":live.texture,"image_handle":format!("{:?}",texture.id()),"image_width":image.width(),"image_height":image.height(),"format":format!("{:?}",image.texture_descriptor.format),"decoded_rgba_sha256":actual_hash,"observation":"current entity MeshMaterial3d -> Assets<StandardMaterial> -> actual base_color_texture -> Assets<Image> CPU bytes"}),
    )
}
pub fn compact(state: &State) -> Value {
    let mut v = state.frame.clone();
    if let Some(rows) = v["accessories"].as_array_mut() {
        for row in rows {
            if let Some(o) = row.as_object_mut() {
                for k in [
                    "rest_model_m",
                    "rest_normals",
                    "full_normalized_positive_influences",
                    "positions",
                    "normals",
                    "uv_0",
                    "indices",
                    "source_uv_pairs",
                ] {
                    o.remove(k);
                }
            }
        }
    }
    if let Some(o) = v.as_object_mut() {
        o.remove("actual_skin_matrices");
    }
    v
}
#[cfg(test)]
mod tests {
    use super::*;
    fn observation_fixture() -> (World, Live) {
        let p = prepare().unwrap().remove(0);
        let image = Image::from_buffer(
            p.png,
            ImageType::Extension("png"),
            CompressedImageFormats::NONE,
            true,
            ImageSampler::default(),
            RenderAssetUsages::default(),
        )
        .unwrap();
        let pixels_sha = format!("{:x}", Sha256::digest(image.data.as_ref().unwrap()));
        let mut world = World::new();
        world.init_resource::<Assets<Image>>();
        world.init_resource::<Assets<Mesh>>();
        world.init_resource::<Assets<StandardMaterial>>();
        let image = world.resource_mut::<Assets<Image>>().add(image);
        let material = world
            .resource_mut::<Assets<StandardMaterial>>()
            .add(StandardMaterial {
                base_color: Color::WHITE,
                base_color_texture: Some(image.clone()),
                perceptual_roughness: 0.7,
                metallic: 0.,
                alpha_mode: AlphaMode::Mask(0.5),
                cull_mode: Some(bevy::render::render_resource::Face::Back),
                double_sided: false,
                ..default()
            });
        let entity = world
            .spawn((AccessoryTag, MeshMaterial3d(material.clone())))
            .id();
        let live = Live {
            name: p.name,
            entity,
            mesh: Handle::default(),
            material,
            image,
            rest: vec![],
            weights: vec![],
            rest_normals: vec![],
            obj: p.obj,
            scales: [1.; 3],
            pixels_sha,
            texture: p.texture,
            hair: false,
            image_size: p.size,
        };
        (world, live)
    }
    #[test]
    fn actual_material_observation_rejects_mutations() {
        let (mut world, live) = observation_fixture();
        let proof = observe_material(&world, &live, true).unwrap();
        assert_eq!(proof["double_sided"], false);
        assert_eq!(proof["cull_mode"], "Some(Back)");
        assert_eq!(proof["decoded_rgba_sha256"], live.pixels_sha);
        world
            .resource_mut::<Assets<StandardMaterial>>()
            .get_mut(&live.material)
            .unwrap()
            .double_sided = true;
        assert!(observe_material(&world, &live, true).is_err());
        world
            .resource_mut::<Assets<StandardMaterial>>()
            .get_mut(&live.material)
            .unwrap()
            .double_sided = false;
        world
            .resource_mut::<Assets<StandardMaterial>>()
            .get_mut(&live.material)
            .unwrap()
            .cull_mode = None;
        assert!(observe_material(&world, &live, true).is_err());
        world
            .resource_mut::<Assets<StandardMaterial>>()
            .get_mut(&live.material)
            .unwrap()
            .cull_mode = Some(bevy::render::render_resource::Face::Back);
        world
            .resource_mut::<Assets<StandardMaterial>>()
            .get_mut(&live.material)
            .unwrap()
            .alpha_mode = AlphaMode::Blend;
        assert!(observe_material(&world, &live, true).is_err());
        world
            .resource_mut::<Assets<StandardMaterial>>()
            .get_mut(&live.material)
            .unwrap()
            .alpha_mode = AlphaMode::Mask(0.5);
        world
            .resource_mut::<Assets<Image>>()
            .get_mut(&live.image)
            .unwrap()
            .data
            .as_mut()
            .unwrap()[0] ^= 1;
        assert!(observe_material(&world, &live, true).is_err());
        world
            .resource_mut::<Assets<Image>>()
            .get_mut(&live.image)
            .unwrap()
            .data
            .as_mut()
            .unwrap()[0] ^= 1;
        assert!(observe_material(&world, &live, true).is_ok());
        let wrong = world
            .resource_mut::<Assets<StandardMaterial>>()
            .add(StandardMaterial::default());
        world.entity_mut(live.entity).insert(MeshMaterial3d(wrong));
        assert!(observe_material(&world, &live, true).is_err());
        world
            .entity_mut(live.entity)
            .insert(MeshMaterial3d(live.material.clone()));
        world
            .resource_mut::<Assets<Image>>()
            .remove(live.image.id());
        assert!(observe_material(&world, &live, true).is_err());
    }
    #[test]
    fn early_stream_failure_disposes_previous_attachment() {
        let (mut world, live) = observation_fixture();
        let entity = live.entity;
        let material = live.material.clone();
        let image = live.image.clone();
        let mut state = State::default();
        state.live.push(live);
        state.key = json!({"old":true});
        state.frame = json!({"old":true});
        state.basis = json!({"character_entity":"missing"});
        assert!(stream(&mut world, &mut state).is_err());
        assert!(world.get_entity(entity).is_err());
        assert!(state.live.is_empty() && state.frame.is_null() && state.error.is_some());
        assert!(
            world
                .resource::<Assets<StandardMaterial>>()
                .get(&material)
                .is_none()
        );
        assert!(world.resource::<Assets<Image>>().get(&image).is_none());
    }
    #[test]
    fn missing_attachment_entity_reaches_update_error_and_disposes_sibling_assets() {
        let (mut world, mut live) = observation_fixture();
        live.rest = vec![[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]];
        live.rest_normals = vec![[0., 0., 1.]; 3];
        live.weights = vec![vec![(0, 1.)]; 3];
        live.obj = Obj {
            count: 3,
            pairs: vec![(0, 0), (1, 1), (2, 2)],
            uv: vec![[0., 0.], [1., 0.], [0., 1.]],
            indices: vec![0, 1, 2],
        };
        let mut mesh = Mesh::new(
            PrimitiveTopology::TriangleList,
            RenderAssetUsages::default(),
        );
        mesh.insert_attribute(
            Mesh::ATTRIBUTE_POSITION,
            vec![[0f32, 0., 0.], [1., 0., 0.], [0., 1., 0.]],
        );
        mesh.insert_attribute(Mesh::ATTRIBUTE_NORMAL, vec![[0f32, 0., 1.]; 3]);
        mesh.insert_attribute(Mesh::ATTRIBUTE_UV_0, live.obj.uv.clone());
        mesh.insert_indices(Indices::U32(live.obj.indices.clone()));
        live.mesh = world.resource_mut::<Assets<Mesh>>().add(mesh);
        world.entity_mut(live.entity).insert((
            Mesh3d(live.mesh.clone()),
            Transform::default(),
            GlobalTransform::default(),
        ));
        let mut sibling = live.clone();
        sibling.entity = world
            .spawn((
                AccessoryTag,
                Mesh3d(live.mesh.clone()),
                MeshMaterial3d(live.material.clone()),
                Transform::default(),
                GlobalTransform::default(),
            ))
            .id();
        let old_entity = live.entity;
        let sibling_entity = sibling.entity;
        let handles = (live.mesh.clone(), live.material.clone(), live.image.clone());
        let snapshot = json!({"generation":7,"revision":2,"character_entity":"fixture-character","parameters":{},"sample":{"serial":4},"bones":(0..53).map(|i|json!({"name":format!("fixture-bone-{i}"),"skin":DMat4::IDENTITY.to_cols_array()})).collect::<Vec<_>>(),"parts":[{"name":"body","mesh_handle":"fixture-body","display_transform":Mat4::IDENTITY.to_cols_array()}]});
        let mut state = State::default();
        state.key = json!({"generation":7,"revision":2,"character":"fixture-character","body":"fixture-body","parameters":{}});
        state.live = vec![live, sibling];
        state.frame = json!({"old":true});
        assert!(world.despawn(old_entity));
        assert!(world.resource::<Assets<Mesh>>().get(&handles.0).is_some());
        assert!(
            world
                .resource::<Assets<StandardMaterial>>()
                .get(&handles.1)
                .is_some()
        );
        assert!(world.resource::<Assets<Image>>().get(&handles.2).is_some());
        let outcome = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            sync(&mut world, &mut state, &snapshot, true)
        }));
        let error = outcome
            .expect("missing entity must return Err, never panic")
            .unwrap_err();
        assert!(error.contains("entity disappeared before transform update"));
        assert!(state.live.is_empty() && state.frame.is_null() && state.error.is_some());
        assert!(world.get_entity(sibling_entity).is_err());
        assert!(world.resource::<Assets<Mesh>>().get(&handles.0).is_none());
        assert!(
            world
                .resource::<Assets<StandardMaterial>>()
                .get(&handles.1)
                .is_none()
        );
        assert!(world.resource::<Assets<Image>>().get(&handles.2).is_none());
    }
    #[test]
    fn fixed_inputs_parse_and_authenticate() {
        let p = prepare().unwrap();
        assert_eq!(p[0].obj.count, 96);
        assert_eq!(p[1].obj.count, 865);
        assert!(
            p[1].mapping
                .rows
                .iter()
                .any(|r| r.coefficients.iter().any(|x| *x < 0.))
        );
    }
    #[test]
    fn signed_final_transfer_keeps_more_than_four() {
        let m = Mapping {
            rows: vec![Row {
                helpers: vec![0, 1],
                coefficients: vec![2., -1.],
                offset: [0.; 3],
            }],
            scales: [(0, 1, 1.); 3],
        };
        let source = vec![
            vec![0.2, 0.3],
            vec![0.1, 0.],
            vec![0.1, 0.],
            vec![0.1, 0.],
            vec![0.1, 0.],
            vec![0., 0.5],
        ];
        let w = transfer(&m, &source).unwrap();
        assert_eq!(w[0].len(), 5);
        assert!((w[0][0].1 - 1. / 9.).abs() < 1e-12);
        assert!(!w[0].iter().any(|x| x.0 == 5));
    }
    #[test]
    fn cage_requires_complete_and_consistent() {
        assert!(
            cage(&json!({"source_ids":[0,0],"rest_positions":[[0.,0.,0.],[1.,0.,0.]]})).is_err()
        );
        assert!(cage(&json!({"source_ids":[0],"rest_positions":[[0.,0.,0.]]})).is_err());
    }
    #[test]
    fn bad_mappings_and_uv_reject() {
        assert!(mapping("obj_file a\nx_scale 0 1 0\nverts 0\n0", 1).is_err());
        assert!(obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3", 3).is_err());
        assert!(obj("v 0 0 0\nvt 0 0\nf 1/2 1/1 1/1", 1).is_err());
    }
    #[test]
    fn exactly_once_placement() {
        let rest = vec![[1., 2., 3.]];
        let n = vec![[0., 1., 0.]];
        let w = vec![vec![(0, 1.)]];
        let (p, _) = skin(&rest, &n, &w, &[DMat4::IDENTITY]).unwrap();
        let display = Mat4::from_translation(Vec3::new(4., 5., 6.));
        assert_eq!(
            display.transform_point3(Vec3::from_array(p[0])),
            Vec3::new(5., 7., 9.)
        );
    }
}

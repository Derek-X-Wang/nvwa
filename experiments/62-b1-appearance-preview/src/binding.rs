//! Exact fitted-source UV correspondence. No source-ID-only UV remapping.
use crate::hash;
use bevy::{mesh::VertexAttributeValues, prelude::*};
use humentity::prelude::*;
use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet};

pub struct Binding {
    pub entity: Entity,
    pub mesh: Handle<Mesh>,
    pub material: Handle<StandardMaterial>,
    pub uv: Vec<[f32; 2]>,
    pub proof: Value,
}
fn f3(mesh: &Mesh) -> Result<&Vec<[f32; 3]>, String> {
    match mesh.attribute(Mesh::ATTRIBUTE_POSITION) {
        Some(VertexAttributeValues::Float32x3(v)) => Ok(v),
        _ => Err("source POSITION absent".into()),
    }
}
fn uv(mesh: &Mesh) -> Result<Vec<[f32; 2]>, String> {
    match mesh.attribute(Mesh::ATTRIBUTE_UV_0) {
        Some(VertexAttributeValues::Float32x2(v)) if v.iter().flatten().all(|n| n.is_finite()) => {
            Ok(v.clone())
        }
        _ => Err("source finite UV_0 absent".into()),
    }
}
fn indices(mesh: &Mesh) -> Result<Vec<usize>, String> {
    Ok(mesh
        .indices()
        .ok_or("source indices absent")?
        .iter()
        .collect())
}
pub fn resolve(world: &mut World, snapshot: &Value) -> Result<Binding, String> {
    let body = snapshot["parts"]
        .as_array()
        .ok_or("snapshot parts absent")?
        .iter()
        .find(|p| p["name"] == "body")
        .ok_or("body absent")?;
    let character_label = snapshot["character_entity"]
        .as_str()
        .ok_or("character identity absent")?;
    let characters: Vec<_> = world
        .query::<(Entity, &CharacterShape)>()
        .iter(world)
        .filter(|(e, _)| format!("{e:?}") == character_label)
        .map(|(e, s)| (e, s.0.clone()))
        .collect();
    if characters.len() != 1 {
        return Err("ambiguous/missing actual character shape".into());
    }
    let (character, shape) = characters[0].clone();
    let template = world
        .resource::<Assets<CharacterShapeAsset>>()
        .get(&shape)
        .ok_or("current shape missing")?
        .template
        .clone();
    let parts: Vec<_> = world
        .query::<(&CharacterPart, &ChildOf)>()
        .iter(world)
        .filter(|(_, p)| p.parent() == character)
        .filter_map(|(p, _)| {
            let path = world.resource::<AssetServer>().get_path(p.mesh.id())?;
            (path.to_string() == "nvwa-b1-verified://body.mhclo").then_some(p.mesh.clone())
        })
        .collect();
    if parts.len() != 1 {
        return Err("ambiguous/missing active source body part".into());
    }
    let fitted_handle = world
        .resource::<CachedMhcloMeshHandles>()
        .get(&(parts[0].clone(), template, MeshBuildLod::Cpu(0)))
        .cloned()
        .ok_or("current fitted source mesh not cached")?;
    let server = world.resource::<AssetServer>();
    let raw_handle = server
        .get_handle::<Mesh>("nvwa-b1-verified://base.obj")
        .ok_or("original loaded body mesh absent")?;
    let verts_handle = server
        .get_handle::<ObjVertsAsset>("nvwa-b1-verified://base.obj")
        .ok_or("original source vertex snapshot absent")?;
    let display_label = body["display_entity"]
        .as_str()
        .ok_or("display identity absent")?;
    let displays: Vec<_> = world
        .query::<(Entity, &Mesh3d, &MeshMaterial3d<StandardMaterial>)>()
        .iter(world)
        .filter(|(e, _, _)| format!("{e:?}") == display_label)
        .map(|(e, m, t)| (e, m.0.clone(), t.0.clone()))
        .collect();
    if displays.len() != 1 {
        return Err("ambiguous/missing actual displayed body".into());
    }
    let (entity, mesh, material) = displays[0].clone();
    if body["mesh_handle"] != format!("{:?}", mesh.id()) {
        return Err("snapshot/display mesh binding mismatch".into());
    }
    let meshes = world.resource::<Assets<Mesh>>();
    let fitted = meshes
        .get(&fitted_handle)
        .ok_or("fitted mesh unavailable")?;
    let raw = meshes.get(&raw_handle).ok_or("original mesh unavailable")?;
    let rawverts = world
        .resource::<Assets<ObjVertsAsset>>()
        .get(&verts_handle)
        .ok_or("original vertex asset unavailable")?;
    let ids = generate_mhid_lookup(&generate_vertex_map(
        &rawverts.vertices,
        &get_vertex_positions(raw),
    ));
    let actual_ids: Vec<u16> =
        serde_json::from_value(body["source_ids"].clone()).map_err(|e| e.to_string())?;
    if ids != actual_ids {
        return Err("source/render duplicate vertex IDs or order mismatch".into());
    }
    let source_uv = uv(fitted)?;
    if source_uv != uv(raw)? || source_uv.len() != ids.len() {
        return Err("fitted/source UV duplicate-order correspondence mismatch".into());
    }
    let full = indices(fitted)?;
    if full != indices(raw)? {
        return Err("fitted/source triangle order mismatch".into());
    }
    let visible: Vec<usize> =
        serde_json::from_value(body["indices"].clone()).map_err(|e| e.to_string())?;
    if full.len() % 3 != 0 || visible.is_empty() || visible.len() % 3 != 0 {
        return Err("invalid triangle arrays".into());
    }
    let mut cursor = 0;
    for tri in full.chunks_exact(3) {
        if cursor < visible.len() && tri == &visible[cursor..cursor + 3] {
            cursor += 3;
        }
    }
    if cursor != visible.len() {
        return Err("displayed triangles are not ordered source triangles".into());
    }
    let base = f3(fitted)?;
    let morph = fitted.morph_targets().ok_or("fitted morph absent")?;
    let rest: Vec<[f32; 3]> =
        serde_json::from_value(body["rest_positions"].clone()).map_err(|e| e.to_string())?;
    if base.len() != ids.len() || morph.len() != ids.len() || rest.len() != ids.len() {
        return Err("fitted rest duplicate coverage mismatch".into());
    }
    let mut max_error = 0f32;
    for i in 0..ids.len() {
        let fitted = (Vec3::from_array(base[i]) + morph[i].position).to_array();
        if !fitted.iter().all(|x| x.is_finite()) {
            return Err("nonfinite fitted source rest".into());
        }
        for j in 0..3 {
            max_error = max_error.max((fitted[j] - rest[i][j]).abs());
        }
    }
    if !max_error.is_finite() || max_error > 1e-6 {
        return Err(format!(
            "current fitted rest correspondence error {max_error}"
        ));
    }
    let mut seams: BTreeMap<u16, BTreeSet<(u32, u32)>> = BTreeMap::new();
    for (id, uv) in ids.iter().zip(&source_uv) {
        seams
            .entry(*id)
            .or_default()
            .insert((uv[0].to_bits(), uv[1].to_bits()));
    }
    let proof = json!({"method":"active CharacterShape+CharacterPart+Cpu(0) fitted cache; raw original duplicate-order IDs; full fitted rest and ordered displayed triangle subsequence","source":"nvwa-b1-verified://base.obj","source_mesh":format!("{:?}",raw_handle.id()),"fitted_source_mesh":format!("{:?}",fitted_handle.id()),"render_vertices":ids.len(),"source_vertices":seams.len(),"source_ids_sha256":hash(&ids)?,"source_full_indices_sha256":hash(&full)?,"visible_indices_sha256":hash(&visible)?,"uv_sha256":hash(&source_uv)?,"uv_seam_source_vertices":seams.values().filter(|v|v.len()>1).count(),"rest_max_component_error":max_error,"v_transform":"verbatim actual Mesh UV_0; no additional V flip","uv_0":source_uv});
    Ok(Binding {
        entity,
        mesh,
        material,
        uv: source_uv,
        proof,
    })
}

//! Isolated source-face colors and one explicitly authored post-LBS point target.
//! Production handles restored before Update; no product input, fit, weights or body mask changes.
use crate::diagnostic::Mode;
use bevy::camera::primitives::{Aabb, MeshAabb};
use bevy::{mesh::VertexAttributeValues, prelude::*};
use nvwa_core::appearance_sha256;
use serde::Deserialize;
use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet};
const OBJ_SHA: &str = "f9f91788c1dd2918fceedd4dd4ada520f56fb8dfd68cbbeb9a4f6bfbd8e101a9";
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Target {
    candidate_id: String,
    source_obj_sha256: String,
    source_id: u16,
    delta_clavicle_m: [f32; 3],
    baseline_request_id: String,
    body_highlight_request_id: String,
    garment_highlight_request_id: String,
}
#[derive(Clone)]
struct Proof {
    mode: Mode,
    identity: Value,
}
struct Swap {
    entity: Entity,
    original: Handle<Mesh>,
    diagnostic: Handle<Mesh>,
    positions: Vec<[f32; 3]>,
    indices: Vec<usize>,
    original_aabb: Option<Aabb>,
    diagnostic_aabb: Aabb,
}
#[derive(Default)]
pub struct State {
    target: Option<Target>,
    target_sha: Option<String>,
    proofs: BTreeMap<String, Proof>,
    swap: Option<Swap>,
    key: String,
    observation: Value,
    restore_error: Option<String>,
    pre_witness: Value,
    last_witness: Value,
    expected_publication_key: String,
}
fn array16(value: &Value) -> Result<[f32; 16], String> {
    serde_json::from_value(value.clone()).map_err(|e| e.to_string())
}
fn hash_json(v: &Value) -> String {
    appearance_sha256(v.to_string().as_bytes())
}
fn rotation(value: &Value) -> Result<Quat, String> {
    let a = array16(value)?;
    if a.iter().any(|v| !v.is_finite()) {
        return Err("nonfinite actual bone matrix".into());
    }
    let (scale, q, _) = Mat4::from_cols_array(&a).to_scale_rotation_translation();
    if (scale - Vec3::ONE).abs().max_element() > 1e-4 || !q.is_finite() {
        return Err("nonrigid actual bone frame".into());
    }
    Ok(q.normalize())
}
pub fn activation(rest: Quat, posed: Quat) -> f32 {
    let q = (rest.inverse() * posed).normalize();
    // f32 quaternion arithmetic rounds the authenticated neutral relation to identity.
    let angle = 2. * q.w.abs().clamp(0., 1.).acos();
    let u = (angle / std::f32::consts::FRAC_PI_4).clamp(0., 1.);
    u * u * (3. - 2. * u)
}
fn delta_for(frame: &Value, target: &Target) -> Result<(Vec3, f32), String> {
    let bones = frame["full_base"]["bones"]
        .as_array()
        .ok_or("actual bones absent")?;
    let arm = bones
        .iter()
        .find(|b| b["name"] == "upperarm_l")
        .ok_or("upperarm_l absent")?;
    let clavicle = bones
        .iter()
        .find(|b| b["name"] == "clavicle_l")
        .ok_or("clavicle_l absent")?;
    let weight = activation(
        rotation(&arm["local_rest"])?,
        rotation(&arm["local_posed"])?,
    );
    let orientation = rotation(&clavicle["canonical_posed"])?;
    Ok((
        orientation * Vec3::from_array(target.delta_clavicle_m) * weight,
        weight,
    ))
}
fn selected(role: &str, tri: &[u16]) -> bool {
    let mut ids = tri.to_vec();
    ids.sort_unstable();
    let fans: &[[u16; 3]] = if role == "body" {
        &[[8319, 8318, 8309], [8319, 8309, 8310]]
    } else {
        &[[830, 168, 212], [830, 212, 847]]
    };
    fans.iter().any(|t| {
        let mut t = *t;
        t.sort_unstable();
        ids == t
    })
}
impl State {
    pub fn has_target(&self) -> bool {
        self.target.is_some()
    }
    pub fn author(&mut self, raw: &str, sha: &str) -> Result<(), String> {
        if self.target.is_some() {
            return Err("one target already authored; replacement rejected".into());
        }
        if appearance_sha256(raw.as_bytes()) != sha {
            return Err("target bytes/SHA256 mismatch".into());
        }
        let t: Target = serde_json::from_str(raw).map_err(|e| e.to_string())?;
        if t.candidate_id != "nvwa-source847-pose-target-v1"
            || t.source_obj_sha256 != OBJ_SHA
            || t.source_id != 847
            || t.delta_clavicle_m.iter().any(|v| !v.is_finite())
            || Vec3::from_array(t.delta_clavicle_m).length() > 0.02
            || Vec3::from_array(t.delta_clavicle_m).length() == 0.
        {
            return Err("target identity/support/finite20mm authoring bound invalid".into());
        }
        let proofs = [
            (&t.baseline_request_id, Mode::Combined),
            (&t.body_highlight_request_id, Mode::SourceBody),
            (&t.garment_highlight_request_id, Mode::SourceGarment),
        ];
        let mut identity = None;
        for (id, mode) in proofs {
            let p = self
                .proofs
                .get(id)
                .ok_or("target needs actual prior baseline/body/garment source captures")?;
            if p.mode != mode || identity.as_ref().is_some_and(|v| v != &p.identity) {
                return Err("source confirmations have different actual identities".into());
            }
            identity = Some(p.identity.clone());
        }
        self.target = Some(t);
        self.target_sha = Some(sha.to_owned());
        self.key.clear();
        Ok(())
    }
    pub fn restore(&mut self, world: &mut World) {
        if let Some(s) = &self.swap {
            match world.get::<Mesh3d>(s.entity) {
                Some(m) if m.0 == s.diagnostic || m.0 == s.original => {
                    world
                        .entity_mut(s.entity)
                        .insert(Mesh3d(s.original.clone()));
                    match s.original_aabb {
                        Some(a) => {
                            world.entity_mut(s.entity).insert(a);
                        }
                        None => {
                            world.entity_mut(s.entity).remove::<Aabb>();
                        }
                    }
                }
                _ => {
                    self.restore_error =
                        Some("source diagnostic entity/mesh changed outside its owned swap".into())
                }
            }
        }
    }
    pub fn clear(&mut self, world: &mut World) {
        self.restore(world);
        if let Some(s) = self.swap.take() {
            world
                .resource_mut::<Assets<Mesh>>()
                .remove(s.diagnostic.id());
        }
        self.key.clear();
        self.observation = Value::Null;
        self.pre_witness = Value::Null;
        self.last_witness = Value::Null;
        self.expected_publication_key.clear();
    }
    pub fn apply(&mut self, world: &mut World, frame: &Value, mode: Mode) -> Result<Value, String> {
        if let Some(error) = self.restore_error.take() {
            return Err(error);
        }
        let key = format!(
            "{}:{mode:?}:{}",
            frame["request_id"],
            self.target_sha.as_deref().unwrap_or("NONE")
        );
        if self.key == key {
            if let Some(s) = &self.swap {
                if world
                    .get::<Mesh3d>(s.entity)
                    .is_none_or(|m| m.0 != s.original)
                {
                    return Err("production mesh binding changed before diagnostic swap".into());
                }
                let meshes = world.resource::<Assets<Mesh>>();
                let actual = meshes.get(&s.original).ok_or("original mesh removed")?;
                let Some(VertexAttributeValues::Float32x3(actual_positions)) =
                    actual.attribute(Mesh::ATTRIBUTE_POSITION)
                else {
                    return Err("original position type changed".into());
                };
                if *actual_positions != s.positions
                    || actual
                        .indices()
                        .ok_or("original indices removed")?
                        .iter()
                        .collect::<Vec<_>>()
                        != s.indices
                {
                    return Err(
                        "source mesh contents changed after correlated capture; recapture required"
                            .into(),
                    );
                }
                world
                    .entity_mut(s.entity)
                    .insert((Mesh3d(s.diagnostic.clone()), s.diagnostic_aabb));
            }
            return Ok(self.observation.clone());
        }
        self.clear(world);
        let id = frame["request_id"]
            .as_str()
            .ok_or("capture request ID absent")?
            .to_owned();
        if mode == Mode::Combined {
            self.observation = json!({"mode":"baseline","target_active":false,"target_authored":self.target_sha,"geometry":"unchanged production mesh/materials","scope":"CPU state, not GPU ownership"});
            self.key = key;
            self.expected_publication_key = self.actual_publication(world, frame)?["key_sha256"]
                .as_str()
                .ok_or("publication key absent")?
                .to_owned();
            return Ok(self.observation.clone());
        }
        let role = if mode == Mode::SourceBody {
            "body"
        } else {
            "garment"
        };
        let part = frame["full_base"]["parts"]
            .as_array()
            .ok_or("parts absent")?
            .iter()
            .find(|p| p["name"] == role)
            .ok_or("source diagnostic part absent")?;
        let ids: Vec<u16> =
            serde_json::from_value(part["source_ids"].clone()).map_err(|e| e.to_string())?;
        let indices: Vec<usize> =
            serde_json::from_value(part["indices"].clone()).map_err(|e| e.to_string())?;
        let actual_positions: Vec<[f32; 3]> =
            serde_json::from_value(part["positions"].clone()).map_err(|e| e.to_string())?;
        let entities: Vec<_> = world
            .iter_entities()
            .filter(|e| json!(format!("{:?}", e.id())) == part["display_entity"])
            .map(|e| e.id())
            .collect();
        if entities.len() != 1 {
            return Err("source display entity absent/ambiguous".into());
        }
        let entity = entities[0];
        let original = world
            .get::<Mesh3d>(entity)
            .ok_or("actual mesh absent")?
            .0
            .clone();
        if json!(format!("{:?}", original.id())) != part["mesh_handle"] {
            return Err("actual source handle differs from capture".into());
        }
        let mut changed = world
            .resource::<Assets<Mesh>>()
            .get(&original)
            .ok_or("source mesh absent")?
            .clone();
        let Some(VertexAttributeValues::Float32x3(pos)) =
            changed.attribute(Mesh::ATTRIBUTE_POSITION)
        else {
            return Err("source positions not Float32x3".into());
        };
        if *pos != actual_positions || ids.len() != pos.len() {
            return Err("actual render/source position binding differs".into());
        }
        let selected_triangles: Vec<_> = indices
            .chunks_exact(3)
            .enumerate()
            .filter_map(|(i, t)| {
                selected(role, &t.iter().map(|i| ids[*i]).collect::<Vec<_>>()).then_some(i)
            })
            .collect();
        let original_material = world
            .get::<MeshMaterial3d<StandardMaterial>>(entity)
            .ok_or("actual material absent")?
            .0
            .clone();
        let observation = if mode != Mode::Corrective {
            if selected_triangles.len() != 2 {
                return Err("exact source quad fan missing/ambiguous".into());
            }
            if let Some(colors) = changed.attribute(Mesh::ATTRIBUTE_COLOR) {
                if !matches!(colors,VertexAttributeValues::Float32x4(v) if v.iter().all(|c|*c==[1.;4]))
                {
                    return Err(
                        "nonwhite source vertex colors would change nonselected faces".into(),
                    );
                }
            }
            changed
                .try_duplicate_vertices()
                .map_err(|e| e.to_string())?;
            let mut colors = vec![[1.; 4]; indices.len()];
            for &tri in &selected_triangles {
                for c in &mut colors[tri * 3..tri * 3 + 3] {
                    *c = if role == "body" {
                        [0., 1., 0., 1.]
                    } else {
                        [1., 0., 1., 1.]
                    };
                }
            }
            changed.insert_attribute(Mesh::ATTRIBUTE_COLOR, colors);
            let Some(VertexAttributeValues::Float32x3(expanded)) =
                changed.attribute(Mesh::ATTRIBUTE_POSITION)
            else {
                return Err("expanded positions absent".into());
            };
            if expanded.len() != indices.len()
                || expanded
                    .iter()
                    .zip(&indices)
                    .any(|(p, i)| p != &actual_positions[*i])
            {
                return Err("diagnostic changed ordered triangle geometry".into());
            }
            json!({"mode":format!("{mode:?}"),"role":role,"source_face0":if role=="body"{7941}else{131},"source_quad_ids":if role=="body"{vec![8319,8318,8309,8310]}else{vec![830,168,212,847]},"source_render_triangles0":selected_triangles,"display_entity":part["display_entity"],"original_mesh":part["mesh_handle"],"ordered_triangle_positions_preserved":true,"all_attributes_duplicated_by_existing_Bevy_API":true,"only_selected_fan_vertex_colors_changed":true,"material_handle":format!("{:?}",original_material.id()),"material_visibility_culling_and_depth_unchanged":true,"target_active":false,"scope":"Actual rendered source-face vertex-color diagnostic; geometry/depth unchanged. CPU binding + screenshot is correspondence evidence, not GPU object-ID readback."})
        } else {
            let target = self.target.as_ref().ok_or("no authored one-shot target")?;
            let (delta, weight) = delta_for(frame, target)?;
            let mut corrected = actual_positions.clone();
            let mut moved = Vec::new();
            for (i, p) in corrected.iter_mut().enumerate() {
                if ids[i] == target.source_id {
                    *p = (Vec3::from_array(*p) + delta).to_array();
                    moved.push(i);
                }
            }
            if moved.is_empty() {
                return Err("source847 not present in actual mesh".into());
            }
            let affected: BTreeSet<_> = indices
                .chunks_exact(3)
                .filter(|t| t.iter().any(|i| ids[*i] == 847))
                .flat_map(|t| t.iter().map(|i| ids[*i]))
                .collect();
            changed.insert_attribute(Mesh::ATTRIBUTE_POSITION, corrected.clone());
            if weight > 0. {
                let Some(VertexAttributeValues::Float32x3(normals)) =
                    changed.attribute(Mesh::ATTRIBUTE_NORMAL)
                else {
                    return Err("normal attribute absent".into());
                };
                let mut normals = normals.clone();
                let mut recomputed = changed.clone();
                recomputed.compute_normals();
                let Some(VertexAttributeValues::Float32x3(new_normals)) =
                    recomputed.attribute(Mesh::ATTRIBUTE_NORMAL)
                else {
                    return Err("recomputed normals absent".into());
                };
                for (i, n) in normals.iter_mut().enumerate() {
                    if affected.contains(&ids[i]) {
                        *n = new_normals[i];
                    }
                }
                changed.insert_attribute(Mesh::ATTRIBUTE_NORMAL, normals);
            }
            let actual_indices = changed
                .indices()
                .ok_or("corrective lost indices")?
                .iter()
                .collect::<Vec<_>>();
            if actual_indices != indices {
                return Err("corrective changed topology".into());
            }
            json!({"mode":"Corrective","candidate_id":target.candidate_id,"target_sha256":self.target_sha,"source_id":847,"delta_clavicle_m":target.delta_clavicle_m,"actual_arm_angle_weight":weight,"delta_mesh_local_m":delta.to_array(),"changed_render_vertex_indices":moved,"normal_source_support":affected,"source_rest_fit_fullpositive_weights_body_mask_topology_materials":"unchanged; correction is explicit post-LBS displayed delta","target_active":weight>0.,"corrected_positions":corrected,"corrected_positions_sha256":hash_json(&json!(corrected)),"material_handle":format!("{:?}",original_material.id()),"scope":"Isolated corrective mesh, not saved Work capability or source replacement; no collision/quality claim"})
        };
        let diagnostic_aabb = changed
            .compute_aabb()
            .ok_or("diagnostic mesh bounds absent")?;
        let original_aabb = world.get::<Aabb>(entity).copied();
        let diagnostic = world.resource_mut::<Assets<Mesh>>().add(changed);
        world
            .entity_mut(entity)
            .insert((Mesh3d(diagnostic.clone()), diagnostic_aabb));
        self.swap = Some(Swap {
            entity,
            original,
            diagnostic,
            positions: actual_positions,
            indices,
            original_aabb,
            diagnostic_aabb,
        });
        self.key = key;
        self.observation = observation;
        self.expected_publication_key = self.actual_publication(world, frame)?["key_sha256"]
            .as_str()
            .ok_or("publication key absent")?
            .to_owned();
        Ok(self.observation.clone())
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn activation_uses_pose_is_smooth_bounded_and_neutral_zero() {
        assert_eq!(activation(Quat::IDENTITY, Quat::IDENTITY), 0.);
        assert_eq!(
            activation(
                Quat::IDENTITY,
                Quat::from_rotation_z(std::f32::consts::FRAC_PI_4)
            ),
            1.
        );
        let values = (0..101)
            .map(|i| {
                activation(
                    Quat::IDENTITY,
                    Quat::from_rotation_z(i as f32 * 0.01 * std::f32::consts::FRAC_PI_4),
                )
            })
            .collect::<Vec<_>>();
        assert!(values.windows(2).all(|v| v[0] <= v[1]));
        assert!(values.iter().all(|v| (0. ..=1.).contains(v)));
        assert!((values[50] - 0.5).abs() < 1e-5);
    }
    #[test]
    fn actual_historical_three_torso_pose_matrices_give_zero_neutral_knee_and_bounded_adjacent_activation()
     {
        let fixture: Value = serde_json::from_str(include_str!(
            "../fixtures/historical-actual-activation.json"
        ))
        .unwrap();
        let target:Target=serde_json::from_value(json!({"candidate_id":"nvwa-source847-pose-target-v1","source_obj_sha256":OBJ_SHA,"source_id":847,"delta_clavicle_m":[0.001,0.,0.],"baseline_request_id":"synthetic-test","body_highlight_request_id":"synthetic-test","garment_highlight_request_id":"synthetic-test"})).unwrap();
        let cases = fixture["cases"].as_array().unwrap();
        assert_eq!(cases.len(), 18);
        for case in cases {
            let frame = json!({"full_base":{"bones":case["bones"]}});
            let (delta, weight) = delta_for(&frame, &target).unwrap();
            assert!(weight.is_finite() && (0. ..=1.).contains(&weight));
            if case["clip"] == "b1_knee_flex_v1" || case["seconds"] == 0 || case["seconds"] == 4 {
                assert_eq!(weight, 0., "{case}");
                assert_eq!(delta, Vec3::ZERO);
            } else if case["seconds"] == 2 {
                assert!((weight - 1.).abs() < 1e-6, "{case}");
                assert!((delta.length() - 0.001).abs() < 1e-6);
            } else {
                assert!(weight > 0. && weight < 1., "{case}");
            }
        }
    }
    #[test]
    fn source_faces_have_exact_fans() {
        assert!(selected("body", &[8319, 8309, 8310]));
        assert!(selected("garment", &[830, 212, 847]));
        assert!(!selected("garment", &[246, 244, 182]));
        assert!(!selected("garment", &[830, 212, 841]));
    }
    #[test]
    fn target_authoring_is_bound_to_hash_support_and_three_same_actual_identities() {
        let mut state = State::default();
        let value = json!({"candidate_id":"nvwa-source847-pose-target-v1","source_obj_sha256":OBJ_SHA,"source_id":847,"delta_clavicle_m":[0.,0.003,0.],"baseline_request_id":"a","body_highlight_request_id":"b","garment_highlight_request_id":"g"});
        let raw = value.to_string();
        let sha = appearance_sha256(raw.as_bytes());
        assert!(state.author(&raw, &sha).is_err());
        for (id, mode) in [
            ("a", Mode::Combined),
            ("b", Mode::SourceBody),
            ("g", Mode::SourceGarment),
        ] {
            state.proofs.insert(
                id.into(),
                Proof {
                    mode,
                    identity: json!({"actual":"same"}),
                },
            );
        }
        assert!(state.author(&raw, "bad").is_err());
        for (field, bad) in [("source_id", json!(848)), ("unknown", json!(true))] {
            let mut changed = value.clone();
            changed[field] = bad;
            let raw = changed.to_string();
            assert!(
                state
                    .author(&raw, &appearance_sha256(raw.as_bytes()))
                    .is_err()
            );
        }
        state.proofs.get_mut("g").unwrap().identity = json!({"actual":"different"});
        assert!(state.author(&raw, &sha).is_err());
        state.proofs.get_mut("g").unwrap().identity = json!({"actual":"same"});
        state.author(&raw, &sha).unwrap();
        assert!(state.has_target());
        assert!(state.author(&raw, &sha).is_err());
    }
}
fn aabb_record(a: Option<&Aabb>) -> Value {
    a.map(|a| json!({"center":a.center.to_array(),"half_extents":a.half_extents.to_array()}))
        .unwrap_or(Value::Null)
}
fn mesh_bytes_key(mesh: &Mesh) -> Result<Value, String> {
    fn floats(v: &[[f32; 3]]) -> String {
        let bytes = v
            .iter()
            .flat_map(|p| p.iter().flat_map(|x| x.to_bits().to_le_bytes()))
            .collect::<Vec<_>>();
        appearance_sha256(&bytes)
    }
    let Some(VertexAttributeValues::Float32x3(p)) = mesh.attribute(Mesh::ATTRIBUTE_POSITION) else {
        return Err("published positions absent".into());
    };
    let Some(VertexAttributeValues::Float32x3(n)) = mesh.attribute(Mesh::ATTRIBUTE_NORMAL) else {
        return Err("published normals absent".into());
    };
    let colors = match mesh.attribute(Mesh::ATTRIBUTE_COLOR) {
        Some(VertexAttributeValues::Float32x4(c)) => Some(appearance_sha256(
            &c.iter()
                .flat_map(|p| p.iter().flat_map(|x| x.to_bits().to_le_bytes()))
                .collect::<Vec<_>>(),
        )),
        None => None,
        _ => return Err("unexpected color attribute".into()),
    };
    let indices = mesh.indices().map(|i| i.iter().collect::<Vec<_>>());
    let attributes=mesh.try_attributes().map_err(|e|e.to_string())?.map(|(attribute,values)|json!({"id":format!("{:?}",attribute.id),"name":attribute.name,"format":format!("{:?}",attribute.format),"values":values.len(),"raw_bytes_sha256":appearance_sha256(values.get_bytes())})).collect::<Vec<_>>();
    let index_format = match mesh.indices() {
        Some(bevy::mesh::Indices::U16(_)) => Some("U16"),
        Some(bevy::mesh::Indices::U32(_)) => Some("U32"),
        None => None,
    };
    Ok(
        json!({"positions_sha256_le_f32":floats(p),"normals_sha256_le_f32":floats(n),"vertex_colors_sha256_le_f32":colors,"indices_sha256":hash_json(&json!(indices)),"vertex_count":p.len(),"index_count":indices.as_ref().map(Vec::len),"complete_rendered_attributes":attributes,"attribute_presence":"complete enumeration; absence changes this list/key","raw_byte_endianness":"native target, little-endian on this Mac and Wasm","index_format":index_format,"primitive_topology":format!("{:?}",mesh.primitive_topology())}),
    )
}
impl State {
    pub fn record_ready(&mut self, frame: &Value, mode: Mode) {
        if matches!(
            mode,
            Mode::Combined | Mode::SourceBody | Mode::SourceGarment
        ) && frame["stable_updates"].as_u64().is_some_and(|n| n >= 2)
            && frame["full_base"]["parameters"]["torso_length"] == 0.
            && frame["full_base"]["sample"]["clip_id"] == "b1_arm_rehearsal_v1"
            && frame["full_base"]["sample"]["source_seconds"] == 2.
        {
            if let Some(id) = frame["request_id"].as_str() {
                self.proofs.insert(
                    id.to_owned(),
                    Proof {
                        mode,
                        identity: frame["identity"].clone(),
                    },
                );
            }
        }
    }
    fn actual_publication(&self, world: &World, frame: &Value) -> Result<Value, String> {
        let mut records = Vec::new();
        for part in frame["full_base"]["parts"]
            .as_array()
            .ok_or("reference parts absent")?
        {
            let entity = world
                .iter_entities()
                .find(|e| json!(format!("{:?}", e.id())) == part["display_entity"])
                .ok_or("actual published entity absent")?;
            let handle = &entity.get::<Mesh3d>().ok_or("published Mesh3d absent")?.0;
            let expected = self
                .swap
                .as_ref()
                .filter(|s| s.entity == entity.id())
                .map(|s| &s.diagnostic);
            if expected.is_some_and(|h| h != handle)
                || (expected.is_none()
                    && json!(format!("{:?}", handle.id())) != part["mesh_handle"])
            {
                return Err(
                    "actual render mesh association differs from selected publication".into(),
                );
            }
            let mesh = world
                .resource::<Assets<Mesh>>()
                .get(handle)
                .ok_or("published asset absent")?;
            let aabb = entity.get::<Aabb>();
            let exact = mesh
                .compute_aabb()
                .ok_or("published mesh compute_aabb absent")?;
            if expected.is_some() && aabb_record(aabb) != aabb_record(Some(&exact)) {
                return Err("changed mesh AABB incoherent".into());
            }
            let material = &entity
                .get::<MeshMaterial3d<StandardMaterial>>()
                .ok_or("published material absent")?
                .0;
            let material_value = world
                .resource::<Assets<StandardMaterial>>()
                .get(material)
                .ok_or("published material asset absent")?;
            let transform = entity
                .get::<GlobalTransform>()
                .ok_or("published transform absent")?
                .to_matrix()
                .to_cols_array();
            if json!(transform) != part["display_transform"] {
                return Err("source display transform changed after reference capture".into());
            }
            records.push(json!({"role":part["name"],"entity":format!("{:?}",entity.id()),"production_mesh_handle":part["mesh_handle"],"actual_render_mesh_handle":format!("{:?}",handle.id()),"buffers":mesh_bytes_key(mesh)?,"actual_aabb":aabb_record(aabb),"computed_mesh_aabb":aabb_record(Some(&exact)),"changed_mesh_exact_bounds":expected.map(|_|true),"inherited_production_no_frustum_culling":entity.contains::<bevy::camera::visibility::NoFrustumCulling>(),"visibility":format!("{:?}",entity.get::<Visibility>()),"material_handle":format!("{:?}",material.id()),"material_debug_sha256":appearance_sha256(format!("{material_value:?}").as_bytes()),"display_transform":transform}));
        }
        let value = json!({"parts":records,"camera":crate::camera_report(world),"work_sha256":crate::current_work(world).ok().map(|s|appearance_sha256(s.as_bytes())),"generation":frame["full_base"]["generation"],"mode":self.observation["mode"],"target_sha256":self.target_sha});
        Ok(json!({"key_sha256":hash_json(&value),"actual":value}))
    }
    pub fn publish_for_visibility(
        &mut self,
        world: &mut World,
        frame: &Value,
        mode: Mode,
        epoch: u64,
    ) -> Result<(), String> {
        self.apply(world, frame, mode)?;
        let actual = self.actual_publication(world, frame)?;
        if self.expected_publication_key.is_empty() {
            self.expected_publication_key = actual["key_sha256"]
                .as_str()
                .ok_or("publication key absent")?
                .to_owned();
        }
        if actual["key_sha256"] != self.expected_publication_key {
            return Err(
                "publication changed against prepared source/mesh/material/camera binding".into(),
            );
        }
        self.pre_witness = json!({"update_epoch":epoch,"publication":actual,"ordering":"PostUpdate after RuntimeSystems::Appearance, before CalculateBounds and CheckVisibility"});
        Ok(())
    }
    pub fn observe_last_before_restore(
        &mut self,
        world: &World,
        frame: &Value,
        epoch: u64,
    ) -> Result<(), String> {
        let actual = self.actual_publication(world, frame)?;
        let matches =
            self.pre_witness["update_epoch"] == epoch && self.pre_witness["publication"] == actual;
        let visibility=frame["full_base"]["parts"].as_array().ok_or("parts absent")?.iter().map(|p|{
            world.iter_entities().find(|e|json!(format!("{:?}",e.id()))==p["display_entity"]).map(|e|json!({"role":p["name"],"entity":format!("{:?}",e.id()),"inherited_visibility":e.get::<InheritedVisibility>().map(|v|v.get()),"view_visibility":e.get::<ViewVisibility>().map(|v|v.get()),"aabb":aabb_record(e.get::<Aabb>())})).unwrap_or(Value::Null)
        }).collect::<Vec<_>>();
        self.last_witness = json!({"update_epoch":epoch,"pre_visibility_publication_matches":matches,"publication":actual,"post_visibility_CPU_observations":visibility});
        if !matches {
            return Err("Last actual handle/content/bounds differ from this update's previsibility publication".into());
        }
        Ok(())
    }
    pub fn verified_record(
        &self,
        world: &World,
        frame: &Value,
        epoch: u64,
    ) -> Result<Value, String> {
        let actual = self.actual_publication(world, frame)?;
        let matched = self.last_witness["update_epoch"] == epoch
            && self.last_witness["pre_visibility_publication_matches"] == true
            && self.last_witness["publication"] == actual;
        let mut value = self.observation.clone();
        value["publication_key_sha256"] = actual["key_sha256"].clone();
        value["actual_render_publication"] = actual["actual"].clone();
        value["pre_visibility_publication_matches"] = json!(matched);
        value["pre_visibility_witness"] = self.pre_witness.clone();
        value["Last_independent_witness"] = self.last_witness.clone();
        value["scope_publication"] = json!(
            "Actual CPU source/modified mesh association and exact changed AABB, measured before/after visibility; inherited production culling policy preserved. Not GPU pixel ownership or presentation receipt. full_base remains unmodified full-positive production reference."
        );
        Ok(value)
    }
}
#[cfg(test)]
mod publication_controls {
    use super::*;
    use bevy::{
        asset::RenderAssetUsages,
        mesh::{Indices, PrimitiveTopology},
    };
    fn fixture() -> (World, Value) {
        let mut w = World::new();
        let frame = fixture_in(&mut w);
        (w, frame)
    }
    fn fixture_in(w: &mut World) -> Value {
        w.init_resource::<Assets<Mesh>>();
        w.init_resource::<Assets<StandardMaterial>>();
        w.init_resource::<nvwa_runtime::EditorState>();
        let doc = nvwa_core::SceneDocument::from_json(include_str!(
            "../works/shoulder-rear-baseline-arms.nvwa.json"
        ))
        .unwrap();
        w.resource_mut::<nvwa_runtime::EditorState>()
            .replace(doc)
            .unwrap();
        let mut parts = Vec::new();
        for (role, ids, z) in [
            ("body", vec![8319, 8318, 8309, 8310], 0.),
            ("garment", vec![830, 168, 212, 847], 0.1),
        ] {
            let pos = vec![[0., 0., z], [1., 0., z], [1., 1., z], [0., 1., z]];
            let norm = vec![[0., 0., 1.]; 4];
            let indices = vec![0, 1, 2, 0, 2, 3];
            let mut mesh = Mesh::new(
                PrimitiveTopology::TriangleList,
                RenderAssetUsages::MAIN_WORLD | RenderAssetUsages::RENDER_WORLD,
            );
            mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, pos.clone());
            mesh.insert_attribute(Mesh::ATTRIBUTE_NORMAL, norm.clone());
            mesh.insert_attribute(Mesh::ATTRIBUTE_UV_0, vec![[0., 0.]; 4]);
            mesh.insert_indices(Indices::U32(indices.clone()));
            let handle = w.resource_mut::<Assets<Mesh>>().add(mesh);
            let material = w
                .resource_mut::<Assets<StandardMaterial>>()
                .add(StandardMaterial::default());
            let entity = w
                .spawn((
                    Mesh3d(handle.clone()),
                    MeshMaterial3d(material),
                    GlobalTransform::IDENTITY,
                    Visibility::Inherited,
                    bevy::camera::visibility::NoFrustumCulling,
                ))
                .id();
            parts.push(json!({"name":role,"display_entity":format!("{entity:?}"),"mesh_handle":format!("{:?}",handle.id()),"source_ids":ids,"indices":indices,"positions":pos,"normals":norm,"display_transform":Mat4::IDENTITY.to_cols_array()}));
        }
        let rest = Mat4::IDENTITY.to_cols_array();
        let arm =
            Mat4::from_quat(Quat::from_rotation_z(std::f32::consts::FRAC_PI_4)).to_cols_array();
        let frame = json!({"request_id":"synthetic-pub","identity":{"synthetic":true},"full_base":{"generation":1,"parameters":{"torso_length":0.},"sample":{"source_seconds":2.,"clip_id":"b1_arm_rehearsal_v1"},"parts":parts,"bones":[{"name":"upperarm_l","local_rest":rest,"local_posed":arm},{"name":"clavicle_l","canonical_posed":rest}]}});
        frame
    }
    #[test]
    fn first_publication_installs_exact_bounds_with_absent_or_incoherent_original_and_restores_it()
    {
        for stale in [false, true] {
            let (mut w, frame) = fixture();
            let entity = w
                .iter_entities()
                .find(|e| {
                    json!(format!("{:?}", e.id()))
                        == frame["full_base"]["parts"][0]["display_entity"]
                })
                .unwrap()
                .id();
            if stale {
                w.entity_mut(entity).insert(Aabb {
                    center: Vec3::splat(99.).into(),
                    half_extents: Vec3::splat(0.1).into(),
                });
            }
            let before = aabb_record(w.get::<Aabb>(entity));
            let mut state = State::default();
            state.apply(&mut w, &frame, Mode::SourceBody).unwrap();
            let swap = state.swap.as_ref().unwrap();
            assert_eq!(
                aabb_record(w.get::<Aabb>(entity)),
                aabb_record(Some(&swap.diagnostic_aabb))
            );
            state.restore(&mut w);
            assert_eq!(aabb_record(w.get::<Aabb>(entity)), before);
            assert!(
                w.get::<bevy::camera::visibility::NoFrustumCulling>(entity)
                    .is_some()
            );
        }
    }
    #[test]
    fn actual_UV_mutation_after_previsibility_must_reject_even_if_geometry_is_unchanged() {
        let (mut w, frame) = fixture();
        // Give the original exact bounds so this regression independently reaches the UV gate.
        let entity = w
            .iter_entities()
            .find(|e| {
                json!(format!("{:?}", e.id())) == frame["full_base"]["parts"][0]["display_entity"]
            })
            .unwrap()
            .id();
        let original = w.get::<Mesh3d>(entity).unwrap().0.clone();
        let bounds = w
            .resource::<Assets<Mesh>>()
            .get(&original)
            .unwrap()
            .compute_aabb()
            .unwrap();
        w.entity_mut(entity).insert(bounds);
        let mut state = State::default();
        state.apply(&mut w, &frame, Mode::SourceBody).unwrap();
        state.restore(&mut w);
        state
            .publish_for_visibility(&mut w, &frame, Mode::SourceBody, 5)
            .unwrap();
        state.observe_last_before_restore(&w, &frame, 5).unwrap();
        let mesh = state.swap.as_ref().unwrap().diagnostic.clone();
        if let Some(VertexAttributeValues::Float32x2(uv)) = w
            .resource_mut::<Assets<Mesh>>()
            .get_mut(&mesh)
            .unwrap()
            .attribute_mut(Mesh::ATTRIBUTE_UV_0)
        {
            uv[0][0] += 0.25;
        }
        assert!(
            state.observe_last_before_restore(&w, &frame, 5).is_err(),
            "changed actual rendered UV must go red even with identical positions/normals"
        );
    }
    #[test]
    fn actual_publication_seam_detects_wrong_epoch_changed_bounds_and_changed_buffers() {
        let (mut w, frame) = fixture();
        let mut state = State::default();
        state.apply(&mut w, &frame, Mode::SourceBody).unwrap();
        state.restore(&mut w);
        state
            .publish_for_visibility(&mut w, &frame, Mode::SourceBody, 7)
            .unwrap();
        state.observe_last_before_restore(&w, &frame, 7).unwrap();
        assert!(
            state.observe_last_before_restore(&w, &frame, 8).is_err(),
            "same data in wrong update is not this-frame publication"
        );
        let entity = state.swap.as_ref().unwrap().entity;
        w.entity_mut(entity).insert(Aabb {
            center: Vec3::ZERO.into(),
            half_extents: Vec3::ZERO.into(),
        });
        assert!(
            state.observe_last_before_restore(&w, &frame, 7).is_err(),
            "mutated actual AABB must go red"
        );
        let bounds = state.swap.as_ref().unwrap().diagnostic_aabb;
        w.entity_mut(entity).insert(bounds);
        let mesh = state.swap.as_ref().unwrap().diagnostic.clone();
        if let Some(VertexAttributeValues::Float32x3(p)) = w
            .resource_mut::<Assets<Mesh>>()
            .get_mut(&mesh)
            .unwrap()
            .attribute_mut(Mesh::ATTRIBUTE_POSITION)
        {
            p[0][0] += 0.1;
        }
        assert!(
            state.observe_last_before_restore(&w, &frame, 7).is_err(),
            "mutated actual render buffer must go red"
        );
        state.restore(&mut w);
        let original = &state.swap.as_ref().unwrap().original;
        assert_eq!(w.get::<Mesh3d>(entity).unwrap().0, *original);
        assert!(
            w.get::<bevy::camera::visibility::NoFrustumCulling>(entity)
                .is_some()
        );
    }
    #[test]
    fn corrective_zero_and_actual_changed_AABB_are_distinct_from_original_full_base() {
        let (mut w, mut frame) = fixture();
        let mut state = State::default();
        for (id, mode) in [
            ("a", Mode::Combined),
            ("b", Mode::SourceBody),
            ("g", Mode::SourceGarment),
        ] {
            state.proofs.insert(
                id.into(),
                Proof {
                    mode,
                    identity: frame["identity"].clone(),
                },
            );
        }
        let raw=json!({"candidate_id":"nvwa-source847-pose-target-v1","source_obj_sha256":OBJ_SHA,"source_id":847,"delta_clavicle_m":[0.,0.,0.003],"baseline_request_id":"a","body_highlight_request_id":"b","garment_highlight_request_id":"g"}).to_string();
        state
            .author(&raw, &appearance_sha256(raw.as_bytes()))
            .unwrap();
        let original = frame["full_base"]["parts"][1]["positions"].clone();
        state.apply(&mut w, &frame, Mode::Corrective).unwrap();
        state.restore(&mut w);
        state
            .publish_for_visibility(&mut w, &frame, Mode::Corrective, 10)
            .unwrap();
        state.observe_last_before_restore(&w, &frame, 10).unwrap();
        let record = state.verified_record(&w, &frame, 10).unwrap();
        assert_eq!(record["pre_visibility_publication_matches"], true);
        assert_eq!(frame["full_base"]["parts"][1]["positions"], original);
        assert_ne!(record["corrected_positions"], original);
        assert_eq!(record["actual_arm_angle_weight"], 1.);
        state.clear(&mut w);
        frame["request_id"] = json!("neutral");
        frame["full_base"]["bones"][0]["local_posed"] = json!(Mat4::IDENTITY.to_cols_array());
        let record = state.apply(&mut w, &frame, Mode::Corrective).unwrap();
        assert_eq!(record["actual_arm_angle_weight"], 0.);
        assert_eq!(record["corrected_positions"], original);
    }
    #[derive(Resource, Default)]
    struct Checks {
        visibility_saw_diagnostic: bool,
        last_validated: bool,
    }
    fn visibility_probe(world: &mut World) {
        let b = world.resource::<crate::Bridge>();
        let swap = b.source.swap.as_ref().unwrap();
        assert_eq!(world.get::<Mesh3d>(swap.entity).unwrap().0, swap.diagnostic);
        assert_eq!(
            aabb_record(world.get::<Aabb>(swap.entity)),
            aabb_record(Some(&swap.diagnostic_aabb))
        );
        world.resource_mut::<Checks>().visibility_saw_diagnostic = true;
    }
    fn last_probe(world: &mut World) {
        let mut b = world.remove_resource::<crate::Bridge>().unwrap();
        let f = b.prepared_frame.as_ref().unwrap();
        b.source
            .observe_last_before_restore(world, f, b.update_epoch)
            .unwrap();
        world.resource_mut::<Checks>().last_validated = true;
        world.insert_resource(b);
    }
    #[test]
    fn production_called_schedule_installs_source_before_visibility_and_Last_checks_same_epoch() {
        let mut app = App::new();
        let frame = fixture_in(app.world_mut());
        app.init_resource::<Checks>();
        let mut bridge = crate::Bridge::default();
        bridge
            .source
            .apply(app.world_mut(), &frame, Mode::SourceBody)
            .unwrap();
        bridge.source.restore(app.world_mut());
        bridge
            .diagnostic
            .configure(Mode::SourceBody, crate::diagnostic::Palette::Textured);
        bridge.prepared_frame = Some(frame);
        app.insert_resource(bridge);
        app.add_systems(PreUpdate, crate::prepare_diagnostic);
        crate::install_source_publication(&mut app);
        app.add_systems(
            PostUpdate,
            visibility_probe.in_set(bevy::camera::visibility::VisibilitySystems::CheckVisibility),
        );
        app.add_systems(Last, last_probe);
        app.update();
        let checks = app.world().resource::<Checks>();
        assert!(checks.visibility_saw_diagnostic && checks.last_validated);
    }
}

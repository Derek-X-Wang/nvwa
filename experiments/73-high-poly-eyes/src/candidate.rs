//! Experiment-only mesh buffer publication. Original mesh is restored at PreUpdate,
//! validated through production, then the selected variant is published at Last.
//! No second entity, display transform, bone skinning or material/image allocation.
use crate::geometry;
use bevy::camera::primitives::{Aabb, MeshAabb};
use bevy::{
    math::DMat4,
    mesh::{Indices, VertexAttributeValues},
    prelude::*,
};
use nvwa_core::appearance_sha256;
use serde::Deserialize;
use serde_json::{Value, json};
#[derive(Clone, Copy, Debug, Default, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Variant {
    #[default]
    AOriginal,
    BHigh,
}
struct Fitted {
    obj: geometry::Obj,
    rest: Vec<[f64; 3]>,
    normals: Vec<[f64; 3]>,
    weights: Vec<Vec<(usize, f64)>>,
    scales: [f64; 3],
}
struct Binding {
    key: String,
    work: String,
    generation: Value,
    entity: Entity,
    character: Entity,
    mesh: Handle<Mesh>,
    material: Handle<StandardMaterial>,
    image: Handle<Image>,
    image_pixels: String,
    material_debug: String,
    placement: [f32; 16],
    a: Fitted,
    b: Fitted,
}
#[derive(Default)]
pub struct State {
    pub variant: Variant,
    binding: Option<Binding>,
    saved: Option<(Entity, Handle<Mesh>, Mesh, Option<Aabb>)>,
    pub motion: Vec<Value>,
    culling_witness: Value,
}
fn hash(v: &Value) -> String {
    appearance_sha256(v.to_string().as_bytes())
}
fn sha(bytes: &[u8], expected: &str) -> Result<(), String> {
    if appearance_sha256(bytes) != expected {
        return Err("high-poly source authentication failed".into());
    }
    Ok(())
}
fn fitted(
    text: &str,
    obj: &str,
    count: usize,
    cage: &[[f64; 3]],
    weights: &[Vec<f64>],
) -> Result<Fitted, String> {
    let mapping = geometry::mapping(text, count)?;
    let obj = geometry::obj(obj, count)?;
    let (rest, scales) = geometry::fit(&mapping, cage)?;
    let weights = geometry::transfer(&mapping, weights)?;
    let normals = geometry::source_normals(&rest, &obj)?;
    Ok(Fitted {
        obj,
        rest,
        normals,
        weights,
        scales,
    })
}
fn entity(world: &World, label: &Value) -> Result<Entity, String> {
    let matches: Vec<_> = world
        .iter_entities()
        .filter(|e| json!(format!("{:?}", e.id())) == *label)
        .map(|e| e.id())
        .collect();
    if matches.len() != 1 {
        return Err("bound entity absent/ambiguous".into());
    }
    Ok(matches[0])
}
fn matrices(bones: &Value) -> Result<Vec<DMat4>, String> {
    let bones = bones.as_array().ok_or("current bones absent")?;
    if bones.len() != 53 {
        return Err("exact53 actual bones required".into());
    }
    bones
        .iter()
        .map(|b| {
            let skin: [f32; 16] =
                serde_json::from_value(b["skin"].clone()).map_err(|e| e.to_string())?;
            Ok(DMat4::from_cols_array(&skin.map(f64::from)))
        })
        .collect()
}
fn arrays(f: &Fitted, bones: &[DMat4]) -> Result<(Vec<[f32; 3]>, Vec<[f32; 3]>), String> {
    let (p, n) = geometry::skin(&f.rest, &f.normals, &f.weights, bones)?;
    Ok((
        f.obj.pairs.iter().map(|(i, _)| p[*i]).collect(),
        f.obj.pairs.iter().map(|(i, _)| n[*i]).collect(),
    ))
}
fn verify_a(mesh: &Mesh, a: &Fitted, bones: &[DMat4]) -> Result<(), String> {
    let (p, n) = arrays(a, bones)?;
    if !matches!(mesh.attribute(Mesh::ATTRIBUTE_POSITION),Some(VertexAttributeValues::Float32x3(v)) if *v==p)
        || !matches!(mesh.attribute(Mesh::ATTRIBUTE_NORMAL),Some(VertexAttributeValues::Float32x3(v)) if *v==n)
        || !matches!(mesh.attribute(Mesh::ATTRIBUTE_UV_0),Some(VertexAttributeValues::Float32x2(v)) if *v==a.obj.uv)
        || mesh.indices().map(|i| i.iter().collect::<Vec<_>>())
            != Some(a.obj.indices.iter().map(|i| *i as usize).collect())
    {
        return Err(
            "A replay differs from actual production positions/normals/UV/indices; B forbidden"
                .into(),
        );
    }
    Ok(())
}
fn publication_matches(witness: &Value, current: &Value) -> bool {
    !witness.is_null() && witness == current
}
impl State {
    pub fn has_binding(&self) -> bool {
        self.binding.is_some()
    }
    pub fn restore(&mut self, world: &mut World) {
        if let Some((entity, handle, original, aabb)) = self.saved.take() {
            if let Some(mut mesh) = world.resource_mut::<Assets<Mesh>>().get_mut(&handle) {
                *mesh = original;
            }
            if let Ok(mut e) = world.get_entity_mut(entity) {
                if let Some(aabb) = aabb {
                    e.insert(aabb);
                } else {
                    e.remove::<Aabb>();
                }
            }
        }
    }
    pub fn clear(&mut self, world: &mut World) {
        self.restore(world);
        self.binding = None;
        self.culling_witness = Value::Null;
    }
    pub fn publish(
        &mut self,
        world: &mut World,
        appearance: &Value,
        base: &Value,
    ) -> Result<Value, String> {
        if self.saved.is_some() {
            return Err("mesh not restored before production validation".into());
        }
        let eye = appearance["accessories"]
            .as_array()
            .ok_or("accessory snapshot absent")?
            .iter()
            .find(|a| a["name"] == "eyes")
            .ok_or("exact production eyes absent")?;
        let body = base["parts"]
            .as_array()
            .ok_or("base parts absent")?
            .iter()
            .find(|p| p["name"] == "body")
            .ok_or("body absent")?;
        let key = hash(&json!([
            base["generation"],
            body["rest_positions"],
            body["source_ids"],
            eye["entity"],
            eye["mesh_handle"],
            eye["material_handle"],
            eye["texture"]
        ]));
        if self.binding.as_ref().is_none_or(|b| b.key != key) {
            let ids: Vec<u16> =
                serde_json::from_value(body["source_ids"].clone()).map_err(|e| e.to_string())?;
            let rest: Vec<[f32; 3]> = serde_json::from_value(body["rest_positions"].clone())
                .map_err(|e| e.to_string())?;
            let cage = geometry::cage(&ids, &rest)?;
            let names = base["bones"]
                .as_array()
                .ok_or("bones absent")?
                .iter()
                .map(|b| {
                    b["name"]
                        .as_str()
                        .map(str::to_owned)
                        .ok_or("bone name absent")
                })
                .collect::<Result<Vec<_>, _>>()?;
            let weights = geometry::weights(&names)?;
            const MAP: &str = include_str!("../source/eyes/high-poly/high-poly.mhclo");
            const OBJ: &str = include_str!("../source/eyes/high-poly/high-poly.obj");
            sha(
                MAP.as_bytes(),
                "b183cfe37120ab726f9b3f2ea6cd3a64c44ce7b4bd91a77c841cf70c04f83a0d",
            )?;
            sha(
                OBJ.as_bytes(),
                "da2493215b708a344c33dc72f2a9a5b8fa985dcc5a70ad3b208995cf871da8e1",
            )?;
            sha(
                include_bytes!("../source/eyes/materials/brown.mhmat"),
                "4abad93ce50541c08127721e77bce035640c9f16bed16cd0f5524b1cd5908465",
            )?;
            let png = include_bytes!("../source/eyes/materials/brown_eye.png");
            sha(
                png,
                "4659691c7295ad6206c78b003e5fd0e5f91dcd53032fa914a229bb48cabe424b",
            )?;
            if png.as_slice()
                != include_bytes!(
                    "../../../assets/appearances/mpfb-b1-cc0-v1/eyes/materials/brown_eye.png"
                )
                .as_slice()
            {
                return Err("A/B texture source bytes differ".into());
            }
            let a = fitted(
                include_str!(
                    "../../../assets/appearances/mpfb-b1-cc0-v1/eyes/low-poly/low-poly.mhclo"
                ),
                include_str!(
                    "../../../assets/appearances/mpfb-b1-cc0-v1/eyes/low-poly/low-poly.obj"
                ),
                96,
                &cage,
                &weights,
            )?;
            let b = fitted(MAP, OBJ, 1064, &cage, &weights)?;
            let entity = entity(world, &eye["entity"])?;
            let character = crate::candidate::entity(world, &base["character_entity"])?;
            let mesh = world
                .get::<Mesh3d>(entity)
                .ok_or("actual eyes Mesh3d absent")?
                .0
                .clone();
            let material = world
                .get::<MeshMaterial3d<StandardMaterial>>(entity)
                .ok_or("actual eyes material binding absent")?
                .0
                .clone();
            let m = world
                .resource::<Assets<StandardMaterial>>()
                .get(&material)
                .ok_or("actual eyes material absent")?;
            let image = m.base_color_texture.clone().ok_or("eyes texture absent")?;
            let pixels = world
                .resource::<Assets<Image>>()
                .get(&image)
                .ok_or("actual bound eye image absent")?;
            let image_pixels =
                appearance_sha256(pixels.data.as_ref().ok_or("actual eye CPU pixels absent")?);
            let work = crate::current_work(world)?;
            let placement = world
                .get::<GlobalTransform>(entity)
                .ok_or("eye placement absent")?
                .to_matrix()
                .to_cols_array();
            if json!(placement) != body["display_transform"] {
                return Err("eyes/body display placement differs".into());
            }
            self.binding = Some(Binding {
                key,
                work,
                generation: base["generation"].clone(),
                entity,
                character,
                mesh,
                material,
                image,
                image_pixels,
                material_debug: format!("{m:?}"),
                placement,
                a,
                b,
            });
        }
        self.apply(world, &base["bones"], &base["sample"])
    }
    fn apply(&mut self, world: &mut World, bones: &Value, sample: &Value) -> Result<Value, String> {
        let bind = self.binding.as_ref().ok_or("candidate binding absent")?;
        if crate::current_work(world)? != bind.work
            || nvwa_runtime::appearance_status(world)
                .generation
                .map(|g| json!(g))
                != Some(bind.generation.clone())
        {
            return Err("candidate Work/generation changed; fresh capture required".into());
        }
        if world
            .get::<Mesh3d>(bind.entity)
            .is_none_or(|m| m.0 != bind.mesh)
            || world
                .get::<MeshMaterial3d<StandardMaterial>>(bind.entity)
                .is_none_or(|m| m.0 != bind.material)
            || world
                .get::<GlobalTransform>(bind.entity)
                .is_none_or(|t| t.to_matrix().to_cols_array() != bind.placement)
        {
            return Err("actual eye entity/mesh/material/placement epoch changed".into());
        }
        let material = world
            .resource::<Assets<StandardMaterial>>()
            .get(&bind.material)
            .ok_or("actual material lost")?;
        if format!("{material:?}") != bind.material_debug
            || material.base_color_texture.as_ref() != Some(&bind.image)
        {
            return Err("original material/image changed before B publication".into());
        }
        let image = world
            .resource::<Assets<Image>>()
            .get(&bind.image)
            .ok_or("actual image lost")?;
        if appearance_sha256(image.data.as_ref().ok_or("CPU image pixels absent")?)
            != bind.image_pixels
        {
            return Err("actual eye image pixels changed".into());
        }
        let matrices = matrices(bones)?;
        let original = world
            .resource::<Assets<Mesh>>()
            .get(&bind.mesh)
            .ok_or("actual eye mesh lost")?;
        verify_a(original, &bind.a, &matrices)?;
        let selected = if self.variant == Variant::AOriginal {
            &bind.a
        } else {
            &bind.b
        };
        let (p, n) = arrays(selected, &matrices)?;
        if self.variant == Variant::BHigh {
            let saved = original.clone();
            let mut assets = world.resource_mut::<Assets<Mesh>>();
            let mut mesh = assets
                .get_mut(&bind.mesh)
                .ok_or("eye mesh lost during publication")?;
            mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, p.clone());
            mesh.insert_attribute(Mesh::ATTRIBUTE_NORMAL, n.clone());
            mesh.insert_attribute(Mesh::ATTRIBUTE_UV_0, selected.obj.uv.clone());
            mesh.insert_indices(Indices::U32(selected.obj.indices.clone()));
            let bound = mesh.compute_aabb().ok_or("actual B bounds absent")?;
            drop(mesh);
            drop(assets);
            let original_aabb = world.get::<Aabb>(bind.entity).copied();
            world.entity_mut(bind.entity).insert(bound);
            self.saved = Some((bind.entity, bind.mesh.clone(), saved, original_aabb));
        }
        let actual = world
            .resource::<Assets<Mesh>>()
            .get(&bind.mesh)
            .ok_or("published eye mesh absent")?;
        if !matches!(actual.attribute(Mesh::ATTRIBUTE_POSITION),Some(VertexAttributeValues::Float32x3(v)) if *v==p)
            || !matches!(actual.attribute(Mesh::ATTRIBUTE_NORMAL),Some(VertexAttributeValues::Float32x3(v)) if *v==n)
            || !matches!(actual.attribute(Mesh::ATTRIBUTE_UV_0),Some(VertexAttributeValues::Float32x2(v)) if *v==selected.obj.uv)
            || actual.indices().map(|i| i.iter().collect::<Vec<_>>())
                != Some(selected.obj.indices.iter().map(|i| *i as usize).collect())
        {
            return Err("actual published B buffers differ".into());
        }
        let publication = json!({"variant":format!("{:?}",self.variant),"positions_sha256":hash(&json!(p)),"normals_sha256":hash(&json!(n)),"placement":bind.placement,"camera":crate::camera_report(world),"work_sha256":appearance_sha256(bind.work.as_bytes()),"generation":bind.generation});
        let culling_matches = publication_matches(&self.culling_witness, &publication);
        Ok(
            json!({"variant":format!("{:?}",self.variant),"A_replay_exact":true,"pre_visibility_publication_matches":culling_matches,"pre_visibility_publication":self.culling_witness,"entity":format!("{:?}",bind.entity),"mesh_handle":format!("{:?}",bind.mesh.id()),"material_handle":format!("{:?}",bind.material.id()),"image_handle":format!("{:?}",bind.image.id()),"decoded_rgba_sha256":bind.image_pixels,"original_standard_material_debug":bind.material_debug,"display_transform":bind.placement,"generation":bind.generation,"sample":sample,"actual_aabb":world.get::<Aabb>(bind.entity).map(|a|json!({"center":a.center.to_array(),"half_extents":a.half_extents.to_array()})),"bounds_policy":"exact mesh compute_aabb; no inflation or disabled culling","source_vertices":selected.obj.count,"render_vertices":p.len(),"triangles":selected.obj.indices.len()/3,"source_uv_pairs":selected.obj.pairs,"rest_source_positions":selected.rest,"rest_source_normals":selected.normals,"full_positive_source_weights":selected.weights,"source_scales":selected.scales,"bones":bones,"published_positions_sha256":hash(&json!(p)),"published_normals_sha256":hash(&json!(n)),"policy":"simple-srgb-mask-v1 unchanged; raw MHCLO decimetres converted once; actual body cage metres; original eye entity placement exactly once","scope":"actual bound CPU arrays; no GPU readback or intended-eyelid-fit claim"}),
        )
    }
    pub fn publish_for_visibility(&mut self, world: &mut World) -> Result<(), String> {
        self.stream(world)?;
        let b = self.binding.as_ref().ok_or("visibility binding absent")?;
        let mesh = world
            .resource::<Assets<Mesh>>()
            .get(&b.mesh)
            .ok_or("visibility mesh absent")?;
        let p = match mesh.attribute(Mesh::ATTRIBUTE_POSITION) {
            Some(VertexAttributeValues::Float32x3(v)) => v,
            _ => return Err("visibility positions absent".into()),
        };
        let n = match mesh.attribute(Mesh::ATTRIBUTE_NORMAL) {
            Some(VertexAttributeValues::Float32x3(v)) => v,
            _ => return Err("visibility normals absent".into()),
        };
        self.culling_witness = json!({"variant":format!("{:?}",self.variant),"positions_sha256":hash(&json!(p)),"normals_sha256":hash(&json!(n)),"placement":b.placement,"camera":crate::camera_report(world),"work_sha256":appearance_sha256(b.work.as_bytes()),"generation":b.generation});
        Ok(())
    }
    pub fn stream(&mut self, world: &mut World) -> Result<(), String> {
        if self.saved.is_some() {
            return Ok(());
        } // Already published once in this Last pass.
        let bind = self.binding.as_ref().ok_or("stream binding absent")?;
        let status = nvwa_runtime::appearance_status(world);
        if !status.ready
            || world
                .resource::<nvwa_runtime::Playback>()
                .seek_request
                .is_some()
        {
            return Ok(());
        }
        // This validates actual A material/image/mesh publication before every B frame.
        nvwa_runtime::appearance_snapshot(world)?;
        let bones = nvwa_b1_adapter::bone_frames(world, bind.character)?;
        let playback = world.resource::<nvwa_runtime::Playback>();
        let sample = json!({"clip_id":playback.clip_id,"position_seconds":playback.position_seconds,"playing":playback.playing});
        let record = self.apply(
            world,
            &serde_json::to_value(bones).map_err(|e| e.to_string())?,
            &sample,
        )?;
        if record["pre_visibility_publication_matches"] == true
            && sample["playing"] == true
            && self.motion.len() < 512
            && self.motion.last().is_none_or(|p| p["sample"] != sample)
        {
            self.motion.push(json!({"variant":record["variant"],"generation":record["generation"],"sample":sample,"A_replay_exact":record["A_replay_exact"],"entity":record["entity"],"mesh_handle":record["mesh_handle"],"material_handle":record["material_handle"],"image_handle":record["image_handle"],"published_positions_sha256":record["published_positions_sha256"],"published_normals_sha256":record["published_normals_sha256"],"scope":"continuous CPU publication witness; separate video observation required"}));
        }
        Ok(())
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn production_called_publication_gate_rejects_every_changed_epoch_field() {
        let current = json!({"variant":"BHigh","positions_sha256":"p","normals_sha256":"n","placement":[1,2],"camera":{"viewport":[1280,720]},"work_sha256":"w","generation":2});
        assert!(publication_matches(&current, &current));
        assert!(!publication_matches(&Value::Null, &current));
        for key in [
            "variant",
            "positions_sha256",
            "normals_sha256",
            "placement",
            "camera",
            "work_sha256",
            "generation",
        ] {
            let mut stale = current.clone();
            stale[key] = Value::Null;
            assert!(!publication_matches(&stale, &current), "{key}");
        }
    }
    #[test]
    fn actual_mesh_and_bounds_restore_before_production_validation() {
        let mut world = World::new();
        world.init_resource::<Assets<Mesh>>();
        let mut original = Mesh::new(
            bevy::mesh::PrimitiveTopology::TriangleList,
            bevy::asset::RenderAssetUsages::default(),
        );
        original.insert_attribute(
            Mesh::ATTRIBUTE_POSITION,
            vec![[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]],
        );
        let mesh = world.resource_mut::<Assets<Mesh>>().add(original.clone());
        let aabb = original.compute_aabb().unwrap();
        let entity = world.spawn((Mesh3d(mesh.clone()), aabb)).id();
        world
            .resource_mut::<Assets<Mesh>>()
            .get_mut(&mesh)
            .unwrap()
            .insert_attribute(Mesh::ATTRIBUTE_POSITION, vec![[9., 9., 9.]; 3]);
        let mut state = State::default();
        state.saved = Some((entity, mesh.clone(), original, Some(aabb)));
        state.restore(&mut world);
        assert!(state.saved.is_none());
        assert!(
            matches!(world.resource::<Assets<Mesh>>().get(&mesh).unwrap().attribute(Mesh::ATTRIBUTE_POSITION),Some(VertexAttributeValues::Float32x3(v)) if v[0]==[0.,0.,0.])
        );
        assert_eq!(world.get::<Aabb>(entity).unwrap().center, aabb.center);
    }
    #[test]
    fn authenticated_candidate_and_no_cap_contract() {
        assert!(
            sha(
                include_bytes!("../source/eyes/high-poly/high-poly.obj"),
                "da2493215b708a344c33dc72f2a9a5b8fa985dcc5a70ad3b208995cf871da8e1"
            )
            .is_ok()
        );
        let obj =
            geometry::obj(include_str!("../source/eyes/high-poly/high-poly.obj"), 1064).unwrap();
        assert_eq!(obj.indices.len() / 3, 2040);
        assert!(obj.pairs.len() > 1064);
    }
    #[test]
    fn a_replay_gate_rejects_changed_upload() {
        let a = Fitted {
            obj: geometry::Obj {
                count: 3,
                pairs: vec![(0, 0), (1, 0), (2, 0)],
                uv: vec![[0., 0.]; 3],
                indices: vec![0, 1, 2],
            },
            rest: vec![[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]],
            normals: vec![[0., 0., 1.]; 3],
            weights: vec![vec![(0, 1.)]; 3],
            scales: [1.; 3],
        };
        let (p, n) = arrays(&a, &[DMat4::IDENTITY]).unwrap();
        let mut mesh = Mesh::new(
            bevy::mesh::PrimitiveTopology::TriangleList,
            bevy::asset::RenderAssetUsages::default(),
        );
        mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, p);
        mesh.insert_attribute(Mesh::ATTRIBUTE_NORMAL, n);
        mesh.insert_attribute(Mesh::ATTRIBUTE_UV_0, a.obj.uv.clone());
        mesh.insert_indices(Indices::U32(vec![0, 1, 2]));
        assert!(verify_a(&mesh, &a, &[DMat4::IDENTITY]).is_ok());
        mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, vec![[0., 0., 0.]; 3]);
        assert!(verify_a(&mesh, &a, &[DMat4::IDENTITY]).is_err());
    }
}

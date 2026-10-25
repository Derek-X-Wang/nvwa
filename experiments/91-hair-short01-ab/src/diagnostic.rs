//! Overrides only actual production entity visibility and material color/unlit.
//! Restored before every production update; no alternate mesh or fit route.
use bevy::{mesh::VertexAttributeValues, prelude::*};
use nvwa_core::appearance_sha256;
use serde::Deserialize;
use serde_json::{Value, json};

#[derive(Clone, Copy, Debug, Default, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Mode {
    #[default]
    Combined,
    BodyOnly,
    HairOnly,
}
#[derive(Clone, Copy, Debug, Default, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Palette {
    #[default]
    Textured,
    UnlitTextured,
    RoleTint,
}
struct Target {
    entity: Entity,
    role: String,
    mesh: Handle<Mesh>,
    material: Handle<StandardMaterial>,
    original_visibility: Option<Visibility>,
}
#[derive(Default)]
pub struct State {
    pub mode: Mode,
    pub palette: Palette,
    targets: Vec<Target>,
    saved_materials: Vec<(Handle<StandardMaterial>, StandardMaterial)>,
    epoch: u64,
    prepared: Option<u64>,
}
impl State {
    pub fn configure(&mut self, mode: Mode, palette: Palette) {
        self.mode = mode;
        self.palette = palette;
        self.epoch += 1;
        self.prepared = None;
    }
    pub fn restore_materials(&mut self, world: &mut World) {
        for (handle, original) in self.saved_materials.drain(..) {
            if let Some(mut material) = world
                .resource_mut::<Assets<StandardMaterial>>()
                .get_mut(&handle)
            {
                *material = original;
            }
        }
    }
    fn visible(&self, role: &str) -> bool {
        match self.mode {
            Mode::Combined => true,
            Mode::BodyOnly => role == "body",
            Mode::HairOnly => role == "hair",
        }
    }
    pub fn prepare(&mut self, world: &mut World) {
        self.restore_materials(world);
        for target in &self.targets {
            if let Ok(mut entity) = world.get_entity_mut(target.entity) {
                if self.visible(&target.role) {
                    match target.original_visibility {
                        Some(v) => {
                            entity.insert(v);
                        }
                        None => {
                            entity.remove::<Visibility>();
                        }
                    }
                } else {
                    entity.insert(Visibility::Hidden);
                }
            }
        }
        self.prepared = (!self.targets.is_empty()).then_some(self.epoch);
    }
    pub fn clear(&mut self, world: &mut World) {
        self.restore_materials(world);
        for target in self.targets.drain(..) {
            if let Ok(mut entity) = world.get_entity_mut(target.entity) {
                match target.original_visibility {
                    Some(v) => {
                        entity.insert(v);
                    }
                    None => {
                        entity.remove::<Visibility>();
                    }
                }
            }
        }
        self.prepared = None;
    }
    pub fn bind(
        &mut self,
        world: &mut World,
        appearance: &Value,
        base: &Value,
    ) -> Result<bool, String> {
        let mut labels = Vec::new();
        for p in base["parts"].as_array().ok_or("base parts absent")? {
            labels.push((
                p["name"].as_str().ok_or("part name absent")?.to_string(),
                p["display_entity"].clone(),
                p["mesh_handle"].clone(),
                None,
            ));
        }
        for p in appearance["accessories"]
            .as_array()
            .ok_or("accessories absent")?
        {
            labels.push((
                p["name"]
                    .as_str()
                    .ok_or("accessory role absent")?
                    .to_string(),
                p["entity"].clone(),
                p["mesh_handle"].clone(),
                Some(p["material_handle"].clone()),
            ));
        }
        let mut targets = Vec::new();
        for (role, entity_label, mesh_label, material_label) in labels {
            let matches: Vec<_> = world
                .iter_entities()
                .filter(|e| json!(format!("{:?}", e.id())) == entity_label)
                .map(|e| e.id())
                .collect();
            if matches.len() != 1 {
                return Err("actual diagnostic entity missing/ambiguous".into());
            }
            let entity = matches[0];
            let mesh = world
                .get::<Mesh3d>(entity)
                .ok_or("actual Mesh3d missing")?
                .0
                .clone();
            let material = world
                .get::<MeshMaterial3d<StandardMaterial>>(entity)
                .ok_or("actual material binding absent")?
                .0
                .clone();
            if json!(format!("{:?}", mesh.id())) != mesh_label
                || material_label.is_some_and(|m| m != format!("{:?}", material.id()))
            {
                return Err("snapshot binding differs from actual entity".into());
            }
            let original_visibility = self
                .targets
                .iter()
                .find(|t| t.entity == entity)
                .map(|t| t.original_visibility)
                .unwrap_or_else(|| world.get::<Visibility>(entity).copied());
            targets.push(Target {
                entity,
                role,
                mesh,
                material,
                original_visibility,
            });
        }
        if targets.iter().filter(|t| t.role == "body").count() != 1
            || targets.iter().filter(|t| t.role == "hair").count() != 1
        {
            return Err("exactly one production body and hair required".into());
        }
        let same = self.targets.len() == targets.len()
            && self.targets.iter().zip(&targets).all(|(a, b)| {
                a.entity == b.entity
                    && a.mesh == b.mesh
                    && a.material == b.material
                    && a.role == b.role
            });
        if !same {
            self.clear(world);
            self.targets = targets;
            self.epoch += 1;
        }
        Ok(self.prepared == Some(self.epoch))
    }
    pub fn apply(&mut self, world: &mut World) -> Result<Value, String> {
        let mut records = Vec::new();
        for target in &self.targets {
            if world
                .get::<Mesh3d>(target.entity)
                .is_none_or(|m| m.0 != target.mesh)
                || world
                    .get::<MeshMaterial3d<StandardMaterial>>(target.entity)
                    .is_none_or(|m| m.0 != target.material)
            {
                return Err("diagnostic binding changed after production validation".into());
            }
            let expected_visibility = if self.visible(&target.role) {
                target.original_visibility
            } else {
                Some(Visibility::Hidden)
            };
            if world.get::<Visibility>(target.entity).copied() != expected_visibility {
                return Err("actual visibility differs from selected isolation".into());
            }
            if !self.visible(&target.role)
                && world
                    .get::<InheritedVisibility>(target.entity)
                    .is_some_and(|v| v.get())
            {
                return Err("hidden target visibility has not propagated".into());
            }
            let before = world
                .resource::<Assets<StandardMaterial>>()
                .get(&target.material)
                .ok_or("diagnostic material absent")?
                .clone();
            if self.palette != Palette::Textured && matches!(target.role.as_str(), "body" | "hair")
            {
                let mut changed = before.clone();
                changed.unlit = true;
                if self.palette == Palette::RoleTint {
                    changed.base_color = if target.role == "body" {
                        Color::srgb(0., 1., 1.)
                    } else {
                        Color::srgb(1., 0., 1.)
                    };
                }
                self.saved_materials
                    .push((target.material.clone(), before.clone()));
                *world
                    .resource_mut::<Assets<StandardMaterial>>()
                    .get_mut(&target.material)
                    .ok_or("diagnostic material lost")? = changed;
            }
            let material = world
                .resource::<Assets<StandardMaterial>>()
                .get(&target.material)
                .ok_or("actual diagnostic material absent")?;
            if material.base_color_texture != before.base_color_texture
                || material.alpha_mode != before.alpha_mode
                || material.cull_mode != before.cull_mode
                || material.double_sided != before.double_sided
            {
                return Err("diagnostic changed coverage/culling policy".into());
            }
            records.push(json!({"role":target.role,"entity":format!("{:?}",target.entity),"mesh_handle":format!("{:?}",target.mesh.id()),"material_handle":format!("{:?}",target.material.id()),"visibility_original":format!("{:?}",target.original_visibility),"visibility_actual":format!("{:?}",world.get::<Visibility>(target.entity)),"inherited_visibility":world.get::<InheritedVisibility>(target.entity).map(|v|v.get()),"view_visibility":world.get::<ViewVisibility>(target.entity).map(|v|v.get()),"isolation_hidden":!self.visible(&target.role),"production_material":material_record(&before),"render_material":material_record(material),"coverage_culling_policy_preserved":true}));
        }
        Ok(
            json!({"mode":format!("{:?}",self.mode),"palette":format!("{:?}",self.palette),"production_appearance_controller_enabled":true,"visibility_prepared_before_postupdate":self.prepared==Some(self.epoch),"targets":records,"other_scene_surfaces":"floor, lights, background and other non-character entities unchanged","scope":"actual CPU entity/material/visibility state at Last; ViewVisibility is CPU camera culling, NOT GPU winner/object-ID/depth readback; base/appearance snapshots validate restored production materials before overrides"}),
        )
    }
    pub fn buffers(
        &self,
        world: &World,
        variant: crate::candidate::Variant,
    ) -> Result<Value, String> {
        self.buffers_checked(world, true, variant)
    }
    fn buffers_checked(
        &self,
        world: &World,
        check_source: bool,
        variant: crate::candidate::Variant,
    ) -> Result<Value, String> {
        let mut records = Vec::new();
        for target in &self.targets {
            let mesh = world
                .resource::<Assets<Mesh>>()
                .get(&target.mesh)
                .ok_or("actual mesh buffer absent")?;
            let vec3 = |attribute| match mesh.attribute(attribute) {
                Some(VertexAttributeValues::Float32x3(v)) => Ok(json!(v)),
                _ => Err("actual vec3 buffer absent".to_string()),
            };
            let positions = vec3(Mesh::ATTRIBUTE_POSITION)?;
            let normals = vec3(Mesh::ATTRIBUTE_NORMAL)?;
            let uv = match mesh.attribute(Mesh::ATTRIBUTE_UV_0) {
                Some(VertexAttributeValues::Float32x2(v)) => json!(v),
                None => Value::Null,
                _ => return Err("UV type unsupported".into()),
            };
            let indices = mesh
                .indices()
                .ok_or("actual indices absent")?
                .iter()
                .collect::<Vec<_>>();
            let global = world
                .get::<GlobalTransform>(target.entity)
                .ok_or("actual global absent")?
                .to_matrix()
                .to_cols_array();
            let source_map = if check_source && target.role == "hair" {
                let map: Value =
                    serde_json::from_str(if variant == crate::candidate::Variant::AOriginal {
                        include_str!("../works/a-short04-source-map.json")
                    } else {
                        include_str!("../works/b-short01-source-map.json")
                    })
                    .map_err(|e| e.to_string())?;
                let expected_uv: Vec<[f32; 2]> =
                    serde_json::from_value(map["uv_0"].clone()).map_err(|e| e.to_string())?;
                if json!(indices) != map["indices"]
                    || uv != json!(expected_uv)
                    || positions.as_array().map(Vec::len)
                        != map["source_uv_pairs"].as_array().map(Vec::len)
                {
                    return Err(
                        "actual hair differs from pinned source corner/UV/index mapping".into(),
                    );
                }
                map
            } else {
                Value::Null
            };
            let material = world
                .resource::<Assets<StandardMaterial>>()
                .get(&target.material)
                .ok_or("actual buffer material absent")?;
            let bound_image = if let Some(handle) = &material.base_color_texture {
                let image = world
                    .resource::<Assets<Image>>()
                    .get(handle)
                    .ok_or("actual buffer image absent")?;
                let pixels = image
                    .data
                    .as_ref()
                    .ok_or("actual CPU image pixels absent")?;
                json!({"handle":format!("{:?}",handle.id()),"width":image.width(),"height":image.height(),"format":format!("{:?}",image.texture_descriptor.format),"mip_count":image.texture_descriptor.mip_level_count,"sampler":format!("{:?}",image.sampler),"decoded_bytes":pixels.len(),"decoded_rgba_sha256":appearance_sha256(pixels),"policy":crate::candidate::image_policy(image)})
            } else {
                Value::Null
            };
            records.push(json!({"role":target.role,"entity":format!("{:?}",target.entity),"mesh_handle":format!("{:?}",target.mesh.id()),"material_handle":format!("{:?}",target.material.id()),"bound_image":bound_image,"source_map":source_map,"positions":positions,"normals":normals,"uv_0":uv,"indices":indices,"display_transform":global,"positions_sha256":appearance_sha256(positions.to_string().as_bytes()),"scope":"already posed metre-space actual uploaded CPU positions; world=display_transform*positions exactly once; no second model_to_world/flip/scale/skin"}));
        }
        Ok(json!(records))
    }
}
fn material_record(m: &StandardMaterial) -> Value {
    json!({"base_color":format!("{:?}",m.base_color),"base_color_texture":m.base_color_texture.as_ref().map(|h|format!("{:?}",h.id())),"unlit":m.unlit,"alpha_mode":format!("{:?}",m.alpha_mode),"cull_mode":format!("{:?}",m.cull_mode),"double_sided":m.double_sided,"roughness":m.perceptual_roughness,"metallic":m.metallic,"full_standard_material_debug":format!("{m:?}")})
}

#[cfg(test)]
mod tests {
    use super::*;
    use bevy::{
        asset::RenderAssetUsages,
        mesh::{Indices, PrimitiveTopology},
    };
    fn fixture() -> (World, State, Value, Value) {
        let mut world = World::new();
        world.init_resource::<Assets<Mesh>>();
        world.init_resource::<Assets<StandardMaterial>>();
        world.init_resource::<Assets<Image>>();
        let mut pixels = Image::default();
        pixels.data = Some(vec![255; 4]);
        let image = world.resource_mut::<Assets<Image>>().add(pixels);
        let mut parts = Vec::new();
        let mut accessories = Vec::new();
        for role in ["body", "clothes", "eyes", "hair"] {
            let mut mesh = Mesh::new(
                PrimitiveTopology::TriangleList,
                RenderAssetUsages::default(),
            );
            mesh.insert_attribute(
                Mesh::ATTRIBUTE_POSITION,
                vec![[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]],
            );
            mesh.insert_attribute(Mesh::ATTRIBUTE_NORMAL, vec![[0., 0., 1.]; 3]);
            mesh.insert_attribute(Mesh::ATTRIBUTE_UV_0, vec![[0., 0.]; 3]);
            mesh.insert_indices(Indices::U32(vec![0, 1, 2]));
            let mesh = world.resource_mut::<Assets<Mesh>>().add(mesh);
            let material = world
                .resource_mut::<Assets<StandardMaterial>>()
                .add(StandardMaterial {
                    base_color_texture: Some(image.clone()),
                    alpha_mode: AlphaMode::Mask(0.5),
                    cull_mode: Some(bevy::render::render_resource::Face::Back),
                    ..default()
                });
            let entity = world
                .spawn((
                    Mesh3d(mesh.clone()),
                    MeshMaterial3d(material.clone()),
                    Transform::default(),
                    Visibility::Inherited,
                ))
                .id();
            // This fixture tests bound controls without running propagation/render schedules.
            world.entity_mut(entity).remove::<InheritedVisibility>();
            if matches!(role, "body" | "clothes") {
                parts.push(json!({"name":role,"display_entity":format!("{entity:?}"),"mesh_handle":format!("{:?}",mesh.id())}));
            } else {
                accessories.push(json!({"name":role,"entity":format!("{entity:?}"),"mesh_handle":format!("{:?}",mesh.id()),"material_handle":format!("{:?}",material.id())}));
            }
        }
        (
            world,
            State::default(),
            json!({"accessories":accessories}),
            json!({"parts":parts}),
        )
    }
    #[test]
    fn actual_bound_controls_restore_materials_and_keep_buffers_and_coverage() {
        let (mut world, mut state, appearance, base) = fixture();
        assert!(!state.bind(&mut world, &appearance, &base).unwrap());
        state.prepare(&mut world);
        assert!(state.bind(&mut world, &appearance, &base).unwrap());
        let original = state
            .buffers_checked(&world, false, crate::candidate::Variant::AOriginal)
            .unwrap();
        let baseline = state.apply(&mut world).unwrap();
        assert!(
            baseline["targets"]
                .as_array()
                .unwrap()
                .iter()
                .all(|t| t["production_material"] == t["render_material"]
                    && t["isolation_hidden"] == false)
        );
        state.configure(Mode::HairOnly, Palette::RoleTint);
        state.prepare(&mut world);
        let tinted = state.apply(&mut world).unwrap();
        assert_eq!(
            original,
            state
                .buffers_checked(&world, false, crate::candidate::Variant::AOriginal)
                .unwrap()
        );
        for target in tinted["targets"].as_array().unwrap() {
            assert_eq!(target["isolation_hidden"], target["role"] != "hair");
            for key in [
                "base_color_texture",
                "alpha_mode",
                "cull_mode",
                "double_sided",
                "roughness",
                "metallic",
            ] {
                assert_eq!(
                    target["production_material"][key],
                    target["render_material"][key]
                );
            }
            if target["role"] == "hair" || target["role"] == "body" {
                assert_eq!(target["render_material"]["unlit"], true);
            }
        }
        state.configure(Mode::Combined, Palette::Textured);
        state.prepare(&mut world);
        let recovered = state.apply(&mut world).unwrap();
        assert_eq!(baseline, recovered);
        assert_eq!(
            original,
            state
                .buffers_checked(&world, false, crate::candidate::Variant::AOriginal)
                .unwrap()
        );
    }
    #[test]
    fn actual_handle_replacement_and_missing_entity_reject() {
        let (mut world, mut state, appearance, base) = fixture();
        state.bind(&mut world, &appearance, &base).unwrap();
        assert!(
            state
                .buffers(&world, crate::candidate::Variant::AOriginal)
                .unwrap_err()
                .contains("pinned source")
        );
        let entity = state.targets[0].entity;
        let old = state.targets[0].material.clone();
        let replaced = world
            .resource_mut::<Assets<StandardMaterial>>()
            .add(StandardMaterial::default());
        world.entity_mut(entity).insert(MeshMaterial3d(replaced));
        assert!(
            state
                .apply(&mut world)
                .unwrap_err()
                .contains("binding changed")
        );
        world.entity_mut(entity).insert(MeshMaterial3d(old));
        assert!(world.despawn(entity));
        assert!(state.bind(&mut world, &appearance, &base).is_err());
    }
    #[test]
    fn clear_restores_actual_visibility_and_material_after_error() {
        let (mut world, mut state, appearance, base) = fixture();
        state.bind(&mut world, &appearance, &base).unwrap();
        state.configure(Mode::BodyOnly, Palette::UnlitTextured);
        state.prepare(&mut world);
        state.apply(&mut world).unwrap();
        let eyes = state
            .targets
            .iter()
            .find(|t| t.role == "hair")
            .unwrap()
            .entity;
        assert_eq!(world.get::<Visibility>(eyes), Some(&Visibility::Hidden));
        state.clear(&mut world);
        assert_eq!(world.get::<Visibility>(eyes), Some(&Visibility::Inherited));
        let handle = &world
            .get::<MeshMaterial3d<StandardMaterial>>(eyes)
            .unwrap()
            .0;
        assert!(
            !world
                .resource::<Assets<StandardMaterial>>()
                .get(handle)
                .unwrap()
                .unlit
        );
    }
}

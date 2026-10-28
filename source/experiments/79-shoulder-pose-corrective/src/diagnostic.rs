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
    SourceBody,
    SourceGarment,
    Corrective,
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
            Mode::Combined | Mode::SourceBody | Mode::SourceGarment | Mode::Corrective => true,
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
            || targets.iter().filter(|t| t.role == "eyes").count() != 1
        {
            return Err("exactly one production body and eyes required".into());
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
            if self.palette != Palette::Textured && matches!(target.role.as_str(), "body" | "eyes")
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
    pub fn buffers(&self, world: &World) -> Result<Value, String> {
        self.buffers_checked(world)
    }
    fn buffers_checked(&self, world: &World) -> Result<Value, String> {
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
            let source_map = Value::Null; // Accessory source validation remains production-owned; no new eye correspondence.
            records.push(json!({"role":target.role,"entity":format!("{:?}",target.entity),"mesh_handle":format!("{:?}",target.mesh.id()),"source_map":source_map,"positions":positions,"normals":normals,"uv_0":uv,"indices":indices,"display_transform":global,"positions_sha256":appearance_sha256(positions.to_string().as_bytes()),"scope":"already posed metre-space actual uploaded CPU positions; world=display_transform*positions exactly once; no second model_to_world/flip/scale/skin"}));
        }
        Ok(json!(records))
    }
}
fn material_record(m: &StandardMaterial) -> Value {
    json!({"base_color":format!("{:?}",m.base_color),"base_color_texture":m.base_color_texture.as_ref().map(|h|format!("{:?}",h.id())),"unlit":m.unlit,"alpha_mode":format!("{:?}",m.alpha_mode),"cull_mode":format!("{:?}",m.cull_mode),"double_sided":m.double_sided,"roughness":m.perceptual_roughness,"metallic":m.metallic,"full_standard_material_debug":format!("{m:?}")})
}

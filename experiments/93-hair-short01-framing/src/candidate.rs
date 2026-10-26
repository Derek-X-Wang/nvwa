//! Experiment-only mesh buffer publication. Original mesh is restored at PreUpdate,
//! validated through production, then the selected variant is published at Last.
//! No second entity, display transform, bone skinning or material allocation.
//! B uses authenticated short01 geometry/UV/texture; existing material policy stays exact.
use crate::geometry;
use bevy::camera::primitives::{Aabb, MeshAabb};
use bevy::{
    asset::RenderAssetUsages,
    image::{CompressedImageFormats, ImageSampler, ImageType},
};
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
    BShort01,
}
// Exact raw-Value policy shared by production-called publication and fixture controls.
const ALLOWED_WORKS: &[&str] = &[
    include_str!("../works/default.nvwa.json"),
    include_str!("../works/head-width-plus.nvwa.json"),
    include_str!("../works/plus-knee.nvwa.json"),
    include_str!("../works/plus-arms.nvwa.json"),
    include_str!("../works/minus-knee.nvwa.json"),
    include_str!("../works/minus-arms.nvwa.json"),
    include_str!("../works/default-knee.nvwa.json"),
    include_str!("../works/default-arms.nvwa.json"),
    include_str!("../works/shoulder-baseline-arms.nvwa.json"),
    include_str!("../works/shoulder-rear-baseline-arms.nvwa.json"),
    include_str!("../works/plus-arms-framing160.nvwa.json"),
    include_str!("../works/plus-knee-framing160.nvwa.json"),
];
fn allows_work_value(actual_work: &Value) -> bool {
    ALLOWED_WORKS
        .iter()
        .any(|raw| serde_json::from_str::<Value>(raw).is_ok_and(|w| w == *actual_work))
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
    a_image: Image,
    b_image: Image,
    b_image_pixels: String,
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
    saved_image: Option<(Handle<Image>, Image)>,
    pub motion: Vec<Value>,
    culling_witness: Value,
}
fn hash(v: &Value) -> String {
    appearance_sha256(v.to_string().as_bytes())
}
/// All non-pixel Image fields in the pinned Bevy version. Debug preserves the
/// complete descriptors and sampler without copying a16MiB RGBA array to JSON.
pub(super) fn image_policy(image: &Image) -> Value {
    json!({"data_order":format!("{:?}",image.data_order),
        "texture_descriptor":format!("{:?}",image.texture_descriptor),
        "sampler":format!("{:?}",image.sampler),
        "texture_view_descriptor":format!("{:?}",image.texture_view_descriptor),
        "asset_usage":format!("{:?}",image.asset_usage),
        "copy_on_resize":image.copy_on_resize})
}
pub(super) fn bound_image_policies(world: &World) -> Value {
    let materials = world.resource::<Assets<StandardMaterial>>();
    let images = world.resource::<Assets<Image>>();
    let mut records=world.iter_entities().filter_map(|entity| {
        entity.get::<Mesh3d>()?;
        let material=&entity.get::<MeshMaterial3d<StandardMaterial>>()?.0;
        let image=materials.get(material)?.base_color_texture.as_ref()?;
        Some(json!({"entity":format!("{:?}",entity.id()),"material":format!("{:?}",material.id()),
            "image":format!("{:?}",image.id()),"policy":images.get(image).map(image_policy)}))
    }).collect::<Vec<_>>();
    records.sort_by_key(Value::to_string);
    json!(records)
}
fn sha(bytes: &[u8], expected: &str) -> Result<(), String> {
    if appearance_sha256(bytes) != expected {
        return Err("hair source authentication failed".into());
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
// The actual publication caller and offline tests use the same authenticated import.
fn short01_fitted(cage: &[[f64; 3]], weights: &[Vec<f64>]) -> Result<Fitted, String> {
    const MAP: &str = include_str!("../candidate/short01/short01.mhclo");
    const OBJ: &str = include_str!("../candidate/short01/short01.obj");
    sha(
        MAP.as_bytes(),
        "ae1ffaa98da5753b803b3a173bede4895d2215e6bb94763f3765a71f0e984f35",
    )?;
    sha(
        OBJ.as_bytes(),
        "d998d8416f9b5d5591f1d756f4d292288d000a6951bc0f4d2e8e72727bbc44fa",
    )?;
    sha(
        include_bytes!("../candidate/short01/short01.mhmat"),
        "01e2e12ce3f3d3c859225456660acadcdd27d4f4b4d888bcbd6f11998cadd975",
    )?;
    sha(
        include_bytes!("../candidate/short01/makehuman_system_assets.json"),
        "e86f1572432cfd062f372adddba4eb7c2e2e31280e96c29291a970320e0a5df0",
    )?;
    fitted(MAP, OBJ, 2984, cage, weights)
}
fn short01_image() -> Result<(Image, String), String> {
    let png = include_bytes!("../candidate/short01/short01_diffuse.png");
    sha(
        png,
        "f34a0957184e3d1e911ed59245f874f8d4843f61ee44ff49f43edb4be0196949",
    )?;
    let image = Image::from_buffer(
        png,
        ImageType::Extension("png"),
        CompressedImageFormats::NONE,
        true,
        ImageSampler::default(),
        RenderAssetUsages::default(),
    )
    .map_err(|e| format!("authenticated short01 PNG decode: {e}"))?;
    let pixels = appearance_sha256(image.data.as_ref().ok_or("short01 RGBA absent")?);
    if image.width() != 2048
        || image.height() != 2048
        || pixels != "aeda8adafdfb7dc9259c074c1b1f9cb053e7d7add625abb909b00f9416606148"
    {
        return Err("short01 decode differs from authenticated original diffuse".into());
    }
    Ok((image, pixels))
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
    pub fn restore(&mut self, world: &mut World) -> Result<(), String> {
        // Detect mutation before overwriting B. A later check would erase a
        // same-pixel B sampler/descriptor change before it could invalidate ready.
        let error = self.binding.as_ref().and_then(|binding| {
            let expected = if self.saved_image.is_some() {
                &binding.b_image
            } else {
                &binding.a_image
            };
            world
                .resource::<Assets<Image>>()
                .get(&binding.image)
                .is_none_or(|actual| actual != expected)
                .then(|| "published hair Image/policy changed before restore".to_string())
        });
        if let Some((handle, original)) = self.saved_image.take() {
            if let Some(mut image) = world.resource_mut::<Assets<Image>>().get_mut(&handle) {
                *image = original;
            }
        } else if error.is_some() {
            if let Some(binding) = &self.binding {
                if let Some(mut image) = world
                    .resource_mut::<Assets<Image>>()
                    .get_mut(&binding.image)
                {
                    *image = binding.a_image.clone();
                }
            }
        }
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
        if let Some(error) = error {
            Err(error)
        } else {
            Ok(())
        }
    }
    pub fn clear(&mut self, world: &mut World) {
        let _ = self.restore(world); // Restoration always runs, including after error.
        self.binding = None;
        self.culling_witness = Value::Null;
    }
    pub fn publish(
        &mut self,
        world: &mut World,
        appearance: &Value,
        base: &Value,
    ) -> Result<Value, String> {
        let actual_work: Value =
            serde_json::from_str(&crate::current_work(world)?).map_err(|e| e.to_string())?;
        let allowed = allows_work_value(&actual_work);
        if !allowed {
            return Err(
                "exact frozen eight-parameter default/head-width-plus Work required".into(),
            );
        }
        if self.saved.is_some() {
            return Err("mesh not restored before production validation".into());
        }
        let hair = appearance["accessories"]
            .as_array()
            .ok_or("accessory snapshot absent")?
            .iter()
            .find(|a| a["name"] == "hair")
            .ok_or("exact production hair absent")?;
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
            hair["entity"],
            hair["mesh_handle"],
            hair["material_handle"],
            hair["texture"]
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
            const MAP: &str = include_str!(
                "../../../assets/appearances/mpfb-b1-cc0-v1/hair/short04/short04.mhclo"
            );
            const OBJ: &str =
                include_str!("../../../assets/appearances/mpfb-b1-cc0-v1/hair/short04/short04.obj");
            sha(
                MAP.as_bytes(),
                "d60640aa4c4ffce1aa269647ba436b6ee0bb21bb948f927b84e27a48d2107157",
            )?;
            sha(
                OBJ.as_bytes(),
                "676964a133ee35ffcea1195382bf75542da7a298931e4001bc7b0d7b707225de",
            )?;
            sha(
                include_bytes!(
                    "../../../assets/appearances/mpfb-b1-cc0-v1/hair/short04/short04.mhmat"
                ),
                "7a3ac74db8478aa0afdb8a596c6fe3997d1a8a09d12211d70e8f1e9f0b7e0e97",
            )?;
            let a = fitted(
                include_str!(
                    "../../../assets/appearances/mpfb-b1-cc0-v1/hair/short04/short04.mhclo"
                ),
                include_str!("../../../assets/appearances/mpfb-b1-cc0-v1/hair/short04/short04.obj"),
                865,
                &cage,
                &weights,
            )?;
            let b = short01_fitted(&cage, &weights)?;
            let (b_image, b_image_pixels) = short01_image()?;
            let entity = entity(world, &hair["entity"])?;
            let character = crate::candidate::entity(world, &base["character_entity"])?;
            let mesh = world
                .get::<Mesh3d>(entity)
                .ok_or("actual hair Mesh3d absent")?
                .0
                .clone();
            let material = world
                .get::<MeshMaterial3d<StandardMaterial>>(entity)
                .ok_or("actual hair material binding absent")?
                .0
                .clone();
            let m = world
                .resource::<Assets<StandardMaterial>>()
                .get(&material)
                .ok_or("actual hair material absent")?;
            let image = m.base_color_texture.clone().ok_or("hair texture absent")?;
            let pixels = world
                .resource::<Assets<Image>>()
                .get(&image)
                .ok_or("actual bound hair image absent")?;
            let image_pixels = appearance_sha256(
                pixels
                    .data
                    .as_ref()
                    .ok_or("actual hair CPU pixels absent")?,
            );
            if image_pixels != "c7ba27fdb3c6c3872f9e0c2c1ddc1b7f042d9fe8211ad0034d1dcb0e5d030bdb"
                || pixels.width() != 2048
                || pixels.height() != 2048
                || image_policy(pixels) != image_policy(&b_image)
            {
                return Err("A/B original image domain/sampler/mip policy differs".into());
            }
            let work = crate::current_work(world)?;
            let placement = world
                .get::<GlobalTransform>(entity)
                .ok_or("hair placement absent")?
                .to_matrix()
                .to_cols_array();
            if json!(placement) != body["display_transform"] {
                return Err("hair/body display placement differs".into());
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
                image_pixels: image_pixels.clone(),
                a_image: pixels.clone(),
                b_image,
                b_image_pixels,
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
        if world.resource::<nvwa_runtime::Playback>().error.is_some()
            || world
                .resource::<nvwa_runtime::EditorState>()
                .open_error
                .is_some()
        {
            return Err("retained Open/playback error forbids candidate publication".into());
        }
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
            return Err("actual hair entity/mesh/material/placement epoch changed".into());
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
        if image != &bind.a_image {
            return Err("actual A hair Image/policy changed before publication".into());
        }
        let original_image = image.clone();
        let matrices = matrices(bones)?;
        let original = world
            .resource::<Assets<Mesh>>()
            .get(&bind.mesh)
            .ok_or("actual hair mesh lost")?;
        verify_a(original, &bind.a, &matrices)?;
        let selected = if self.variant == Variant::AOriginal {
            &bind.a
        } else {
            &bind.b
        };
        let (p, n) = arrays(selected, &matrices)?;
        if self.variant == Variant::BShort01 {
            let saved = original.clone();
            let mut assets = world.resource_mut::<Assets<Mesh>>();
            let mut mesh = assets
                .get_mut(&bind.mesh)
                .ok_or("hair mesh lost during publication")?;
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
            self.saved_image = Some((bind.image.clone(), original_image));
            *world
                .resource_mut::<Assets<Image>>()
                .get_mut(&bind.image)
                .ok_or("hair image lost during publication")? = bind.b_image.clone();
        }
        let actual = world
            .resource::<Assets<Mesh>>()
            .get(&bind.mesh)
            .ok_or("published hair mesh absent")?;
        if !matches!(actual.attribute(Mesh::ATTRIBUTE_POSITION),Some(VertexAttributeValues::Float32x3(v)) if *v==p)
            || !matches!(actual.attribute(Mesh::ATTRIBUTE_NORMAL),Some(VertexAttributeValues::Float32x3(v)) if *v==n)
            || !matches!(actual.attribute(Mesh::ATTRIBUTE_UV_0),Some(VertexAttributeValues::Float32x2(v)) if *v==selected.obj.uv)
            || actual.indices().map(|i| i.iter().collect::<Vec<_>>())
                != Some(selected.obj.indices.iter().map(|i| *i as usize).collect())
        {
            return Err("actual published B buffers differ".into());
        }
        let image = world
            .resource::<Assets<Image>>()
            .get(&bind.image)
            .ok_or("published hair image absent")?;
        let actual_pixels = appearance_sha256(image.data.as_ref().ok_or("published RGBA absent")?);
        let expected_pixels = if self.variant == Variant::AOriginal {
            &bind.image_pixels
        } else {
            &bind.b_image_pixels
        };
        let expected_image = if self.variant == Variant::AOriginal {
            &bind.a_image
        } else {
            &bind.b_image
        };
        if &actual_pixels != expected_pixels || image != expected_image {
            return Err("actual published image pixels differ".into());
        }
        let publication = json!({"variant":format!("{:?}",self.variant),"positions_sha256":hash(&json!(p)),"normals_sha256":hash(&json!(n)),"image_rgba_sha256":actual_pixels,"image_policy":image_policy(image),"placement":bind.placement,"camera":crate::camera_report(world),"work_sha256":appearance_sha256(bind.work.as_bytes()),"generation":bind.generation});
        let culling_matches = publication_matches(&self.culling_witness, &publication);
        Ok(
            json!({"variant":format!("{:?}",self.variant),"A_replay_exact":true,"pre_visibility_publication_matches":culling_matches,"pre_visibility_publication":self.culling_witness,"entity":format!("{:?}",bind.entity),"mesh_handle":format!("{:?}",bind.mesh.id()),"material_handle":format!("{:?}",bind.material.id()),"image_handle":format!("{:?}",bind.image.id()),"decoded_rgba_sha256":actual_pixels,"original_decoded_rgba_sha256":bind.image_pixels,"actual_image_width":image.width(),"actual_image_height":image.height(),"actual_image_format":format!("{:?}",image.texture_descriptor.format),"actual_image_mip_count":image.texture_descriptor.mip_level_count,"actual_image_sampler":format!("{:?}",image.sampler),"actual_image_policy":image_policy(image),"original_standard_material_debug":bind.material_debug,"display_transform":bind.placement,"generation":bind.generation,"sample":sample,"actual_aabb":world.get::<Aabb>(bind.entity).map(|a|json!({"center":a.center.to_array(),"half_extents":a.half_extents.to_array()})),"bounds_policy":"exact mesh compute_aabb; no inflation or disabled culling","source_vertices":selected.obj.count,"render_vertices":p.len(),"triangles":selected.obj.indices.len()/3,"source_uv_pairs":selected.obj.pairs,"rest_source_positions":selected.rest,"rest_source_normals":selected.normals,"full_positive_source_weights":selected.weights,"source_scales":selected.scales,"bones":bones,"published_positions_sha256":hash(&json!(p)),"published_normals_sha256":hash(&json!(n)),"policy":"simple-srgb-mask-v1 unchanged; raw MHCLO decimetres converted once; actual body cage metres; original hair entity placement exactly once","scope":"actual bound CPU arrays; no GPU readback or rendered-hairline quality claim"}),
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
        let image = world
            .resource::<Assets<Image>>()
            .get(&b.image)
            .ok_or("previsibility image absent")?;
        let pixels = appearance_sha256(image.data.as_ref().ok_or("previsibility RGBA absent")?);
        self.culling_witness = json!({"variant":format!("{:?}",self.variant),"positions_sha256":hash(&json!(p)),"normals_sha256":hash(&json!(n)),"image_rgba_sha256":pixels,"image_policy":image_policy(image),"placement":b.placement,"camera":crate::camera_report(world),"work_sha256":appearance_sha256(b.work.as_bytes()),"generation":b.generation});
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
            self.motion.push(json!({"variant":record["variant"],"generation":record["generation"],"sample":sample,"observed_bones":record["bones"],"observation_coverage":"actual53named bone_frames hierarchy and all supplied model-local matrix fields at retained samples only; intervals between samples UNOBSERVED; joint motion absent from retained matrices NOT-COVERED; no CPU replay is labeled observed","A_replay_exact":record["A_replay_exact"],"entity":record["entity"],"mesh_handle":record["mesh_handle"],"material_handle":record["material_handle"],"image_handle":record["image_handle"],"published_positions_sha256":record["published_positions_sha256"],"published_normals_sha256":record["published_normals_sha256"],"scope":"continuous CPU publication witness; separate video observation required"}));
        }
        Ok(())
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn every_frozen_cohort_roundtrips_through_actual_allowlist() {
        for raw in ALLOWED_WORKS.iter().skip(2) {
            let pinned: Value = serde_json::from_str(raw).unwrap();
            let document = nvwa_core::SceneDocument::from_json(raw).unwrap();
            let actual: Value = serde_json::from_str(&document.to_json().unwrap()).unwrap();
            assert_eq!(
                pinned, actual,
                "fixture numeric tokens must match actual SceneDocument serialization"
            );
            assert!(
                allows_work_value(&actual),
                "actual publication gate must admit every frozen fixture"
            );
            // Same typed recipe, different numeric kind: this is the observed r1 failure.
            // Require the exact live gate to reject it, without relaxing its policy.
            let mut integer_mutation = actual.clone();
            integer_mutation["character"]["parameters"]["torso_length"] = json!(
                actual["character"]["parameters"]["torso_length"]
                    .as_f64()
                    .unwrap() as i64
            );
            assert!(nvwa_core::SceneDocument::from_json(&integer_mutation.to_string()).is_ok());
            assert!(!allows_work_value(&integer_mutation));
        }
    }
    #[test]
    fn production_called_publication_gate_rejects_every_changed_epoch_field() {
        let current = json!({"variant":"BShort01","positions_sha256":"p","normals_sha256":"n","image_rgba_sha256":"i","image_policy":{"sampler":"Default"},"placement":[1,2],"camera":{"viewport":[1280,720]},"work_sha256":"w","generation":2});
        assert!(publication_matches(&current, &current));
        assert!(!publication_matches(&Value::Null, &current));
        for key in [
            "variant",
            "positions_sha256",
            "normals_sha256",
            "image_rgba_sha256",
            "image_policy",
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
        world.init_resource::<Assets<Image>>();
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
        let original_image = Image::default();
        let image = world
            .resource_mut::<Assets<Image>>()
            .add(original_image.clone());
        world
            .resource_mut::<Assets<Image>>()
            .get_mut(&image)
            .unwrap()
            .data = Some(vec![9; 4]);
        state.saved_image = Some((image.clone(), original_image.clone()));
        state.restore(&mut world).unwrap();
        assert!(state.saved.is_none());
        assert!(state.saved_image.is_none());
        assert_eq!(
            world.resource::<Assets<Image>>().get(&image).unwrap().data,
            original_image.data
        );
        assert!(
            matches!(world.resource::<Assets<Mesh>>().get(&mesh).unwrap().attribute(Mesh::ATTRIBUTE_POSITION),Some(VertexAttributeValues::Float32x3(v)) if v[0]==[0.,0.,0.])
        );
        assert_eq!(world.get::<Aabb>(entity).unwrap().center, aabb.center);
    }
    #[test]
    fn authenticated_candidate_and_no_cap_contract() {
        assert!(
            sha(
                include_bytes!(
                    "../../../assets/appearances/mpfb-b1-cc0-v1/hair/short04/short04.obj"
                ),
                "676964a133ee35ffcea1195382bf75542da7a298931e4001bc7b0d7b707225de"
            )
            .is_ok()
        );
        let obj = geometry::obj(
            include_str!("../../../assets/appearances/mpfb-b1-cc0-v1/hair/short04/short04.obj"),
            865,
        )
        .unwrap();
        assert_eq!(obj.indices.len() / 3, 1050);
        assert!(obj.pairs.len() == 991);
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

#[cfg(test)]
#[path = "source_tests.rs"]
mod source_tests;

#[cfg(test)]
#[path = "framing_source_tests.rs"]
mod framing_source_tests;

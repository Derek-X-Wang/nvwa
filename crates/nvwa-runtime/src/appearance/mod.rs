//! Saved appearance binds only the current production B1 body. It owns every
//! generated accessory mesh/material/image and restores the original body UV/material.
mod assets;
mod geometry;
use crate::{
    EditorState, RuntimeStatus,
    b1::{AppearanceFit, AppearanceFrame, appearance_fit, appearance_frame, appearance_identity},
};
use bevy::{
    asset::RenderAssetUsages,
    math::DMat4,
    mesh::{Indices, PrimitiveTopology, VertexAttributeValues},
    prelude::*,
    render::render_resource::{Face, TextureFormat},
};
use nvwa_core::{CharacterAppearance, appearance_sha256};
use serde_json::{Value, json};

#[derive(Resource, Clone, Debug, Default)]
pub struct AppearanceStatus {
    pub requested: CharacterAppearance,
    /// Invalidated on any pending/error binding. Never a stale successful selection.
    pub applied: Option<CharacterAppearance>,
    pub generation: Option<u64>,
    pub revision: Option<u64>,
    pub character_entity: Option<String>,
    pub body_entity: Option<String>,
    pub ready: bool,
    pub pending: bool,
    pub error: Option<String>,
}
#[derive(Clone, PartialEq)]
struct Key {
    generation: u64,
    character: Entity,
    body: Entity,
    mesh: Handle<Mesh>,
    flags: (bool, bool, bool),
}
impl Key {
    fn new(frame: &AppearanceFrame, flags: (bool, bool, bool)) -> Self {
        Self {
            generation: frame.generation,
            character: frame.character,
            body: frame.body,
            mesh: frame.mesh.clone(),
            flags,
        }
    }
}
struct Texture {
    handle: Handle<Image>,
    pixels_sha: String,
    size: u32,
}
struct SkinBinding {
    entity: Entity,
    mesh: Handle<Mesh>,
    baseline: Handle<StandardMaterial>,
    material: Handle<StandardMaterial>,
    texture: Texture,
    original_uv: Option<VertexAttributeValues>,
    uv: Vec<[f32; 2]>,
}
struct Live {
    name: &'static str,
    entity: Entity,
    mesh: Handle<Mesh>,
    material: Handle<StandardMaterial>,
    texture: Texture,
    rest: Vec<[f64; 3]>,
    normals: Vec<[f64; 3]>,
    weights: Vec<Vec<(usize, f64)>>,
    obj: geometry::Obj,
    hair: bool,
}
#[derive(Resource, Default)]
pub(super) struct AppearanceRuntime {
    authenticated: bool,
    key: Option<Key>,
    skin: Option<SkinBinding>,
    live: Vec<Live>,
    failed: Option<(Key, u64, String)>,
}
fn hash(value: Value) -> Result<String, String> {
    Ok(appearance_sha256(
        &serde_json::to_vec(&value).map_err(|e| e.to_string())?,
    ))
}
fn texture(world: &mut World, image: Image, size: u32) -> Result<Texture, String> {
    let pixels_sha = appearance_sha256(
        image
            .data
            .as_ref()
            .ok_or("appearance: decoded CPU pixels absent")?,
    );
    Ok(Texture {
        handle: world.resource_mut::<Assets<Image>>().add(image),
        pixels_sha,
        size,
    })
}
/// All material policy lives here so a reviewed future policy has one boundary.
fn accessory_material(image: Handle<Image>, hair: bool) -> StandardMaterial {
    StandardMaterial {
        base_color: Color::WHITE,
        base_color_texture: Some(image),
        perceptual_roughness: 0.7,
        metallic: 0.,
        alpha_mode: AlphaMode::Mask(0.5),
        cull_mode: if hair { None } else { Some(Face::Back) },
        double_sided: hair,
        ..default()
    }
}
fn dispose(world: &mut World, state: &mut AppearanceRuntime) -> Result<(), String> {
    let mut errors = vec![];
    if let Some(skin) = state.skin.take() {
        if let Some(mut mesh) = world.resource_mut::<Assets<Mesh>>().get_mut(&skin.mesh) {
            match skin.original_uv {
                Some(uv) => {
                    mesh.insert_attribute(Mesh::ATTRIBUTE_UV_0, uv);
                }
                None => {
                    mesh.remove_attribute(Mesh::ATTRIBUTE_UV_0);
                }
            }
        }
        if world.get_entity(skin.entity).is_ok() {
            if world
                .get::<Mesh3d>(skin.entity)
                .is_some_and(|m| m.0 == skin.mesh)
            {
                if let Ok(mut entity) = world.get_entity_mut(skin.entity) {
                    entity.insert(MeshMaterial3d(skin.baseline));
                }
            } else {
                errors.push("appearance: body mesh binding changed during restoration".to_string());
            }
        }
        world
            .resource_mut::<Assets<StandardMaterial>>()
            .remove(skin.material.id());
        world
            .resource_mut::<Assets<Image>>()
            .remove(skin.texture.handle.id());
    }
    for live in state.live.drain(..) {
        let _ = world.despawn(live.entity);
        world.resource_mut::<Assets<Mesh>>().remove(live.mesh.id());
        world
            .resource_mut::<Assets<StandardMaterial>>()
            .remove(live.material.id());
        world
            .resource_mut::<Assets<Image>>()
            .remove(live.texture.handle.id());
    }
    state.key = None;
    if errors.is_empty() {
        Ok(())
    } else {
        Err(errors.join("; "))
    }
}
fn matrices(frame: &AppearanceFrame) -> Result<Vec<DMat4>, String> {
    if frame.bones.len() != 53 {
        return Err("appearance: exact53 actual bones required".into());
    }
    frame
        .bones
        .iter()
        .map(|b| {
            let m = DMat4::from_cols_array(&b.skin.map(f64::from));
            if !m.is_finite() || !m.determinant().is_finite() || m.determinant().abs() < 1e-12 {
                return Err("appearance: actual skin matrix singular/nonfinite".into());
            }
            Ok(m)
        })
        .collect()
}
type PreparedAccessory = (
    geometry::Prepared,
    Vec<[f64; 3]>,
    Vec<Vec<(usize, f64)>>,
    Vec<[f64; 3]>,
    Vec<[f32; 3]>,
    Vec<[f32; 3]>,
    Image,
);
fn prepare(
    frame: &AppearanceFrame,
    fit: &AppearanceFit,
    flags: (bool, bool, bool),
) -> Result<(Option<Image>, Vec<PreparedAccessory>), String> {
    let matrices = matrices(frame)?;
    // Decode, fit, transfer, and skin every selected role before allocating or publishing.
    let skin_image = if flags.0 {
        Some(assets::decode(assets::SKIN_PNG, 2048)?)
    } else {
        None
    };
    let mut prepared = vec![];
    if flags.1 || flags.2 {
        let cage = geometry::cage(&fit.source_ids, &fit.rest)?;
        let source = geometry::weights(
            &frame
                .bones
                .iter()
                .map(|b| b.name.clone())
                .collect::<Vec<_>>(),
        )?;
        for p in geometry::prepare()?
            .into_iter()
            .filter(|p| if p.hair { flags.2 } else { flags.1 })
        {
            let (rest, _scales) = geometry::fit(&p.mapping, &cage)?;
            let weights = geometry::transfer(&p.mapping, &source)?;
            let normals = geometry::source_normals(&rest, &p.obj)?;
            let (positions, posed_normals) = geometry::skin(&rest, &normals, &weights, &matrices)?;
            let image = assets::decode(p.png, p.size)?;
            prepared.push((p, rest, weights, normals, positions, posed_normals, image));
        }
    }
    Ok((skin_image, prepared))
}
/// Candidate Open authenticates and fits all selected roles before committing Work/body.
pub(super) fn preflight(
    frame: &AppearanceFrame,
    fit: &AppearanceFit,
    appearance: &CharacterAppearance,
) -> Result<(), String> {
    if let Some(flags) = appearance.b1_flags() {
        assets::authenticate()?;
        let _ = prepare(frame, fit, flags)?;
    }
    Ok(())
}
fn build(
    world: &mut World,
    state: &mut AppearanceRuntime,
    frame: &AppearanceFrame,
    flags: (bool, bool, bool),
) -> Result<(), String> {
    if !state.authenticated {
        assets::authenticate()?;
        state.authenticated = true;
    }
    let fit = appearance_fit(world, frame)?;
    let baseline = world
        .resource::<Assets<StandardMaterial>>()
        .get(&frame.baseline)
        .ok_or("appearance: original material missing")?
        .clone();
    let original_uv = world
        .resource::<Assets<Mesh>>()
        .get(&frame.mesh)
        .ok_or("appearance: current body mesh absent")?
        .attribute(Mesh::ATTRIBUTE_UV_0)
        .cloned();
    let (skin_image, prepared) = prepare(frame, &fit, flags)?;
    if let Some(image) = skin_image {
        let texture = texture(world, image, 2048)?;
        let mut material = baseline;
        material.base_color = Color::WHITE;
        material.base_color_texture = Some(texture.handle.clone());
        let material = world
            .resource_mut::<Assets<StandardMaterial>>()
            .add(material);
        state.skin = Some(SkinBinding {
            entity: frame.body,
            mesh: frame.mesh.clone(),
            baseline: frame.baseline.clone(),
            material: material.clone(),
            texture,
            original_uv,
            uv: fit.uv.clone(),
        });
        world
            .resource_mut::<Assets<Mesh>>()
            .get_mut(&frame.mesh)
            .ok_or("appearance: body mesh lost during bind")?
            .insert_attribute(Mesh::ATTRIBUTE_UV_0, fit.uv);
        world
            .get_entity_mut(frame.body)
            .map_err(|_| "appearance: body entity lost during bind")?
            .insert(MeshMaterial3d(material));
    }
    for (p, rest, weights, normals, positions, posed_normals, image) in prepared {
        let texture = texture(world, image, p.size)?;
        let material = world
            .resource_mut::<Assets<StandardMaterial>>()
            .add(accessory_material(texture.handle.clone(), p.hair));
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
                Name::new(format!("B1 saved {}", p.name)),
                Mesh3d(mesh.clone()),
                MeshMaterial3d(material.clone()),
                Transform::from_matrix(frame.placement),
                GlobalTransform::from(frame.placement),
            ))
            .id();
        state.live.push(Live {
            name: p.name,
            entity,
            mesh,
            material,
            texture,
            rest,
            normals,
            weights,
            obj: p.obj,
            hair: p.hair,
        });
    }
    state.key = Some(Key::new(frame, flags));
    Ok(())
}
fn observe_texture(world: &World, texture: &Texture, pixels: bool) -> Result<Value, String> {
    let image = world
        .resource::<Assets<Image>>()
        .get(&texture.handle)
        .ok_or("appearance: bound image asset missing")?;
    if image.width() != texture.size
        || image.height() != texture.size
        || image.texture_descriptor.format != TextureFormat::Rgba8UnormSrgb
        || image
            .data
            .as_ref()
            .is_none_or(|d| d.len() != texture.size as usize * texture.size as usize * 4)
    {
        return Err("appearance: bound image domain changed".into());
    }
    let pixel_hash = if pixels {
        let hash = appearance_sha256(
            image
                .data
                .as_ref()
                .ok_or("appearance: bound pixels missing")?,
        );
        if hash != texture.pixels_sha {
            return Err("appearance: bound decoded image pixels changed".into());
        }
        Some(hash)
    } else {
        None
    };
    Ok(
        json!({"image_handle":format!("{:?}",texture.handle.id()),"width":image.width(),"height":image.height(),"format":format!("{:?}",image.texture_descriptor.format),"decoded_rgba_sha256":pixel_hash}),
    )
}
fn observe_skin(world: &World, skin: &SkinBinding, pixels: bool) -> Result<Value, String> {
    if world
        .get::<Mesh3d>(skin.entity)
        .is_none_or(|m| m.0 != skin.mesh)
        || world
            .get::<MeshMaterial3d<StandardMaterial>>(skin.entity)
            .is_none_or(|m| m.0 != skin.material)
    {
        return Err("appearance: current body mesh/material binding changed".into());
    }
    let material = world
        .resource::<Assets<StandardMaterial>>()
        .get(&skin.material)
        .ok_or("appearance: skin material absent")?;
    let baseline = world
        .resource::<Assets<StandardMaterial>>()
        .get(&skin.baseline)
        .ok_or("appearance: baseline material absent")?;
    if material.base_color != Color::WHITE
        || material.base_color_texture.as_ref() != Some(&skin.texture.handle)
        || material.metallic != baseline.metallic
        || material.perceptual_roughness != baseline.perceptual_roughness
        || material.alpha_mode != baseline.alpha_mode
        || material.cull_mode != baseline.cull_mode
        || material.double_sided != baseline.double_sided
    {
        return Err("appearance: skin material policy/binding changed".into());
    }
    let meshes = world.resource::<Assets<Mesh>>();
    let mesh = meshes
        .get(&skin.mesh)
        .ok_or("appearance: skin mesh missing")?;
    if !matches!(mesh.attribute(Mesh::ATTRIBUTE_UV_0),Some(VertexAttributeValues::Float32x2(v)) if v==&skin.uv)
    {
        return Err("appearance: body duplicate-order UV binding changed".into());
    }
    Ok(
        json!({"entity":format!("{:?}",skin.entity),"mesh_handle":format!("{:?}",skin.mesh.id()),"material_handle":format!("{:?}",skin.material.id()),"base_color":format!("{:?}",material.base_color),"roughness":material.perceptual_roughness,"metallic":material.metallic,"alpha_mode":format!("{:?}",material.alpha_mode),"cull_mode":format!("{:?}",material.cull_mode),"double_sided":material.double_sided,"uv_sha256":if pixels{Some(hash(json!(skin.uv))?)}else{None},"texture":observe_texture(world,&skin.texture,pixels)?}),
    )
}
fn observe_live(world: &World, live: &Live, pixels: bool) -> Result<Value, String> {
    if world
        .get::<Mesh3d>(live.entity)
        .is_none_or(|m| m.0 != live.mesh)
        || world
            .get::<MeshMaterial3d<StandardMaterial>>(live.entity)
            .is_none_or(|m| m.0 != live.material)
    {
        return Err("appearance: accessory entity mesh/material binding changed".into());
    }
    let material = world
        .resource::<Assets<StandardMaterial>>()
        .get(&live.material)
        .ok_or("appearance: accessory material absent")?;
    let expected = accessory_material(live.texture.handle.clone(), live.hair);
    if material.base_color != expected.base_color
        || material.base_color_texture != expected.base_color_texture
        || material.perceptual_roughness != expected.perceptual_roughness
        || material.metallic != expected.metallic
        || material.alpha_mode != expected.alpha_mode
        || material.cull_mode != expected.cull_mode
        || material.double_sided != expected.double_sided
    {
        return Err("appearance: accessory material policy/binding changed".into());
    }
    Ok(
        json!({"name":live.name,"entity":format!("{:?}",live.entity),"mesh_handle":format!("{:?}",live.mesh.id()),"material_handle":format!("{:?}",live.material.id()),"base_color":format!("{:?}",material.base_color),"roughness":material.perceptual_roughness,"metallic":material.metallic,"alpha_mode":format!("{:?}",material.alpha_mode),"cull_mode":format!("{:?}",material.cull_mode),"double_sided":material.double_sided,"texture":observe_texture(world,&live.texture,pixels)?}),
    )
}
fn stream(
    world: &mut World,
    state: &AppearanceRuntime,
    frame: &AppearanceFrame,
) -> Result<(), String> {
    let key = state
        .key
        .as_ref()
        .ok_or("appearance: no applied identity")?;
    if *key != Key::new(frame, key.flags) {
        return Err("appearance: stale generation/body binding".into());
    }
    if let Some(skin) = &state.skin {
        observe_skin(world, skin, false)?;
    } else if world
        .get::<MeshMaterial3d<StandardMaterial>>(frame.body)
        .is_none_or(|m| m.0 != frame.baseline)
    {
        return Err("appearance: baseline body material binding changed".into());
    }
    let matrices = matrices(frame)?;
    for live in &state.live {
        observe_live(world, live, false)?;
        let (positions, normals) =
            geometry::skin(&live.rest, &live.normals, &live.weights, &matrices)?;
        {
            let mut meshes = world.resource_mut::<Assets<Mesh>>();
            let mut mesh = meshes
                .get_mut(&live.mesh)
                .ok_or("appearance: accessory CPU mesh disappeared")?;
            if !matches!(mesh.attribute(Mesh::ATTRIBUTE_UV_0),Some(VertexAttributeValues::Float32x2(v)) if v==&live.obj.uv)
                || mesh.indices().map(|i| i.iter().collect::<Vec<_>>())
                    != Some(live.obj.indices.iter().map(|i| *i as usize).collect())
            {
                return Err("appearance: accessory UV/triangle binding changed".into());
            }
            mesh.insert_attribute(
                Mesh::ATTRIBUTE_POSITION,
                live.obj
                    .pairs
                    .iter()
                    .map(|(i, _)| positions[*i])
                    .collect::<Vec<_>>(),
            );
            mesh.insert_attribute(
                Mesh::ATTRIBUTE_NORMAL,
                live.obj
                    .pairs
                    .iter()
                    .map(|(i, _)| normals[*i])
                    .collect::<Vec<_>>(),
            );
        }
        world
            .get_entity_mut(live.entity)
            .map_err(|_| "appearance: accessory entity disappeared before transform update")?
            .insert((
                Transform::from_matrix(frame.placement),
                GlobalTransform::from(frame.placement),
            ));
    }
    Ok(())
}
fn invalidate(
    world: &mut World,
    state: &mut AppearanceRuntime,
    status: &mut AppearanceStatus,
    error: String,
) {
    let cleanup = dispose(world, state).err();
    status.ready = false;
    status.applied = None;
    status.error = Some(match cleanup {
        Some(cleanup) => format!("{error}; {cleanup}"),
        None => error,
    });
}
pub(super) fn update(world: &mut World) {
    let mut state = world
        .remove_resource::<AppearanceRuntime>()
        .unwrap_or_default();
    let mut status = AppearanceStatus::default();
    let doc = world.resource::<EditorState>().document().cloned();
    if let Some((generation, character, body)) = appearance_identity(world) {
        status.generation = Some(generation);
        status.character_entity = Some(format!("{character:?}"));
        status.body_entity = Some(format!("{body:?}"));
    }
    if let Some(doc) = doc {
        status.revision = Some(doc.revision);
        status.requested = doc.character.appearance.clone();
        if let Err(error) = status.requested.validate_for(&doc.profile.backend) {
            invalidate(world, &mut state, &mut status, error.to_string());
        } else if !doc.profile.backend.is_b1() {
            if let Err(error) = dispose(world, &mut state) {
                status.error = Some(error);
            } else {
                status.ready = true;
                status.applied = Some(status.requested.clone());
            }
        } else {
            match appearance_frame(world) {
                Err(error) => {
                    status.pending = world.resource::<RuntimeStatus>().error.is_none();
                    invalidate(world, &mut state, &mut status, error);
                }
                Ok(frame) => {
                    status.generation = Some(frame.generation);
                    status.revision = Some(frame.revision);
                    status.character_entity = Some(format!("{:?}", frame.character));
                    status.body_entity = Some(format!("{:?}", frame.body));
                    let flags = status.requested.b1_flags().unwrap_or((false, false, false));
                    let key = Key::new(&frame, flags);
                    let result = if let Some((_, _, error)) =
                        state.failed.as_ref().filter(|(failed_key, revision, _)| {
                            failed_key == &key && *revision == frame.revision
                        }) {
                        Err(error.clone())
                    } else {
                        (|| {
                            if state.key.as_ref() != Some(&key) {
                                dispose(world, &mut state)?;
                                if flags != (false, false, false) {
                                    build(world, &mut state, &frame, flags)?;
                                } else {
                                    state.key = Some(key.clone());
                                }
                            }
                            stream(world, &state, &frame)
                        })()
                    };
                    match result {
                        Ok(()) => {
                            state.failed = None;
                            status.ready = true;
                            status.applied = Some(status.requested.clone());
                        }
                        Err(error) => {
                            state.failed = Some((key, frame.revision, error.clone()));
                            invalidate(world, &mut state, &mut status, error);
                        }
                    }
                }
            }
        }
    } else {
        let _ = dispose(world, &mut state);
        status.pending = true;
        status.error = Some("appearance: no current Work".into());
    }
    if let Some(mut runtime_status) = world.get_resource_mut::<RuntimeStatus>() {
        runtime_status.appearance_error = if status.pending {
            None
        } else {
            status.error.clone()
        };
        if !status.ready && !status.pending {
            runtime_status.ready = false;
        }
    }
    world.insert_resource(state);
    world.insert_resource(status);
}
/// Latest controller status. Snapshot below revalidates actual CPU bindings before evidence.
pub fn appearance_status(world: &World) -> AppearanceStatus {
    world
        .get_resource::<AppearanceStatus>()
        .cloned()
        .unwrap_or_default()
}
/// Bounded actual CPU observation. It never exports whole body arrays or claims GPU readback.
/// Errors invalidate applied evidence and dispose generated appearance resources.
pub fn appearance_snapshot(world: &mut World) -> Result<Value, String> {
    let result = (|| {
        let status = world
            .get_resource::<AppearanceStatus>()
            .ok_or("appearance status absent")?;
        let doc = world
            .resource::<EditorState>()
            .document()
            .ok_or("appearance Work absent")?;
        if !status.ready
            || status.applied.as_ref() != Some(&doc.character.appearance)
            || status.requested != doc.character.appearance
        {
            return Err(status
                .error
                .clone()
                .unwrap_or("appearance is pending/current Work changed".into()));
        }
        if !doc.profile.backend.is_b1() {
            return Ok(
                json!({"requested":status.requested,"applied":status.applied,"ready":true,"body":null,"observation":"baseline; non-B1 backend"}),
            );
        }
        let frame = appearance_frame(world)?;
        let state = world.resource::<AppearanceRuntime>();
        let key = state
            .key
            .as_ref()
            .ok_or("appearance current identity absent")?;
        if *key
            != Key::new(
                &frame,
                doc.character
                    .appearance
                    .b1_flags()
                    .unwrap_or((false, false, false)),
            )
            || status.generation != Some(frame.generation)
            || status.revision != Some(frame.revision)
        {
            return Err("appearance snapshot identity is stale".into());
        }
        let skin = state
            .skin
            .as_ref()
            .map(|skin| observe_skin(world, skin, true))
            .transpose()?;
        let matrices = matrices(&frame)?;
        let mut accessories = vec![];
        for live in &state.live {
            let mut item = observe_live(world, live, true)?;
            let meshes = world.resource::<Assets<Mesh>>();
            let mesh = meshes
                .get(&live.mesh)
                .ok_or("appearance actual mesh absent")?;
            let (p, n) = geometry::skin(&live.rest, &live.normals, &live.weights, &matrices)?;
            let expected_positions = live
                .obj
                .pairs
                .iter()
                .map(|(i, _)| p[*i])
                .collect::<Vec<_>>();
            let expected_normals = live
                .obj
                .pairs
                .iter()
                .map(|(i, _)| n[*i])
                .collect::<Vec<_>>();
            if !matches!(mesh.attribute(Mesh::ATTRIBUTE_POSITION),Some(VertexAttributeValues::Float32x3(v)) if v==&expected_positions)
                || !matches!(mesh.attribute(Mesh::ATTRIBUTE_NORMAL),Some(VertexAttributeValues::Float32x3(v)) if v==&expected_normals)
                || !matches!(mesh.attribute(Mesh::ATTRIBUTE_UV_0),Some(VertexAttributeValues::Float32x2(v)) if v==&live.obj.uv)
                || mesh.indices().map(|i| i.iter().collect::<Vec<_>>())
                    != Some(live.obj.indices.iter().map(|i| *i as usize).collect())
            {
                return Err(
                    "appearance actual mesh upload differs from current full-positive frame".into(),
                );
            }
            let placement = world
                .get::<GlobalTransform>(live.entity)
                .ok_or("appearance actual placement absent")?
                .to_matrix();
            if placement != frame.placement {
                return Err("appearance actual placement differs from current body".into());
            }
            item["source_vertices"] = json!(live.obj.count);
            item["render_vertices"] = json!(expected_positions.len());
            item["triangles"] = json!(live.obj.indices.len() / 3);
            item["max_positive_influences"] = json!(live.weights.iter().map(Vec::len).max());
            item["positions_sha256"] = json!(hash(json!(expected_positions))?);
            item["normals_sha256"] = json!(hash(json!(expected_normals))?);
            item["uv_sha256"] = json!(hash(json!(live.obj.uv))?);
            item["indices_sha256"] = json!(hash(json!(live.obj.indices))?);
            item["display_transform"] = json!(placement.to_cols_array());
            accessories.push(item);
        }
        let actual_material = world
            .get::<MeshMaterial3d<StandardMaterial>>(frame.body)
            .ok_or("appearance actual body material absent")?;
        if state.skin.is_none() && actual_material.0 != frame.baseline {
            return Err("appearance actual baseline binding changed".into());
        }
        let meshes = world.resource::<Assets<Mesh>>();
        let body = meshes
            .get(&frame.mesh)
            .ok_or("appearance actual body mesh missing")?;
        let positions = match body.attribute(Mesh::ATTRIBUTE_POSITION) {
            Some(VertexAttributeValues::Float32x3(v)) => v,
            _ => return Err("appearance actual body positions missing".into()),
        };
        Ok(
            json!({"requested":status.requested,"applied":status.applied,"ready":true,"generation":frame.generation,"revision":frame.revision,"serial":frame.serial,"character_entity":format!("{:?}",frame.character),"body_entity":format!("{:?}",frame.body),"body_mesh":format!("{:?}",frame.mesh.id()),"body_material":format!("{:?}",actual_material.0.id()),"body_vertices":positions.len(),"body_positions_sha256":hash(json!(positions))?,"skin":skin,"accessories":accessories,"observation":"current entity handles -> CPU Assets<Mesh/StandardMaterial/Image>; NOT GPU readback","error":null}),
        )
    })();
    if let Err(error) = &result {
        let mut state = world
            .remove_resource::<AppearanceRuntime>()
            .unwrap_or_default();
        let mut status = appearance_status(world);
        invalidate(world, &mut state, &mut status, error.clone());
        if let Some(mut runtime_status) = world.get_resource_mut::<RuntimeStatus>() {
            runtime_status.appearance_error = Some(error.clone());
            runtime_status.ready = false;
        }
        world.insert_resource(state);
        world.insert_resource(status);
    }
    result
}

#[cfg(test)]
pub(super) fn test_influence_bone_names(
    world: &World,
    role: &str,
) -> Result<std::collections::BTreeSet<String>, String> {
    let state = world.resource::<AppearanceRuntime>();
    let frame = appearance_frame(world)?;
    let live = state
        .live
        .iter()
        .find(|live| live.name == role)
        .ok_or("test role is not bound")?;
    live.weights
        .iter()
        .flat_map(|row| row.iter().map(|(bone, _)| *bone))
        .map(|bone| {
            frame
                .bones
                .get(bone)
                .map(|bone| bone.name.clone())
                .ok_or("test influence bone is absent".into())
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> (World, AppearanceRuntime, AppearanceFrame) {
        let mut world = World::new();
        world.init_resource::<Assets<Mesh>>();
        world.init_resource::<Assets<StandardMaterial>>();
        world.init_resource::<Assets<Image>>();
        let image = assets::decode(geometry::prepare().unwrap().remove(0).png, 1024).unwrap();
        let texture = texture(&mut world, image, 1024).unwrap();
        let material = world
            .resource_mut::<Assets<StandardMaterial>>()
            .add(accessory_material(texture.handle.clone(), false));
        let obj = geometry::Obj {
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
        mesh.insert_attribute(Mesh::ATTRIBUTE_UV_0, obj.uv.clone());
        mesh.insert_indices(Indices::U32(obj.indices.clone()));
        let mesh = world.resource_mut::<Assets<Mesh>>().add(mesh);
        let entity = world
            .spawn((
                Mesh3d(mesh.clone()),
                MeshMaterial3d(material.clone()),
                Transform::default(),
                GlobalTransform::default(),
            ))
            .id();
        let baseline = world
            .resource_mut::<Assets<StandardMaterial>>()
            .add(StandardMaterial::default());
        let body_mesh = world.resource_mut::<Assets<Mesh>>().add(Mesh::new(
            PrimitiveTopology::TriangleList,
            RenderAssetUsages::default(),
        ));
        let body = world
            .spawn((
                Mesh3d(body_mesh.clone()),
                MeshMaterial3d(baseline.clone()),
                Transform::default(),
                GlobalTransform::default(),
            ))
            .id();
        let character = world.spawn_empty().id();
        let frame = AppearanceFrame {
            generation: 1,
            revision: 2,
            serial: 4,
            character,
            body,
            mesh: body_mesh,
            baseline,
            placement: Mat4::IDENTITY,
            bones: (0..53)
                .map(|i| nvwa_b1_adapter::BoneFrame {
                    name: format!("bone-{i}"),
                    parent: None,
                    rest: Mat4::IDENTITY.to_cols_array(),
                    posed: Mat4::IDENTITY.to_cols_array(),
                    inverse_bind: Mat4::IDENTITY.to_cols_array(),
                    local_rest: Mat4::IDENTITY.to_cols_array(),
                    local_posed: Mat4::IDENTITY.to_cols_array(),
                    skin: Mat4::IDENTITY.to_cols_array(),
                    canonical_rest: None,
                    canonical_posed: None,
                    frame_gauge: None,
                })
                .collect(),
        };
        let live = Live {
            name: "eyes",
            entity,
            mesh,
            material,
            texture,
            rest: vec![[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]],
            normals: vec![[0., 0., 1.]; 3],
            weights: vec![vec![(0, 1.)]; 3],
            obj,
            hair: false,
        };
        let state = AppearanceRuntime {
            key: Some(Key::new(&frame, (false, true, false))),
            live: vec![live],
            ..default()
        };
        (world, state, frame)
    }
    /// Synthetic controller input, not a claim that an authored clip moves the head.
    /// Read actual entity-bound CPU buffers after the production streaming seam.
    #[test]
    fn synthetic_controller_stream_updates_only_when_a_driving_bone_changes() {
        let (mut world, state, mut frame) = fixture();
        let live = &state.live[0];
        let actual_positions = |world: &World| {
            let handle = &world.get::<Mesh3d>(live.entity).unwrap().0;
            assert_eq!(handle, &live.mesh);
            match world
                .resource::<Assets<Mesh>>()
                .get(handle)
                .unwrap()
                .attribute(Mesh::ATTRIBUTE_POSITION)
                .unwrap()
            {
                VertexAttributeValues::Float32x3(v) => v.clone(),
                _ => panic!("actual POSITION type changed"),
            }
        };
        stream(&mut world, &state, &frame).unwrap();
        let neutral = actual_positions(&world);
        // Negative control: this bone is outside every stored positive row.
        assert!(live.weights.iter().all(|row| row.as_slice() == [(0, 1.)]));
        frame.bones[1].skin = Mat4::from_translation(Vec3::new(9., 8., 7.)).to_cols_array();
        stream(&mut world, &state, &frame).unwrap();
        assert_eq!(actual_positions(&world), neutral);
        // Positive control: move the actual driving bone input, retaining all entity/asset handles.
        let translation = Vec3::new(0.25, -0.5, 0.75);
        frame.bones[0].skin = Mat4::from_translation(translation).to_cols_array();
        stream(&mut world, &state, &frame).unwrap();
        let driven = actual_positions(&world);
        assert_ne!(driven, neutral);
        for (before, after) in neutral.iter().zip(&driven) {
            assert_eq!(
                Vec3::from_array(*after),
                Vec3::from_array(*before) + translation
            );
        }
        assert_eq!(
            world
                .get::<MeshMaterial3d<StandardMaterial>>(live.entity)
                .unwrap()
                .0,
            live.material
        );
        assert_eq!(
            world
                .get::<GlobalTransform>(live.entity)
                .unwrap()
                .to_matrix(),
            frame.placement
        );
        // Restoring the bone returns the same uploaded vertices, ruling out accumulated offsets.
        frame.bones[0].skin = Mat4::IDENTITY.to_cols_array();
        stream(&mut world, &state, &frame).unwrap();
        assert_eq!(actual_positions(&world), neutral);
    }

    #[test]
    fn actual_bound_material_pixels_and_missing_entity_reject() {
        let (mut world, mut state, frame) = fixture();
        stream(&mut world, &state, &frame).unwrap();
        let live = &state.live[0];
        observe_live(&world, live, true).unwrap();
        world
            .resource_mut::<Assets<StandardMaterial>>()
            .get_mut(&live.material)
            .unwrap()
            .alpha_mode = AlphaMode::Blend;
        assert!(
            stream(&mut world, &state, &frame)
                .unwrap_err()
                .contains("material policy")
        );
        world
            .resource_mut::<Assets<StandardMaterial>>()
            .get_mut(&live.material)
            .unwrap()
            .alpha_mode = AlphaMode::Mask(0.5);
        world
            .resource_mut::<Assets<Image>>()
            .get_mut(&live.texture.handle)
            .unwrap()
            .data
            .as_mut()
            .unwrap()[0] ^= 1;
        assert!(
            observe_live(&world, live, true)
                .unwrap_err()
                .contains("pixels changed")
        );
        world
            .resource_mut::<Assets<Image>>()
            .get_mut(&live.texture.handle)
            .unwrap()
            .data
            .as_mut()
            .unwrap()[0] ^= 1;
        let (entity, mesh, material, image) = (
            live.entity,
            live.mesh.clone(),
            live.material.clone(),
            live.texture.handle.clone(),
        );
        assert!(world.despawn(entity));
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            stream(&mut world, &state, &frame)
        }));
        assert!(result.expect("missing entity must be fallible").is_err());
        let mut status = AppearanceStatus {
            applied: Some(CharacterAppearance::b1_cc0(false, true, false)),
            ready: true,
            ..default()
        };
        invalidate(
            &mut world,
            &mut state,
            &mut status,
            "fixture binding failure".into(),
        );
        assert!(
            state.live.is_empty()
                && state.key.is_none()
                && !status.ready
                && status.applied.is_none()
        );
        assert!(world.resource::<Assets<Mesh>>().get(&mesh).is_none());
        assert!(
            world
                .resource::<Assets<StandardMaterial>>()
                .get(&material)
                .is_none()
        );
        assert!(world.resource::<Assets<Image>>().get(&image).is_none());
    }
    #[test]
    fn candidate_preflight_rejects_bad_fitted_cage_before_allocating() {
        let (world, _state, frame) = fixture();
        let before = (
            world.resource::<Assets<Mesh>>().len(),
            world.resource::<Assets<StandardMaterial>>().len(),
            world.resource::<Assets<Image>>().len(),
        );
        let fit = AppearanceFit {
            source_ids: vec![0],
            rest: vec![[0., 0., 0.]],
            uv: vec![[0., 0.]],
        };
        assert!(
            preflight(
                &frame,
                &fit,
                &CharacterAppearance::b1_cc0(false, true, true)
            )
            .unwrap_err()
            .contains("full19158 cage")
        );
        assert_eq!(
            before,
            (
                world.resource::<Assets<Mesh>>().len(),
                world.resource::<Assets<StandardMaterial>>().len(),
                world.resource::<Assets<Image>>().len()
            )
        );
        assert!(assets::decode(b"invalid image", 1024).is_err());
    }
    #[test]
    fn stale_generation_and_changed_mesh_reject_then_dispose() {
        let (mut world, mut state, mut frame) = fixture();
        frame.generation += 1;
        assert!(
            stream(&mut world, &state, &frame)
                .unwrap_err()
                .contains("stale generation")
        );
        frame.generation -= 1;
        let live = &state.live[0];
        let mesh = live.mesh.clone();
        world
            .resource_mut::<Assets<Mesh>>()
            .get_mut(&mesh)
            .unwrap()
            .remove_attribute(Mesh::ATTRIBUTE_UV_0);
        assert!(
            stream(&mut world, &state, &frame)
                .unwrap_err()
                .contains("UV/triangle")
        );
        dispose(&mut world, &mut state).unwrap();
        assert!(world.resource::<Assets<Mesh>>().get(&mesh).is_none());
    }
    #[test]
    fn baseline_restores_exact_uv_and_original_material_and_disposes_generated_handles() {
        let (mut world, mut state, frame) = fixture();
        let image = assets::decode(assets::SKIN_PNG, 2048).unwrap();
        let texture = texture(&mut world, image, 2048).unwrap();
        let image_handle = texture.handle.clone();
        let mut material = world
            .resource::<Assets<StandardMaterial>>()
            .get(&frame.baseline)
            .unwrap()
            .clone();
        material.base_color = Color::WHITE;
        material.base_color_texture = Some(texture.handle.clone());
        let material = world
            .resource_mut::<Assets<StandardMaterial>>()
            .add(material);
        let material_handle = material.clone();
        let original = vec![[0.25f32, 0.75]];
        let applied = vec![[0.5f32, 0.5]];
        world
            .resource_mut::<Assets<Mesh>>()
            .get_mut(&frame.mesh)
            .unwrap()
            .insert_attribute(Mesh::ATTRIBUTE_UV_0, applied.clone());
        world
            .entity_mut(frame.body)
            .insert(MeshMaterial3d(material.clone()));
        state.skin = Some(SkinBinding {
            entity: frame.body,
            mesh: frame.mesh.clone(),
            baseline: frame.baseline.clone(),
            material,
            texture,
            original_uv: Some(VertexAttributeValues::Float32x2(original.clone())),
            uv: applied,
        });
        observe_skin(&world, state.skin.as_ref().unwrap(), true).unwrap();
        dispose(&mut world, &mut state).unwrap();
        assert_eq!(
            world
                .get::<MeshMaterial3d<StandardMaterial>>(frame.body)
                .unwrap()
                .0,
            frame.baseline
        );
        assert_eq!(
            world
                .resource::<Assets<Mesh>>()
                .get(&frame.mesh)
                .unwrap()
                .attribute(Mesh::ATTRIBUTE_UV_0),
            Some(&VertexAttributeValues::Float32x2(original))
        );
        assert!(
            world
                .resource::<Assets<StandardMaterial>>()
                .get(&material_handle)
                .is_none()
        );
        assert!(
            world
                .resource::<Assets<Image>>()
                .get(&image_handle)
                .is_none()
        );
    }
}

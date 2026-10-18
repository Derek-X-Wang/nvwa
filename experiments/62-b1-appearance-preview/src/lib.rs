//! Temporary appearance overlay around the exact production Studio App.
mod binding;
use bevy::{
    asset::RenderAssetUsages,
    image::{CompressedImageFormats, ImageSampler, ImageType},
    mesh::VertexAttributeValues,
    prelude::*,
    render::render_resource::TextureFormat,
};
use nvwa_core::{Command, TimelineClip};
use nvwa_runtime::{EditorState, Playback, RuntimeStatus, b1_frame_snapshot};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::VecDeque;
const PNG: &[u8] = include_bytes!(
    "../assets/skins/young_caucasian_female2/young_lightskinned_female_diffuse2.png"
);
const PNG_SHA: &str = "8d1fb3ceedf142fad32a3504eca1feb4539aecca6de66acde1514b9a61fc7ba0";
pub fn hash<T: serde::Serialize>(value: &T) -> Result<String, String> {
    Ok(format!(
        "{:x}",
        Sha256::digest(serde_json::to_vec(value).map_err(|e| e.to_string())?)
    ))
}
struct Bound {
    entity: Entity,
    mesh: Handle<Mesh>,
    plain: Handle<StandardMaterial>,
    plain_value: StandardMaterial,
    skin: Handle<StandardMaterial>,
    original_uv: Option<VertexAttributeValues>,
    uv: Vec<[f32; 2]>,
    proof: Value,
}
#[derive(Resource, Default)]
pub struct Preview {
    queue: VecDeque<Value>,
    pending: Option<(Value, f64)>,
    desired: bool,
    bound: Option<Bound>,
    image: Option<Handle<Image>>,
    image_pixels_sha: String,
    restored: Value,
    captured_transport: Value,
    requested_identity: Value,
    marker: Value,
    report: Value,
    frame: Option<Value>,
    #[cfg(not(target_arch = "wasm32"))]
    native_command: String,
}
#[cfg(target_arch = "wasm32")]
thread_local! {static QUEUE:std::cell::RefCell<VecDeque<Value>>=const{std::cell::RefCell::new(VecDeque::new())};static REPORT:std::cell::RefCell<String>=const{std::cell::RefCell::new(String::new())};static FRAME:std::cell::RefCell<String>=const{std::cell::RefCell::new(String::new())};static REJECTION:std::cell::RefCell<Option<String>>=const{std::cell::RefCell::new(None)};}
pub struct AppearancePreviewPlugin;
impl Plugin for AppearancePreviewPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<Preview>().add_systems(Last, controller);
    }
}
pub fn studio_app() -> App {
    let mut app = nvwa_studio::build_app();
    app.add_plugins(AppearancePreviewPlugin);
    app
}
/// Same validated controller route for native tests; no alternate renderer.
pub fn enqueue_preview(world: &mut World, value: Value) -> Result<(), String> {
    let mut p = world.resource_mut::<Preview>();
    p.pending = None;
    p.queue.clear();
    p.frame = None;
    match validate(&value) {
        Ok(()) => {
            p.report = json!({"phase":"pending","request":value});
            p.queue.push_back(value);
            Ok(())
        }
        Err(error) => {
            p.report = json!({"phase":"error","error":error});
            Err(error)
        }
    }
}
pub fn preview_report(world: &World) -> Value {
    let p = world.resource::<Preview>();
    if p.report["phase"] == "captured"
        && (transport(world) != p.captured_transport
            || marker(world).as_ref().ok() != Some(&p.marker))
    {
        json!({"phase":"stale","reason":"current Work or transport differs from captured proof"})
    } else {
        p.report.clone()
    }
}
pub fn preview_frame(world: &World) -> Option<Value> {
    if preview_report(world)["phase"] == "captured" {
        world.resource::<Preview>().frame.clone()
    } else {
        None
    }
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen(start)]
pub fn start() {
    let _ = studio_app().run();
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_62_command(command: String) -> Result<(), wasm_bindgen::JsValue> {
    let parsed = serde_json::from_str::<Value>(&command)
        .map_err(|e| e.to_string())
        .and_then(|v| {
            validate(&v)?;
            Ok(v)
        });
    FRAME.with(|f| f.borrow_mut().clear());
    REJECTION.with(|r| *r.borrow_mut() = None);
    match parsed {
        Ok(v) => {
            let id = v["request_id"].clone();
            let result = QUEUE.with(|q| {
                let mut q = q.borrow_mut();
                if q.len() >= 8 {
                    return Err("preview command queue full".to_string());
                }
                q.clear();
                q.push_back(v);
                Ok(())
            });
            if let Err(e) = result {
                REJECTION.with(|r| *r.borrow_mut() = Some(e.clone()));
                REPORT.with(|r| *r.borrow_mut() = json!({"phase":"error","error":e}).to_string());
                return Err(wasm_bindgen::JsValue::from_str(&e));
            }
            REPORT
                .with(|r| *r.borrow_mut() = json!({"phase":"pending","request_id":id}).to_string());
            Ok(())
        }
        Err(e) => {
            REJECTION.with(|r| *r.borrow_mut() = Some(e.clone()));
            REPORT.with(|r| *r.borrow_mut() = json!({"phase":"error","error":e}).to_string());
            Err(wasm_bindgen::JsValue::from_str(&e))
        }
    }
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_62_report() -> String {
    REPORT.with(|r| r.borrow().clone())
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_62_frame() -> String {
    FRAME.with(|r| r.borrow().clone())
}
fn validate(v: &Value) -> Result<(), String> {
    let o = v.as_object().ok_or("command object required")?;
    if o.keys().any(|k| {
        ![
            "request_id",
            "action",
            "clip_id",
            "seconds",
            "torso_length",
            "jaw_drop",
        ]
        .contains(&k.as_str())
    }) {
        return Err("unknown preview command key".into());
    }
    let id = v["request_id"].as_str().ok_or("request_id required")?;
    if id.is_empty()
        || id.len() > 64
        || !id
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
    {
        return Err("invalid request_id".into());
    }
    if !matches!(
        v["action"].as_str(),
        Some("plain" | "skin" | "report" | "sample" | "play" | "pause")
    ) {
        return Err("invalid action".into());
    }
    if v["action"] == "sample" {
        if !matches!(
            v["clip_id"].as_str(),
            Some("b1_arm_rehearsal_v1" | "b1_knee_flex_v1")
        ) {
            return Err("invalid authored clip".into());
        }
        for k in ["seconds", "torso_length", "jaw_drop"] {
            let x = v[k].as_f64().ok_or("finite number required")?;
            let range = if k == "seconds" {
                0.0..=4.0
            } else {
                -1.0..=1.0
            };
            if !x.is_finite() || !range.contains(&x) {
                return Err(format!("{k} out of range"));
            }
        }
    }
    Ok(())
}
fn command(world: &mut World, p: &mut Preview, v: &Value) -> Result<(), String> {
    validate(v)?;
    match v["action"].as_str().unwrap() {
        "plain" => p.desired = false,
        "skin" => p.desired = true,
        "play" => world.resource_mut::<Playback>().playing = true,
        "pause" => world.resource_mut::<Playback>().playing = false,
        "sample" => {
            let doc = world
                .resource::<EditorState>()
                .document()
                .ok_or("open actual B1 motion Work first")?
                .clone();
            if !doc.profile.backend.is_b1_motion() {
                return Err("active Work is not same B1 motion profile".into());
            }
            let values = [
                (
                    "torso_length".into(),
                    v["torso_length"].as_f64().unwrap() as f32,
                ),
                ("jaw_drop".into(), v["jaw_drop"].as_f64().unwrap() as f32),
            ]
            .into_iter()
            .collect();
            if doc.character.parameters != values {
                world
                    .resource_mut::<EditorState>()
                    .apply(Command::SetParameters {
                        character_id: doc.character.id,
                        values,
                    })?;
            }
            let clips = vec![TimelineClip {
                id: "probe-entry".into(),
                clip_id: v["clip_id"].as_str().unwrap().into(),
                start_seconds: 0.,
                duration_seconds: 4.,
                speed: 1.,
                looping: false,
            }];
            if world.resource::<EditorState>().document().unwrap().timeline != clips {
                world
                    .resource_mut::<EditorState>()
                    .apply(Command::SetTimeline { clips })?;
            }
            let mut t = world.resource_mut::<Playback>();
            t.playing = false;
            t.seek_request = Some(v["seconds"].as_f64().unwrap() as f32);
        }
        _ => {}
    }
    Ok(())
}
fn marker(world: &World) -> Result<Value, String> {
    let e = world.resource::<EditorState>();
    if e.pending_open.is_some() {
        return Err("B1 open verification is pending; previous appearance proof invalid".into());
    }
    if let Some(error) = &e.open_error {
        return Err(format!("B1 open failed: {error}"));
    }
    let status = world.resource::<RuntimeStatus>();
    if !status.ready || status.error.is_some() {
        return Err(format!(
            "B1 runtime is not currently ready: {} {:?}",
            status.phase, status.error
        ));
    }
    let d = e.visible_document().ok_or("no actual Work open")?;
    if !d.profile.backend.is_b1_motion() {
        return Err("same B1 motion v2 Work required".into());
    }
    let mut roots = Vec::new();
    let mut meshes = Vec::new();
    for entity in world.iter_entities() {
        if let Some(shape) = entity.get::<humentity::prelude::CharacterShape>() {
            roots.push((format!("{:?}", entity.id()), format!("{:?}", shape.0.id())));
        }
        if let Some(mesh) = entity.get::<Mesh3d>() {
            meshes.push((
                format!("{:?}", entity.id()),
                format!("{:?}", mesh.0.id()),
                world.resource::<Assets<Mesh>>().get(&mesh.0).is_some(),
            ));
        }
    }
    roots.sort();
    meshes.sort();
    if roots.is_empty() {
        return Err("actual public character shape binding absent".into());
    }
    Ok(
        json!({"binding_identity_basis":"public current Work hash+RuntimeStatus+actual Entity/asset-handle generations; not private EditorState generation","document_sha256":hash(d)?,"parameters":d.character.parameters,"revision":d.revision,"character_shape_bindings":roots,"display_mesh_bindings":meshes,"runtime_ready":status.ready,"runtime_error":status.error}),
    )
}
fn transport(world: &World) -> Value {
    let t = world.resource::<Playback>();
    json!({"clip_id":t.clip_id,"playing":t.playing,"position_seconds":t.position_seconds,"seek_request":t.seek_request,"timeline_id":t.active_timeline_id,"completed":t.completed,"error":t.error})
}
fn uv_value(values: Option<&VertexAttributeValues>) -> Result<Value, String> {
    match values {
        None => Ok(Value::Null),
        Some(VertexAttributeValues::Float32x2(v)) => Ok(json!(v)),
        _ => Err("unexpected UV_0 type".into()),
    }
}
fn restore(world: &mut World, p: &mut Preview) -> Result<(), String> {
    if let Some(b) = &p.bound {
        if let Ok(e) = world.get_entity(b.entity) {
            if e.get::<Mesh3d>().is_none_or(|mesh| mesh.0 != b.mesh) {
                return Err("preview entity mesh changed outside overlay".into());
            }
            let m = e
                .get::<MeshMaterial3d<StandardMaterial>>()
                .ok_or("preview material component disappeared")?;
            if m.0 != b.skin {
                return Err("preview material binding changed outside overlay".into());
            }
        }
    }
    if let Some(b) = p.bound.take() {
        let mut mesh_present = false;
        let mut uv_verified = false;
        let expected_uv = uv_value(b.original_uv.as_ref())?;
        if let Some(mut mesh) = world.resource_mut::<Assets<Mesh>>().get_mut(&b.mesh) {
            mesh_present = true;
            match b.original_uv.clone() {
                Some(uv) => {
                    mesh.insert_attribute(Mesh::ATTRIBUTE_UV_0, uv);
                }
                None => {
                    mesh.remove_attribute(Mesh::ATTRIBUTE_UV_0);
                }
            }
            uv_verified = mesh.attribute(Mesh::ATTRIBUTE_UV_0) == b.original_uv.as_ref();
            if !uv_verified {
                return Err("original UV restoration failed".into());
            }
        }
        let entity_present = if let Ok(mut e) = world.get_entity_mut(b.entity) {
            e.insert(MeshMaterial3d(b.plain.clone()));
            true
        } else {
            false
        };
        let material_verified = world
            .get::<MeshMaterial3d<StandardMaterial>>(b.entity)
            .is_some_and(|m| m.0 == b.plain);
        p.restored = json!({"state":if mesh_present&&entity_present&&material_verified&&uv_verified{"verified-original-binding-restored"}else{"old-binding-disposed-not-current-restoration"},"old_mesh":format!("{:?}",b.mesh.id()),"old_entity":format!("{:?}",b.entity),"expected_material":format!("{:?}",b.plain.id()),"mesh_present":mesh_present,"entity_present":entity_present,"material_verified":material_verified,"expected_uv_sha256":hash(&expected_uv)?,"uv_exact_restore":uv_verified});
        world
            .resource_mut::<Assets<StandardMaterial>>()
            .remove(b.skin.id());
    }
    Ok(())
}
fn image(world: &mut World, p: &mut Preview) -> Result<Handle<Image>, String> {
    if let Some(h) = &p.image {
        if world.resource::<Assets<Image>>().get(h).is_none() {
            return Err("preview image asset disappeared".into());
        }
        return Ok(h.clone());
    }
    if format!("{:x}", Sha256::digest(PNG)) != PNG_SHA {
        return Err("embedded approved diffuse SHA mismatch".into());
    }
    if PNG.len() != 3_724_137
        || PNG.len() < 33
        || &PNG[..8] != b"\x89PNG\r\n\x1a\n"
        || &PNG[12..16] != b"IHDR"
        || u32::from_be_bytes(PNG[16..20].try_into().unwrap()) != 2048
        || u32::from_be_bytes(PNG[20..24].try_into().unwrap()) != 2048
        || PNG[24] != 8
        || PNG[25] != 2
        || PNG[28] != 0
    {
        return Err("fixed PNG must be2048RGB8 noninterlaced".into());
    }
    let im = Image::from_buffer(
        PNG,
        ImageType::Extension("png"),
        CompressedImageFormats::NONE,
        true,
        ImageSampler::default(),
        RenderAssetUsages::default(),
    )
    .map_err(|e| e.to_string())?;
    if im.width() != 2048
        || im.height() != 2048
        || im.texture_descriptor.format != TextureFormat::Rgba8UnormSrgb
        || im.data.as_ref().is_none_or(|d| d.len() != 2048 * 2048 * 4)
    {
        return Err("decoded sRGB RGBA image bounds mismatch".into());
    }
    p.image_pixels_sha = format!(
        "{:x}",
        Sha256::digest(im.data.as_ref().ok_or("decoded pixels absent")?)
    );
    let h = world.resource_mut::<Assets<Image>>().add(im);
    p.image = Some(h.clone());
    Ok(h)
}
fn capture(world: &mut World, p: &mut Preview, request: &Value) -> Result<(Value, Value), String> {
    let _current_binding_identity = marker(world)?;
    let before = b1_frame_snapshot(world)?;
    if request["action"] == "sample" {
        for k in ["torso_length", "jaw_drop"] {
            if (before["parameters"][k].as_f64().ok_or("parameter absent")?
                - request[k].as_f64().unwrap())
            .abs()
                > 1e-6
            {
                return Err("requested shape not yet published".into());
            }
        }
        if before["sample"]["clip_id"] != request["clip_id"]
            || before["sample"]["timeline_id"] != "probe-entry"
            || (before["sample"]["source_seconds"]
                .as_f64()
                .ok_or("source time absent")?
                - request["seconds"].as_f64().unwrap())
            .abs()
                > 1e-6
        {
            return Err("requested sample not yet published".into());
        }
    }
    if !p.desired {
        restore(world, p)?;
    } else if p.bound.is_none() {
        let b = binding::resolve(world, &before)?;
        let h = image(world, p)?;
        let original = world
            .resource::<Assets<StandardMaterial>>()
            .get(&b.material)
            .ok_or("plain material missing")?
            .clone();
        let mut skin = original.clone();
        skin.base_color = Color::WHITE;
        skin.base_color_texture = Some(h);
        let material = world.resource_mut::<Assets<StandardMaterial>>().add(skin);
        let original_uv = world
            .resource::<Assets<Mesh>>()
            .get(&b.mesh)
            .ok_or("display mesh absent")?
            .attribute(Mesh::ATTRIBUTE_UV_0)
            .cloned();
        let _ = uv_value(original_uv.as_ref())?;
        world
            .resource_mut::<Assets<Mesh>>()
            .get_mut(&b.mesh)
            .ok_or("display mesh absent")?
            .insert_attribute(Mesh::ATTRIBUTE_UV_0, b.uv.clone());
        world
            .entity_mut(b.entity)
            .insert(MeshMaterial3d(material.clone()));
        p.bound = Some(Bound {
            entity: b.entity,
            mesh: b.mesh,
            plain: b.material,
            plain_value: original,
            skin: material,
            original_uv,
            uv: b.uv,
            proof: b.proof,
        });
    }
    let after = b1_frame_snapshot(world)?;
    if before != after {
        return Err("appearance bind changed fresh production geometry/bones/sample".into());
    }
    let geometry = hash(&before)?;
    let appearance = manifest(world, p, &after)?;
    let mut compact = appearance.clone();
    if let Some(o) = compact.as_object_mut() {
        o.remove("actual_uv_0");
        if let Some(proof) = o.get_mut("source_uv_proof").and_then(Value::as_object_mut) {
            proof.remove("uv_0");
        }
    }
    let report = json!({"phase":"captured","request":request,"label":"Experimental appearance · not saved","desired":if p.desired{"skin"}else{"plain"},"applied":if p.bound.is_some(){"skin"}else{"plain"},"identity":marker(world)?,"requested_identity":p.requested_identity,"requested_published_generation":before["generation"],"applied_generation":after["generation"],"sample":after["sample"],"parameters":after["parameters"],"geometry_before_sha256":geometry,"geometry_after_sha256":geometry,"geometry_equal":true,"appearance":compact});
    let frame = json!({"request":request,"snapshot":after,"geometry_before_sha256":geometry,"geometry_after_sha256":geometry,"geometry_equal":true,"appearance":appearance});
    Ok((report, frame))
}
fn manifest(world: &World, p: &Preview, snapshot: &Value) -> Result<Value, String> {
    let body = snapshot["parts"]
        .as_array()
        .ok_or("parts absent")?
        .iter()
        .find(|v| v["name"] == "body")
        .ok_or("body absent")?;
    if let Some(b) = &p.bound {
        let meshes = world.resource::<Assets<Mesh>>();
        let mesh = meshes.get(&b.mesh).ok_or("bound mesh lost")?;
        let uv = match mesh.attribute(Mesh::ATTRIBUTE_UV_0) {
            Some(VertexAttributeValues::Float32x2(v)) => v,
            _ => return Err("actual bound UV absent".into()),
        };
        if uv != &b.uv {
            return Err("actual bound UV differs from fitted source".into());
        }
        let material = world
            .get::<MeshMaterial3d<StandardMaterial>>(b.entity)
            .ok_or("actual material component lost")?;
        if material.0 != b.skin {
            return Err("actual preview material handle mismatch".into());
        }
        let mats = world.resource::<Assets<StandardMaterial>>();
        let actual = mats.get(&material.0).ok_or("actual material asset lost")?;
        let handle = actual
            .base_color_texture
            .as_ref()
            .ok_or("actual texture not attached")?;
        if Some(handle) != p.image.as_ref() || actual.base_color != Color::WHITE {
            return Err("actual texture/tint mismatch".into());
        }
        let im = world
            .resource::<Assets<Image>>()
            .get(handle)
            .ok_or("actual image absent")?;
        if im.width() != 2048
            || im.height() != 2048
            || im.texture_descriptor.format != TextureFormat::Rgba8UnormSrgb
        {
            return Err("actual decoded image changed".into());
        }
        let pixels = im.data.as_ref().ok_or("actual image pixels absent")?;
        let pixels_sha = format!("{:x}", Sha256::digest(pixels));
        if pixels_sha != p.image_pixels_sha {
            return Err("actual image pixel data differs from authenticated decode".into());
        }
        let plain = mats.get(&b.plain).ok_or("original material lost")?;
        if format!("{plain:?}") != format!("{:?}", b.plain_value) {
            return Err("original plain material changed".into());
        }
        let mut contrast = actual.clone();
        contrast.base_color = b.plain_value.base_color;
        contrast.base_color_texture = b.plain_value.base_color_texture.clone();
        if format!("{contrast:?}") != format!("{:?}", b.plain_value) {
            return Err("non-color material properties changed".into());
        }
        Ok(
            json!({"state":"skin","body_mesh":body["mesh_handle"],"display_entity":body["display_entity"],"material_handle":format!("{:?}",material.0.id()),"original_material_handle":format!("{:?}",b.plain.id()),"white_tint":true,"roughness":actual.perceptual_roughness,"image_handle":format!("{:?}",handle.id()),"image":{"source_sha256":PNG_SHA,"source_bytes":PNG.len(),"width":im.width(),"height":im.height(),"format":format!("{:?}",im.texture_descriptor.format),"actual_rgba_sha256":format!("{:x}",Sha256::digest(pixels)),"decoded_bytes":pixels.len()},"actual_uv_0":uv,"actual_uv_count":uv.len(),"other_material_properties_preserved":true,"actual_uv_sha256":hash(uv)?,"source_uv_proof":b.proof,"not_saved":true,"pixel_quality":"NOT-RUN; actual rendering requires inspection"}),
        )
    } else {
        let label = body["display_entity"]
            .as_str()
            .ok_or("display identity absent")?;
        let entities: Vec<_> = world
            .iter_entities()
            .filter(|e| format!("{:?}", e.id()) == label)
            .collect();
        if entities.len() != 1 {
            return Err("plain display binding ambiguous".into());
        }
        let e = &entities[0];
        let mesh = e.get::<Mesh3d>().ok_or("plain mesh missing")?;
        let material = e
            .get::<MeshMaterial3d<StandardMaterial>>()
            .ok_or("plain material missing")?;
        if format!("{:?}", mesh.0.id())
            != body["mesh_handle"]
                .as_str()
                .ok_or("mesh identity missing")?
        {
            return Err("plain mesh identity mismatch".into());
        }
        let asset = world
            .resource::<Assets<Mesh>>()
            .get(&mesh.0)
            .ok_or("plain mesh asset missing")?;
        let actual = world
            .resource::<Assets<StandardMaterial>>()
            .get(&material.0)
            .ok_or("plain material asset missing")?;
        let actual_uv = match asset.attribute(Mesh::ATTRIBUTE_UV_0) {
            None => Value::Null,
            Some(VertexAttributeValues::Float32x2(v)) => json!(v),
            _ => return Err("plain UV type invalid".into()),
        };
        let same_restored_mesh = p.restored["old_mesh"] == body["mesh_handle"];
        if same_restored_mesh
            && (p.restored["expected_material"] != format!("{:?}", material.0.id())
                || p.restored["expected_uv_sha256"] != hash(&actual_uv)?)
        {
            return Err(
                "actual current plain restoration no longer matches saved originals".into(),
            );
        }
        Ok(
            json!({"state":"plain","plain_origin":if same_restored_mesh{"verified-restored-current-binding"}else{"initial-or-new-current-plain-binding"},"body_mesh":body["mesh_handle"],"display_entity":body["display_entity"],"material_handle":format!("{:?}",material.0.id()),"actual_uv_present":!actual_uv.is_null(),"actual_uv_sha256":hash(&actual_uv)?,"base_color":format!("{:?}",actual.base_color),"texture_handle":actual.base_color_texture.as_ref().map(|h|format!("{:?}",h.id())),"roughness":actual.perceptual_roughness,"not_saved":true,"restoration":p.restored}),
        )
    }
}
fn controller(world: &mut World) {
    let mut p = world.remove_resource::<Preview>().unwrap();
    #[cfg(target_arch = "wasm32")]
    {
        let incoming = QUEUE.with(|q| q.borrow_mut().drain(..).collect::<Vec<_>>());
        if !incoming.is_empty() {
            p.pending = None;
            p.queue.clear();
            p.frame = None;
            p.queue.extend(incoming);
        }
        if let Some(error) = REJECTION.with(|r| r.borrow_mut().take()) {
            p.pending = None;
            p.queue.clear();
            p.frame = None;
            p.report = json!({"phase":"error","error":error});
        }
    }
    #[cfg(not(target_arch = "wasm32"))]
    if let Ok(path) = std::env::var("B1_62_COMMAND_FILE") {
        if let Ok(s) = std::fs::read_to_string(path) {
            if s != p.native_command {
                p.native_command = s.clone();
                p.pending = None;
                p.queue.clear();
                p.frame = None;
                match serde_json::from_str(&s) {
                    Ok(v) => p.queue.push_back(v),
                    Err(e) => {
                        p.report = json!({"phase":"error","error":e.to_string()});
                    }
                }
            }
        }
    }
    let now = world.resource::<Time<Real>>().elapsed_secs_f64();
    if p.report["phase"] == "captured" && transport(world) != p.captured_transport {
        p.frame = None;
        p.report = json!({"phase":"stale","reason":"actual transport changed since captured proof; request a fresh report","desired":if p.desired{"skin"}else{"plain"}});
    }
    let current = marker(world);
    if current.as_ref().ok() != Some(&p.marker) {
        p.frame = None;
        let restored = restore(world, &mut p);
        p.marker = current.clone().unwrap_or(Value::Null);
        if let Err(e) = restored {
            p.pending = None;
            p.queue.clear();
            p.report = json!({"phase":"error","error":e});
        } else if p.pending.is_none() && p.queue.is_empty() && p.report["phase"] != "error" {
            p.pending = Some((
                json!({"request_id":"automatic-rebind","action":"report"}),
                now,
            ));
            p.report = json!({"phase":"pending","reason":"current Work/generation changed; previous proof invalidated"});
        }
    }
    if p.pending.is_none() {
        if let Some(v) = p.queue.pop_front() {
            p.frame = None;
            match command(world, &mut p, &v) {
                Ok(()) => {
                    p.requested_identity = marker(world).unwrap_or(Value::Null);
                    p.pending = Some((v.clone(), now));
                    p.report = json!({"phase":"pending","request":v});
                }
                Err(e) => {
                    p.report = json!({"phase":"error","request":v,"error":e});
                }
            }
        }
    } else if let Some((v, started)) = p.pending.take() {
        match capture(world, &mut p, &v) {
            Ok((report, frame)) => {
                p.captured_transport = transport(world);
                p.report = report;
                p.frame = Some(frame);
            }
            Err(e) => {
                p.frame = None;
                p.report = json!({"phase":"pending","request":v,"error":e});
                if now - started < 45. {
                    p.pending = Some((v, started));
                } else {
                    let restoration = restore(world, &mut p).err();
                    p.report =
                        json!({"phase":"error","request":v,"error":e,"restore_error":restoration});
                }
            }
        }
    }
    #[cfg(target_arch = "wasm32")]
    {
        REPORT.with(|r| *r.borrow_mut() = p.report.to_string());
        FRAME
            .with(|r| *r.borrow_mut() = p.frame.as_ref().map(Value::to_string).unwrap_or_default());
    }
    world.insert_resource(p);
}

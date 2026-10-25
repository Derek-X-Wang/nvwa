//! Isolated actual-production hair diagnostic. Geometry and appearance controller unchanged.
mod candidate;
mod diagnostic;
mod geometry;
use bevy::prelude::*;
use nvwa_core::{Command, SceneDocument, appearance_sha256};
use nvwa_runtime::{
    EditorState, Playback, RuntimeStatus, appearance_snapshot, appearance_status, b1_frame_snapshot,
};
use serde::Deserialize;
use serde_json::{Value, json};
use std::collections::{BTreeMap, VecDeque};
const MAX_REQUEST: usize = 16 * 1024 * 1024;
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    request_id: String,
    action: String,
    command: Option<Command>,
    work_json: Option<String>,
    seek_seconds: Option<f32>,
    playing: Option<bool>,
    mode: Option<diagnostic::Mode>,
    palette: Option<diagnostic::Palette>,
    variant: Option<candidate::Variant>,
}
fn parse(raw: &str) -> Result<Request, String> {
    if raw.len() > MAX_REQUEST {
        return Err("acceptance request exceeds16MiB".into());
    }
    let req: Request = serde_json::from_str(raw).map_err(|e| e.to_string())?;
    // Typed decoding above rejects duplicate fields, including inside Command.
    // Presence below also rejects explicit null and action-irrelevant optional keys.
    let wire: Value = serde_json::from_str(raw).map_err(|e| e.to_string())?;
    let fields = wire.as_object().ok_or("request object required")?;
    for (key, value) in fields {
        if key == "request_id" || key == "action" {
            continue;
        }
        let allowed = match req.action.as_str() {
            "command" => key == "command",
            "open" => key == "work_json",
            "playback" => key == "seek_seconds" || key == "playing",
            "witness" => key == "seek_seconds",
            "diagnostic" => key == "mode" || key == "palette" || key == "variant",
            _ => false,
        };
        if !allowed || value.is_null() {
            return Err(format!(
                "field {key} is null or does not belong to action {}",
                req.action
            ));
        }
    }

    if req.request_id.is_empty()
        || req.request_id.len() > 64
        || !req
            .request_id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
    {
        return Err("request_id needs1..64 ASCII letters/digits/underscore/hyphen".into());
    }
    let command = req.command.is_some();
    let open = req.work_json.is_some();
    let playback = req.seek_seconds.is_some() || req.playing.is_some();
    let diagnostic = req.mode.is_some() || req.palette.is_some() || req.variant.is_some();
    let valid = match req.action.as_str() {
        "command" => command && !open && !playback,
        "open" => open && !command && !playback,
        "playback" => playback && !command && !open,
        "capture" => !command && !open && !playback && !diagnostic,
        "witness" => {
            req.seek_seconds.is_some_and(|t| t == 0. || t == 2.)
                && req.playing.is_none()
                && !command
                && !open
                && !diagnostic
        }
        "diagnostic" => {
            req.mode.is_some()
                && req.palette.is_some()
                && req.variant.is_some()
                && !command
                && !open
                && !playback
        }
        _ => false,
    };
    if !valid {
        return Err("action requires exactly its documented fields".into());
    }
    if req.seek_seconds.is_some_and(|t| !t.is_finite() || t < 0.) {
        return Err("seek_seconds must be finite/nonnegative".into());
    }
    Ok(req)
}
struct Pending {
    id: String,
    action: String,
    work_sha: String,
    started: f64,
    seek: Option<f32>,
    playing: Option<bool>,
    open_previous_generation: Option<u64>,
    expects_new_b1_generation: bool,
    stable_identity: Option<Value>,
    stable_epoch: Option<u64>,
    stable_updates: u32,
}
#[derive(Resource, Default)]
struct Bridge {
    incoming: VecDeque<String>,
    pending: Option<Pending>,
    seen: BTreeMap<String, String>,
    report: Value,
    captured_identity: Value,
    work: String,
    frame: Option<Value>,
    diagnostic: diagnostic::State,
    candidate: candidate::State,
    stable_key: String,
    stable_updates: u32,
    #[cfg(not(target_arch = "wasm32"))]
    native_input: String,
    #[cfg(not(target_arch = "wasm32"))]
    native_output: String,
    frame_export_key: String,
    update_epoch: u64,
}
#[cfg(any(target_arch = "wasm32", test))]
thread_local! {static INCOMING:std::cell::RefCell<VecDeque<String>>=const{std::cell::RefCell::new(VecDeque::new())};static REPORT:std::cell::RefCell<String>=const{std::cell::RefCell::new(String::new())};static FRAME:std::cell::RefCell<String>=const{std::cell::RefCell::new(String::new())};static WORK:std::cell::RefCell<String>=const{std::cell::RefCell::new(String::new())};}
pub fn studio_app() -> App {
    let mut app = nvwa_studio::build_app();
    install_bridge(&mut app);
    app
}
fn install_bridge(app: &mut App) {
    app.insert_resource(Bridge {
        frame_export_key: "startup".into(),
        ..default()
    })
    .add_systems(PreUpdate, prepare_diagnostic)
    .add_systems(
        PostUpdate,
        publish_before_visibility
            .after(nvwa_runtime::RuntimeSystems::Appearance)
            .before(bevy::camera::visibility::VisibilitySystems::CalculateBounds)
            .before(bevy::camera::visibility::VisibilitySystems::CheckVisibility),
    )
    .add_systems(Last, controller);
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen(start)]
pub fn start() {
    let _ = studio_app().run();
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_76_command(raw: String) -> Result<(), wasm_bindgen::JsValue> {
    queue_web_command(raw).map_err(|error| wasm_bindgen::JsValue::from_str(&error))
}
/// Shared actual Web ingress seam. Pending REPORT prevents an old FRAME from
/// certifying a new request; retaining FRAME preserves identical replay export.
#[cfg(any(target_arch = "wasm32", test))]
fn queue_web_command(raw: String) -> Result<(), String> {
    let parsed = parse(&raw);
    INCOMING.with(|q| {
        let mut q = q.borrow_mut();
        q.clear();
        q.push_back(raw);
    });
    REPORT.with(|r| *r.borrow_mut() = json!({"phase":"pending","current":false}).to_string());
    parsed.map(|_| ())
}
#[cfg(any(target_arch = "wasm32", test))]
fn publish_web_state(bridge: &Bridge, frame_changed: bool) {
    REPORT.with(|r| *r.borrow_mut() = bridge.report.to_string());
    WORK.with(|w| *w.borrow_mut() = bridge.work.clone());
    if frame_changed {
        FRAME.with(|f| {
            *f.borrow_mut() = bridge
                .frame
                .as_ref()
                .map(Value::to_string)
                .unwrap_or_default()
        });
    }
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_76_report() -> String {
    REPORT.with(|r| r.borrow().clone())
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_76_work() -> String {
    WORK.with(|w| w.borrow().clone())
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_76_frame() -> String {
    FRAME.with(|f| f.borrow().clone())
}
fn current_work(world: &World) -> Result<String, String> {
    world
        .resource::<EditorState>()
        .document()
        .ok_or("no current Work")?
        .to_json()
        .map_err(|e| e.to_string())
}
fn identity(world: &World) -> Value {
    let appearance = appearance_status(world);
    let playback = world.resource::<Playback>();
    let editor = world.resource::<EditorState>();
    let runtime = world.resource::<RuntimeStatus>();
    let document_hash =
        |doc: &SceneDocument| doc.to_json().ok().map(|s| appearance_sha256(s.as_bytes()));
    json!({"work_sha256":current_work(world).ok().map(|s|appearance_sha256(s.as_bytes())),"generation":appearance.generation,"revision":appearance.revision,"body_entity":appearance.body_entity,"appearance_ready":appearance.ready,"appearance_pending":appearance.pending,"appearance_error":appearance.error,"preview_sha256":editor.preview.as_ref().and_then(document_hash),"pending_open_sha256":editor.pending_open.as_ref().and_then(document_hash),"open_error":editor.open_error,"runtime_ready":runtime.ready,"runtime_error":runtime.error,"runtime_appearance_error":runtime.appearance_error,"stage_error":runtime.stage_error,"clip_id":playback.clip_id,"timeline_id":playback.active_timeline_id,"seconds":playback.position_seconds,"playing":playback.playing,"completed":playback.completed,"seek_request":playback.seek_request,"playback_error":playback.error,"camera":camera_report(world),"environment":environment_report(world),"bound_image_policies":candidate::bound_image_policies(world)})
}
fn invalidate_stale(world: &World, bridge: &mut Bridge) {
    if bridge.report["phase"] == "ready" && identity(world) != bridge.captured_identity {
        bridge.frame = None;
        bridge.report["phase"] = json!("stale");
        bridge.report["current"] = json!(false);
        bridge.report["current_identity"] = identity(world);
    }
}

fn fail(bridge: &mut Bridge, id: Value, error: String) {
    bridge.pending = None;
    bridge.frame = None;
    bridge.report = json!({"phase":"error","request_id":id,"acknowledged":true,"request_succeeded":false,"current":false,"error":error});
    bridge.captured_identity = Value::Null;
}
fn dispatch(world: &mut World, bridge: &mut Bridge, raw: String) {
    let request = match parse(&raw) {
        Ok(r) => r,
        Err(error) => {
            let id = serde_json::from_str::<Value>(&raw)
                .ok()
                .map(|v| v["request_id"].clone())
                .unwrap_or(Value::Null);
            fail(bridge, id, error);
            return;
        }
    };
    let digest = appearance_sha256(raw.as_bytes());
    if let Some(previous) = bridge.seen.get(&request.request_id) {
        if previous == &digest && bridge.report["request_id"] == request.request_id {
            return;
        }
        fail(
            bridge,
            json!(request.request_id),
            "request_id already used; identical replay only retains its current acknowledgement"
                .into(),
        );
        return;
    }
    if bridge.pending.is_some() {
        fail(
            bridge,
            json!(request.request_id),
            "previous request still pending; wait for terminal acknowledgement".into(),
        );
        return;
    }
    if bridge.seen.len() >= 128 {
        fail(
            bridge,
            json!(request.request_id),
            "acceptance session request limit128 reached".into(),
        );
        return;
    }
    bridge.seen.insert(request.request_id.clone(), digest);
    let id = request.request_id.clone();
    let action = request.action.clone();
    let seek = request.seek_seconds;
    let playing = if request.action == "witness" {
        Some(false)
    } else {
        request.playing
    };
    let open_previous_generation = appearance_status(world).generation;
    let mut expects_new_b1_generation = false;
    if matches!(request.action.as_str(), "open" | "command") {
        bridge.candidate.clear(world);
    }
    let result = (|| {
        match request.action.as_str() {
            "command" => world
                .resource_mut::<EditorState>()
                .apply(request.command.ok_or("shared Command missing")?)?,
            "open" => {
                let doc = SceneDocument::from_json(
                    request.work_json.as_deref().ok_or("work_json missing")?,
                )
                .map_err(|e| e.to_string())?;
                expects_new_b1_generation = doc.profile.backend.is_b1();
                world.resource_mut::<EditorState>().request_open(doc)?;
            }
            "playback" | "witness" => {
                if request.playing == Some(true) {
                    if bridge.diagnostic.mode != diagnostic::Mode::Combined
                        || bridge.diagnostic.palette != diagnostic::Palette::Textured
                        || bridge.frame.is_none()
                        || bridge.report["current"] != true
                    {
                        return Err(
                            "motion observation requires a current combined/textured capture first"
                                .into(),
                        );
                    }
                    bridge.candidate.motion.clear();
                }
                if request.action == "witness" {
                    bridge
                        .diagnostic
                        .configure(diagnostic::Mode::Combined, diagnostic::Palette::Textured);
                }
                let doc = world
                    .resource::<EditorState>()
                    .document()
                    .ok_or("no current Work")?;
                if !doc.profile.backend.is_b1_motion() {
                    return Err("playback acceptance requires production B1 motion backend".into());
                }
                if seek.is_some_and(|t| t > doc.timeline_duration_seconds()) {
                    return Err("seek exceeds current Work duration".into());
                }
                let mut playback = world.resource_mut::<Playback>();
                if let Some(seek) = seek {
                    playback.seek_request = Some(seek);
                }
                if let Some(playing) = playing {
                    playback.playing = playing;
                }
            }
            "diagnostic" => {
                bridge.candidate.variant = request.variant.ok_or("variant absent")?;
                bridge.stable_key.clear();
                bridge.stable_updates = 0;
                bridge.diagnostic.configure(
                    request.mode.ok_or("mode absent")?,
                    request.palette.ok_or("palette absent")?,
                );
            }
            "capture" => {}
            _ => return Err("unsupported action".into()),
        }
        Ok::<_, String>(())
    })();
    if let Err(error) = result {
        fail(bridge, json!(id), error);
        return;
    }
    let target = world
        .resource::<EditorState>()
        .pending_open
        .as_ref()
        .and_then(|d| d.to_json().ok())
        .or_else(|| current_work(world).ok());
    let Some(target) = target else {
        fail(bridge, json!(id), "no requested Work after action".into());
        return;
    };
    bridge.pending = Some(Pending {
        id: id.clone(),
        action,
        work_sha: appearance_sha256(target.as_bytes()),
        started: world.resource::<Time<Real>>().elapsed_secs_f64(),
        seek,
        playing,
        open_previous_generation,
        expects_new_b1_generation,
        stable_identity: None,
        stable_epoch: None,
        stable_updates: 0,
    });
    bridge.frame = None;
    bridge.captured_identity = Value::Null;
    bridge.report = json!({"phase":"pending","request_id":id,"acknowledged":false,"request_succeeded":null,"current":false});
}
fn hash_json(v: &Value) -> String {
    appearance_sha256(v.to_string().as_bytes())
}
fn base_capture(world: &World) -> Result<Value, String> {
    let doc = world
        .resource::<EditorState>()
        .document()
        .ok_or("no current Work")?;
    if !doc.profile.backend.is_b1_motion() {
        return Ok(
            json!({"scope":"full frame snapshot only supports admitted B1 motion; appearance snapshot separately validates static B1","status":"NOT-EXPORTED"}),
        );
    }
    let frame = b1_frame_snapshot(world)?;
    let parts=frame["parts"].as_array().ok_or("base parts missing")?.iter().map(|p|json!({"name":p["name"],"display_entity":p["display_entity"],"mesh_handle":p["mesh_handle"],"vertices":p["positions"].as_array().map(Vec::len),"indices":p["indices"].as_array().map(Vec::len),"positions_sha256":hash_json(&p["positions"]),"normals_sha256":hash_json(&p["normals"]),"rest_positions_sha256":hash_json(&p["rest_positions"]),"indices_sha256":hash_json(&p["indices"]),"display_transform":p["display_transform"],"source_ids":p["source_ids"]})).collect::<Vec<_>>();
    Ok(
        json!({"generation":frame["generation"],"revision":frame["revision"],"character_entity":frame["character_entity"],"backend":frame["backend"],"parameters":frame["parameters"],"sample":frame["sample"],"bone_count":frame["bones"].as_array().map(Vec::len),"bones_sha256":hash_json(&frame["bones"]),"parts":parts,"scope":"production b1_frame_snapshot -> bounded hashes/counts; CPU only"}),
    )
}
// Same f32 camera conversion as the pinned production stage mirror. This does
// not place the camera: it checks the actual local AND propagated global camera
// against the newly committed Work, before sampling complete identity stability.
fn open_stage_camera_is_current(world: &World) -> bool {
    let editor = world.resource::<EditorState>();
    let Some(doc) = editor.document() else {
        return false;
    };
    if world
        .resource::<nvwa_runtime::StageViewOverride>()
        .camera(editor)
        != Some(&doc.stage.camera)
    {
        return false;
    }
    let camera = &doc.stage.camera;
    let scale = doc.character.scale;
    let (azimuth, elevation) = (
        camera.azimuth_degrees.to_radians(),
        camera.elevation_degrees.to_radians(),
    );
    let target = Vec3::Y * camera.target_height * scale;
    let orbit = Vec3::new(
        azimuth.sin() * elevation.cos(),
        elevation.sin(),
        azimuth.cos() * elevation.cos(),
    );
    let expected = Transform::from_translation(target + orbit * camera.distance * scale)
        .looking_at(target, Vec3::Y)
        .to_matrix();
    let cameras: Vec<_> = world
        .iter_entities()
        .filter(|e| e.contains::<nvwa_runtime::SceneCamera>())
        .collect();
    if cameras.len() != 1 {
        return false;
    }
    let entity = &cameras[0];
    let (Some(local), Some(global), Some(Projection::Perspective(projection))) = (
        entity.get::<Transform>(),
        entity.get::<GlobalTransform>(),
        entity.get::<Projection>(),
    ) else {
        return false;
    };
    // Reuse the existing pinned-camera bound; never waive a changed camera.
    local.to_matrix().abs_diff_eq(expected, 1e-6)
        && global.to_matrix().abs_diff_eq(expected, 1e-6)
        && projection.fov == camera.fov_degrees.to_radians()
        && projection.near == 0.05 * scale
        && projection.far == 250.0 * scale
}
impl Pending {
    fn observe_identity(&mut self, identity: &Value, epoch: u64) -> bool {
        if self.stable_identity.as_ref() != Some(identity)
            || self
                .stable_epoch
                .is_some_and(|previous| epoch != previous && epoch != previous.wrapping_add(1))
        {
            self.stable_identity = Some(identity.clone());
            self.stable_updates = 0;
            self.stable_epoch = None;
        }
        if self.stable_epoch != Some(epoch) {
            self.stable_epoch = Some(epoch);
            self.stable_updates += 1;
        }
        self.stable_updates >= 2
    }
}

fn settle(world: &mut World, bridge: &mut Bridge) {
    let Some(mut pending) = bridge.pending.take() else {
        return;
    };
    let now = world.resource::<Time<Real>>().elapsed_secs_f64();
    if now - pending.started > 45. {
        fail(
            bridge,
            json!(pending.id),
            "request did not reach diagnostic/production readiness within45seconds".into(),
        );
        return;
    }
    let editor = world.resource::<EditorState>();
    let runtime = world.resource::<RuntimeStatus>();
    let appearance = appearance_status(world);
    // Production uses pending+error for a transition reason (including the
    // initial absent Work). Like71's typed transition gate, wait on that state;
    // the pending check below still forbids ready. A nonpending appearance
    // error and every retained editor/runtime/playback error remain terminal.
    let appearance_error = if appearance.pending {
        None
    } else {
        appearance.error.clone()
    };
    let error = editor
        .open_error
        .clone()
        .or_else(|| runtime.error.clone())
        .or_else(|| runtime.appearance_error.clone())
        .or_else(|| runtime.stage_error.clone())
        .or(appearance_error)
        .or_else(|| world.resource::<Playback>().error.clone());
    if let Some(error) = error {
        fail(bridge, json!(pending.id), error);
        return;
    }
    if editor.preview.is_some() {
        fail(bridge,json!(pending.id),"cannot certify saved Work while an editor preview is active; commit or cancel the preview".into());
        return;
    }
    if editor.pending_open.is_some()
        || !runtime.ready
        || !appearance.ready
        || appearance.pending
        || world.resource::<Playback>().seek_request.is_some()
    {
        if now - pending.started > 45. {
            fail(
                bridge,
                json!(pending.id),
                "request did not reach current ready production frame within45seconds".into(),
            );
        } else {
            bridge.pending = Some(pending);
        }
        return;
    }
    if pending.expects_new_b1_generation
        && (appearance.generation.is_none()
            || appearance.generation == pending.open_previous_generation)
    {
        fail(
            bridge,
            json!(pending.id),
            "Open candidate was canceled or did not publish a new B1 generation".into(),
        );
        return;
    }
    let work = match current_work(world) {
        Ok(work) => work,
        Err(error) => {
            fail(bridge, json!(pending.id), error);
            return;
        }
    };
    if appearance_sha256(work.as_bytes()) != pending.work_sha {
        fail(
            bridge,
            json!(pending.id),
            "current Work differs from requested Work before acknowledgement".into(),
        );
        return;
    }
    let playback = world.resource::<Playback>();
    if pending.playing.is_some_and(|p| playback.playing != p)
        || pending.seek.is_some_and(|t| {
            pending.playing == Some(false) && (playback.position_seconds - t).abs() > 1e-4
        })
    {
        fail(
            bridge,
            json!(pending.id),
            "actual held playback differs from request".into(),
        );
        return;
    }
    let before = identity(world);
    let capture = appearance_snapshot(world)
        .and_then(|appearance| base_capture(world).map(|base| (appearance, base)));
    match capture {
        Ok((appearance, base)) => {
            let after = identity(world);
            if before != after {
                fail(
                    bridge,
                    json!(pending.id),
                    "current identity changed during CPU capture".into(),
                );
                return;
            }
            if pending.action == "open" {
                let stage_current = open_stage_camera_is_current(world);
                if !stage_current || !pending.observe_identity(&after, bridge.update_epoch) {
                    if !stage_current {
                        pending.stable_identity = None;
                        pending.stable_epoch = None;
                        pending.stable_updates = 0;
                    }
                    bridge.pending = Some(pending);
                    return;
                }
            }
            // Capture only the fixed eight-parameter default/head-width-plus cases; Open/playback acks remain general.
            if matches!(
                pending.action.as_str(),
                "diagnostic" | "capture" | "witness"
            ) {
                if let Err(error) = fixed_case(
                    world,
                    &base,
                    pending.action == "witness",
                    world.resource::<Playback>().position_seconds,
                ) {
                    fail(bridge, json!(pending.id), error);
                    return;
                }
                match bridge.diagnostic.bind(world, &appearance, &base) {
                    Ok(true) => {}
                    Ok(false) => {
                        bridge.pending = Some(pending);
                        return;
                    }
                    Err(error) => {
                        fail(bridge, json!(pending.id), error);
                        return;
                    }
                }
                let full_base = match b1_frame_snapshot(world) {
                    Ok(frame) => frame,
                    Err(error) => {
                        fail(bridge, json!(pending.id), error);
                        return;
                    }
                };
                let verification = bridge.candidate.publish(world, &appearance, &full_base);
                let candidate = match verification {
                    Ok(record) => record,
                    Err(error) => {
                        fail(bridge, json!(pending.id), error);
                        return;
                    }
                };
                let stable = hash_json(&json!([
                    pending.id,
                    before,
                    candidate["published_positions_sha256"],
                    candidate["published_normals_sha256"],
                    candidate["decoded_rgba_sha256"],
                    candidate["variant"]
                ]));
                if candidate["pre_visibility_publication_matches"] != true {
                    bridge.stable_updates = 0;
                } else if bridge.stable_key == stable {
                    bridge.stable_updates += 1;
                } else {
                    bridge.stable_key = stable;
                    bridge.stable_updates = 1;
                }
                if bridge.stable_updates < 2 {
                    bridge.pending = Some(pending);
                    return;
                }
                match bridge.diagnostic.buffers(world, bridge.candidate.variant) {
                    Ok(buffers) => {
                        bridge.frame = Some(
                            json!({"endpoint":if cfg!(target_arch="wasm32"){"web"}else{"native"},"request_id":pending.id,"work_sha256":pending.work_sha,"base":base,"full_base":full_base,"fixed_case":"eight-parameter76-bounded","appearance":appearance,"buffers":buffers,"candidate":candidate,"stable_updates":bridge.stable_updates,"camera":camera_report(world),"identity":after}),
                        )
                    }
                    Err(error) => {
                        fail(bridge, json!(pending.id), error);
                        return;
                    }
                }
            }
            bridge.captured_identity = after.clone();
            bridge.work = work.clone();
            bridge.report = json!({"endpoint":if cfg!(target_arch="wasm32"){"web"}else{"native"},"phase":"ready","request_id":pending.id,"action":pending.action,"acknowledged":true,"request_succeeded":true,"current":true,"captured_identity":after,"appearance":appearance,"base":base,"work_json":work,"work_sha256":pending.work_sha,"open_error":world.resource::<EditorState>().open_error,"camera":camera_report(world),"scope":"production appearance validated with restored materials; diagnostic override and actual CPU buffers exported separately; GPU/rendered/performance proof separate"});
        }
        Err(error) => fail(bridge, json!(pending.id), error),
    }
}
#[cfg(not(target_arch = "wasm32"))]
fn atomic_write(path: &str, text: &str) -> std::io::Result<()> {
    let target = std::path::Path::new(path);
    let tmp = target.with_extension("nvwa76.tmp");
    std::fs::write(&tmp, text)?;
    std::fs::rename(tmp, target)
}
fn controller(world: &mut World) {
    let mut bridge = world.remove_resource::<Bridge>().unwrap();
    if let Err(error) = bridge.candidate.restore(world) {
        let id = bridge.report["request_id"].clone();
        fail(&mut bridge, id, error);
        bridge.candidate.clear(world);
    }
    #[cfg(target_arch = "wasm32")]
    bridge
        .incoming
        .extend(INCOMING.with(|q| q.borrow_mut().drain(..).collect::<Vec<_>>()));
    #[cfg(not(target_arch = "wasm32"))]
    if let Ok(path) = std::env::var("B1_76_COMMAND_FILE") {
        match std::fs::read_to_string(&path) {
            Ok(raw) => {
                if raw != bridge.native_input {
                    bridge.native_input = raw.clone();
                    bridge.incoming.push_back(raw);
                }
            }
            Err(error) => {
                bridge.native_input.clear();
                fail(
                    &mut bridge,
                    Value::Null,
                    format!("native command file: {error}"),
                );
            }
        }
    }
    invalidate_stale(world, &mut bridge);
    if let Some(raw) = bridge.incoming.pop_front() {
        dispatch(world, &mut bridge, raw);
    } else {
        settle(world, &mut bridge);
    }
    if let Ok(work) = current_work(world) {
        bridge.work = work;
    }
    if bridge.candidate.has_binding() && bridge.report["phase"] != "error" {
        if let Err(error) = bridge.candidate.stream(world) {
            let id = bridge.report["request_id"].clone();
            fail(&mut bridge, id, error);
        }
    }
    if bridge.report["current"] == true && bridge.frame.is_some() {
        match bridge.diagnostic.apply(world) {
            Ok(observation) => {
                bridge.report["diagnostic"] = observation.clone();
                if let Some(frame) = &mut bridge.frame {
                    frame["diagnostic"] = observation;
                }
            }
            Err(error) => {
                let id = bridge.report["request_id"].clone();
                fail(&mut bridge, id, error);
                bridge.diagnostic.clear(world);
            }
        }
    } else if bridge.report["phase"] == "error" || bridge.report["phase"] == "stale" {
        bridge.diagnostic.clear(world);
        if bridge.report["phase"] == "error" {
            bridge.candidate.clear(world);
        }
    }
    #[cfg(not(target_arch = "wasm32"))]
    if let Ok(path) = std::env::var("B1_76_REPORT_FILE") {
        let text = bridge.report.to_string();
        if text != bridge.native_output {
            match atomic_write(&path, &text) {
                Ok(()) => bridge.native_output = text,
                Err(error) => {
                    let id = bridge.report["request_id"].clone();
                    fail(&mut bridge, id, format!("native report file: {error}"));
                }
            }
        }
    }
    let frame_key = current_frame_export_key(&bridge);
    let frame_changed = frame_key != bridge.frame_export_key;
    if frame_changed {
        #[cfg(not(target_arch = "wasm32"))]
        if let Ok(path) = std::env::var("B1_76_FRAME_FILE") {
            if let Some(frame) = &bridge.frame {
                if let Err(error) = atomic_write(&path, &frame.to_string()) {
                    let id = bridge.report["request_id"].clone();
                    fail(&mut bridge, id, format!("native frame file: {error}"));
                }
            } else {
                let _ = std::fs::remove_file(path);
            }
        }
        bridge.frame_export_key = frame_key;
    }
    #[cfg(any(target_arch = "wasm32", test))]
    publish_web_state(&bridge, frame_changed);
    #[cfg(not(target_arch = "wasm32"))]
    if let Ok(path) = std::env::var("B1_76_MOTION_FILE") {
        let _=atomic_write(&path,&json!({"samples":bridge.candidate.motion,"scope":"CPU motion witness only; no GPU video or performance claim"}).to_string());
    }
    #[cfg(target_arch = "wasm32")]
    MOTION.with(|m| *m.borrow_mut() = json!({"samples":bridge.candidate.motion}).to_string());
    world.insert_resource(bridge);
}
fn publish_before_visibility(world: &mut World) {
    let mut bridge = world.remove_resource::<Bridge>().unwrap();
    if bridge.candidate.has_binding() {
        if let Err(error) = bridge.candidate.publish_for_visibility(world) {
            let id = bridge.report["request_id"].clone();
            fail(&mut bridge, id, error);
            bridge.candidate.clear(world);
        }
    }
    world.insert_resource(bridge);
}
#[cfg(target_arch = "wasm32")]
thread_local! {static MOTION:std::cell::RefCell<String>=const{std::cell::RefCell::new(String::new())};}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_76_motion() -> String {
    MOTION.with(|m| m.borrow().clone())
}
fn current_frame_export_key(bridge: &Bridge) -> String {
    bridge
        .frame
        .as_ref()
        .map(|f| hash_json(&json!([f["request_id"], f["identity"], f["diagnostic"]])))
        .unwrap_or_default()
}
fn prepare_diagnostic(world: &mut World) {
    let mut bridge = world.remove_resource::<Bridge>().unwrap();
    bridge.update_epoch = bridge.update_epoch.wrapping_add(1);
    if let Err(error) = bridge.candidate.restore(world) {
        let id = bridge.report["request_id"].clone();
        fail(&mut bridge, id, error);
        bridge.candidate.clear(world);
    }
    bridge.diagnostic.prepare(world);
    world.insert_resource(bridge);
}
fn camera_report(world: &World) -> Value {
    let cameras = world
        .iter_entities()
        .filter(|e| e.contains::<nvwa_runtime::SceneCamera>())
        .collect::<Vec<_>>();
    if cameras.len() != 1 {
        return json!({"error":"exactly one SceneCamera required"});
    }
    let e = &cameras[0];
    json!({"entity":format!("{:?}",e.id()),"global_transform":e.get::<GlobalTransform>().map(|t|t.to_matrix().to_cols_array()),"projection":e.get::<Projection>().map(|p|format!("{p:?}")),"msaa":e.get::<Msaa>().map(|m|format!("{m:?}")),"viewport":e.get::<Camera>().and_then(|c|c.physical_viewport_size()).map(|v|v.to_array()),"active":e.get::<Camera>().map(|c|c.is_active),"sub_camera_view":e.get::<Camera>().map(|c|format!("{:?}",c.sub_camera_view)),"reference65_sub_camera_view":"UNKNOWN: experiment65 did not export this field; actual68 value is exported and must remain identical across controls"})
}
fn environment_report(world: &World) -> Value {
    let lights=world.iter_entities().filter_map(|e|e.get::<DirectionalLight>().map(|light|json!({"entity":format!("{:?}",e.id()),"light":format!("{light:?}"),"global_transform":e.get::<GlobalTransform>().map(|t|t.to_matrix().to_cols_array())}))).collect::<Vec<_>>();
    json!({"directional_lights":lights,"ambient":world.get_resource::<GlobalAmbientLight>().map(|a|format!("{a:?}")),"clear_color":world.get_resource::<ClearColor>().map(|c|format!("{c:?}")),"scope":"actual CPU environment components; no light/GPU-buffer readback"})
}
fn fixed_case(world: &World, base: &Value, _shoulder: bool, seconds: f32) -> Result<(), String> {
    let actual = world
        .resource::<EditorState>()
        .document()
        .ok_or("fixed Work absent")?;
    let fixtures = [
        (
            include_str!("../works/default.nvwa.json"),
            include_str!("../works/reference-default.json"),
        ),
        (
            include_str!("../works/head-width-plus.nvwa.json"),
            include_str!("../works/reference-head-width-plus.json"),
        ),
        (
            include_str!("../works/default-arms.nvwa.json"),
            include_str!("../works/reference-default-arms.json"),
        ),
        (
            include_str!("../works/default-knee.nvwa.json"),
            include_str!("../works/reference-default-knee.json"),
        ),
        (
            include_str!("../works/minus-arms.nvwa.json"),
            include_str!("../works/reference-minus-arms.json"),
        ),
        (
            include_str!("../works/minus-knee.nvwa.json"),
            include_str!("../works/reference-minus-knee.json"),
        ),
        (
            include_str!("../works/plus-arms.nvwa.json"),
            include_str!("../works/reference-plus-arms.json"),
        ),
        (
            include_str!("../works/plus-knee.nvwa.json"),
            include_str!("../works/reference-plus-knee.json"),
        ),
        (
            include_str!("../works/shoulder-baseline-arms.nvwa.json"),
            include_str!("../works/reference-shoulder-baseline-arms.json"),
        ),
        (
            include_str!("../works/shoulder-rear-baseline-arms.nvwa.json"),
            include_str!("../works/reference-shoulder-rear-baseline-arms.json"),
        ),
    ];
    let pinned = fixtures
        .iter()
        .find_map(|(work, camera)| {
            (SceneDocument::from_json(work).ok().as_ref() == Some(actual)).then_some(*camera)
        })
        .ok_or("exact frozen experiment78 cohort Work required")?;
    let playback = world.resource::<Playback>();
    if (seconds != 0. && seconds != 2.)
        || playback.playing
        || playback.clip_id != actual.timeline[0].clip_id
        || (playback.position_seconds - seconds).abs() > 1e-6
        || base["sample"]["source_seconds"]
            .as_f64()
            .is_none_or(|s| (s - f64::from(seconds)).abs() > 1e-6)
    {
        return Err("paused source0/source2 frozen action sample required".into());
    }
    let camera = camera_report(world);
    if camera["error"].is_string() || camera["active"] != true {
        return Err("actual camera unavailable".into());
    }
    pinned_camera_gate(
        &camera,
        &serde_json::from_str(pinned).map_err(|e| e.to_string())?,
    )
}
fn pinned_camera_gate(camera: &Value, pinned: &Value) -> Result<(), String> {
    let actual_global: Vec<f64> =
        serde_json::from_value(camera["global_transform"].clone()).map_err(|e| e.to_string())?;
    let pinned_global: Vec<f64> =
        serde_json::from_value(pinned["camera"]["global_transform"].clone())
            .map_err(|e| e.to_string())?;
    if actual_global.len() != 16
        || actual_global
            .iter()
            .zip(&pinned_global)
            .any(|(a, b)| (a - b).abs() > 1e-6)
        || camera["viewport"] != pinned["camera"]["viewport_size_pixels"]
        || camera["msaa"] != pinned["camera"]["msaa"]
        || camera["projection"] != pinned["camera"]["projection"]
    {
        return Err(
            "camera transform/projection/viewport/MSAA differs from pinned hairline camera".into(),
        );
    }
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn open_identity_stability_does_not_count_duplicate_or_skipped_epochs() {
        let mut pending = Pending {
            id: "epoch".into(),
            action: "open".into(),
            work_sha: "test".into(),
            started: 0.,
            seek: None,
            playing: None,
            open_previous_generation: None,
            expects_new_b1_generation: true,
            stable_identity: None,
            stable_epoch: None,
            stable_updates: 0,
        };
        let identity = json!({"work":"current","camera":{"height":1.65}});
        assert!(!pending.observe_identity(&identity, 10));
        assert!(!pending.observe_identity(&identity, 10));
        assert!(pending.observe_identity(&identity, 11));
        let changed = json!({"work":"current","camera":{"height":1.66}});
        assert!(!pending.observe_identity(&changed, 12));
        assert!(!pending.observe_identity(&changed, 14));
        assert!(pending.observe_identity(&changed, 15));
    }
    #[test]
    fn variant_is_typed_and_required() {
        assert!(parse(r#"{"request_id":"x","action":"diagnostic","mode":"combined","palette":"textured","variant":"b_short01"}"#).is_ok());
        assert!(
            parse(
                r#"{"request_id":"x","action":"diagnostic","mode":"combined","palette":"textured"}"#
            )
            .is_err()
        );
        assert!(parse(r#"{"request_id":"x","action":"diagnostic","mode":"combined","palette":"textured","variant":"unknown"}"#).is_err());
        assert!(
            parse(r#"{"request_id":"x","action":"capture","variant":"b_short01"}"#).is_err()
        );
    }
    #[test]
    fn camera_gate_keeps_original_bounds() {
        let pinned: Value =
            serde_json::from_str(include_str!("../works/reference-default.json")).unwrap();
        let mut actual = pinned["camera"].clone();
        actual["viewport"] = actual["viewport_size_pixels"].clone();
        assert!(pinned_camera_gate(&actual, &pinned).is_ok());
        actual["global_transform"][13] =
            json!(actual["global_transform"][13].as_f64().unwrap() + 0.00001);
        assert!(pinned_camera_gate(&actual, &pinned).is_err());
    }
}

#[cfg(test)]
mod protocol_tests;

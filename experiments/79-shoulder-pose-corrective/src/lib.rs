//! Isolated actual-production shoulder source diagnostic; corrective inactive until one target is authored.
mod diagnostic;
mod source;
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
    target_json: Option<String>,
    target_sha256: Option<String>,
    palette: Option<diagnostic::Palette>,
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
            "diagnostic" => key == "mode" || key == "palette",
            "author_target" => key == "target_json" || key == "target_sha256",
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
    let target = req.target_json.is_some() || req.target_sha256.is_some();
    if target && req.action != "author_target" {
        return Err("target fields require author_target".into());
    }
    if req
        .palette
        .is_some_and(|p| p != diagnostic::Palette::Textured)
    {
        return Err("79 retains textured production materials".into());
    }
    let command = req.command.is_some();
    let open = req.work_json.is_some();
    let playback = req.seek_seconds.is_some() || req.playing.is_some();
    let diagnostic = req.mode.is_some() || req.palette.is_some();
    let valid = match req.action.as_str() {
        "author_target" => {
            req.target_json.is_some()
                && req.target_sha256.is_some()
                && !command
                && !open
                && !playback
                && !diagnostic
        }
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
            req.mode.is_some() && req.palette.is_some() && !command && !open && !playback
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
    source: source::State,
    #[cfg(not(target_arch = "wasm32"))]
    native_input: String,
    #[cfg(not(target_arch = "wasm32"))]
    native_output: String,
    frame_export_key: String,
    prepared_frame: Option<Value>,
    update_epoch: u64,
    stable_key: String,
    stable_epoch: Option<u64>,
    stable_updates: u32,
}
#[cfg(any(target_arch = "wasm32", test))]
thread_local! {static INCOMING:std::cell::RefCell<VecDeque<String>>=const{std::cell::RefCell::new(VecDeque::new())};static REPORT:std::cell::RefCell<String>=const{std::cell::RefCell::new(String::new())};static FRAME:std::cell::RefCell<String>=const{std::cell::RefCell::new(String::new())};static WORK:std::cell::RefCell<String>=const{std::cell::RefCell::new(String::new())};}
pub fn studio_app() -> App {
    let mut app = nvwa_studio::build_app();
    app.insert_resource(Bridge {
        frame_export_key: "startup".into(),
        ..default()
    })
    .add_systems(PreUpdate, prepare_diagnostic);
    install_source_publication(&mut app);
    app.add_systems(Last, controller);
    app
}
fn install_source_publication(app: &mut App) {
    app.add_systems(
        PostUpdate,
        publish_before_visibility
            .after(nvwa_runtime::RuntimeSystems::Appearance)
            .before(bevy::camera::visibility::VisibilitySystems::CalculateBounds)
            .before(bevy::camera::visibility::VisibilitySystems::CheckVisibility),
    );
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen(start)]
pub fn start() {
    let _ = studio_app().run();
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_79_command(raw: String) -> Result<(), wasm_bindgen::JsValue> {
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
pub fn b1_79_report() -> String {
    REPORT.with(|r| r.borrow().clone())
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_79_work() -> String {
    WORK.with(|w| w.borrow().clone())
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_79_frame() -> String {
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
    json!({"work_sha256":current_work(world).ok().map(|s|appearance_sha256(s.as_bytes())),"generation":appearance.generation,"revision":appearance.revision,"body_entity":appearance.body_entity,"appearance_ready":appearance.ready,"appearance_error":appearance.error,"preview_sha256":editor.preview.as_ref().and_then(document_hash),"pending_open_sha256":editor.pending_open.as_ref().and_then(document_hash),"open_error":editor.open_error,"runtime_ready":runtime.ready,"runtime_error":runtime.error,"runtime_appearance_error":runtime.appearance_error,"stage_error":runtime.stage_error,"clip_id":playback.clip_id,"timeline_id":playback.active_timeline_id,"seconds":playback.position_seconds,"playing":playback.playing,"completed":playback.completed,"seek_request":playback.seek_request,"camera":camera_report(world),"environment":environment_report(world)})
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
    bridge.prepared_frame = None;
    bridge.stable_key.clear();
    bridge.stable_epoch = None;
    bridge.stable_updates = 0;
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
    bridge.source.clear(world);
    bridge.prepared_frame = None;
    bridge.stable_key.clear();
    bridge.stable_epoch = None;
    bridge.stable_updates = 0;
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
                let mode = request.mode.ok_or("mode absent")?;
                if mode == diagnostic::Mode::Corrective && !bridge.source.has_target() {
                    return Err("no source-confirmed one-shot corrective target authored".into());
                }
                bridge
                    .diagnostic
                    .configure(mode, request.palette.ok_or("palette absent")?);
            }
            "author_target" => bridge.source.author(
                request.target_json.as_deref().ok_or("target_json absent")?,
                request
                    .target_sha256
                    .as_deref()
                    .ok_or("target_sha256 absent")?,
            )?,
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
fn settle(world: &mut World, bridge: &mut Bridge) {
    let Some(pending) = bridge.pending.take() else {
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
    let error = if pending.action == "open" {
        editor.open_error.clone()
    } else {
        None
    }
    .or_else(|| runtime.error.clone())
    .or_else(|| runtime.appearance_error.clone())
    .or_else(|| runtime.stage_error.clone());
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
            // Capture only the separately frozen shoulder camera/recipe/action cohort; Open/playback acks remain general.
            if matches!(
                pending.action.as_str(),
                "diagnostic" | "capture" | "witness"
            ) {
                if let Err(error) = fixed_case(
                    world,
                    &base,
                    pending.action == "witness",
                    pending.seek.unwrap_or(2.),
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
                let buffers = match bridge.diagnostic.buffers(world) {
                    Ok(v) => v,
                    Err(error) => {
                        fail(bridge, json!(pending.id), error);
                        return;
                    }
                };
                let mut frame = json!({"endpoint":if cfg!(target_arch="wasm32"){"web"}else{"native"},"request_id":pending.id,"work_sha256":pending.work_sha,"base":base,"full_base":full_base,"fixed_case":"79-source-shoulder-frozen-camera","appearance":appearance,"buffers":buffers,"camera":camera_report(world),"identity":after});
                if let Err(error) = bridge.source.apply(world, &frame, bridge.diagnostic.mode) {
                    fail(bridge, json!(pending.id), error);
                    return;
                }
                let source = match bridge
                    .source
                    .verified_record(world, &frame, bridge.update_epoch)
                {
                    Ok(v) => v,
                    Err(error) => {
                        fail(bridge, json!(pending.id), error);
                        return;
                    }
                };
                let key = hash_json(&json!([
                    pending.id,
                    after,
                    base,
                    source["publication_key_sha256"]
                ]));
                let stable = observe_publication(
                    bridge,
                    &key,
                    bridge.update_epoch,
                    source["pre_visibility_publication_matches"] == true,
                );
                frame["source_diagnostic"] = source;
                frame["stable_updates"] = json!(bridge.stable_updates);
                frame["capture_update_epoch"] = json!(bridge.update_epoch);
                bridge.prepared_frame = Some(frame.clone());
                if !stable {
                    bridge.pending = Some(pending);
                    return;
                }
                bridge.source.record_ready(&frame, bridge.diagnostic.mode);
                bridge.frame = Some(frame);
            }
            bridge.captured_identity = after.clone();
            bridge.work = work.clone();
            bridge.report = json!({"endpoint":if cfg!(target_arch="wasm32"){"web"}else{"native"},"phase":"ready","request_id":pending.id,"action":pending.action,"acknowledged":true,"request_succeeded":true,"current":true,"stable_updates":bridge.stable_updates,"capture_update_epoch":bridge.update_epoch,"captured_identity":after,"appearance":appearance,"base":base,"work_json":work,"work_sha256":pending.work_sha,"open_error":world.resource::<EditorState>().open_error,"camera":camera_report(world),"scope":"production appearance validated with restored materials; diagnostic override and actual CPU buffers exported separately; GPU/rendered/performance proof separate"});
            if let Some(frame) = &bridge.frame {
                bridge.report["source_diagnostic"] = frame["source_diagnostic"].clone();
            }
        }
        Err(error) => fail(bridge, json!(pending.id), error),
    }
}
#[cfg(not(target_arch = "wasm32"))]
fn atomic_write(path: &str, text: &str) -> std::io::Result<()> {
    let target = std::path::Path::new(path);
    let tmp = target.with_extension("nvwa79.tmp");
    std::fs::write(&tmp, text)?;
    std::fs::rename(tmp, target)
}
fn controller(world: &mut World) {
    let mut bridge = world.remove_resource::<Bridge>().unwrap();
    if let Some(frame) = bridge.prepared_frame.as_ref() {
        if let Err(error) =
            bridge
                .source
                .observe_last_before_restore(world, frame, bridge.update_epoch)
        {
            let id = bridge.report["request_id"].clone();
            fail(&mut bridge, id, error);
            bridge.source.clear(world);
        }
    }
    bridge.source.restore(world);
    #[cfg(target_arch = "wasm32")]
    bridge
        .incoming
        .extend(INCOMING.with(|q| q.borrow_mut().drain(..).collect::<Vec<_>>()));
    #[cfg(not(target_arch = "wasm32"))]
    if let Ok(path) = std::env::var("B1_79_COMMAND_FILE") {
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
    if bridge.report["current"] == true && bridge.frame.is_some() {
        bridge.source.restore(world);
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
        if bridge.report["current"] == true {
            let result = (|| {
                let frame = bridge.frame.as_ref().ok_or("ready frame absent")?;
                bridge.source.apply(world, frame, bridge.diagnostic.mode)?;
                let actual = bridge
                    .source
                    .verified_record(world, frame, bridge.update_epoch)?;
                if actual["pre_visibility_publication_matches"] != true
                    || actual["publication_key_sha256"]
                        != frame["source_diagnostic"]["publication_key_sha256"]
                {
                    return Err("ready actual publication changed; stale capture rejected".into());
                }
                Ok::<_, String>(())
            })();
            if let Err(error) = result {
                let id = bridge.report["request_id"].clone();
                fail(&mut bridge, id, error);
                bridge.source.clear(world);
            }
        }
    } else if bridge.report["phase"] == "error" || bridge.report["phase"] == "stale" {
        bridge.source.clear(world);
        bridge.diagnostic.clear(world);
    }
    #[cfg(not(target_arch = "wasm32"))]
    if let Ok(path) = std::env::var("B1_79_REPORT_FILE") {
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
        if let Ok(path) = std::env::var("B1_79_FRAME_FILE") {
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
    #[cfg(target_arch = "wasm32")]
    publish_web_state(&bridge, frame_changed);
    world.insert_resource(bridge);
}
fn current_frame_export_key(bridge: &Bridge) -> String {
    bridge
        .frame
        .as_ref()
        .map(|f| {
            hash_json(&json!([
                f["request_id"],
                f["identity"],
                f["diagnostic"],
                f["source_diagnostic"]
            ]))
        })
        .unwrap_or_default()
}
fn prepare_diagnostic(world: &mut World) {
    let mut bridge = world.remove_resource::<Bridge>().unwrap();
    bridge.update_epoch = bridge.update_epoch.wrapping_add(1);
    bridge.source.restore(world);
    bridge.diagnostic.prepare(world);
    world.insert_resource(bridge);
}
fn observe_publication(bridge: &mut Bridge, key: &str, epoch: u64, matches: bool) -> bool {
    if !matches {
        bridge.stable_key.clear();
        bridge.stable_epoch = None;
        bridge.stable_updates = 0;
        return false;
    }
    if bridge.stable_key == key && bridge.stable_epoch == Some(epoch) {
        return bridge.stable_updates >= 2;
    }
    if bridge.stable_key == key
        && bridge
            .stable_epoch
            .is_some_and(|e| e.wrapping_add(1) == epoch)
    {
        bridge.stable_updates += 1;
    } else {
        bridge.stable_key = key.to_owned();
        bridge.stable_updates = 1;
    }
    bridge.stable_epoch = Some(epoch);
    bridge.stable_updates >= 2
}
fn publish_before_visibility(world: &mut World) {
    let mut bridge = world.remove_resource::<Bridge>().unwrap();
    if let Some(frame) = bridge.prepared_frame.as_ref() {
        let result = bridge.source.publish_for_visibility(
            world,
            frame,
            bridge.diagnostic.mode,
            bridge.update_epoch,
        );
        if let Err(error) = result {
            let id = bridge.report["request_id"].clone();
            fail(&mut bridge, id, error);
            bridge.source.clear(world);
        }
    }
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
    json!({"entity":format!("{:?}",e.id()),"global_transform":e.get::<GlobalTransform>().map(|t|t.to_matrix().to_cols_array()),"projection":e.get::<Projection>().map(|p|format!("{p:?}")),"msaa":e.get::<Msaa>().map(|m|format!("{m:?}")),"viewport":e.get::<Camera>().and_then(|c|c.physical_viewport_size()).map(|v|v.to_array()),"active":e.get::<Camera>().map(|c|c.is_active),"sub_camera_view":e.get::<Camera>().map(|c|format!("{:?}",c.sub_camera_view)),"scope":"79 actual exported scene camera; compared to separately frozen new camera fixture, not historical65 camera"})
}
fn environment_report(world: &World) -> Value {
    let lights=world.iter_entities().filter_map(|e|e.get::<DirectionalLight>().map(|light|json!({"entity":format!("{:?}",e.id()),"light":format!("{light:?}"),"global_transform":e.get::<GlobalTransform>().map(|t|t.to_matrix().to_cols_array())}))).collect::<Vec<_>>();
    json!({"directional_lights":lights,"ambient":world.get_resource::<GlobalAmbientLight>().map(|a|format!("{a:?}")),"clear_color":world.get_resource::<ClearColor>().map(|c|format!("{c:?}")),"scope":"actual CPU environment components; no light/GPU-buffer readback"})
}
fn fixed_case(
    world: &World,
    base: &Value,
    _old_shoulder: bool,
    _old_seconds: f32,
) -> Result<(), String> {
    let frozen = SceneDocument::from_json(include_str!(
        "../works/shoulder-rear-baseline-arms.nvwa.json"
    ))
    .map_err(|e| e.to_string())?;
    let front = SceneDocument::from_json(include_str!("../works/shoulder-baseline-arms.nvwa.json"))
        .map_err(|e| e.to_string())?;
    let actual = world
        .resource::<EditorState>()
        .document()
        .ok_or("79 fixed Work absent")?;
    let mut expected = frozen.clone();
    let torso = actual
        .character
        .parameters
        .get("torso_length")
        .copied()
        .ok_or("torso absent")?;
    if ![-1., 0., 1.].contains(&torso) {
        return Err("79 supports frozen torso-1/0/+1 only".into());
    }
    expected
        .character
        .parameters
        .insert("torso_length".into(), torso);
    expected.revision = actual.revision;
    if actual.stage.camera == front.stage.camera {
        expected.stage.camera = front.stage.camera.clone();
    }
    let clip = world.resource::<Playback>().clip_id.as_str();
    if !["b1_arm_rehearsal_v1", "b1_knee_flex_v1"].contains(&clip) {
        return Err("79 unsupported clip".into());
    }
    if expected.timeline.len() != 1 || actual.timeline.len() != 1 {
        return Err("79 requires one authored entry".into());
    }
    expected.timeline[0].clip_id = clip.to_owned();
    if actual != &expected {
        return Err("79 Work differs from separately frozen recipe/action/camera cohort".into());
    }
    let playback = world.resource::<Playback>();
    let seconds = playback.position_seconds;
    if playback.playing
        || ![0., 1., 2., 3., 4.].contains(&seconds)
        || (clip == "b1_knee_flex_v1" && seconds != 2.)
        || base["sample"]["source_seconds"]
            .as_f64()
            .is_none_or(|s| (s - f64::from(seconds)).abs() > 1e-6)
    {
        return Err("79 requires exact held arm0/1/2/3/4 or knee2".into());
    }
    let camera = camera_report(world);
    let views: Value =
        serde_json::from_str(include_str!("../works/cameras.json")).map_err(|e| e.to_string())?;
    let name = if actual.stage.camera == front.stage.camera {
        "front"
    } else {
        "rear"
    };
    let matrix: Vec<f64> =
        serde_json::from_value(camera["global_transform"].clone()).map_err(|e| e.to_string())?;
    let pinned: Vec<f64> =
        serde_json::from_value(views[name].clone()).map_err(|e| e.to_string())?;
    if matrix.len() != 16
        || matrix
            .iter()
            .zip(&pinned)
            .any(|(a, b)| (a - b).abs() > 1e-6)
        || camera["viewport"] != json!([1280, 720])
        || camera["msaa"] != "Sample4"
        || camera["sub_camera_view"]
            != "Some(SubCameraView { full_size: UVec2(81920, 39040), offset: Vec2(0.0, 0.0), size: UVec2(81920, 46080) })"
        || camera["projection"]
            != "Perspective(PerspectiveProjection { fov: 0.5235988, aspect_ratio: 1.7777778, near: 0.05, far: 250.0, near_clip_plane: Vec4(0.0, 0.0, -1.0, -0.1) })"
        || camera["active"] != true
    {
        return Err("79 actual camera differs from frozen new camera fixture".into());
    }
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn measured_publication_stability_requires_distinct_consecutive_epochs_and_resets() {
        let mut b = Bridge::default();
        assert!(!observe_publication(&mut b, "a", 10, true));
        assert_eq!(b.stable_updates, 1);
        assert!(!observe_publication(&mut b, "a", 10, true));
        assert_eq!(b.stable_updates, 1);
        assert!(observe_publication(&mut b, "a", 11, true));
        assert_eq!(b.stable_updates, 2);
        assert!(!observe_publication(&mut b, "mutated-source", 12, true));
        assert_eq!(b.stable_updates, 1);
        assert!(!observe_publication(&mut b, "mutated-source", 13, false));
        assert_eq!(b.stable_updates, 0);
        assert!(!observe_publication(&mut b, "mutated-source", 14, true));
        assert!(!observe_publication(&mut b, "mutated-source", 16, true));
        assert_eq!(b.stable_updates, 1);
        assert!(observe_publication(&mut b, "mutated-source", 17, true));
        fail(&mut b, json!("error"), "injected".into());
        assert_eq!(b.stable_updates, 0);
        assert!(b.prepared_frame.is_none());
    }
    #[test]
    fn protocol_rejects_unbounded_diagnostics_and_missing_target() {
        assert!(parse(r#"{"request_id":"s","action":"diagnostic","mode":"source_body","palette":"textured"}"#).is_ok());
        for raw in [
            r#"{"request_id":"s","action":"diagnostic","mode":"body_only","palette":"textured"}"#,
            r#"{"request_id":"s","action":"diagnostic","mode":"combined","palette":"role_tint"}"#,
            r#"{"request_id":"s","action":"author_target","target_json":"{}"}"#,
            r#"{"request_id":"s","action":"capture","target_json":"{}"}"#,
            r#"{"request_id":"s","request_id":"s","action":"capture"}"#,
        ] {
            assert!(parse(raw).is_err(), "{raw}");
        }
    }
    #[test]
    fn actual_ingress_invalidates_old_ready_and_duplicate_replay_retains_correlated_frame() {
        let raw = r#"{"request_id":"replay","action":"capture"}"#.to_string();
        let frame = json!({"request_id":"replay","identity":{"generation":1}});
        let mut bridge = Bridge {
            report: json!({"phase":"ready","current":true,"request_id":"replay"}),
            frame: Some(frame.clone()),
            ..default()
        };
        bridge
            .seen
            .insert("replay".into(), appearance_sha256(raw.as_bytes()));
        bridge.frame_export_key = current_frame_export_key(&bridge);
        publish_web_state(&bridge, true);
        queue_web_command(raw).unwrap();
        let pending: Value = serde_json::from_str(&REPORT.with(|r| r.borrow().clone())).unwrap();
        assert_eq!(pending["current"], false);
        let raw = INCOMING.with(|q| q.borrow_mut().pop_front().unwrap());
        dispatch(&mut World::new(), &mut bridge, raw);
        publish_web_state(
            &bridge,
            current_frame_export_key(&bridge) != bridge.frame_export_key,
        );
        assert_eq!(
            serde_json::from_str::<Value>(&FRAME.with(|f| f.borrow().clone())).unwrap(),
            frame
        );
        assert!(
            queue_web_command(r#"{"request_id":"bad","action":"unsupported"}"#.into()).is_err()
        );
        let raw = INCOMING.with(|q| q.borrow_mut().pop_front().unwrap());
        dispatch(&mut World::new(), &mut bridge, raw);
        publish_web_state(&bridge, true);
        assert!(bridge.frame.is_none());
        assert!(FRAME.with(|f| f.borrow().is_empty()));
    }
}

//! Acceptance bridge around unchanged production Studio. No rendering, meshes,
//! materials, images, launch options, or selection state are implemented here.
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
    let valid = match req.action.as_str() {
        "command" => command && !open && !playback,
        "open" => open && !command && !playback,
        "playback" => playback && !command && !open,
        "capture" => !command && !open && !playback,
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
    #[cfg(not(target_arch = "wasm32"))]
    native_input: String,
    #[cfg(not(target_arch = "wasm32"))]
    native_output: String,
}
#[cfg(target_arch = "wasm32")]
thread_local! {static INCOMING:std::cell::RefCell<VecDeque<String>>=const{std::cell::RefCell::new(VecDeque::new())};static REPORT:std::cell::RefCell<String>=const{std::cell::RefCell::new(String::new())};static WORK:std::cell::RefCell<String>=const{std::cell::RefCell::new(String::new())};}
pub fn studio_app() -> App {
    let mut app = nvwa_studio::build_app();
    app.init_resource::<Bridge>().add_systems(Last, controller);
    app
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen(start)]
pub fn start() {
    let _ = studio_app().run();
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_66_command(raw: String) -> Result<(), wasm_bindgen::JsValue> {
    // Parse through shared typed Command now; invalid input is still delivered so
    // its failed acknowledgement replaces any earlier successful evidence.
    let parsed = parse(&raw);
    INCOMING.with(|q| {
        let mut q = q.borrow_mut();
        q.clear();
        q.push_back(raw);
    });
    REPORT.with(|r| *r.borrow_mut() = json!({"phase":"pending","current":false}).to_string());
    parsed
        .map(|_| ())
        .map_err(|e| wasm_bindgen::JsValue::from_str(&e))
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_66_report() -> String {
    REPORT.with(|r| r.borrow().clone())
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_66_work() -> String {
    WORK.with(|w| w.borrow().clone())
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
    json!({"work_sha256":current_work(world).ok().map(|s|appearance_sha256(s.as_bytes())),"generation":appearance.generation,"revision":appearance.revision,"body_entity":appearance.body_entity,"appearance_ready":appearance.ready,"appearance_error":appearance.error,"preview_sha256":editor.preview.as_ref().and_then(document_hash),"pending_open_sha256":editor.pending_open.as_ref().and_then(document_hash),"open_error":editor.open_error,"runtime_ready":runtime.ready,"runtime_error":runtime.error,"runtime_appearance_error":runtime.appearance_error,"stage_error":runtime.stage_error,"clip_id":playback.clip_id,"timeline_id":playback.active_timeline_id,"seconds":playback.position_seconds,"playing":playback.playing,"completed":playback.completed,"seek_request":playback.seek_request})
}
fn invalidate_stale(world: &World, bridge: &mut Bridge) {
    if bridge.report["phase"] == "ready" && identity(world) != bridge.captured_identity {
        bridge.report["phase"] = json!("stale");
        bridge.report["current"] = json!(false);
        bridge.report["current_identity"] = identity(world);
    }
}

fn fail(bridge: &mut Bridge, id: Value, error: String) {
    bridge.pending = None;
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
    let playing = request.playing;
    let open_previous_generation = appearance_status(world).generation;
    let mut expects_new_b1_generation = false;
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
            "playback" => {
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
    let parts=frame["parts"].as_array().ok_or("base parts missing")?.iter().map(|p|json!({"name":p["name"],"display_entity":p["display_entity"],"mesh_handle":p["mesh_handle"],"vertices":p["positions"].as_array().map(Vec::len),"indices":p["indices"].as_array().map(Vec::len),"positions_sha256":hash_json(&p["positions"]),"normals_sha256":hash_json(&p["normals"]),"rest_positions_sha256":hash_json(&p["rest_positions"]),"indices_sha256":hash_json(&p["indices"]),"display_transform":p["display_transform"]})).collect::<Vec<_>>();
    Ok(
        json!({"generation":frame["generation"],"revision":frame["revision"],"character_entity":frame["character_entity"],"backend":frame["backend"],"parameters":frame["parameters"],"sample":frame["sample"],"bone_count":frame["bones"].as_array().map(Vec::len),"bones_sha256":hash_json(&frame["bones"]),"parts":parts,"scope":"production b1_frame_snapshot -> bounded hashes/counts; CPU only"}),
    )
}
fn settle(world: &mut World, bridge: &mut Bridge) {
    let Some(pending) = bridge.pending.take() else {
        return;
    };
    let now = world.resource::<Time<Real>>().elapsed_secs_f64();
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
            bridge.captured_identity = after.clone();
            bridge.work = work.clone();
            bridge.report = json!({"phase":"ready","request_id":pending.id,"action":pending.action,"acknowledged":true,"request_succeeded":true,"current":true,"captured_identity":after,"appearance":appearance,"base":base,"work_json":work,"work_sha256":pending.work_sha,"open_error":world.resource::<EditorState>().open_error,"scope":"unchanged Studio; production CPU state; GPU/rendered/performance proof separate"});
        }
        Err(error) => fail(bridge, json!(pending.id), error),
    }
}
#[cfg(not(target_arch = "wasm32"))]
fn atomic_write(path: &str, text: &str) -> std::io::Result<()> {
    let target = std::path::Path::new(path);
    let tmp = target.with_extension("nvwa66.tmp");
    std::fs::write(&tmp, text)?;
    std::fs::rename(tmp, target)
}
fn controller(world: &mut World) {
    let mut bridge = world.remove_resource::<Bridge>().unwrap();
    #[cfg(target_arch = "wasm32")]
    bridge
        .incoming
        .extend(INCOMING.with(|q| q.borrow_mut().drain(..).collect::<Vec<_>>()));
    #[cfg(not(target_arch = "wasm32"))]
    if let Ok(path) = std::env::var("B1_66_COMMAND_FILE") {
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
    #[cfg(target_arch = "wasm32")]
    {
        REPORT.with(|r| *r.borrow_mut() = bridge.report.to_string());
        WORK.with(|w| *w.borrow_mut() = bridge.work.clone());
    }
    #[cfg(not(target_arch = "wasm32"))]
    if let Ok(path) = std::env::var("B1_66_REPORT_FILE") {
        let text = bridge.report.to_string();
        if text != bridge.native_output {
            match atomic_write(&path, &text) {
                Ok(()) => bridge.native_output = text,
                Err(error) => fail(
                    &mut bridge,
                    Value::Null,
                    format!("native report file: {error}"),
                ),
            }
        }
    }
    world.insert_resource(bridge);
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn strict_bridge_keeps_shared_command_and_work_json_parsers() {
        assert!(parse(r#"{"request_id":"a","action":"capture"}"#).is_ok());
        assert!(
            parse(r#"{"request_id":"a","action":"command","command":{"type":"undo"}}"#).is_ok()
        );
        assert!(parse(r#"{"request_id":"a","action":"unsupported"}"#).is_err());
        assert!(parse(r#"{"request_id":"a","action":"capture","playing":false}"#).is_err());
        assert!(parse(r#"{"request_id":"a","action":"capture","command":null}"#).is_err());
        assert!(
            parse(r#"{"request_id":"a","action":"open","work_json":"{}","playing":null}"#).is_err()
        );
        assert!(
            parse(r#"{"request_id":"a","action":"playback","playing":false,"seek_seconds":null}"#)
                .is_err()
        );

        assert!(parse(r#"{"request_id":"a","request_id":"b","action":"capture"}"#).is_err());
        assert!(
            parse(
                r#"{"request_id":"a","action":"command","command":{"type":"undo","extra":true}}"#
            )
            .is_err()
        );
    }
}

#[cfg(test)]
mod transaction_tests {
    use super::*;
    fn world() -> World {
        let mut world = World::new();
        world.init_resource::<EditorState>();
        world.init_resource::<RuntimeStatus>();
        world.init_resource::<Playback>();
        world.init_resource::<nvwa_runtime::AppearanceStatus>();
        world.init_resource::<Time<Real>>();
        world
            .resource_mut::<EditorState>()
            .replace(SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_motion()).unwrap())
            .unwrap();
        world
    }
    fn mark_ready(world: &mut World) {
        world.resource_mut::<RuntimeStatus>().ready = true;
        let revision = world.resource::<EditorState>().document().unwrap().revision;
        let mut appearance = world.resource_mut::<nvwa_runtime::AppearanceStatus>();
        appearance.ready = true;
        appearance.generation = Some(7);
        appearance.revision = Some(revision);
        appearance.applied = Some(nvwa_core::CharacterAppearance::None);
        appearance.body_entity = Some("fixture-body".into());
    }
    #[test]
    fn preview_stales_prior_proof_and_blocks_saved_work_capture() {
        let mut world = world();
        mark_ready(&mut world);
        let saved = current_work(&world).unwrap();
        let captured = identity(&world);
        let mut bridge = Bridge {
            report: json!({"phase":"ready","request_id":"earlier","current":true}),
            captured_identity: captured.clone(),
            ..default()
        };
        let mut values = world
            .resource::<EditorState>()
            .document()
            .unwrap()
            .character
            .parameters
            .clone();
        values.insert("torso_length".into(), 0.5);
        world
            .resource_mut::<EditorState>()
            .preview_parameters(values)
            .unwrap();
        assert_eq!(
            current_work(&world).unwrap(),
            saved,
            "preview does not change saved Work hash"
        );
        assert_ne!(identity(&world), captured);
        invalidate_stale(&world, &mut bridge);
        assert_eq!(bridge.report["phase"], "stale");
        assert_eq!(bridge.report["current"], false);
        dispatch(
            &mut world,
            &mut bridge,
            r#"{"request_id":"preview-capture","action":"capture"}"#.into(),
        );
        settle(&mut world, &mut bridge);
        assert_eq!(bridge.report["phase"], "error");
        assert_eq!(bridge.report["request_succeeded"], false);
        assert!(
            bridge.report["error"]
                .as_str()
                .unwrap()
                .contains("editor preview is active")
        );
        assert_eq!(current_work(&world).unwrap(), saved);
    }
    #[test]
    fn identical_work_open_cancellation_cannot_acknowledge_old_generation() {
        let mut world = world();
        mark_ready(&mut world);
        let saved = current_work(&world).unwrap();
        let mut bridge = Bridge::default();
        dispatch(
            &mut world,
            &mut bridge,
            json!({"request_id":"same-open","action":"open","work_json":saved}).to_string(),
        );
        assert!(world.resource::<EditorState>().pending_open.is_some());
        assert_eq!(
            bridge.pending.as_ref().unwrap().open_previous_generation,
            Some(7)
        );
        assert!(bridge.pending.as_ref().unwrap().expects_new_b1_generation);
        world.resource_mut::<EditorState>().cancel_pending_open();
        assert_eq!(
            current_work(&world).unwrap(),
            saved,
            "same-content cancellation leaves identical Work"
        );
        settle(&mut world, &mut bridge);
        assert_eq!(bridge.report["phase"], "error");
        assert_eq!(bridge.report["request_succeeded"], false);
        assert_eq!(
            bridge.report["error"],
            "Open candidate was canceled or did not publish a new B1 generation"
        );
    }
    #[test]
    fn pending_open_and_runtime_error_invalidate_current_identity() {
        let mut world = world();
        mark_ready(&mut world);
        let captured = identity(&world);
        let doc = world.resource::<EditorState>().document().unwrap().clone();
        world
            .resource_mut::<EditorState>()
            .request_open(doc)
            .unwrap();
        assert_ne!(identity(&world), captured);
        world.resource_mut::<EditorState>().cancel_pending_open();
        assert_eq!(identity(&world), captured);
        world.resource_mut::<RuntimeStatus>().ready = false;
        assert_ne!(identity(&world), captured);
        world.resource_mut::<RuntimeStatus>().ready = true;
        world.resource_mut::<RuntimeStatus>().error = Some("failed current frame".into());
        assert_ne!(identity(&world), captured);
    }
    #[test]
    fn stage_failure_cannot_acknowledge_a_ready_frame() {
        let mut world = world();
        let mut bridge = Bridge::default();
        dispatch(
            &mut world,
            &mut bridge,
            r#"{"request_id":"failed-stage","action":"capture"}"#.into(),
        );
        world.resource_mut::<RuntimeStatus>().ready = true;
        world.resource_mut::<RuntimeStatus>().stage_error =
            Some("failed requested stage conversion".into());
        world.resource_mut::<nvwa_runtime::AppearanceStatus>().ready = true;
        settle(&mut world, &mut bridge);
        assert_eq!(bridge.report["phase"], "error");
        assert_eq!(bridge.report["request_succeeded"], false);
        assert_eq!(bridge.report["error"], "failed requested stage conversion");
        assert_eq!(
            identity(&world)["stage_error"],
            "failed requested stage conversion"
        );
    }
    #[test]
    fn rejected_open_and_shared_command_never_acknowledge_older_success() {
        let mut world = world();
        let before = current_work(&world).unwrap();
        let mut bridge = Bridge {
            report: json!({"phase":"ready","request_succeeded":true,"current":true}),
            ..default()
        };
        dispatch(
            &mut world,
            &mut bridge,
            r#"{"request_id":"bad-open","action":"open","work_json":"{}"}"#.into(),
        );
        assert_eq!(bridge.report["phase"], "error");
        assert_eq!(bridge.report["request_succeeded"], false);
        assert_eq!(bridge.report["request_id"], "bad-open");
        assert_eq!(current_work(&world).unwrap(), before);
        assert!(world.resource::<EditorState>().pending_open.is_none());
        dispatch(
            &mut world,
            &mut bridge,
            r#"{"request_id":"bad-undo","action":"command","command":{"type":"undo"}}"#.into(),
        );
        assert_eq!(bridge.report["phase"], "error");
        assert_eq!(bridge.report["request_succeeded"], false);
        assert_eq!(bridge.report["request_id"], "bad-undo");
        settle(&mut world, &mut bridge);
        assert_eq!(bridge.report["phase"], "error");
        assert_eq!(current_work(&world).unwrap(), before);
    }
}

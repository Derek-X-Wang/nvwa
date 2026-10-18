//! Acceptance bridge around unchanged production Studio. No rendering, meshes,
//! materials, images, launch options, or selection state are implemented here.
mod observation;
mod transition;
use bevy::prelude::*;
use nvwa_core::{Command, SceneDocument, appearance_sha256};
use nvwa_runtime::{
    EditorState, Playback, RuntimeStatus, appearance_snapshot, appearance_status, b1_frame_snapshot,
};
use serde::Deserialize;
use serde_json::{Value, json};
use std::collections::{BTreeMap, VecDeque};
use transition::stable_observation;
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
    stable_identity: Option<Value>,
    stable_frames: u8,
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
    frame_export_key: String,
    #[cfg(not(target_arch = "wasm32"))]
    native_input: String,
    #[cfg(not(target_arch = "wasm32"))]
    native_output: String,
}
#[cfg(any(target_arch = "wasm32", test))]
thread_local! {static INCOMING:std::cell::RefCell<VecDeque<String>>=const{std::cell::RefCell::new(VecDeque::new())};static REPORT:std::cell::RefCell<String>=const{std::cell::RefCell::new(String::new())};static FRAME:std::cell::RefCell<String>=const{std::cell::RefCell::new(String::new())};static WORK:std::cell::RefCell<String>=const{std::cell::RefCell::new(String::new())};}
pub fn studio_app() -> App {
    let mut app = nvwa_studio::build_app();
    app.insert_resource(Bridge {
        frame_export_key: "startup".into(),
        ..default()
    })
    .add_systems(Last, controller);
    app
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen(start)]
pub fn start() {
    let _ = studio_app().run();
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_71_command(raw: String) -> Result<(), wasm_bindgen::JsValue> {
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
pub fn b1_71_report() -> String {
    REPORT.with(|r| r.borrow().clone())
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_71_work() -> String {
    WORK.with(|w| w.borrow().clone())
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_71_frame() -> String {
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
    json!({"work_sha256":current_work(world).ok().map(|s|appearance_sha256(s.as_bytes())),"generation":appearance.generation,"revision":appearance.revision,"body_entity":appearance.body_entity,"appearance_ready":appearance.ready,"appearance_pending":appearance.pending,"appearance_error":appearance.error,"preview_sha256":editor.preview.as_ref().and_then(document_hash),"pending_open_sha256":editor.pending_open.as_ref().and_then(document_hash),"open_error":editor.open_error,"runtime_ready":runtime.ready,"runtime_error":runtime.error,"runtime_appearance_error":runtime.appearance_error,"stage_error":runtime.stage_error,"clip_id":playback.clip_id,"timeline_id":playback.active_timeline_id,"seconds":playback.position_seconds,"playing":playback.playing,"completed":playback.completed,"seek_request":playback.seek_request,"playback_error":playback.error,"camera":observation::camera(world),"environment":observation::environment(world)})
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
    if bridge.seen.len() >= 512 {
        fail(
            bridge,
            json!(request.request_id),
            "acceptance session request limit512 reached".into(),
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
        stable_identity: None,
        stable_frames: 0,
    });
    bridge.frame = None;
    bridge.captured_identity = Value::Null;
    bridge.report = json!({"phase":"pending","request_id":id,"acknowledged":false,"request_succeeded":null,"current":false});
}
fn hash_json(v: &Value) -> String {
    appearance_sha256(v.to_string().as_bytes())
}
fn base_capture(world: &World) -> Result<Value, String> {
    b1_frame_snapshot(world)
}
// Called only after typed readiness and the strict producer snapshot succeed.
// Compare typed f32 parameters directly; pretty Work JSON has shorter decimals.
fn validate_current_base(
    world: &World,
    base: &Value,
    appearance: &nvwa_runtime::AppearanceStatus,
) -> Result<(), String> {
    let doc = world
        .resource::<EditorState>()
        .document()
        .ok_or("current Work absent")?;
    let version = doc
        .profile
        .backend
        .b1_asset_version()
        .ok_or("current Work has no B1 base identity")?;
    for (key, expected) in [
        ("backend", json!(doc.profile.backend)),
        ("profile_id", json!(doc.profile.id)),
        ("asset_id", json!(version.asset_id())),
        ("revision", json!(doc.revision)),
        ("parameters", json!(doc.character.parameters)),
        ("diagnostic_pose", json!(doc.character.diagnostic_pose)),
        (
            "mode",
            json!(if doc.timeline.is_empty() {
                "diagnostic"
            } else {
                "motion"
            }),
        ),
    ] {
        if base.get(key) != Some(&expected) {
            return Err(format!(
                "published B1 base {key} differs from current typed Work"
            ));
        }
    }
    if appearance.generation.is_none()
        || base["generation"].as_u64() != appearance.generation
        || appearance.revision != Some(doc.revision)
        || appearance.requested != doc.character.appearance
        || appearance.applied.as_ref() != Some(&doc.character.appearance)
    {
        return Err(
            "published B1 base differs from current appearance Work/generation binding".into(),
        );
    }
    if appearance
        .character_entity
        .as_deref()
        .is_none_or(str::is_empty)
        || base["character_entity"].as_str() != appearance.character_entity.as_deref()
        || appearance.body_entity.as_deref().is_none_or(str::is_empty)
        || base_body(base)?["display_entity"].as_str() != appearance.body_entity.as_deref()
    {
        return Err(
            "published B1 base differs from current appearance character/body binding".into(),
        );
    }
    let playback = world.resource::<Playback>();
    for (key, expected) in [
        ("clip_id", json!(playback.clip_id)),
        ("timeline_id", json!(playback.active_timeline_id)),
        ("position_seconds", json!(playback.position_seconds)),
        ("playing", json!(playback.playing)),
        ("completed", json!(playback.completed)),
    ] {
        if base["sample"].get(key) != Some(&expected) {
            return Err(format!(
                "published B1 base sample {key} differs from current transport"
            ));
        }
    }
    if !base["sample"]["serial"].as_u64().is_some_and(|s| s > 0)
        || !base["sample"]["source_seconds"]
            .as_f64()
            .is_some_and(f64::is_finite)
    {
        return Err("published B1 base has no valid current source sample".into());
    }
    Ok(())
}
fn base_body(base: &Value) -> Result<&Value, String> {
    let parts = base["parts"]
        .as_array()
        .ok_or("published B1 base parts absent")?;
    let mut bodies = parts.iter().filter(|part| part["name"] == "body");
    let body = bodies.next().ok_or("published B1 body absent")?;
    if bodies.next().is_some() {
        return Err("published B1 body is ambiguous".into());
    }
    Ok(body)
}
fn validate_appearance_binding(base: &Value, appearance: &Value) -> Result<(), String> {
    let body = base_body(base)?;
    for (key, expected) in [
        ("base_asset_id", &base["asset_id"]),
        ("generation", &base["generation"]),
        ("revision", &base["revision"]),
        ("character_entity", &base["character_entity"]),
        ("body_entity", &body["display_entity"]),
        ("body_mesh", &body["mesh_handle"]),
        ("serial", &base["sample"]["serial"]),
    ] {
        if appearance.get(key) != Some(expected) {
            return Err(format!(
                "appearance snapshot {key} differs from current published B1 base"
            ));
        }
    }
    Ok(())
}
fn settle(world: &mut World, bridge: &mut Bridge) {
    let Some(mut pending) = bridge.pending.take() else {
        return;
    };
    let now = world.resource::<Time<Real>>().elapsed_secs_f64();
    let editor = world.resource::<EditorState>();
    let runtime = world.resource::<RuntimeStatus>();
    let appearance = appearance_status(world);
    let playback = world.resource::<Playback>();
    match transition::check(transition::State {
        elapsed: now - pending.started,
        errors: [
            editor.open_error.as_deref(),
            runtime.error.as_deref(),
            runtime.appearance_error.as_deref(),
            runtime.stage_error.as_deref(),
        ],
        appearance_error: appearance.error.as_deref(),
        playback_error: playback.error.as_deref(),
        preview: editor.preview.is_some(),
        pending_open: editor.pending_open.is_some(),
        runtime_ready: runtime.ready,
        appearance_ready: appearance.ready,
        appearance_pending: appearance.pending,
        seek_pending: playback.seek_request.is_some(),
    }) {
        Err(error) => {
            fail(bridge, json!(pending.id), error);
            return;
        }
        Ok(transition::Readiness::Waiting) => {
            transition::reset_stability(&mut pending.stable_identity, &mut pending.stable_frames);
            bridge.pending = Some(pending);
            return;
        }
        Ok(transition::Readiness::Ready) => {}
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
    let live = world.resource::<Playback>().playing;
    if !live
        && !stable_observation(
            &mut pending.stable_identity,
            &mut pending.stable_frames,
            &before,
        )
    {
        bridge.pending = Some(pending);
        return;
    }
    let evidence_kind = if live {
        "live-transient; next-frame staleness expected"
    } else {
        "held-stable-two-frames"
    };
    // Strict publication and typed Work/status identity precede the appearance
    // snapshot, whose failure path invalidates/disposes appearance state.
    let capture = base_capture(world).and_then(|base| {
        validate_current_base(world, &base, &appearance)?;
        let appearance = appearance_snapshot(world)?;
        validate_appearance_binding(&base, &appearance)?;
        let observed = observation::bindings(world, &base, &appearance)?;
        Ok((appearance, base, observed))
    });
    match capture {
        Ok((appearance, base, observed)) => {
            let after = identity(world);
            if before != after {
                fail(
                    bridge,
                    json!(pending.id),
                    "current identity changed during CPU capture".into(),
                );
                return;
            }
            bridge.frame = Some(
                json!({"endpoint":if cfg!(target_arch="wasm32"){"web"}else{"native"},"request_id":pending.id,"evidence_kind":evidence_kind,"stable_observations":pending.stable_frames,"action":pending.action,"work_sha256":pending.work_sha,"work_json":work,"identity":after,"full_base":base,"appearance":appearance,"observed":observed,"camera":observation::camera(world),"scope":"exact production full snapshot + actual bound CPU buffers; no GPU texel/depth/readback or rendered admission"}),
            );
            bridge.captured_identity = after.clone();
            bridge.work = work.clone();
            bridge.report = json!({"endpoint":if cfg!(target_arch="wasm32"){"web"}else{"native"},"phase":"ready","request_id":pending.id,"evidence_kind":evidence_kind,"stable_observations":pending.stable_frames,"action":pending.action,"acknowledged":true,"request_succeeded":true,"current":true,"captured_identity":after,"appearance":appearance,"base_summary":observation::base_summary(&base),"work_json":work,"work_sha256":pending.work_sha,"open_error":world.resource::<EditorState>().open_error,"scope":"unchanged Studio; production CPU state; GPU/rendered/performance proof separate"});
        }
        Err(error) => fail(bridge, json!(pending.id), error),
    }
}
#[cfg(not(target_arch = "wasm32"))]
fn atomic_write(path: &str, text: &str) -> std::io::Result<()> {
    let target = std::path::Path::new(path);
    let tmp = target.with_extension("nvwa71.tmp");
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
    if let Ok(path) = std::env::var("B1_71_COMMAND_FILE") {
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
    let frame_key = current_frame_export_key(&bridge);
    let frame_changed = frame_key != bridge.frame_export_key;
    #[cfg(not(target_arch = "wasm32"))]
    {
        if frame_changed {
            if let Ok(path) = std::env::var("B1_71_FRAME_FILE") {
                let result = if let Some(frame) = &bridge.frame {
                    atomic_write(&path, &frame.to_string())
                } else {
                    match std::fs::remove_file(&path) {
                        Ok(()) => Ok(()),
                        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
                        Err(e) => Err(e),
                    }
                };
                if let Err(error) = result {
                    let id = bridge.report["request_id"].clone();
                    fail(&mut bridge, id, format!("native frame file: {error}"));
                }
            }
        }
        if let Ok(path) = std::env::var("B1_71_REPORT_FILE") {
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
    }
    #[cfg(target_arch = "wasm32")]
    publish_web_state(&bridge, frame_changed);
    bridge.frame_export_key = frame_key;
    world.insert_resource(bridge);
}
fn current_frame_export_key(bridge: &Bridge) -> String {
    bridge
        .frame
        .as_ref()
        .map(|f| hash_json(&json!([f["request_id"], f["identity"], f["appearance"]])))
        .unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn web_ready_identical_replay_retains_correlated_frame_through_actual_ingress_and_export() {
        let raw = r#"{"request_id":"web-replay","action":"capture"}"#.to_string();
        let frame = json!({"request_id":"web-replay","retained":true});
        let mut bridge = Bridge {
            report: json!({"phase":"ready","current":true,"request_id":"web-replay"}),
            frame: Some(frame.clone()),
            frame_export_key: "unchanged-key".into(),
            ..default()
        };
        bridge
            .seen
            .insert("web-replay".into(), appearance_sha256(raw.as_bytes()));
        bridge.frame_export_key = current_frame_export_key(&bridge);
        publish_web_state(&bridge, true);
        queue_web_command(raw).unwrap();
        assert_eq!(
            serde_json::from_str::<Value>(&REPORT.with(|r| r.borrow().clone())).unwrap()["phase"],
            "pending"
        );
        let incoming = INCOMING.with(|q| q.borrow_mut().pop_front().unwrap());
        dispatch(&mut World::new(), &mut bridge, incoming);
        // Actual cache unchanged branch, which failed when ingress cleared FRAME.
        let changed = current_frame_export_key(&bridge) != bridge.frame_export_key;
        assert!(
            !changed,
            "identical replay must use the actual unchanged-cache branch"
        );
        publish_web_state(&bridge, changed);
        let report: Value = serde_json::from_str(&REPORT.with(|r| r.borrow().clone())).unwrap();
        let exported: Value = serde_json::from_str(&FRAME.with(|f| f.borrow().clone())).unwrap();
        assert_eq!(report["phase"], "ready");
        assert_eq!(report["current"], true);
        assert_eq!(report["request_id"], exported["request_id"]);
        assert_eq!(exported, frame);
        // Invalid ingress must still be processed, invalidate old ready evidence,
        // and clear the frame through the same changed export branch.
        assert!(
            queue_web_command(r#"{"request_id":"bad-web","action":"unsupported"}"#.into()).is_err()
        );
        let incoming = INCOMING.with(|q| q.borrow_mut().pop_front().unwrap());
        dispatch(&mut World::new(), &mut bridge, incoming);
        publish_web_state(&bridge, true);
        assert_eq!(bridge.report["request_id"], "bad-web");
        assert_eq!(bridge.report["phase"], "error");
        FRAME.with(|f| assert!(f.borrow().is_empty()));
    }

    #[test]
    fn held_gate_waits_two_actual_identity_frames_and_resets_for_camera_or_sample_change() {
        let mut prior = None;
        let mut count = 0;
        let before = json!({"camera":"before-fit","sample":2,"generation":1});
        let after = json!({"camera":"after-fit","sample":2,"generation":1});
        assert!(!stable_observation(&mut prior, &mut count, &before));
        assert!(!stable_observation(&mut prior, &mut count, &after));
        assert!(stable_observation(&mut prior, &mut count, &after));
        assert!(!stable_observation(
            &mut prior,
            &mut count,
            &json!({"camera":"after-fit","sample":4,"generation":1})
        ));
    }
    #[test]
    fn bounded512_digest_ledger_rejects_new_request_without_losing_correlation() {
        let mut bridge = Bridge::default();
        for i in 0..512 {
            bridge
                .seen
                .insert(format!("prior-{i}"), "digest-only".into());
        }
        bridge.frame = Some(json!({"old":true}));
        dispatch(
            &mut World::new(),
            &mut bridge,
            r#"{"request_id":"overflow","action":"capture"}"#.into(),
        );
        assert_eq!(bridge.report["phase"], "error");
        assert_eq!(bridge.report["request_id"], "overflow");
        assert!(
            bridge.report["error"]
                .as_str()
                .unwrap()
                .contains("limit512")
        );
        assert_eq!(bridge.seen.len(), 512);
        assert!(bridge.frame.is_none());
    }
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
        appearance.character_entity = Some("fixture-character".into());
    }
    // These are actual observer-policy/identity unit controls with resource or
    // metadata fixtures, not fabricated successful production mesh captures.
    #[test]
    fn pending_appearance_reason_waits_resets_held_state_and_reaches_base_before_appearance() {
        let mut world = world();
        mark_ready(&mut world);
        let mut bridge = Bridge::default();
        dispatch(
            &mut world,
            &mut bridge,
            r#"{"request_id":"typed-pending","action":"capture"}"#.into(),
        );
        let original_started = bridge.pending.as_ref().unwrap().started;
        bridge.pending.as_mut().unwrap().stable_identity = Some(identity(&world));
        bridge.pending.as_mut().unwrap().stable_frames = 1;
        {
            let mut status = world.resource_mut::<nvwa_runtime::AppearanceStatus>();
            status.pending = true;
            status.error = Some("opaque transition reason".into());
        }
        settle(&mut world, &mut bridge);
        assert_eq!(bridge.report["phase"], "pending");
        assert_eq!(bridge.report["acknowledged"], false);
        assert!(bridge.report["request_succeeded"].is_null());
        assert!(bridge.frame.is_none());
        assert!(bridge.pending.as_ref().unwrap().stable_identity.is_none());
        assert_eq!(bridge.pending.as_ref().unwrap().stable_frames, 0);
        world
            .resource_mut::<Time<Real>>()
            .advance_by(std::time::Duration::from_secs(15));
        settle(&mut world, &mut bridge);
        assert_eq!(bridge.pending.as_ref().unwrap().started, original_started);
        {
            let mut status = world.resource_mut::<nvwa_runtime::AppearanceStatus>();
            status.pending = false;
            status.error = None;
        }
        settle(&mut world, &mut bridge);
        assert_eq!(bridge.report["phase"], "pending");
        assert_eq!(bridge.pending.as_ref().unwrap().stable_frames, 1);
        settle(&mut world, &mut bridge);
        assert_eq!(bridge.report["phase"], "error");
        assert_eq!(bridge.report["error"], "B1 runtime absent");
        assert_eq!(bridge.report["request_succeeded"], false);
        let status = world.resource::<nvwa_runtime::AppearanceStatus>();
        assert!(
            status.ready,
            "base failure must precede appearance snapshot invalidation"
        );
        assert!(status.error.is_none());
        assert_eq!(status.applied, Some(nvwa_core::CharacterAppearance::None));
    }
    #[test]
    fn all_actual_error_channels_stay_terminal_while_appearance_transition_waits() {
        for channel in 0..6 {
            let mut world = world();
            mark_ready(&mut world);
            let mut bridge = Bridge::default();
            dispatch(
                &mut world,
                &mut bridge,
                r#"{"request_id":"typed-error","action":"capture"}"#.into(),
            );
            {
                let mut status = world.resource_mut::<nvwa_runtime::AppearanceStatus>();
                status.pending = true;
                status.error = Some("opaque transition reason".into());
            }
            let error = format!("actual failure channel {channel}");
            match channel {
                0 => world.resource_mut::<EditorState>().open_error = Some(error.clone()),
                1 => world.resource_mut::<RuntimeStatus>().error = Some(error.clone()),
                2 => world.resource_mut::<RuntimeStatus>().appearance_error = Some(error.clone()),
                3 => world.resource_mut::<RuntimeStatus>().stage_error = Some(error.clone()),
                4 => world.resource_mut::<Playback>().error = Some(error.clone()),
                _ => {
                    let mut status = world.resource_mut::<nvwa_runtime::AppearanceStatus>();
                    status.pending = false;
                    status.error = Some(error.clone());
                }
            }
            settle(&mut world, &mut bridge);
            assert_eq!(bridge.report["error"], error);
            assert_eq!(bridge.report["phase"], "error");
            assert_eq!(bridge.report["acknowledged"], true);
            assert_eq!(bridge.report["request_succeeded"], false);
            assert!(bridge.pending.is_none());
            assert!(bridge.frame.is_none());
        }
    }
    #[test]
    fn typed_pending_times_out_on_original_request_deadline() {
        let mut world = world();
        mark_ready(&mut world);
        let mut bridge = Bridge::default();
        dispatch(
            &mut world,
            &mut bridge,
            r#"{"request_id":"typed-timeout","action":"capture"}"#.into(),
        );
        world
            .resource_mut::<nvwa_runtime::AppearanceStatus>()
            .pending = true;
        world.resource_mut::<nvwa_runtime::AppearanceStatus>().error =
            Some("pending reason".into());
        world
            .resource_mut::<Time<Real>>()
            .advance_by(std::time::Duration::from_secs(46));
        settle(&mut world, &mut bridge);
        assert_eq!(bridge.report["phase"], "error");
        assert_eq!(bridge.report["request_succeeded"], false);
        assert_eq!(
            bridge.report["error"],
            "request did not reach current stable production identity within45seconds"
        );
        assert!(bridge.pending.is_none());
        assert!(bridge.frame.is_none());
    }
    #[test]
    fn changed_saved_work_cannot_reuse_a_pending_request_or_call_appearance_snapshot() {
        let mut world = world();
        mark_ready(&mut world);
        let mut bridge = Bridge::default();
        dispatch(
            &mut world,
            &mut bridge,
            r#"{"request_id":"typed-stale-work","action":"capture"}"#.into(),
        );
        let doc = world.resource::<EditorState>().document().unwrap().clone();
        let mut values = doc.character.parameters;
        values.insert("torso_length".into(), 0.5);
        world
            .resource_mut::<EditorState>()
            .apply(Command::SetParameters {
                character_id: doc.character.id,
                values,
            })
            .unwrap();
        settle(&mut world, &mut bridge);
        assert_eq!(bridge.report["phase"], "error");
        assert_eq!(
            bridge.report["error"],
            "current Work differs from requested Work before acknowledgement"
        );
        assert!(world.resource::<nvwa_runtime::AppearanceStatus>().ready);
        assert!(bridge.frame.is_none());
    }
    fn metadata_fixture(world: &World) -> Value {
        let doc = world.resource::<EditorState>().document().unwrap();
        let status = appearance_status(world);
        let playback = world.resource::<Playback>();
        json!({"backend":doc.profile.backend,"profile_id":doc.profile.id,"asset_id":doc.profile.backend.b1_asset_version().unwrap().asset_id(),"revision":doc.revision,"parameters":doc.character.parameters,"generation":status.generation,"character_entity":status.character_entity,"diagnostic_pose":doc.character.diagnostic_pose,"mode":"motion","parts":[{"name":"body","display_entity":status.body_entity,"mesh_handle":"fixture-mesh"}],"sample":{"clip_id":playback.clip_id,"timeline_id":playback.active_timeline_id,"position_seconds":playback.position_seconds,"source_seconds":0.0,"playing":playback.playing,"completed":playback.completed,"serial":1}})
    }
    #[test]
    fn base_identity_guard_rejects_stale_fields_and_uses_exact_typed_f32() {
        let mut world = world();
        let mut doc =
            SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character()).unwrap();
        doc.character.parameters.insert("neck_width".into(), 0.2);
        world.resource_mut::<EditorState>().replace(doc).unwrap();
        mark_ready(&mut world);
        let base = metadata_fixture(&world);
        let appearance = appearance_status(&world);
        assert!(validate_current_base(&world, &base, &appearance).is_ok());
        for key in [
            "backend",
            "profile_id",
            "asset_id",
            "revision",
            "parameters",
            "generation",
            "character_entity",
            "diagnostic_pose",
            "mode",
        ] {
            let mut stale = base.clone();
            stale[key] = Value::Null;
            assert!(
                validate_current_base(&world, &stale, &appearance).is_err(),
                "{key}"
            );
        }
        for key in [
            "clip_id",
            "timeline_id",
            "position_seconds",
            "playing",
            "completed",
            "serial",
            "source_seconds",
        ] {
            let mut stale = base.clone();
            stale["sample"][key] = Value::Null;
            assert!(
                validate_current_base(&world, &stale, &appearance).is_err(),
                "{key}"
            );
        }
        let mut stale = base.clone();
        stale["parts"][0]["display_entity"] = json!("old-body");
        assert!(validate_current_base(&world, &stale, &appearance).is_err());
        let mut stale = base.clone();
        stale["parameters"] = serde_json::from_str::<Value>(&current_work(&world).unwrap())
            .unwrap()["character"]["parameters"]
            .clone();
        assert_ne!(
            stale["parameters"], base["parameters"],
            "pretty JSON decimal differs from exact promoted f32"
        );
        assert!(validate_current_base(&world, &stale, &appearance).is_err());
        assert!(validate_current_base(&world, &base, &appearance).is_ok());
    }
    #[test]
    fn appearance_capture_must_share_base_body_generation_and_sample_serial() {
        let mut world = world();
        mark_ready(&mut world);
        let base = metadata_fixture(&world);
        let appearance = json!({"base_asset_id":base["asset_id"],"generation":base["generation"],"revision":base["revision"],"character_entity":base["character_entity"],"body_entity":base["parts"][0]["display_entity"],"body_mesh":base["parts"][0]["mesh_handle"],"serial":base["sample"]["serial"]});
        assert!(validate_appearance_binding(&base, &appearance).is_ok());
        for key in [
            "base_asset_id",
            "generation",
            "revision",
            "character_entity",
            "body_entity",
            "body_mesh",
            "serial",
        ] {
            let mut stale = appearance.clone();
            stale[key] = Value::Null;
            assert!(validate_appearance_binding(&base, &stale).is_err(), "{key}");
        }
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
    fn retained_open_or_playback_error_cannot_acknowledge_a_capture() {
        for open in [true, false] {
            let mut world = world();
            mark_ready(&mut world);
            if open {
                world.resource_mut::<EditorState>().open_error = Some("failed prior Open".into());
            } else {
                world.resource_mut::<Playback>().error = Some("failed current transport".into());
            }
            let mut bridge = Bridge::default();
            dispatch(
                &mut world,
                &mut bridge,
                r#"{"request_id":"current-error","action":"capture"}"#.into(),
            );
            settle(&mut world, &mut bridge);
            assert_eq!(bridge.report["request_id"], "current-error");
            assert_eq!(bridge.report["phase"], "error");
            assert!(bridge.frame.is_none());
        }
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

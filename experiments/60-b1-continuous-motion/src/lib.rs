//! Additive diagnostics around the exact production Studio App. No alternate evaluator.
use bevy::prelude::*;
use nvwa_core::{Command, TimelineClip};
use nvwa_runtime::{EditorState, Playback, b1_frame_snapshot};
use serde_json::{Value, json};
use std::collections::VecDeque;

#[derive(Resource, Default)]
struct Probe {
    queue: VecDeque<Value>,
    pending: Option<(Value, f64)>,
    report: Value,
    frame: Option<Value>,
    #[cfg(not(target_arch = "wasm32"))]
    last_command: String,
    #[cfg(not(target_arch = "wasm32"))]
    last_report: String,
    #[cfg(not(target_arch = "wasm32"))]
    report_serial: u64,
}
#[cfg(target_arch = "wasm32")]
thread_local! {
    static WEB_QUEUE: std::cell::RefCell<VecDeque<Value>> = const { std::cell::RefCell::new(VecDeque::new()) };
    static WEB_REPORT: std::cell::RefCell<String> = const { std::cell::RefCell::new(String::new()) };
    static WEB_FRAME: std::cell::RefCell<String> = const { std::cell::RefCell::new(String::new()) };
}
pub fn studio_app() -> App {
    let mut app = nvwa_studio::build_app();
    app.init_resource::<Probe>().add_systems(Last, controller);
    app
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen(start)]
pub fn start() {
    let _ = studio_app().run();
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_60_command(command: String) -> Result<(), wasm_bindgen::JsValue> {
    let value: Value = serde_json::from_str(&command)
        .map_err(|e| wasm_bindgen::JsValue::from_str(&e.to_string()))?;
    WEB_QUEUE.with(|q| q.borrow_mut().push_back(value));
    Ok(())
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_60_report() -> String {
    WEB_REPORT.with(|r| r.borrow().clone())
}
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen::prelude::wasm_bindgen]
pub fn b1_60_frame() -> String {
    WEB_FRAME.with(|r| r.borrow().clone())
}

fn validate(value: &Value) -> Result<(), String> {
    let object = value.as_object().ok_or("command must be an object")?;
    for key in object.keys() {
        if ![
            "request_id",
            "action",
            "clip_id",
            "seconds",
            "torso_length",
            "jaw_drop",
        ]
        .contains(&key.as_str())
        {
            return Err(format!("unknown probe command field {key}"));
        }
    }
    let id = value["request_id"].as_str().ok_or("request_id required")?;
    if id.is_empty()
        || id.len() > 64
        || !id
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
    {
        return Err("invalid request_id".into());
    }
    if !matches!(
        value["action"].as_str(),
        Some("sample" | "snapshot" | "play" | "pause")
    ) {
        return Err("unknown action".into());
    }
    if value["action"] == "sample" {
        if !matches!(
            value["clip_id"].as_str(),
            Some("b1_arm_rehearsal_v1" | "b1_knee_flex_v1")
        ) {
            return Err("invalid authored clip".into());
        }
        for key in ["seconds", "torso_length", "jaw_drop"] {
            let n = value[key]
                .as_f64()
                .ok_or_else(|| format!("{key} must be finite numeric"))?;
            let bounds = if key == "seconds" {
                0.0..=4.0
            } else {
                -1.0..=1.0
            };
            if !n.is_finite() || !bounds.contains(&n) {
                return Err(format!("{key} out of bounds"));
            }
        }
    }
    Ok(())
}
fn apply(world: &mut World, value: &Value) -> Result<(), String> {
    validate(value)?;
    if value["action"] == "sample" {
        let document = world
            .resource::<EditorState>()
            .document()
            .ok_or("open an actual B1 motion Work first")?
            .clone();
        if !document.profile.backend.is_b1_motion() {
            return Err("actual active Work is not B1 motion v2".into());
        }
        let parameters = [
            (
                "torso_length".into(),
                value["torso_length"].as_f64().unwrap() as f32,
            ),
            (
                "jaw_drop".into(),
                value["jaw_drop"].as_f64().unwrap() as f32,
            ),
        ]
        .into_iter()
        .collect();
        if document.character.parameters != parameters {
            world
                .resource_mut::<EditorState>()
                .apply(Command::SetParameters {
                    character_id: document.character.id,
                    values: parameters,
                })?;
        }
        let clip = value["clip_id"].as_str().unwrap();
        let clips = vec![TimelineClip {
            id: "probe-entry".into(),
            clip_id: clip.into(),
            start_seconds: 0.0,
            duration_seconds: 4.0,
            speed: 1.0,
            looping: false,
        }];
        if world.resource::<EditorState>().document().unwrap().timeline != clips {
            world
                .resource_mut::<EditorState>()
                .apply(Command::SetTimeline { clips })?;
        }
        let mut playback = world.resource_mut::<Playback>();
        playback.playing = false;
        playback.seek_request = Some(value["seconds"].as_f64().unwrap() as f32);
    } else if value["action"] == "play" {
        world.resource_mut::<Playback>().playing = true;
    } else if value["action"] == "pause" {
        world.resource_mut::<Playback>().playing = false;
    }
    Ok(())
}
fn matches_request(frame: &Value, request: &Value) -> bool {
    request["action"] != "sample"
        || (frame["parameters"]["torso_length"]
            .as_f64()
            .zip(request["torso_length"].as_f64())
            .is_some_and(|(a, b)| (a - b).abs() <= 1e-6)
            && frame["parameters"]["jaw_drop"]
                .as_f64()
                .zip(request["jaw_drop"].as_f64())
                .is_some_and(|(a, b)| (a - b).abs() <= 1e-6)
            && frame["sample"]["clip_id"] == request["clip_id"]
            && frame["sample"]["timeline_id"] == "probe-entry"
            && frame["sample"]["source_seconds"]
                .as_f64()
                .zip(request["seconds"].as_f64())
                .is_some_and(|(a, b)| (a - b).abs() <= 1e-6))
}
#[cfg(not(target_arch = "wasm32"))]
fn write_native_report(report: &str, serial: u64) -> Result<(), String> {
    let out = std::env::var("B1_60_CAPTURE_DIR")
        .map_err(|_| "B1_60_CAPTURE_DIR is required for native status")?;
    let root = std::path::Path::new(&out);
    if !root.is_absolute() || !root.is_dir() {
        return Err("native status directory must exist and be absolute".into());
    }
    let temporary = root.join(format!(".probe-status-{}-{serial}.tmp", std::process::id()));
    use std::io::Write;
    let mut file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temporary)
        .map_err(|e| e.to_string())?;
    file.write_all(report.as_bytes())
        .and_then(|_| file.write_all(b"\n"))
        .and_then(|_| file.sync_all())
        .map_err(|e| e.to_string())?;
    drop(file);
    std::fs::rename(&temporary, root.join("probe-status.json")).map_err(|e| e.to_string())?;
    Ok(())
}
fn controller(world: &mut World) {
    let mut probe = world.remove_resource::<Probe>().unwrap();
    #[cfg(target_arch = "wasm32")]
    WEB_QUEUE.with(|q| probe.queue.extend(q.borrow_mut().drain(..)));
    #[cfg(not(target_arch = "wasm32"))]
    if let Ok(path) = std::env::var("B1_60_COMMAND_FILE") {
        if let Ok(bytes) = std::fs::read_to_string(path) {
            if bytes != probe.last_command {
                probe.last_command = bytes.clone();
                match serde_json::from_str(&bytes) {
                    Ok(command) => probe.queue.push_back(command),
                    Err(error) => {
                        probe.report = json!({"error":error.to_string(),"evidence":"actual Studio additive controller"})
                    }
                }
            }
        }
    }
    let now = world.resource::<Time<Real>>().elapsed_secs_f64();
    if probe.pending.is_none() {
        if let Some(request) = probe.queue.pop_front() {
            match apply(world, &request) {
                Ok(()) => {
                    probe.report = json!({"request":request,"phase":"pending","evidence":"actual Studio additive controller"});
                    probe.pending = Some((request, now));
                }
                Err(error) => {
                    probe.report = json!({"request":request,"phase":"rejected","error":error})
                }
            }
        }
    } else if let Some((request, started)) = probe.pending.take() {
        match b1_frame_snapshot(world) {
            Ok(frame) if matches_request(&frame, &request) => {
                let record = json!({"kind":"studio","request":request,"snapshot":frame,"evidence":"exact production nvwa_studio::build_app + additive controller; CPU uploaded buffers, not GPU readback"});
                #[cfg(not(target_arch = "wasm32"))]
                let saved = (|| -> Result<(), String> {
                    let out = std::env::var("B1_60_CAPTURE_DIR").map_err(
                        |_| "B1_60_CAPTURE_DIR must be an existing owned absolute directory",
                    )?;
                    let root = std::path::Path::new(&out);
                    if !root.is_absolute() || !root.is_dir() {
                        return Err("capture directory must already exist and be absolute".into());
                    }
                    let path =
                        root.join(format!("{}.json", request["request_id"].as_str().unwrap()));
                    use std::io::Write;
                    let mut f = std::fs::OpenOptions::new()
                        .write(true)
                        .create_new(true)
                        .open(path)
                        .map_err(|e| e.to_string())?;
                    serde_json::to_writer(&mut f, &record).map_err(|e| e.to_string())?;
                    f.write_all(b"\n").map_err(|e| e.to_string())?;
                    Ok(())
                })();
                #[cfg(target_arch = "wasm32")]
                let saved: Result<(), String> = Ok(());
                probe.report = match saved {
                    Ok(()) => {
                        json!({"request":request,"phase":"captured","sample":record["snapshot"]["sample"],"evidence":record["evidence"]})
                    }
                    Err(error) => json!({"request":request,"phase":"capture-error","error":error}),
                };
                probe.frame = Some(record);
            }
            result => {
                if now - started > 45.0 {
                    probe.report = json!({"request":request,"phase":"timeout","error":result.err().unwrap_or_else(||"actual published snapshot does not match requested recipe/time".into())});
                } else {
                    probe.pending = Some((request, started));
                }
            }
        }
    }
    #[cfg(target_arch = "wasm32")]
    {
        WEB_REPORT.with(|r| *r.borrow_mut() = probe.report.to_string());
        if let Some(frame) = probe.frame.take() {
            WEB_FRAME.with(|r| *r.borrow_mut() = frame.to_string());
        }
    }
    #[cfg(not(target_arch = "wasm32"))]
    {
        let report = probe.report.to_string();
        if report != probe.last_report {
            probe.report_serial += 1;
            if let Err(error) = write_native_report(&report, probe.report_serial) {
                eprintln!("B1_60_STATUS_ERROR {error}: {report}");
            }
            probe.last_report = report;
        }
    }
    world.insert_resource(probe);
}

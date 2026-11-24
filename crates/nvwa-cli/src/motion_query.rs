//! Numeric observation of authenticated B1 motion without a render app.
use bevy::{asset::AssetMetaCheck, prelude::*, time::TimeUpdateStrategy};
use nvwa_core::{CoreError, SceneDocument, appearance_sha256};
use nvwa_runtime::{
    EditorState, NvwaRuntimePlugin, Playback, RuntimeStatus, StartupDocumentPolicy,
    b1_foot_clearance, b1_running_observation, register_b1_asset_source,
};
use serde_json::{Value, json};
use std::{
    path::Path,
    time::{Duration, Instant},
};

const MAX_SAMPLES: usize = 201;
const NEAR_CM: f64 = 0.5;
const BELOW_CM: f64 = -0.05;
const JUMP_CM: f64 = 0.5;

struct Frame {
    seconds: f32,
    clip: String,
    feet: [f64; 2],
    geometry: Value,
}

fn headless_app(root: &str, work: SceneDocument) -> Result<App, String> {
    let root = Path::new(root).canonicalize().map_err(|e| e.to_string())?;
    if !root.is_dir() {
        return Err("Asset root must be a directory".into());
    }
    let mut app = App::new();
    register_b1_asset_source(&mut app);
    app.add_plugins((
        MinimalPlugins,
        AssetPlugin {
            file_path: root.to_str().ok_or("Asset root must be UTF-8")?.into(),
            meta_check: AssetMetaCheck::Never,
            ..default()
        },
        bevy::transform::TransformPlugin,
        bevy::world_serialization::WorldSerializationPlugin,
        bevy::scene::ScenePlugin,
        bevy::mesh::MeshPlugin,
        bevy::image::ImagePlugin::default(),
        bevy::animation::AnimationPlugin,
        bevy::gltf::GltfPlugin::default(),
    ))
    .init_asset::<StandardMaterial>()
    .insert_resource(StartupDocumentPolicy::WaitForOpen)
    .add_plugins(NvwaRuntimePlugin);
    if !work.profile.backend.is_b1_running() {
        // Saved clothing/hair presentation has no role in visible body-foot sampling.
        app.configure_sets(
            PostUpdate,
            nvwa_runtime::RuntimeSystems::Appearance.run_if(|| false),
        );
    }
    app.finish();
    app.cleanup();
    app.world_mut()
        .resource_mut::<EditorState>()
        .request_open(work)?;
    let deadline = Instant::now() + Duration::from_secs(30);
    loop {
        app.update();
        let world = app.world();
        let status = world.resource::<RuntimeStatus>();
        let editor = world.resource::<EditorState>();
        if let Some(error) = editor.open_error.as_ref().or(status.error.as_ref()) {
            return Err(error.clone());
        }
        if editor.pending_open.is_none() && status.ready {
            break;
        }
        if Instant::now() >= deadline {
            return Err(format!("Timed out opening B1 Work: {}", status.phase));
        }
        std::thread::sleep(Duration::from_millis(2));
    }
    app.insert_resource(TimeUpdateStrategy::ManualDuration(Duration::ZERO));
    Ok(app)
}

fn seek(app: &mut App, seconds: f32) -> Result<&World, String> {
    app.world_mut().resource_mut::<Playback>().seek_request = Some(seconds);
    app.update();
    let world = app.world();
    let playback = world.resource::<Playback>();
    if let Some(error) = &playback.error {
        return Err(error.clone());
    }
    if playback.position_seconds != seconds || playback.playing || playback.seek_request.is_some() {
        return Err(format!(
            "B1 did not publish the requested paused frame at {seconds}s"
        ));
    }
    Ok(world)
}

fn frame(app: &mut App, seconds: f32) -> Result<Frame, String> {
    let world = seek(app, seconds)?;
    let geometry = b1_foot_clearance(world)?;
    let clearance = |side| geometry[side].as_f64().ok_or("Clearance value absent");
    Ok(Frame {
        seconds,
        clip: world.resource::<Playback>().active_timeline_id.clone(),
        feet: [clearance("left_cm")?, clearance("right_cm")?],
        geometry,
    })
}

fn rounded(value: f64) -> f64 {
    (value * 100_000.0).round() / 100_000.0 + 0.0
}

fn intervals(frames: &[Frame], side: usize, matches: impl Fn(f64) -> bool) -> Vec<[f64; 2]> {
    let mut output = Vec::new();
    let mut first = None;
    for (i, frame) in frames.iter().enumerate() {
        if matches(frame.feet[side]) {
            first.get_or_insert(frame.seconds);
        } else if let Some(start) = first.take() {
            output.push([
                rounded(f64::from(start)),
                rounded(f64::from(frames[i - 1].seconds)),
            ]);
        }
    }
    if let Some(start) = first {
        output.push([
            rounded(f64::from(start)),
            rounded(f64::from(frames.last().unwrap().seconds)),
        ]);
    }
    output
}

fn sample_times(start: f64, end: f64, step: f64) -> Result<Vec<f32>, CoreError> {
    let endpoint = end as f32;
    let mut times = Vec::new();
    for index in 0..MAX_SAMPLES {
        let time = (start + index as f64 * step) as f32;
        if time >= endpoint {
            times.push(endpoint);
            return Ok(times);
        }
        if times.last() != Some(&time) {
            times.push(time);
        }
    }
    Err(CoreError::new(
        "motion_query_range",
        format!("At most {MAX_SAMPLES} regular samples per query"),
    ))
}

struct QueryRequest<'a> {
    path: &'a Path,
    assets: &'a str,
    start: f64,
    end: f64,
    step: f64,
    expand: bool,
}

fn query_request<'a>(
    args: &'a [String],
    usage: &str,
    range_code: &str,
) -> Result<QueryRequest<'a>, CoreError> {
    let [path, assets, start, end, step, rest @ ..] = args else {
        return Err(CoreError::new("usage", usage));
    };
    let expand = match rest {
        [] => false,
        [flag] if flag == "--samples" => true,
        _ => return Err(CoreError::new("usage", usage)),
    };
    let number = |text: &str| {
        text.parse::<f64>()
            .ok()
            .filter(|value| value.is_finite())
            .ok_or_else(|| CoreError::new(range_code, "Times must be finite numbers"))
    };
    Ok(QueryRequest {
        path: Path::new(path),
        assets,
        start: number(start)?,
        end: number(end)?,
        step: number(step)?,
        expand,
    })
}

impl QueryRequest<'_> {
    fn times(
        &self,
        range_end: f64,
        duration: f64,
        range_code: &str,
    ) -> Result<Vec<f32>, CoreError> {
        let Self {
            start, end, step, ..
        } = *self;
        if start < 0.0 || end < start || range_end > duration || step < 0.001 {
            return Err(CoreError::new(
                range_code,
                format!("Require 0 <= start <= end <= {duration}s and step >= 0.001s"),
            ));
        }
        sample_times(start, end, step).map_err(|error| CoreError::new(range_code, error.message))
    }
}

pub(super) fn run(args: &[String]) -> Result<Value, CoreError> {
    let request = query_request(args, super::MOTION_QUERY_USAGE, "motion_query_range")?;
    let raw = super::read(request.path)?;
    let work = SceneDocument::from_json(&raw)?;
    if !super::supports_motion_query(&work) {
        return Err(CoreError::new(
            "motion_query_unsupported_work",
            "Motion query supports finite B1 rehearsal timelines",
        ));
    }
    let sha256 = appearance_sha256(raw.as_bytes());
    let duration = f64::from(work.timeline_duration_seconds());
    let times = request.times(
        f64::from(request.end as f32),
        duration,
        "motion_query_range",
    )?;
    let QueryRequest {
        assets,
        start,
        end,
        step,
        expand,
        ..
    } = request;
    let revision = work.revision;
    let mut boundaries: Vec<f32> = work
        .timeline
        .iter()
        .map(|clip| clip.start_seconds)
        .filter(|time| *time > start as f32 && *time <= end as f32)
        .collect();
    boundaries.sort_by(f32::total_cmp);
    let failure = |message| CoreError::new("motion_query_failed", message);
    let mut app = headless_app(assets, work).map_err(failure)?;
    let mut frames = Vec::with_capacity(times.len());
    for seconds in times {
        frames.push(frame(&mut app, seconds).map_err(failure)?);
    }
    let mut anomalies = Vec::new();
    let mut feet = serde_json::Map::new();
    for (side, name) in ["left", "right"].into_iter().enumerate() {
        for [first, last] in intervals(&frames, side, |cm| cm < BELOW_CM) {
            anomalies.push(json!({"kind":"below_floor","foot":name,"start_s":first,"end_s":last}));
        }
        let min = frames
            .iter()
            .map(|row| row.feet[side])
            .fold(f64::INFINITY, f64::min);
        let max = frames
            .iter()
            .map(|row| row.feet[side])
            .fold(f64::NEG_INFINITY, f64::max);
        feet.insert(
            name.into(),
            json!({
                "min_cm":rounded(min),"max_cm":rounded(max),
                "near_floor_s":intervals(&frames, side, |cm| (BELOW_CM..=NEAR_CM).contains(&cm))
            }),
        );
    }
    let mut boundary_rows = Vec::new();
    for seconds in boundaries {
        let before = frame(&mut app, seconds.next_down()).map_err(failure)?;
        let after = frame(&mut app, seconds).map_err(failure)?;
        let delta = [
            after.feet[0] - before.feet[0],
            after.feet[1] - before.feet[1],
        ];
        for (side, name) in ["left", "right"].into_iter().enumerate() {
            if delta[side].abs() > JUMP_CM {
                anomalies.push(json!({"kind":"boundary_clearance_jump","foot":name,
                    "start_s":rounded(f64::from(seconds)),"end_s":rounded(f64::from(seconds)),
                    "delta_cm":rounded(delta[side])}));
            }
        }
        boundary_rows.push(
            json!({"at_s":rounded(f64::from(seconds)), "from":before.clip,
            "to":after.clip,"delta_cm":{"left":rounded(delta[0]),"right":rounded(delta[1])}}),
        );
    }
    let mut result = json!({
        "schema_version":1,"work":{"revision":revision,"sha256":sha256},
        "sampling":{"start_s":start,"end_s":end,"step_s":step,"count":frames.len(),
            "boundary_count":boundary_rows.len(),"boundary_method":"previous_representable_f32_second_and_exact_start"},
        "method":"visible_b1_body_foot_min_stage_y","floor_y_m":0,
        "thresholds_cm":{"near_floor_max":NEAR_CM,"below_floor":BELOW_CM,"boundary_jump_abs":JUMP_CM},
        "feet":feet,"boundaries":boundary_rows,"anomalies":anomalies,
        "scope":"sampled geometry; no force, shoe or visual judgement",
    });
    if expand {
        result["samples"] = json!(
            frames
                .iter()
                .map(|row| json!({
                    "t_s":row.seconds,"timeline_id":row.clip,"geometry":row.geometry,
                }))
                .collect::<Vec<_>>()
        );
    }
    Ok(result)
}

struct TravelFrame {
    seconds: f32,
    source_seconds: f64,
    timeline_id: String,
    origins: [[f64; 3]; 2],
}

// Use the Work's serialized precision for public timestamps, including query bounds.
fn work_seconds(seconds: f32) -> f64 {
    seconds.to_string().parse().expect("finite Work timestamp")
}

impl TravelFrame {
    fn value(&self) -> Value {
        json!({
            "t_s": work_seconds(self.seconds),
            "source_t_s": self.source_seconds,
            "timeline_id": self.timeline_id,
            "positions_metres": {"body": self.origins[0], "garment": self.origins[1]},
        })
    }
}

fn travel_frame(app: &mut App, seconds: f32) -> Result<TravelFrame, String> {
    let world = seek(app, seconds)?;
    let publication = b1_running_observation(world)?;
    // The running publication validates the actual matrices in body, garment order.
    // These are column-major stage transforms. The final column contains xyz.
    let matrices: [[f64; 16]; 2] =
        serde_json::from_value(publication["display_transforms"].clone())
            .map_err(|error| error.to_string())?;
    let source_seconds = publication["resolved"]["source_seconds"]
        .as_f64()
        .ok_or("Running publication missing source time")?;
    Ok(TravelFrame {
        seconds,
        source_seconds,
        timeline_id: world.resource::<Playback>().active_timeline_id.clone(),
        origins: matrices.map(|matrix| [matrix[12], matrix[13], matrix[14]]),
    })
}

pub(super) fn run_travel(args: &[String]) -> Result<Value, CoreError> {
    let request = query_request(args, super::TRAVEL_QUERY_USAGE, "travel_query_range")?;
    let raw = super::read(request.path)?;
    let work = SceneDocument::from_json(&raw)?;
    if !super::supports_travel_query(&work) {
        return Err(CoreError::new(
            "travel_query_unsupported_work",
            "Travel query requires a finite B1 running timeline at a stage presentation scale of 0.001 through 100",
        ));
    }
    // Validate the requested time against the public decimal endpoint. The
    // runtime still seeks at f32 precision after the request passes that check.
    let duration = work_seconds(work.timeline_duration_seconds());
    let times = request.times(request.end, duration, "travel_query_range")?;
    let revision = work.revision;
    let failure = |message| CoreError::new("travel_query_failed", message);
    let mut app = headless_app(request.assets, work).map_err(failure)?;
    let frames = times
        .into_iter()
        .map(|seconds| travel_frame(&mut app, seconds).map_err(failure))
        .collect::<Result<Vec<_>, _>>()?;
    let first = frames.first().expect("at least one sample");
    let last = frames.last().expect("at least one sample");
    let displacement = |part: usize| {
        std::array::from_fn::<_, 3, _>(|axis| last.origins[part][axis] - first.origins[part][axis])
    };
    let mut result = json!({
        "schema_version": 1,
        "work": {"revision": revision, "sha256": appearance_sha256(raw.as_bytes())},
        "sampling": {"start_s": request.start, "end_s": request.end, "step_s": request.step,
                     "count": frames.len()},
        "method": "production_b1_body_and_garment_display_origins",
        "space": "stage_world_xyz",
        "axes": {"up": "+Y", "forward": "+Z"},
        "start": first.value(),
        "end": last.value(),
        "displacement_metres": {"body": displacement(0), "garment": displacement(1)},
    });
    if request.expand {
        result["samples"] = json!(frames.iter().map(TravelFrame::value).collect::<Vec<_>>());
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exact_decimal_endpoint_fits_the_sample_cap() {
        let times = sample_times(0.141, 0.341, 0.001).unwrap();
        assert_eq!(times.len(), MAX_SAMPLES);
        assert_eq!(times.first().copied(), Some(0.141));
        assert_eq!(times.last().copied(), Some(0.341));
        assert!(sample_times(0.141, 0.3415, 0.001).is_err());
    }
}

//! One-shot Web preview of an unchanged B1 Work through the production Studio.
#[cfg(any(target_arch = "wasm32", test))]
use nvwa_core::SceneDocument;
#[cfg(any(target_arch = "wasm32", test))]
use nvwa_runtime::{AppearanceStatus, EditorState, Playback, RuntimeStatus};

#[cfg(any(target_arch = "wasm32", test))]
fn validate_request(raw_work: &str, seconds: f32) -> Result<SceneDocument, String> {
    let document = SceneDocument::from_json(raw_work).map_err(|error| error.to_string())?;
    if !document.profile.backend.is_b1() {
        return Err("Preview supports the existing B1 backend only".into());
    }
    let end = document.timeline_duration_seconds();
    if !seconds.is_finite() || !(0.0..=end).contains(&seconds) {
        return Err(format!(
            "Preview seconds must be finite and between 0 and {end}; static Works support only 0"
        ));
    }
    Ok(document)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[cfg(any(target_arch = "wasm32", test))]
enum Phase {
    Loading,
    Seeking,
    Settling,
    AwaitingCallback,
    Rendered,
    Failed,
}

#[cfg(any(target_arch = "wasm32", test))]
impl Phase {
    fn captured(&mut self) -> bool {
        if *self != Self::AwaitingCallback {
            return false;
        }
        *self = Self::Rendered;
        true
    }
}

#[cfg(any(target_arch = "wasm32", test))]
fn request_error<'a>(
    phase: Phase,
    expected: &SceneDocument,
    editor: &'a EditorState,
    runtime: &'a RuntimeStatus,
    appearance: &'a AppearanceStatus,
    playback: &'a Playback,
) -> Option<&'a str> {
    let immediate = editor
        .open_error
        .as_deref()
        .or(runtime.error.as_deref())
        .or(runtime.stage_error.as_deref())
        .or(playback.error.as_deref());
    if immediate.is_some() {
        return immediate;
    }
    // Appearance cannot bind before the initial B1 Open commits. Defer only
    // that typed startup state; never clear errors or match their wording.
    if phase == Phase::Loading
        && editor.document().is_none()
        && editor.pending_open.as_ref() == Some(expected)
    {
        return None;
    }
    runtime
        .appearance_error
        .as_deref()
        .or(appearance.error.as_deref())
}

#[cfg(target_arch = "wasm32")]
mod web {
    use super::{Phase, request_error, validate_request};
    use bevy::{
        prelude::*,
        render::view::screenshot::{Screenshot, ScreenshotCaptured},
        window::{PrimaryWindow, WindowResolution},
    };
    use nvwa_core::{SceneDocument, appearance_sha256};
    use nvwa_runtime::{
        AppearanceStatus, EditorState, Playback, RuntimeStatus, SceneCamera, StageViewOverride,
        StartupDocumentPolicy, b1_foot_clearance, b1_frame_snapshot,
    };
    use serde_json::{Value, json};
    use wasm_bindgen::prelude::*;

    const WIDTH: u32 = 1280;
    const HEIGHT: u32 = 720;
    const TIMEOUT_SECONDS: f64 = 60.0;

    thread_local! {
        static STARTED: std::cell::Cell<bool> = const { std::cell::Cell::new(false) };
    }

    #[derive(Clone, Debug, PartialEq)]
    struct FrameIdentity {
        file_context: (u64, u64),
        clip_id: String,
        timeline_id: String,
        completed: bool,
        camera_entity: Entity,
        camera_transform: [f32; 16],
        camera_projection: [f32; 16],
        camera_sub_view: String,
        camera_viewport: String,
        width: u32,
        height: u32,
        scale_factor: f32,
    }

    #[derive(Resource)]
    struct Preview {
        expected: SceneDocument,
        work_sha256: String,
        seconds: f32,
        started: f64,
        phase: Phase,
        identity: Option<FrameIdentity>,
        stable_frames: u8,
        capture_entity: Option<Entity>,
        callback_size: Option<(u32, u32)>,
        published: bool,
    }

    fn status_element() -> Result<web_sys::Element, JsValue> {
        web_sys::window()
            .and_then(|window| window.document())
            .and_then(|document| document.get_element_by_id("preview-status"))
            .ok_or_else(|| JsValue::from_str("Missing pre#preview-status"))
    }

    fn write_status(value: Value) {
        if let Ok(element) = status_element() {
            element.set_text_content(Some(&value.to_string()));
        }
    }

    fn receipt(
        preview: &Preview,
        status: &str,
        error: Option<&str>,
        foot_clearance: Value,
    ) -> Value {
        json!({
            "schema_version": 1,
            "status": status,
            "work_sha256": preview.work_sha256,
            "document_revision": preview.expected.revision,
            "seconds": preview.seconds,
            "camera": preview.expected.stage.camera,
            "playing": false,
            "capture_callback": preview.callback_size.is_some(),
            "physical_width": WIDTH,
            "physical_height": HEIGHT,
            "scale_factor": 1.0,
            "foot_clearance": foot_clearance,
            "error": error,
        })
    }

    fn fail(preview: &mut Preview, error: &str) {
        preview.phase = Phase::Failed;
        write_status(receipt(preview, "failed", Some(error), Value::Null));
    }

    fn launch_query() -> Result<(), JsValue> {
        let window = web_sys::window().ok_or_else(|| JsValue::from_str("No browser window"))?;
        let query = web_sys::UrlSearchParams::new_with_str(&window.location().search()?)?;
        if query.get_all("player").length() != 1
            || query.get("player").as_deref() != Some("1")
            || query.has("work")
            || query.has("benchmark")
        {
            return Err(JsValue::from_str(
                "Preview requires ?player=1 without work or benchmark launch queries",
            ));
        }
        Ok(())
    }

    /// The bootstrap supplies the exact fetched UTF-8 Work. This entry starts once.
    #[wasm_bindgen]
    pub fn start_preview(raw_work: &str, seconds: f32) -> Result<(), JsValue> {
        if STARTED.with(|started| started.get()) {
            return Err(JsValue::from_str("This preview has already started"));
        }
        launch_query()?;
        let element = status_element()?;
        let expected =
            validate_request(raw_work, seconds).map_err(|error| JsValue::from_str(&error))?;
        let mut app = nvwa_studio::build_app();
        app.insert_resource(StartupDocumentPolicy::WaitForOpen);
        app.world_mut()
            .resource_mut::<EditorState>()
            .request_open(expected.clone())
            .map_err(|error| JsValue::from_str(&error))?;
        let mut windows = app
            .world_mut()
            .query_filtered::<&mut Window, With<PrimaryWindow>>();
        let mut window = windows
            .single_mut(app.world_mut())
            .map_err(|error| JsValue::from_str(&format!("Preview window: {error}")))?;
        window.resolution = WindowResolution::new(WIDTH, HEIGHT).with_scale_factor_override(1.0);
        window.fit_canvas_to_parent = false;
        window.resizable = false;
        app.insert_resource(bevy::winit::WinitSettings::continuous());
        app.insert_resource(Preview {
            expected,
            work_sha256: appearance_sha256(raw_work.as_bytes()),
            seconds,
            started: js_sys::Date::now() / 1000.0,
            phase: Phase::Loading,
            identity: None,
            stable_frames: 0,
            capture_entity: None,
            callback_size: None,
            published: false,
        });
        app.add_systems(Last, drive);
        element.set_text_content(None);
        STARTED.with(|started| started.set(true));
        app.run();
        Ok(())
    }

    fn current_frame(world: &mut World, preview: &Preview) -> Result<FrameIdentity, String> {
        let editor = world.resource::<EditorState>();
        if editor.document() != Some(&preview.expected)
            || editor.pending_open.is_some()
            || editor.preview.is_some()
        {
            return Err(
                "Requested committed Work changed or another Open/preview is active".into(),
            );
        }
        let view = world.resource::<StageViewOverride>();
        if view.camera(editor) != Some(&preview.expected.stage.camera) {
            return Err("Preview camera differs from the saved Work camera".into());
        }
        let playback = world.resource::<Playback>();
        if playback.playing
            || playback.seek_request.is_some()
            || playback.position_seconds != preview.seconds
        {
            return Err("Published paused playback differs from the requested seconds".into());
        }
        let file_context = editor.file_context_identity();
        let clip_id = playback.clip_id.clone();
        let timeline_id = playback.active_timeline_id.clone();
        let completed = playback.completed;
        let mut windows = world.query_filtered::<&Window, With<PrimaryWindow>>();
        let window = windows
            .single(world)
            .map_err(|error| format!("Preview window: {error}"))?;
        let (width, height, scale_factor) = (
            window.physical_width(),
            window.physical_height(),
            window.scale_factor(),
        );
        if (width, height) != (WIDTH, HEIGHT) || scale_factor != 1.0 {
            return Err("Preview physical window changed from 1280x720 at scale 1".into());
        }
        let mut cameras =
            world.query_filtered::<(Entity, &Camera, &GlobalTransform), With<SceneCamera>>();
        let (camera_entity, camera, transform) = cameras
            .single(world)
            .map_err(|error| format!("Preview scene camera: {error}"))?;
        if !camera.is_active {
            return Err("Preview scene camera is inactive".into());
        }
        Ok(FrameIdentity {
            file_context,
            clip_id,
            timeline_id,
            completed,
            camera_entity,
            camera_transform: transform.to_matrix().to_cols_array(),
            camera_projection: camera.clip_from_view().to_cols_array(),
            camera_sub_view: format!("{:?}", camera.sub_camera_view),
            camera_viewport: format!("{:?}", camera.viewport),
            width,
            height,
            scale_factor,
        })
    }

    fn drive(world: &mut World) {
        // Remove only during this exclusive system, so resource reads stay simple.
        let mut preview = world
            .remove_resource::<Preview>()
            .expect("Preview resource is installed");
        update(world, &mut preview);
        world.insert_resource(preview);
    }

    fn update(world: &mut World, preview: &mut Preview) {
        if preview.phase == Phase::Failed {
            return;
        }
        if !preview.published && js_sys::Date::now() / 1000.0 - preview.started > TIMEOUT_SECONDS {
            fail(preview, "Preview exceeded the 60 second deadline");
            return;
        }
        let editor = world.resource::<EditorState>();
        let runtime = world.resource::<RuntimeStatus>();
        let appearance = world.resource::<AppearanceStatus>();
        let playback = world.resource::<Playback>();
        let error = request_error(
            preview.phase,
            &preview.expected,
            editor,
            runtime,
            appearance,
            playback,
        );
        if let Some(error) = error {
            fail(preview, error);
            return;
        }
        let ready = runtime.ready && appearance.ready && !appearance.pending;
        if preview.phase == Phase::Loading {
            if editor.preview.is_some() {
                fail(preview, "An editor preview replaced the requested Work");
                return;
            }
            if let Some(document) = editor.document()
                && document != &preview.expected
            {
                fail(
                    preview,
                    "A different Work was committed during preview loading",
                );
                return;
            }
            if let Some(document) = editor.pending_open.as_ref()
                && document != &preview.expected
            {
                fail(preview, "A different Open replaced the requested Work");
                return;
            }
            if !ready || editor.document().is_none() || editor.pending_open.is_some() {
                return;
            }
            // Open publishes at zero and resets transport. Seek only after it commits.
            let mut playback = world.resource_mut::<Playback>();
            playback.playing = false;
            // Schema-1 B1 is static and has no seek consumer. Open already
            // published its only supported time (zero); retain that real frame.
            if preview.expected.profile.backend.is_b1_motion() {
                playback.seek_request = Some(preview.seconds);
            }
            preview.phase = Phase::Seeking;
            return;
        }
        if !ready {
            fail(
                preview,
                "Runtime or appearance lost readiness during preview capture",
            );
            return;
        }
        if preview.phase == Phase::Seeking && playback.seek_request.is_some() {
            return;
        }
        let identity = match current_frame(world, preview) {
            Ok(identity) => identity,
            Err(error) => {
                fail(preview, &error);
                return;
            }
        };
        match preview.phase {
            Phase::Seeking => {
                preview.identity = Some(identity);
                preview.stable_frames = 1;
                preview.phase = Phase::Settling;
            }
            Phase::Settling => {
                if preview.identity.as_ref() == Some(&identity) {
                    preview.stable_frames += 1;
                } else {
                    preview.identity = Some(identity);
                    preview.stable_frames = 1;
                }
                if preview.stable_frames >= 3 {
                    preview.phase = Phase::AwaitingCallback;
                    preview.capture_entity = Some(
                        world
                            .spawn(Screenshot::primary_window())
                            .observe(captured)
                            .id(),
                    );
                }
            }
            Phase::AwaitingCallback | Phase::Rendered => {
                if preview.identity.as_ref() != Some(&identity) {
                    fail(
                        preview,
                        "Work, transport, camera or dimensions changed during capture",
                    );
                    return;
                }
                if preview.phase == Phase::Rendered && !preview.published {
                    let clearance = if preview.expected.profile.backend.is_b1_motion() {
                        match b1_frame_snapshot(world).and_then(|_| b1_foot_clearance(world)) {
                            Ok(value) => value,
                            Err(error) => {
                                fail(preview, &format!("Foot clearance: {error}"));
                                return;
                            }
                        }
                    } else {
                        Value::Null
                    };
                    write_status(receipt(preview, "rendered", None, clearance));
                    preview.published = true;
                }
            }
            Phase::Loading | Phase::Failed => unreachable!(),
        }
    }

    fn captured(capture: On<ScreenshotCaptured>, mut preview: ResMut<Preview>) {
        if preview.phase != Phase::AwaitingCallback
            || preview.capture_entity != Some(capture.entity)
        {
            return;
        }
        let size = capture.image.texture_descriptor.size;
        if (size.width, size.height) != (WIDTH, HEIGHT)
            || capture.image.data.as_ref().is_none_or(Vec::is_empty)
        {
            fail(
                &mut preview,
                "Screenshot callback returned an empty or incorrectly sized image",
            );
            return;
        }
        preview.callback_size = Some((size.width, size.height));
        preview.phase.captured();
    }
}

#[cfg(not(target_arch = "wasm32"))]
fn main() {
    eprintln!("nvwa-preview is a Web preview entry; build for wasm32 with manual-start");
}

#[cfg(target_arch = "wasm32")]
fn main() {}

#[cfg(test)]
mod tests {
    use super::*;
    use nvwa_core::CharacterProfile;

    fn raw(document: &SceneDocument) -> String {
        document.to_json().unwrap()
    }

    #[test]
    fn static_b1_accepts_only_zero_and_keeps_saved_camera_and_document() {
        let mut document = SceneDocument::from_profile(CharacterProfile::b1()).unwrap();
        document.stage.camera = nvwa_core::StageCamera::detail();
        let json = raw(&document);
        assert_eq!(validate_request(&json, 0.0).unwrap(), document);
        assert!(
            validate_request(&json, 0.01)
                .unwrap_err()
                .contains("static Works")
        );
    }

    #[test]
    fn motion_accepts_endpoints_and_rejects_nonfinite_negative_or_out_of_range_time() {
        let document = SceneDocument::from_profile(CharacterProfile::b1_motion()).unwrap();
        let json = raw(&document);
        let end = document.timeline_duration_seconds();
        assert!(end > 0.0);
        assert_eq!(validate_request(&json, 0.0).unwrap(), document);
        assert_eq!(validate_request(&json, end).unwrap(), document);
        for seconds in [
            f32::NAN,
            f32::INFINITY,
            f32::NEG_INFINITY,
            -0.01,
            end + 0.01,
        ] {
            assert!(
                validate_request(&json, seconds)
                    .unwrap_err()
                    .contains("Preview seconds")
            );
        }
    }

    #[test]
    fn empty_motion_timeline_also_accepts_only_zero() {
        let mut document = SceneDocument::from_profile(CharacterProfile::b1_motion()).unwrap();
        document.timeline.clear();
        let json = raw(&document);
        assert_eq!(validate_request(&json, 0.0).unwrap(), document);
        assert!(validate_request(&json, 1.0).is_err());
    }

    #[test]
    fn glb_and_malformed_work_are_rejected_at_the_shared_boundary() {
        let profile =
            CharacterProfile::from_json(include_str!("../../../assets/character.profile.json"))
                .unwrap();
        let document = SceneDocument::from_profile(profile).unwrap();
        assert!(
            validate_request(&raw(&document), 0.0)
                .unwrap_err()
                .contains("B1 backend")
        );
        for malformed in ["", "{}", "{not json}"] {
            assert!(validate_request(malformed, 0.0).is_err());
        }
    }

    #[test]
    fn only_an_awaited_callback_can_complete_and_late_callbacks_cannot_revive_failure() {
        for initial in [
            Phase::Loading,
            Phase::Seeking,
            Phase::Settling,
            Phase::Rendered,
            Phase::Failed,
        ] {
            let mut phase = initial;
            assert!(!phase.captured());
            assert_eq!(phase, initial);
        }
        let mut phase = Phase::AwaitingCallback;
        assert!(phase.captured());
        assert_eq!(phase, Phase::Rendered);
        phase = Phase::Failed;
        assert!(!phase.captured());
        assert_eq!(phase, Phase::Failed);
    }

    #[test]
    fn appearance_errors_wait_only_for_the_exact_initial_pending_open() {
        let expected = SceneDocument::from_profile(CharacterProfile::b1_motion()).unwrap();
        let mut editor = EditorState::default();
        editor.request_open(expected.clone()).unwrap();
        let mut runtime = RuntimeStatus {
            appearance_error: Some("projected appearance error".into()),
            ..Default::default()
        };
        let appearance = AppearanceStatus {
            error: Some("direct appearance error".into()),
            ..Default::default()
        };
        let playback = Playback::default();
        let error = |phase, editor: &EditorState, runtime: &RuntimeStatus| {
            request_error(phase, &expected, editor, runtime, &appearance, &playback)
                .map(str::to_owned)
        };
        assert_eq!(error(Phase::Loading, &editor, &runtime), None);
        assert_eq!(
            error(Phase::Seeking, &editor, &runtime).as_deref(),
            Some("projected appearance error")
        );
        let mut wrong = expected.clone();
        wrong.stage.camera = nvwa_core::StageCamera::detail();
        editor.request_open(wrong).unwrap();
        assert_eq!(
            error(Phase::Loading, &editor, &runtime).as_deref(),
            Some("projected appearance error")
        );
        editor.cancel_pending_open();
        assert_eq!(
            error(Phase::Loading, &editor, &runtime).as_deref(),
            Some("projected appearance error")
        );
        editor.replace(expected.clone()).unwrap();
        assert_eq!(
            error(Phase::Loading, &editor, &runtime).as_deref(),
            Some("projected appearance error")
        );
        runtime.appearance_error = None;
        assert_eq!(
            error(Phase::Loading, &editor, &runtime).as_deref(),
            Some("direct appearance error")
        );
    }

    #[test]
    fn initial_pending_open_never_defers_open_runtime_stage_or_playback_errors() {
        let expected = SceneDocument::from_profile(CharacterProfile::b1_motion()).unwrap();
        for source in 0..4 {
            let mut editor = EditorState::default();
            editor.request_open(expected.clone()).unwrap();
            let mut runtime = RuntimeStatus::default();
            let mut playback = Playback::default();
            match source {
                0 => editor.open_error = Some("immediate error".into()),
                1 => runtime.error = Some("immediate error".into()),
                2 => runtime.stage_error = Some("immediate error".into()),
                3 => playback.error = Some("immediate error".into()),
                _ => unreachable!(),
            }
            let appearance = AppearanceStatus {
                error: Some("startup appearance error".into()),
                ..Default::default()
            };
            assert_eq!(
                request_error(
                    Phase::Loading,
                    &expected,
                    &editor,
                    &runtime,
                    &appearance,
                    &playback,
                ),
                Some("immediate error"),
            );
        }
    }
}

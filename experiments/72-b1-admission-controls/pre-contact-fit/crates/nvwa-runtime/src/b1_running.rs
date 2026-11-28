//! Exact running profile: frozen source interpolation and coherent publication.
use super::*;
use bevy::math::DVec4;
use nvwa_b1_adapter::BoneRotation;
use nvwa_core::{B1_RUN_CLIP_ID, running::ResolvedRunning};
use serde_json::{Value, json, value::RawValue};
use std::sync::OnceLock;

const CONTROL_DATA: &str = include_str!("b1_running_controls.json");
struct Key {
    q: Vec<DVec4>,
    tangent: Vec<DVec4>,
}
pub(super) struct RunningBuffers {
    positions: Vec<[f32; 3]>,
    normals: Vec<[f32; 3]>,
    tangents: Vec<[f32; 4]>,
}
pub(super) fn capture_buffers(
    world: &World,
    active: &Session,
) -> Result<Vec<RunningBuffers>, String> {
    use bevy::mesh::VertexAttributeValues;
    active
        .display_meshes
        .iter()
        .map(|h| {
            let mesh = world
                .resource::<Assets<Mesh>>()
                .get(h)
                .ok_or("running mesh absent")?;
            let positions = match mesh.attribute(Mesh::ATTRIBUTE_POSITION) {
                Some(VertexAttributeValues::Float32x3(v)) => v.clone(),
                _ => return Err("running positions absent".into()),
            };
            let normals = match mesh.attribute(Mesh::ATTRIBUTE_NORMAL) {
                Some(VertexAttributeValues::Float32x3(v)) => v.clone(),
                _ => return Err("running normals absent".into()),
            };
            let tangents = match mesh.attribute(Mesh::ATTRIBUTE_TANGENT) {
                Some(VertexAttributeValues::Float32x4(v)) => v.clone(),
                _ => return Err("running tangents absent".into()),
            };
            Ok(RunningBuffers {
                positions,
                normals,
                tangents,
            })
        })
        .collect()
}
struct Controls {
    bones: Vec<String>,
    keys: Vec<Key>,
}
// Timestamp tokens need correctly rounded decimal parsing before exact grid validation.
// The existing JSON Value parser does not enable its float_roundtrip feature.
fn raw_control_times(source: &str) -> Result<Vec<f64>, String> {
    let root: BTreeMap<String, &RawValue> =
        serde_json::from_str(source).map_err(|e| e.to_string())?;
    let rows: Vec<&RawValue> = serde_json::from_str(
        root.get("frames")
            .ok_or("running source keys absent")?
            .get(),
    )
    .map_err(|e| e.to_string())?;
    if rows.len() != 961 {
        return Err("running source key coverage mismatch".into());
    }
    rows.into_iter()
        .map(|row| {
            let fields: BTreeMap<String, &RawValue> =
                serde_json::from_str(row.get()).map_err(|e| e.to_string())?;
            fields
                .get("seconds")
                .and_then(|raw| raw.get().parse::<f64>().ok())
                .filter(|seconds| seconds.is_finite())
                .ok_or("running source time invalid".to_string())
        })
        .collect()
}
fn parse_controls(source: &str) -> Result<Controls, String> {
    let data: Value = serde_json::from_str(source).map_err(|e| e.to_string())?;
    if data["schema_version"] != 1 || data["sampling_hz"] != 240 || data["duration_seconds"] != 4 {
        return Err("running source header mismatch".into());
    }
    let bones = data["bone_order"]
        .as_array()
        .ok_or("running source bone order absent")?
        .iter()
        .map(|n| {
            n.as_str()
                .map(str::to_owned)
                .ok_or("running bone name invalid".to_string())
        })
        .collect::<Result<Vec<_>, _>>()?;
    let rows = data["frames"]
        .as_array()
        .ok_or("running source keys absent")?;
    if bones.len() != 16 || rows.len() != 961 {
        return Err("running source key coverage mismatch".into());
    }
    let times = raw_control_times(source)?;
    let mut keys = Vec::new();
    for (i, row) in rows.iter().enumerate() {
        if times[i] != i as f64 / 240.0 {
            return Err("running source time mismatch".into());
        }
        let read = |name: &str| -> Result<Vec<DVec4>, String> {
            let values = row[name]
                .as_array()
                .ok_or("running source components absent")?;
            if values.len() != 16 {
                return Err("running source component coverage mismatch".into());
            }
            values
                .iter()
                .map(|v| {
                    let a = v.as_array().ok_or("running quaternion invalid")?;
                    if a.len() != 4 {
                        return Err("running quaternion size invalid".into());
                    }
                    let mut x = [0.0; 4];
                    for j in 0..4 {
                        x[j] = a[j]
                            .as_f64()
                            .filter(|x| x.is_finite())
                            .ok_or("running component nonfinite")?;
                    }
                    Ok(DVec4::from_array(x))
                })
                .collect()
        };
        let q = read("rotations_xyzw")?;
        let tangent = read("tangents_xyzw_per_second")?;
        if q.iter().any(|q| (q.length_squared() - 1.0).abs() > 1e-10) {
            return Err("running key is not unit".into());
        }
        if (i == 0 || i == 960)
            && (q.iter().any(|q| *q != DVec4::W) || tangent.iter().any(|v| *v != DVec4::ZERO))
        {
            return Err("running endpoint contract changed".into());
        }
        keys.push(Key { q, tangent });
    }
    Ok(Controls { bones, keys })
}
fn controls() -> Result<&'static Controls, String> {
    static DATA: OnceLock<Result<Controls, String>> = OnceLock::new();
    DATA.get_or_init(|| parse_controls(CONTROL_DATA))
        .as_ref()
        .map_err(Clone::clone)
}
fn orientation(data: &Controls, bone: usize, seconds: f64) -> (DVec4, DVec4) {
    let index = ((seconds * 240.0).floor() as usize).min(959);
    let u = seconds * 240.0 - index as f64;
    orientation_cell(data, bone, index, u)
}
fn orientation_cell(data: &Controls, bone: usize, index: usize, u: f64) -> (DVec4, DVec4) {
    let h = 1.0 / 240.0;
    let (a, b) = (&data.keys[index], &data.keys[index + 1]);
    let r = a.q[bone] * (2.0 * u.powi(3) - 3.0 * u * u + 1.0)
        + a.tangent[bone] * (h * (u.powi(3) - 2.0 * u * u + u))
        + b.q[bone] * (-2.0 * u.powi(3) + 3.0 * u * u)
        + b.tangent[bone] * (h * (u.powi(3) - u * u));
    let derivative = a.q[bone] * ((6.0 * u * u - 6.0 * u) / h)
        + a.tangent[bone] * (3.0 * u * u - 4.0 * u + 1.0)
        + b.q[bone] * ((-6.0 * u * u + 6.0 * u) / h)
        + b.tangent[bone] * (3.0 * u * u - 2.0 * u);
    let q = r / r.length();
    (q, (derivative - q * q.dot(derivative)) / r.length())
}
pub(super) fn pose(seconds: f64) -> Result<DiagnosticPose, String> {
    if !seconds.is_finite() || !(0.0..=4.0).contains(&seconds) {
        return Err("running source time must be finite within0..4".into());
    }
    let data = controls()?;
    let mut rotations = Vec::with_capacity(16);
    for (i, name) in data.bones.iter().enumerate() {
        let (q, _) = orientation(data, i, seconds);
        if !q.is_finite() {
            return Err("running interpolant normalizer invalid".into());
        }
        let q = Quat::from_xyzw(q.x as f32, q.y as f32, q.z as f32, q.w as f32).normalize();
        let (axis, radians) = q.to_axis_angle();
        rotations.push(BoneRotation {
            bone: name.clone(),
            axis: if radians == 0.0 {
                Vec3::X.to_array()
            } else {
                axis.to_array()
            },
            degrees: radians.to_degrees(),
        });
    }
    Ok(DiagnosticPose {
        pose_id: B1_RUN_CLIP_ID.into(),
        rotations,
    })
}
pub(super) fn placement(
    base: Transform,
    doc: &SceneDocument,
    position: f32,
) -> Result<Transform, String> {
    let resolved = nvwa_core::running::resolve(doc, position).map_err(|e| e.to_string())?;
    let mut placed = base;
    placed.translation *= doc.character.scale;
    placed.scale *= doc.character.scale;
    placed.translation += Vec3::from_array(
        resolved
            .actor_offset_metres
            .map(|v| (v * f64::from(doc.character.scale)) as f32),
    );
    if !placed.to_matrix().is_finite() {
        return Err("running placement is nonfinite".into());
    }
    Ok(placed)
}
pub(super) fn backup_pose(
    world: &World,
    active: &Session,
) -> Result<Vec<(Entity, Transform, GlobalTransform)>, String> {
    active
        .bone_bindings
        .iter()
        .map(|(_, e)| {
            Ok((
                *e,
                *world
                    .get::<Transform>(*e)
                    .ok_or("running bone local absent")?,
                *world
                    .get::<GlobalTransform>(*e)
                    .ok_or("running bone global absent")?,
            ))
        })
        .collect()
}
pub(super) fn restore_pose(world: &mut World, active: &mut Session) {
    if let Some(backup) = active.running_pose_backup.take() {
        for (entity, local, global) in backup {
            if let Ok(mut entity) = world.get_entity_mut(entity) {
                entity.insert((local, global));
            }
        }
    }
}
fn placements(
    world: &World,
    active: &Session,
    doc: &SceneDocument,
    position: f32,
) -> Result<Vec<Transform>, String> {
    validate_structure(world, active)?;
    active
        .displays
        .iter()
        .zip(&active.display_transforms)
        .enumerate()
        .map(|(index, (e, base))| {
            let material = world
                .get::<MeshMaterial3d<StandardMaterial>>(*e)
                .ok_or("running material binding absent")?;
            if world
                .resource::<Assets<StandardMaterial>>()
                .get(&material.0)
                .is_none()
                || (index == 1 && active.materials.get(index) != Some(&material.0))
            {
                return Err("running material destination changed".into());
            }
            if world.get::<Transform>(*e).is_none() || world.get::<GlobalTransform>(*e).is_none() {
                return Err("running display transform destination absent".into());
            }
            placement(*base, doc, position)
        })
        .collect()
}
pub(super) fn prepare_candidate(
    world: &mut World,
    c: &mut Candidate,
) -> Result<crate::appearance::RunningAppearancePlan, String> {
    let s = c.session.as_mut().ok_or("running candidate absent")?;
    for display in &s.displays {
        world.entity_mut(*display).insert(Visibility::Hidden);
    }
    s.running_buffers = capture_buffers(world, s)?;
    candidate_plan(world, c)
}
pub(super) fn candidate_plan(
    world: &World,
    c: &Candidate,
) -> Result<crate::appearance::RunningAppearancePlan, String> {
    let s = c.session.as_ref().ok_or("running candidate absent")?;
    let sample = s
        .last_sample
        .as_ref()
        .ok_or("running candidate sample absent")?;
    let transforms = placements(world, s, &c.document, sample.position)?;
    let mut frame = appearance_frame_for_session(world, s, c.document.revision)?;
    let fit = appearance_fit_for_session(world, s, &frame)?;
    frame.placement = transforms[0].to_matrix();
    if c.is_open {
        frame.generation = world
            .resource::<EditorState>()
            .document_generation
            .saturating_add(1);
    }
    crate::appearance::prepare_running(world, &frame, Some(&fit), &c.document.character.appearance)
}
pub(super) fn commit_candidate(
    world: &mut World,
    s: &Session,
    doc: &SceneDocument,
    plan: crate::appearance::RunningAppearancePlan,
) {
    let position = s.last_sample.as_ref().expect("prepared sample").position;
    for (e, base) in s.displays.iter().zip(&s.display_transforms) {
        let t = placement(*base, doc, position).expect("candidate placement preflighted");
        world
            .entity_mut(*e)
            .insert((t, GlobalTransform::from(t), Visibility::Inherited));
    }
    crate::appearance::commit_running(world, plan);
    // Clear a repaired physical error or an older rejection superseded by the
    // current finite seek fulfilled by this sample. Keep a newer invalid rejection.
    let recovered_error = world.resource::<RuntimeStatus>().error.clone();
    let playback = world.resource::<Playback>();
    let fulfilled_seek = playback
        .seek_request
        .is_some_and(|t| t.is_finite() && requested_position(doc, playback) == position);
    if fulfilled_seek
        || (recovered_error.is_some() && playback.error.as_ref() == recovered_error.as_ref())
    {
        world.resource_mut::<Playback>().error = None;
    }
}
pub(super) fn publish(world: &mut World, runtime: &mut B1Runtime) {
    let Some(active) = runtime
        .active
        .as_mut()
        .filter(|s| s.running && s.pending_sample.is_some())
    else {
        return;
    };
    let result: Result<(), String> = (|| {
        let doc = world
            .resource::<EditorState>()
            .visible_document()
            .ok_or("running Work absent")?
            .clone();
        if !doc.profile.backend.is_b1_running()
            || active.selection != Selection::from_doc(&doc)
            || active.generation != world.resource::<EditorState>().document_generation
        {
            return Err("running publication ownership changed".into());
        }
        let sample = active.pending_sample.as_ref().unwrap();
        let transforms = placements(world, active, &doc, sample.position)?;
        let bones = active
            .rig
            .as_ref()
            .ok_or("running rig absent")?
            .frames(world, active.character)?;
        let frames = active
            .skins
            .iter()
            .map(|skin| skin.evaluate(&bones))
            .collect::<Result<Vec<_>, _>>()?;
        if frames.len() != 2 {
            return Err("running requires both skin buffers".into());
        }
        for handle in &active.display_meshes {
            if world.resource::<Assets<Mesh>>().get(handle).is_none() {
                return Err("running display destination absent".into());
            }
        }
        let mut frame = appearance_frame_for_session(world, active, doc.revision)?;
        frame.bones = bones.clone();
        frame.placement = transforms[0].to_matrix();
        frame.serial = active.serial.saturating_add(1);
        let fit = if crate::appearance::running_needs_fit(world, &frame, &doc.character.appearance)
        {
            Some(appearance_fit_for_session(world, active, &frame)?)
        } else {
            None
        };
        let appearance = crate::appearance::prepare_running(
            world,
            &frame,
            fit.as_ref(),
            &doc.character.appearance,
        )?;
        let published_buffers = frames
            .iter()
            .map(|f| RunningBuffers {
                positions: f.positions.clone(),
                normals: f.normals.clone(),
                tangents: f.tangents.clone(),
            })
            .collect();
        // No fallible operation follows: one exclusive normal publication.
        for (handle, frame) in active.display_meshes.iter().zip(frames) {
            let mut meshes = world.resource_mut::<Assets<Mesh>>();
            let mut mesh = meshes
                .get_mut(handle)
                .expect("preflighted body destination");
            mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, frame.positions);
            mesh.insert_attribute(Mesh::ATTRIBUTE_NORMAL, frame.normals);
            mesh.insert_attribute(Mesh::ATTRIBUTE_TANGENT, frame.tangents);
        }
        for (entity, t) in active.displays.iter().zip(transforms) {
            world
                .entity_mut(*entity)
                .insert((t, GlobalTransform::from(t)));
        }
        crate::appearance::commit_running(world, appearance);
        active.running_buffers = published_buffers;
        active.last_bones = bones;
        active.last_sample = active.pending_sample.take();
        active.serial = active.serial.saturating_add(1);
        active.frame_error = None;
        active.running_pose_backup = None;
        adopt_published_transport(
            &doc,
            &mut world.resource_mut::<Playback>(),
            active.last_sample.as_ref().unwrap(),
        );
        world.resource_mut::<Playback>().error = None;
        world.resource_mut::<RuntimeStatus>().error = None;
        Ok(())
    })();
    if let Err(error) = result {
        restore_pose(world, active);
        {
            let requested = world
                .resource::<EditorState>()
                .visible_document()
                .map(|d| d.character.appearance.clone());
            let mut status = world.resource_mut::<crate::appearance::AppearanceStatus>();
            if let Some(requested) = requested {
                status.requested = requested;
            }
            status.ready = false;
            status.applied = None;
            status.pending = false;
            status.retained = true;
            status.error = Some(error.clone());
        }
        frame_failure(world, active, error);
    } else {
        refresh_active_status(world, runtime);
    }
}
/// Shared cheap binding validation for playback headers and full geometry.
pub(super) fn resolved_binding(
    world: &World,
) -> Result<(&Session, &SceneDocument, ResolvedRunning), String> {
    let runtime = world.resource::<B1Runtime>();
    let active = runtime.active.as_ref().ok_or("running session absent")?;
    let editor = world.resource::<EditorState>();
    let doc = editor.visible_document().ok_or("running Work absent")?;
    if !active.running
        || !doc.profile.backend.is_b1_running()
        || active.frame_error.is_some()
        || active.pending_sample.is_some()
        || editor.pending_open.is_some()
        || active.generation != editor.document_generation
        || active.selection != Selection::from_doc(doc)
    {
        return Err("running frame pending/failed/stale".into());
    }
    validate_structure(world, active)?;
    if !world.resource::<Playback>().position_seconds.is_finite() {
        return Err("running published time nonfinite".into());
    }
    placements(
        world,
        active,
        doc,
        world.resource::<Playback>().position_seconds,
    )?;
    if active.running_buffers.len() != 2 {
        return Err("running published buffers absent".into());
    }
    {
        use bevy::mesh::VertexAttributeValues;
        for (i, (handle, bound)) in active
            .display_meshes
            .iter()
            .zip(&active.running_buffers)
            .enumerate()
        {
            let mesh = world
                .resource::<Assets<Mesh>>()
                .get(handle)
                .ok_or("running mesh absent")?;
            if !matches!(mesh.attribute(Mesh::ATTRIBUTE_POSITION),Some(VertexAttributeValues::Float32x3(v)) if v==&bound.positions)
                || !matches!(mesh.attribute(Mesh::ATTRIBUTE_NORMAL),Some(VertexAttributeValues::Float32x3(v)) if v==&bound.normals)
                || !matches!(mesh.attribute(Mesh::ATTRIBUTE_TANGENT),Some(VertexAttributeValues::Float32x4(v)) if v==&bound.tangents)
                || mesh.indices().map(|i| i.iter().collect::<Vec<_>>())
                    != Some(active.display_indices[i].clone())
            {
                return Err("running body buffers changed since publication".into());
            }
        }
    }
    let binding = active
        .published_binding
        .as_ref()
        .ok_or("running publication binding absent")?;
    let playback = world.resource::<Playback>();
    if !playback.position_seconds.is_finite()
        || binding.document != *doc
        || playback.seek_request.is_some()
        || !super::super::same_transport(playback, &binding.transport)
        || active.last_sample.as_ref() != Some(&frame_sample(doc, playback.position_seconds))
    {
        return Err("running Work/transport changed since publication".into());
    }
    let resolved =
        nvwa_core::running::resolve(doc, playback.position_seconds).map_err(|e| e.to_string())?;
    for ((e, base), bound) in active
        .displays
        .iter()
        .zip(&active.display_transforms)
        .zip(&binding.display_transforms)
    {
        let expected = placement(*base, doc, playback.position_seconds)?.to_matrix();
        let actual = world
            .get::<GlobalTransform>(*e)
            .ok_or("running placement absent")?
            .to_matrix();
        if !actual.abs_diff_eq(expected, 1e-6)
            || actual.to_cols_array() != *bound
            || world
                .get::<Transform>(*e)
                .is_none_or(|t| t.to_matrix() != actual)
        {
            return Err("running actual placement binding changed".into());
        }
    }
    let bones = active
        .rig
        .as_ref()
        .ok_or("running rig absent")?
        .frames(world, active.character)?;
    if bones.len() != active.last_bones.len()
        || bones.iter().zip(&active.last_bones).any(|(a, b)| {
            a.name != b.name
                || a.parent != b.parent
                || a.rest != b.rest
                || a.posed != b.posed
                || a.inverse_bind != b.inverse_bind
                || a.local_rest != b.local_rest
                || a.local_posed != b.local_posed
                || a.skin != b.skin
                || a.canonical_rest != b.canonical_rest
                || a.canonical_posed != b.canonical_posed
                || a.frame_gauge != b.frame_gauge
        })
    {
        return Err("running actual bones changed since publication".into());
    }
    let frame = appearance_frame_for_session(world, active, doc.revision)?;
    crate::appearance::running_observation(world, &frame, &doc.character.appearance, false)?;
    Ok((active, doc, resolved))
}
pub(super) fn observation(world: &World) -> Result<Value, String> {
    static CONTROL_HASH: OnceLock<String> = OnceLock::new();
    let control_hash =
        CONTROL_HASH.get_or_init(|| nvwa_core::appearance_sha256(CONTROL_DATA.as_bytes()));
    let (active, doc, resolved) = resolved_binding(world)?;
    let playback = world.resource::<Playback>();
    if let Some(error) = &playback.error {
        return Err(error.clone());
    }
    let status = world.resource::<RuntimeStatus>();
    if !status.ready
        || status.error.is_some()
        || status.appearance_error.is_some()
        || status.stage_error.is_some()
    {
        return Err("running runtime not ready".into());
    }
    Ok(
        json!({"schema_version":1,"kind":"b1_running_publication","generation":active.generation,"revision":doc.revision,"profile_id":doc.profile.id,"work_sha256":nvwa_core::appearance_sha256(doc.to_json().map_err(|e|e.to_string())?.as_bytes()),"serial":active.serial,"playing":playback.playing,"completed":playback.completed,"position_seconds":playback.position_seconds,"resolved":resolved,"display_transforms":active.published_binding.as_ref().unwrap().display_transforms,"control_sha256":control_hash,"ready":true,"error":null}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn canonical_timestamp_tokens_load_all_961_controls_including_row_25() {
        let times = raw_control_times(CONTROL_DATA).unwrap();
        assert_eq!(times.len(), 961);
        assert_eq!(times[25].to_bits(), (25.0_f64 / 240.0).to_bits());
        assert_eq!(times[25].to_bits(), 0.10416666666666667_f64.to_bits());
        for (i, time) in times.iter().enumerate() {
            assert_eq!(time.to_bits(), (i as f64 / 240.0).to_bits(), "row{i}");
        }
        let parsed = parse_controls(CONTROL_DATA).unwrap();
        assert_eq!(parsed.keys.len(), 961);
        assert_eq!(parsed.bones.len(), 16);
        assert!(pose(0.0).is_ok());
        assert!(pose(times[25]).is_ok());
    }
    #[test]
    fn raw_timestamp_mutations_reject_wrong_missing_nonfinite_and_unordered_rows() {
        // Mutate only one raw timestamp token. Value roundtripping would rewrite
        // unrelated frozen timestamps and invalidate the regression witness.
        const ROW25: &str = "\"seconds\":0.10416666666666667,";
        assert_eq!(CONTROL_DATA.matches(ROW25).count(), 1);
        for raw in [
            "0.10416666666666669",     // adjacent wrong binary64; no tolerance
            "0.1",                     // repeated preceding row / out of order
            "0.10833333333333334",     // following row before its own slot
            "\"0.10416666666666667\"", // strings are not numeric timestamps
            "null",
            "1e400", // valid JSON number, nonfinite binary64
            "NaN",   // invalid JSON/nonfinite token
        ] {
            let changed = CONTROL_DATA.replacen(ROW25, &format!("\"seconds\":{raw},"), 1);
            assert!(
                parse_controls(&changed).is_err(),
                "accepted raw token {raw}"
            );
        }
        let missing = CONTROL_DATA.replacen(ROW25, "\"missing_seconds\":0.10416666666666667,", 1);
        assert!(parse_controls(&missing).is_err());
    }
    #[test]
    fn consumer_uses_frozen_shared_tangents_and_exact_neutral_endpoints() {
        let c = controls().unwrap();
        assert_eq!(c.keys.len(), 961);
        for t in [0.0, 4.0] {
            for b in 0..16 {
                let (q, d) = orientation(c, b, t);
                assert_eq!(q, DVec4::W);
                assert_eq!(d, DVec4::ZERO);
            }
            assert!(pose(t).unwrap().rotations.iter().all(|r| r.degrees == 0.0));
        }
        for k in 1..960 {
            for b in 0..16 {
                let (q, d) = orientation_cell(c, b, k - 1, 1.0);
                let (r, e) = orientation_cell(c, b, k, 0.0);
                assert!((q - r).length() < 1e-12);
                assert!((d - e).length() < 1e-9);
                let actual = pose(k as f64 / 240.0).unwrap().rotations[b].clone();
                let decoded = Quat::from_axis_angle(
                    Vec3::from_array(actual.axis),
                    actual.degrees.to_radians(),
                );
                let key = c.keys[k].q[b];
                let expected =
                    Quat::from_xyzw(key.x as f32, key.y as f32, key.z as f32, key.w as f32)
                        .normalize();
                assert!(decoded.dot(expected).abs() > 1.0 - 1e-6);
            }
        }
        assert!(pose(f64::NAN).is_err());
        assert!(pose(4.01).is_err());
    }
    #[test]
    fn displacement_scale_is_applied_once_to_the_same_base() {
        let d = SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_running()).unwrap();
        let mut scaled = d.clone();
        scaled.character.scale = 1.5;
        let base = Transform::from_xyz(0.0, 0.8, 0.0);
        let a = placement(base, &d, 4.0).unwrap();
        let b = placement(base, &scaled, 4.0).unwrap();
        assert_eq!(a.translation, Vec3::new(0.0, 0.8, 2.0));
        assert!(b.translation.abs_diff_eq(a.translation * 1.5, 1e-6));
    }
}

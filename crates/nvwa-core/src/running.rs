//! Finite running timing and stage-facing travel. No renderer or frame history.
use crate::{B1_RUN_CLIP_ID, CoreError, Result, SceneDocument, TimelineClip};
use serde::Serialize;

pub const SOURCE_SECONDS: f64 = 4.0;
pub const FORWARD_METRES: f64 = 2.0;
pub const SPEED_METRES_PER_SECOND: f64 = FORWARD_METRES / 3.6;

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ResolvedRunning {
    pub clip_id: String,
    pub timeline_id: String,
    pub position_seconds: f32,
    pub source_elapsed_seconds: f64,
    pub source_seconds: f64,
    pub completed_cycles: u64,
    pub anchor_metres: [f64; 3],
    pub source_offset_metres: [f64; 3],
    pub actor_offset_metres: [f64; 3],
}
fn invalid(message: &str) -> CoreError {
    CoreError::new("invalid_running_timeline", message)
}

/// Original source displacement, before character scale. +Z forward, +Y up.
pub fn displacement(clip: &str, source: f64) -> Result<[f64; 3]> {
    if !source.is_finite() {
        return Err(invalid("Running source time must be finite"));
    }
    if matches!(clip, "b1_arm_rehearsal_v1" | "b1_knee_flex_v1") {
        return Ok([0.0; 3]);
    }
    if clip != B1_RUN_CLIP_ID {
        return Err(invalid("Unknown running-profile source clip"));
    }
    let t = source.clamp(0.0, SOURCE_SECONDS);
    let z = if t <= 0.4 {
        let u = t / 0.4;
        SPEED_METRES_PER_SECOND * 0.4 * (u.powi(3) - 0.5 * u.powi(4))
    } else if t <= 3.6 {
        SPEED_METRES_PER_SECOND * (t - 0.2)
    } else {
        let u = (t - 3.6) / 0.4;
        SPEED_METRES_PER_SECOND * 3.4
            + SPEED_METRES_PER_SECOND * 0.4 * (u - u.powi(3) + 0.5 * u.powi(4))
    };
    let y = if (0.4..3.6).contains(&t) {
        let q = ((t - 0.4) / 0.8).rem_euclid(0.5);
        if q <= 0.18 {
            0.0
        } else {
            0.035 * (std::f64::consts::PI * (q - 0.18) / 0.32).sin().powi(2)
        }
    } else {
        0.0
    };
    Ok([0.0, y, z])
}
fn entry_sample(entry: &TimelineClip, wall: f64) -> Result<(f64, f64, u64, [f64; 3])> {
    let elapsed = wall.clamp(0.0, f64::from(entry.duration_seconds)) * f64::from(entry.speed);
    if !elapsed.is_finite() {
        return Err(invalid("Running source elapsed overflow"));
    }
    let (phase, cycles) = if entry.looping {
        let cycles = (elapsed / SOURCE_SECONDS).floor();
        if cycles >= u64::MAX as f64 {
            return Err(invalid("Running cycle count overflow"));
        }
        (elapsed.rem_euclid(SOURCE_SECONDS), cycles as u64)
    } else {
        (elapsed.min(SOURCE_SECONDS), 0)
    };
    let mut offset = displacement(&entry.clip_id, phase)?;
    if cycles > 0 {
        let end = displacement(&entry.clip_id, SOURCE_SECONDS)?;
        offset[0] += cycles as f64 * end[0];
        offset[2] += cycles as f64 * end[2];
    }
    Ok((elapsed, phase, cycles, offset))
}
/// Resolve only from the validated Work and wall time, including gaps and cuts.
pub fn resolve(doc: &SceneDocument, position: f32) -> Result<ResolvedRunning> {
    if !doc.profile.backend.is_b1_running() || !position.is_finite() {
        return Err(invalid("Expected running Work and finite time"));
    }
    let position = position.clamp(0.0, doc.timeline_duration_seconds());
    if doc.timeline.is_empty() {
        return Ok(ResolvedRunning {
            clip_id: String::new(),
            timeline_id: String::new(),
            position_seconds: 0.0,
            source_elapsed_seconds: 0.0,
            source_seconds: 0.0,
            completed_cycles: 0,
            anchor_metres: [0.0; 3],
            source_offset_metres: [0.0; 3],
            actor_offset_metres: [0.0; 3],
        });
    }
    let mut entries = doc.timeline.iter().collect::<Vec<_>>();
    entries.sort_by(|a, b| a.start_seconds.total_cmp(&b.start_seconds));
    let selected = entries
        .iter()
        .rposition(|e| e.start_seconds <= position)
        .unwrap_or(0);
    let mut anchor = [0.0; 3];
    for entry in &entries[..selected] {
        let (_, _, _, end) = entry_sample(entry, f64::from(entry.duration_seconds))?;
        anchor[0] += end[0];
        anchor[2] += end[2];
    }
    let entry = entries[selected];
    let (elapsed, phase, cycles, offset) =
        entry_sample(entry, f64::from(position) - f64::from(entry.start_seconds))?;
    let total = [anchor[0] + offset[0], offset[1], anchor[2] + offset[2]];
    if total.iter().any(|v| {
        !v.is_finite()
            || !(v * f64::from(doc.character.scale)).is_finite()
            || (v * f64::from(doc.character.scale)).abs() > f64::from(f32::MAX)
    }) {
        return Err(invalid("Running placement overflow"));
    }
    Ok(ResolvedRunning {
        clip_id: entry.clip_id.clone(),
        timeline_id: entry.id.clone(),
        position_seconds: position,
        source_elapsed_seconds: elapsed,
        source_seconds: phase,
        completed_cycles: cycles,
        anchor_metres: anchor,
        source_offset_metres: offset,
        actor_offset_metres: total,
    })
}
pub(crate) fn validate(doc: &SceneDocument) -> Result<()> {
    if doc.is_single_loop() {
        return Err(invalid(
            "Running Works require finite arrangements; a start-zero singleton loop is unsupported",
        ));
    }
    resolve(doc, doc.timeline_duration_seconds())?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{B1_V4_ASSET_ID, CharacterBackend, CharacterProfile};
    fn entry(
        id: &str,
        clip: &str,
        start: f32,
        duration: f32,
        speed: f32,
        looping: bool,
    ) -> TimelineClip {
        TimelineClip {
            id: id.into(),
            clip_id: clip.into(),
            start_seconds: start,
            duration_seconds: duration,
            speed,
            looping,
        }
    }
    #[test]
    fn cut_bounce_is_held_in_gap_but_never_accumulated_into_next_action() {
        let mut d = SceneDocument::from_profile(CharacterProfile::b1_running()).unwrap();
        d.timeline = vec![
            entry("a", B1_RUN_CLIP_ID, 0.0, 0.672, 1.0, false),
            entry("b", B1_RUN_CLIP_ID, 1.0, 0.672, 1.0, false),
            entry("c", "b1_arm_rehearsal_v1", 2.0, 4.0, 1.0, false),
        ];
        d.validate().unwrap();
        let gap = resolve(&d, 0.9).unwrap();
        assert!((gap.actor_offset_metres[1] - 0.035).abs() < 1e-6);
        let second = resolve(&d, 1.672).unwrap();
        assert!((second.actor_offset_metres[1] - 0.035).abs() < 1e-6);
        assert!((second.actor_offset_metres[2] - 0.52444444).abs() < 1e-6);
        let arrival = resolve(&d, 2.0).unwrap();
        assert_eq!(arrival.actor_offset_metres[1], 0.0);
        for t in [2.0, 0.9, 1.3, 0.0, 2.0] {
            assert_eq!(
                resolve(&d, t).unwrap(),
                resolve(&SceneDocument::from_json(&d.to_json().unwrap()).unwrap(), t).unwrap()
            );
        }
    }
    #[test]
    fn finite_loops_speed_trim_and_replay_are_not_frame_history() {
        let mut d = SceneDocument::from_profile(CharacterProfile::b1_running()).unwrap();
        d.timeline = vec![
            entry("run", B1_RUN_CLIP_ID, 0.0, 2.0, 2.0, false),
            entry("hold", "b1_arm_rehearsal_v1", 2.0, 4.0, 1.0, false),
        ];
        d.validate().unwrap();
        assert_eq!(
            resolve(&d, 2.0).unwrap().actor_offset_metres,
            [0.0, 0.0, 2.0]
        );
        d.timeline[0].duration_seconds = 3.0;
        d.timeline[0].looping = true;
        d.timeline[1].start_seconds = 3.0;
        d.validate().unwrap();
        let s = resolve(&d, 3.0).unwrap();
        assert!((s.actor_offset_metres[2] - 3.0).abs() < 1e-9);
        assert_eq!(resolve(&d, 0.0).unwrap().actor_offset_metres, [0.0; 3]);
        d.timeline.truncate(1);
        assert!(d.validate().is_err());
        d.timeline[0].looping = false;
        assert!(d.validate().is_ok());
    }
    #[test]
    fn old_serialized_profiles_match_the_existing_work_fixtures() {
        for (raw, profile) in [
            (
                include_str!("../../../examples/b1-diagnostic.nvwa.json"),
                CharacterProfile::b1(),
            ),
            (
                include_str!("../../../examples/b1-character.nvwa.json"),
                CharacterProfile::b1_character(),
            ),
            (
                include_str!("../../../examples/b1-contour.nvwa.json"),
                CharacterProfile::b1_character_contour(),
            ),
            (
                include_str!("../../../examples/b1-character-lower-contour.nvwa.json"),
                CharacterProfile::b1_character_lower_contour(),
            ),
        ] {
            let fixture: serde_json::Value = serde_json::from_str(raw).unwrap();
            assert_eq!(serde_json::to_value(profile).unwrap(), fixture["profile"]);
        }
    }
    #[test]
    fn overflow_and_nonfinite_requests_do_not_create_plausible_placement() {
        let mut d = SceneDocument::from_profile(CharacterProfile::b1_running()).unwrap();
        assert!(resolve(&d, f32::NAN).is_err());
        d.timeline = vec![
            entry("huge", B1_RUN_CLIP_ID, 0.0, 1e30, 1.0, true),
            entry("tail", "b1_arm_rehearsal_v1", 1e30, 4.0, 1.0, false),
        ];
        assert!(d.validate().is_err());
        d = SceneDocument::from_profile(CharacterProfile::b1_running()).unwrap();
        d.character.scale = f32::MAX;
        assert!(d.validate().is_err());
    }
    #[test]
    fn undo_redo_and_reopen_recompute_anchors_from_the_saved_work() {
        use crate::{Command, CommandEnvelope, Editor};
        let initial = SceneDocument::from_profile(CharacterProfile::b1_running()).unwrap();
        let before = resolve(&initial, 2.0).unwrap().actor_offset_metres;
        let mut editor = Editor::new(initial).unwrap();
        let clips = vec![
            entry("run", B1_RUN_CLIP_ID, 0.0, 2.0, 2.0, false),
            entry("tail", "b1_arm_rehearsal_v1", 2.0, 4.0, 1.0, false),
        ];
        for (id, command) in [
            ("edit", Command::SetTimeline { clips }),
            ("undo", Command::Undo),
            ("redo", Command::Redo),
        ] {
            let expected_revision = editor.document().revision;
            editor
                .apply(CommandEnvelope {
                    command_id: id.into(),
                    expected_revision,
                    command,
                })
                .unwrap();
            let offset = resolve(editor.document(), 2.0).unwrap().actor_offset_metres;
            if id == "undo" {
                assert_eq!(offset, before);
            } else {
                assert_eq!(offset, [0.0, 0.0, 2.0]);
            }
        }
        let reopened = SceneDocument::from_json(&editor.document().to_json().unwrap()).unwrap();
        assert_eq!(
            resolve(&reopened, 0.0).unwrap().actor_offset_metres,
            [0.0; 3]
        );
        assert_eq!(
            resolve(&reopened, 2.0).unwrap().actor_offset_metres,
            [0.0, 0.0, 2.0]
        );
    }
    #[test]
    fn identity_is_exact_and_old_catalogues_remain_two_clips() {
        for p in [
            CharacterProfile::b1_motion(),
            CharacterProfile::b1_character(),
            CharacterProfile::b1_character_contour(),
            CharacterProfile::b1_character_lower_contour(),
        ] {
            assert_eq!(
                p.clips.iter().map(|c| c.id.as_str()).collect::<Vec<_>>(),
                ["b1_arm_rehearsal_v1", "b1_knee_flex_v1"]
            );
        }
        assert_eq!(
            CharacterProfile::b1_running().clips[1..],
            CharacterProfile::b1_motion().clips
        );
        let mut p = CharacterProfile::b1_running();
        p.clips[0].duration_seconds = 3.0;
        assert!(p.validate().is_err());
        let bad = CharacterBackend::B1Cpu {
            schema_version: 6,
            asset_id: "wrong".into(),
        };
        assert!(bad.validate().is_err());
        assert!(!bad.is_b1_running());
        assert!(!bad.is_b1_motion());
        assert!(
            CharacterBackend::B1Cpu {
                schema_version: 7,
                asset_id: B1_V4_ASSET_ID.into()
            }
            .validate()
            .is_err()
        );
    }
}

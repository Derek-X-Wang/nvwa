//! A bounded, editable pose sequence for the existing B1 rehearsal rig.
use super::{CoreError, Result, TimelineClip};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub const REFERENCE_CLIP_ID: &str = "b1_reference_motion";
pub const REFERENCE_BONES: &[&str] = &[
    "pelvis",
    "spine_02",
    "spine_03",
    "head",
    "thigh_l",
    "thigh_r",
    "calf_l",
    "calf_r",
    "foot_l",
    "foot_r",
    "ball_l",
    "ball_r",
    "upperarm_l",
    "upperarm_r",
    "lowerarm_l",
    "lowerarm_r",
];

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ReferenceMotion {
    pub duration_seconds: f32,
    pub rotations: BTreeMap<String, RotationTrack>,
    pub pelvis_offsets: Vec<PelvisKey>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RotationTrack {
    pub axis: [f32; 3],
    pub keys: Vec<RotationKey>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RotationKey {
    pub seconds: f32,
    pub degrees: f32,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PelvisKey {
    pub seconds: f32,
    pub offset_metres: [f32; 3],
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ReferencePose {
    pub rotations: Vec<ReferenceRotation>,
    pub pelvis_offset_metres: [f32; 3],
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ReferenceRotation {
    pub bone: String,
    pub axis: [f32; 3],
    pub degrees: f32,
}

fn invalid(message: impl Into<String>) -> CoreError {
    CoreError::new("invalid_reference_motion", message)
}

fn validate_times(times: impl Iterator<Item = f32>, duration: f32) -> Result<()> {
    let mut previous = None;
    let mut count = 0;
    for time in times {
        if !time.is_finite()
            || !(0.0..=duration).contains(&time)
            || previous.map_or(time != 0.0, |p| p >= time)
        {
            return Err(invalid(
                "Keys must start at zero and increase to the duration",
            ));
        }
        previous = Some(time);
        count += 1;
    }
    if !(2..=120).contains(&count) || previous != Some(duration) {
        return Err(invalid(
            "Each track requires 2–120 keys ending at the duration",
        ));
    }
    Ok(())
}

fn interpolate<T, V: Copy>(
    keys: &[T],
    seconds: f32,
    time: impl Fn(&T) -> f32,
    value: impl Fn(&T) -> V,
    blend: impl Fn(V, V, f32) -> V,
) -> V {
    let upper = keys.partition_point(|key| time(key) < seconds);
    let next = &keys[upper];
    if time(next) == seconds {
        return value(next);
    }
    let previous = &keys[upper - 1];
    let fraction = (seconds - time(previous)) / (time(next) - time(previous));
    blend(value(previous), value(next), fraction)
}

impl ReferenceMotion {
    pub(crate) fn validate(&self) -> Result<()> {
        if !(3.0..=5.0).contains(&self.duration_seconds) || self.rotations.is_empty() {
            return Err(invalid(
                "A reference motion requires a 3–5 second duration and rotations",
            ));
        }
        for (bone, track) in &self.rotations {
            if !REFERENCE_BONES.contains(&bone.as_str()) {
                return Err(invalid(format!("Unsupported B1 joint: {bone}")));
            }
            let length_squared: f32 = track.axis.iter().map(|axis| axis * axis).sum();
            if !(0.999..=1.001).contains(&length_squared)
                || track
                    .keys
                    .iter()
                    .any(|key| !(-180.0..=180.0).contains(&key.degrees))
            {
                return Err(invalid(
                    "Rotations require a unit axis and angles from −180 to 180 degrees",
                ));
            }
            validate_times(
                track.keys.iter().map(|key| key.seconds),
                self.duration_seconds,
            )?;
        }
        validate_times(
            self.pelvis_offsets.iter().map(|key| key.seconds),
            self.duration_seconds,
        )?;
        if self.pelvis_offsets.iter().any(|key| {
            key.offset_metres
                .iter()
                .any(|value| !(-0.25..=0.25).contains(value))
        }) {
            return Err(invalid(
                "Pelvis offsets must be within ±0.25 metres per axis",
            ));
        }
        Ok(())
    }

    pub(crate) fn validate_shaped_timeline(&self, clips: &[TimelineClip]) -> Result<()> {
        self.validate()?;
        let [clip] = clips else {
            return Err(invalid(
                "A shaped reference motion requires exactly one timeline entry",
            ));
        };
        super::id(&clip.id, "timeline id")?;
        if clip.clip_id != REFERENCE_CLIP_ID
            || clip.start_seconds != 0.0
            || clip.duration_seconds != self.duration_seconds
            || clip.speed != 1.0
            || clip.looping
        {
            return Err(invalid(
                "The shaped reference clip must start at zero and play the full source once at normal speed",
            ));
        }
        if self.rotations.values().any(|track| {
            track.keys.first().unwrap().degrees != 0.0 || track.keys.last().unwrap().degrees != 0.0
        }) || self.pelvis_offsets.first().unwrap().offset_metres != [0.0; 3]
            || self.pelvis_offsets.last().unwrap().offset_metres != [0.0; 3]
        {
            return Err(invalid(
                "A shaped reference motion must start and end at the fitted neutral pose",
            ));
        }
        Ok(())
    }

    pub(crate) fn clip(&self) -> TimelineClip {
        TimelineClip {
            id: "reference-motion".into(),
            clip_id: REFERENCE_CLIP_ID.into(),
            start_seconds: 0.0,
            duration_seconds: self.duration_seconds,
            speed: 1.0,
            looping: false,
        }
    }

    pub(crate) fn set_rotation_key(
        &mut self,
        bone: &str,
        seconds: f32,
        degrees: f32,
    ) -> Result<()> {
        let key = self
            .rotations
            .get_mut(bone)
            .and_then(|track| track.keys.iter_mut().find(|key| key.seconds == seconds))
            .ok_or_else(|| invalid(format!("No existing key for {bone} at {seconds}s")))?;
        key.degrees = degrees;
        Ok(())
    }

    /// Evaluate an already validated Work at a time within the reference span.
    pub(crate) fn sample(&self, seconds: f32) -> Result<ReferencePose> {
        if !(0.0..=self.duration_seconds).contains(&seconds) {
            return Err(invalid("Query time must be within the reference span"));
        }
        let rotations = self
            .rotations
            .iter()
            .map(|(bone, track)| ReferenceRotation {
                bone: bone.clone(),
                axis: track.axis,
                degrees: interpolate(
                    &track.keys,
                    seconds,
                    |key| key.seconds,
                    |key| key.degrees,
                    |a, b, t| a + ((b - a + 180.0).rem_euclid(360.0) - 180.0) * t,
                ),
            })
            .collect();
        let pelvis_offset_metres = interpolate(
            &self.pelvis_offsets,
            seconds,
            |key| key.seconds,
            |key| key.offset_metres,
            |a, b, t| std::array::from_fn(|i| a[i] + (b[i] - a[i]) * t),
        );
        Ok(ReferencePose {
            rotations,
            pelvis_offset_metres,
        })
    }
}

#[cfg(test)]
mod shaped_tests {
    use super::*;
    use crate::{CharacterProfile, Command, Editor, SceneDocument, running};
    use serde_json::json;

    fn shaped_work() -> SceneDocument {
        let mut work =
            SceneDocument::from_profile(CharacterProfile::b1_character_belly_shape()).unwrap();
        work.profile = CharacterProfile::b1_shaped_motion();
        work.character.profile_id = work.profile.id.clone();
        let motion: ReferenceMotion = serde_json::from_value(json!({
            "duration_seconds": 5,
            "rotations": {"pelvis": {"axis": [0,1,0], "keys": [
                {"seconds":0,"degrees":0},{"seconds":2.5,"degrees":15},{"seconds":5,"degrees":0}
            ]}},
            "pelvis_offsets": [
                {"seconds":0,"offset_metres":[0,0,0]},{"seconds":5,"offset_metres":[0,0,0]}
            ]
        }))
        .unwrap();
        let mut clip = motion.clip();
        clip.id = "pump-stop".into();
        work.timeline = vec![clip];
        work.reference_motion = Some(motion);
        work.validate().unwrap();
        work
    }

    #[test]
    fn shaped_reference_plays_the_complete_named_entry_with_no_stage_travel() {
        let work = shaped_work();
        let restored = SceneDocument::from_json(&work.to_json().unwrap()).unwrap();
        assert_eq!(work, restored);
        for t in [0.0, 2.5, 4.5, 5.0] {
            let resolved = running::resolve(&restored, t).unwrap();
            assert_eq!(resolved.timeline_id, "pump-stop");
            assert_eq!(resolved.clip_id, REFERENCE_CLIP_ID);
            assert_eq!(resolved.source_seconds, f64::from(t));
            assert_eq!(resolved.actor_offset_metres, [0.0; 3]);
        }
        assert_eq!(
            restored.reference_pose_at(2.5).unwrap().rotations[0].degrees,
            15.0
        );
    }

    #[test]
    fn shaped_profile_rejects_unplayable_timelines_and_unsupported_shape_edits() {
        let work = shaped_work();
        let base = serde_json::to_value(&work).unwrap();
        for (field, value) in [
            ("clip_id", json!(crate::B1_SHAPED_STEP_CLIP_ID)),
            ("id", json!(" ")),
            ("looping", json!(true)),
            ("start_seconds", json!(1)),
            ("duration_seconds", json!(2.5)),
            ("speed", json!(2)),
        ] {
            let mut candidate = base.clone();
            candidate["timeline"][0][field] = value;
            assert!(
                SceneDocument::from_json(&candidate.to_string()).is_err(),
                "{field}"
            );
        }
        assert!(SceneDocument::from_profile(CharacterProfile::b1_shaped_motion()).is_err());
        let editor = Editor::new(work).unwrap();
        assert!(
            editor
                .preview(&Command::SetTimeline { clips: vec![] })
                .is_err()
        );
        assert!(
            editor
                .preview(&Command::SetDiagnosticPose {
                    character_id: editor.document().character.id.clone(),
                    pose_id: "shoulder".into()
                })
                .is_err()
        );
        for name in [
            "buttocks_volume",
            "bust_circumference",
            "belly_shape_strength",
        ] {
            let mut candidate = base.clone();
            candidate["character"]["parameters"][name] = json!(0.1);
            assert!(
                SceneDocument::from_json(&candidate.to_string()).is_err(),
                "{name}"
            );
            assert!(
                editor
                    .preview(&Command::SetParameters {
                        character_id: editor.document().character.id.clone(),
                        values: [(name.into(), 0.1)].into(),
                    })
                    .is_err(),
                "{name}"
            );
        }
        for field in [
            "arm_pose_holds",
            "arm_rotation_tracks",
            "shaped_step_distances",
        ] {
            let mut candidate = base.clone();
            candidate[field] = json!({});
            assert!(
                SceneDocument::from_json(&candidate.to_string()).is_err(),
                "{field}"
            );
        }
    }
}

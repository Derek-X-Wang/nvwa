//! Deterministic Nvwa-authored rehearsal. These clips are not AI-generated.
use crate::{BoneRotation, DiagnosticPose};

pub const CLIP_IDS: [&str; 2] = ["b1_arm_rehearsal_v1", "b1_knee_flex_v1"];
pub const DURATION_SECONDS: f32 = 4.0;
/// Fixed authored ankle counteraxis for this admitted rig's canonical rest.
/// L = inverse(calf rest rotation) * foot rest rotation; axis = inverse(L) * X.
/// The two admitted shape parameters leave this lower-leg rest frame unchanged.
/// This is authored motion, not a per-frame contact constraint or IK solver.
pub const KNEE_FOOT_COUNTER_AXIS: [f32; 3] = [0.9686015, -0.0100681, -0.2484144];

/// Canonical Blender bone-local rest-frame rotations. No root motion or IK.
pub fn sample(clip_id: &str, seconds: f32) -> Result<DiagnosticPose, String> {
    if !seconds.is_finite() {
        return Err("motion source time must be finite".into());
    }
    let t = seconds.clamp(0.0, DURATION_SECONDS);
    let amplitude = if t == 0.0 || t == DURATION_SECONDS {
        0.0
    } else {
        (1.0 - (std::f32::consts::TAU * t / DURATION_SECONDS).cos()) * 0.5
    };
    let rotations = match clip_id {
        "b1_arm_rehearsal_v1" => vec![
            BoneRotation {
                bone: "upperarm_l".into(),
                axis: [0.0, 0.0, 1.0],
                degrees: 45.0 * amplitude,
            },
            BoneRotation {
                bone: "lowerarm_l".into(),
                axis: [0.0, 0.0, 1.0],
                degrees: 75.0 * amplitude,
            },
        ],
        "b1_knee_flex_v1" => vec![
            BoneRotation {
                bone: "calf_l".into(),
                axis: [1.0, 0.0, 0.0],
                degrees: 65.0 * amplitude,
            },
            BoneRotation {
                bone: "foot_l".into(),
                axis: KNEE_FOOT_COUNTER_AXIS,
                degrees: -65.0 * amplitude,
            },
        ],
        _ => return Err(format!("unsupported authored motion: {clip_id}")),
    };
    Ok(DiagnosticPose {
        pose_id: clip_id.into(),
        rotations,
    })
}

pub fn contacts(clip_id: &str, seconds: f32) -> Result<(&'static str, &'static str), String> {
    sample(clip_id, seconds)?;
    Ok((
        if clip_id == CLIP_IDS[1] && seconds > 0.0 && seconds < DURATION_SECONDS {
            "moving"
        } else {
            "planted"
        },
        "planted",
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn authored_cycles_have_exact_rest_endpoints_and_admitted_extrema() {
        for id in CLIP_IDS {
            for t in [0.0, 4.0] {
                assert!(
                    sample(id, t)
                        .unwrap()
                        .rotations
                        .iter()
                        .all(|r| r.degrees == 0.0)
                );
            }
        }
        assert_eq!(sample(CLIP_IDS[0], 2.0).unwrap().rotations[0].degrees, 45.0);
        assert_eq!(sample(CLIP_IDS[1], 2.0).unwrap().rotations[0].degrees, 65.0);
        assert!(sample("unknown", 1.0).is_err());
        assert!(sample(CLIP_IDS[0], f32::NAN).is_err());
        assert_eq!(contacts(CLIP_IDS[1], 2.0).unwrap(), ("moving", "planted"));
    }
}

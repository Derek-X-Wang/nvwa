//! Static authored diagnostics in canonical bone-local rest frames.
use crate::DiagnosticPose;
use serde::Deserialize;

/// Exact approved authored pose document; contains no reference mesh or matrices.
pub const DIAGNOSTIC_POSES_JSON: &str = include_str!("poses.json");
pub const DIAGNOSTIC_POSES_SHA256: &str =
    "8e51c044841eb1c6cb96d583ca927cceb51ddf7d0729f4526f61777c8b7adab2";

/// Return an exact authored pose. Unknown IDs are errors, without a neutral fallback.
pub fn diagnostic_pose(pose_id: &str) -> Result<DiagnosticPose, String> {
    #[derive(Deserialize)]
    struct PoseSet {
        poses: Vec<DiagnosticPose>,
    }
    let set: PoseSet = serde_json::from_str(DIAGNOSTIC_POSES_JSON)
        .map_err(|error| format!("invalid packaged diagnostic poses: {error}"))?;
    set.poses
        .into_iter()
        .find(|pose| pose.pose_id == pose_id)
        .ok_or_else(|| format!("unsupported diagnostic pose: {pose_id}"))
}

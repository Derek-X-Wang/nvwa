//! Fit a bounded authored reach to a time-aligned fingertip path.
use super::{headless_app, sample_times, seek, work_seconds};
use bevy::{
    math::{DQuat, DVec3},
    prelude::App,
};
use nvwa_core::{
    Command, CommandEnvelope, CoreError, Editor, SceneDocument, appearance_sha256,
    reference_motion::{REFERENCE_CLIP_ID, RotationKey, RotationTrack},
};
use nvwa_runtime::{B1ContactHand, EditorState, b1_running_index_position};
use serde_json::{Value, json};
use std::path::Path;

const PROBE_DEGREES: f32 = 8.0;
const MAX_CORRECTION_DEGREES: f64 = 24.0;
const MAX_TRACK_KEYS: usize = 120;
const MAX_CONTROLS: usize = 12;

fn failed(message: impl Into<String>) -> CoreError {
    CoreError::new("contact_fit_failed", message)
}

fn range_error(message: impl Into<String>) -> CoreError {
    CoreError::new("contact_fit_range", message)
}

fn fingertip(app: &mut App, seconds: f32, hand: B1ContactHand) -> Result<DVec3, CoreError> {
    let world = seek(app, seconds).map_err(failed)?;
    let position = b1_running_index_position(world, hand)?;
    Ok(DVec3::from_array(position.map(f64::from)))
}

fn source_times(
    work: &SceneDocument,
    times: &[f32],
    editable: bool,
) -> Result<Vec<f32>, CoreError> {
    if !crate::supports_contact_edit(work) {
        return Err(CoreError::new(
            "contact_fit_unsupported_work",
            "Contact fit requires shaped-motion Works with authored reference motion",
        ));
    }
    let first = nvwa_core::running::resolve(work, times[0])?;
    let last = nvwa_core::running::resolve(work, times[times.len() - 1])?;
    if first.clip_id != REFERENCE_CLIP_ID || first.timeline_id != last.timeline_id {
        return Err(range_error(
            "The window must be within one reference clip in each Work",
        ));
    }
    let entry = work
        .timeline
        .iter()
        .find(|clip| clip.id == first.timeline_id)
        .expect("resolved reference clip");
    if times[0] < entry.start_seconds
        || times[times.len() - 1] > entry.start_seconds + entry.duration_seconds
    {
        return Err(range_error(
            "The window must be within one reference clip in each Work",
        ));
    }
    if editable
        && work
            .timeline
            .iter()
            .filter(|clip| clip.clip_id == REFERENCE_CLIP_ID)
            .count()
            > 1
    {
        return Err(CoreError::new(
            "contact_fit_unsupported_work",
            "The edited Work must use the shared reference motion in only one timeline entry",
        ));
    }
    let sources = times
        .iter()
        .map(|&seconds| {
            nvwa_core::running::resolve(work, seconds).map(|sample| sample.source_seconds as f32)
        })
        .collect::<Result<Vec<_>, _>>()?;
    if sources.windows(2).any(|pair| pair[0] >= pair[1]) {
        return Err(range_error(
            "Sample times must be distinct in each reference clip",
        ));
    }
    Ok(sources)
}

fn wrapped_angle(degrees: f32) -> f32 {
    if (-180.0..=180.0).contains(&degrees) {
        degrees
    } else {
        (degrees + 180.0).rem_euclid(360.0) - 180.0
    }
}

#[derive(Clone, Copy, Default)]
struct Response {
    tangent: DVec3,
    radial: DVec3,
    axis: DVec3,
}

impl Response {
    fn measured(base: DVec3, plus: DVec3, minus: DVec3) -> Self {
        let radians = f64::from(PROBE_DEGREES).to_radians();
        let tangent = (plus - minus) / (2.0 * radians.sin());
        let radial = ((plus + minus) * 0.5 - base) / (radians.cos() - 1.0);
        let axis = radial.cross(tangent).normalize_or_zero();
        Self {
            tangent,
            radial,
            axis,
        }
    }

    fn apply(self, distal_delta: DVec3, radians: f64) -> DVec3 {
        let rotated = if self.axis == DVec3::ZERO {
            distal_delta
        } else {
            DQuat::from_axis_angle(self.axis, radians) * distal_delta
        };
        rotated + self.tangent * radians.sin() + self.radial * (radians.cos() - 1.0)
    }
}

fn measure_response(
    app: &mut App,
    work: &SceneDocument,
    bone: &str,
    wall: f32,
    source: f32,
    base: DVec3,
    hand: B1ContactHand,
) -> Result<Response, CoreError> {
    let pose = work.reference_pose_at_source(source)?;
    let degrees = pose
        .rotations
        .iter()
        .find(|rotation| rotation.bone == bone)
        .expect("candidate has an authored rotation")
        .degrees;
    let probe = |app: &mut App, delta| {
        let mut preview = work.clone();
        let motion = preview.reference_motion.as_mut().expect("validated motion");
        // This preview is evaluated only at source. Two original neutral
        // endpoints leave a slot even when the saved track has 120 keys.
        motion.rotations.get_mut(bone).expect("authored bone").keys = vec![
            RotationKey {
                seconds: 0.0,
                degrees: 0.0,
            },
            RotationKey {
                seconds: source,
                degrees: wrapped_angle(degrees + delta),
            },
            RotationKey {
                seconds: motion.duration_seconds,
                degrees: 0.0,
            },
        ];
        app.world_mut().resource_mut::<EditorState>().preview = Some(preview);
        fingertip(app, wall, hand)
    };
    let plus = probe(app, PROBE_DEGREES)?;
    let minus = probe(app, -PROBE_DEGREES)?;
    app.world_mut()
        .resource_mut::<EditorState>()
        .cancel_preview();
    Ok(Response::measured(base, plus, minus))
}

struct Frame {
    wall: f32,
    source: f32,
    base: DVec3,
    goal: DVec3,
    weight: f64,
    basis: Vec<f64>,
    responses: Vec<Response>,
}

fn control_weights(phase: f64, controls: usize) -> Vec<f64> {
    // Uniform cubic basis with a zero-slope fade at the fit boundaries.
    let grid = phase * (controls - 3) as f64;
    let segment = (grid.floor() as usize).min(controls - 4);
    let u = grid - segment as f64;
    let fade_width = 1.0 / (controls - 3) as f64;
    let edge = (phase.min(1.0 - phase) / fade_width).clamp(0.0, 1.0);
    let fade = edge * edge * (3.0 - 2.0 * edge);
    let mut basis = vec![0.0; controls];
    for (index, weight) in [
        (1.0 - u).powi(3),
        3.0 * u.powi(3) - 6.0 * u.powi(2) + 4.0,
        -3.0 * u.powi(3) + 3.0 * u.powi(2) + 3.0 * u + 1.0,
        u.powi(3),
    ]
    .into_iter()
    .enumerate()
    {
        basis[segment + index] = weight * (fade / 6.0);
    }
    basis
}

fn correction(controls: &[f64], basis: &[f64]) -> f64 {
    controls
        .iter()
        .zip(basis)
        .map(|(control, weight)| control * weight)
        .sum()
}

fn predict(frame: &Frame, selected: &[usize], angles: &[f64]) -> DVec3 {
    // Apply the distal correction first so each ancestor rotates the
    // displacement of its descendants as well as the unperturbed fingertip.
    let delta = selected
        .iter()
        .zip(angles)
        .rev()
        .fold(DVec3::ZERO, |delta, (&joint, &angle)| {
            frame.responses[joint].apply(delta, angle)
        });
    frame.base + delta
}

fn solve_normal(mut normal: Vec<Vec<f64>>, mut right: Vec<f64>) -> Vec<f64> {
    let n = right.len();
    // A positive damping term makes the normal matrix positive definite.
    for i in 0..n {
        for j in 0..=i {
            let product = (0..j).map(|k| normal[i][k] * normal[j][k]).sum::<f64>();
            normal[i][j] = if i == j {
                (normal[i][j] - product).sqrt()
            } else {
                (normal[i][j] - product) / normal[j][j]
            };
        }
        right[i] = (right[i] - (0..i).map(|j| normal[i][j] * right[j]).sum::<f64>()) / normal[i][i];
    }
    for i in (0..n).rev() {
        right[i] =
            (right[i] - (i + 1..n).map(|j| normal[j][i] * right[j]).sum::<f64>()) / normal[i][i];
    }
    right
}

struct Candidate {
    selected: Vec<usize>,
    coefficients: Vec<f64>,
    rms: f64,
    predicted: Vec<DVec3>,
}

fn angles(coefficients: &[f64], basis: &[f64]) -> Vec<f64> {
    coefficients
        .chunks_exact(basis.len())
        .map(|joint| correction(joint, basis))
        .collect()
}

fn rms(frames: &[Frame], positions: impl Iterator<Item = DVec3>) -> f64 {
    let total_weight = frames.iter().map(|frame| frame.weight).sum::<f64>();
    (frames
        .iter()
        .zip(positions)
        .map(|(frame, point)| frame.weight * point.distance_squared(frame.goal))
        .sum::<f64>()
        / total_weight)
        .sqrt()
}

fn solve(frames: &[Frame], selected: Vec<usize>, controls: usize) -> Candidate {
    let count = selected.len() * controls;
    let mut coefficients = vec![0.0; count];
    let limit = MAX_CORRECTION_DEGREES.to_radians();
    const ANGLE_PENALTY: f64 = 1.0e-5;
    const CURVATURE_PENALTY: f64 = 4.0e-4;
    let objective = |coefficients: &[f64]| {
        let path = frames
            .iter()
            .map(|frame| predict(frame, &selected, &angles(coefficients, &frame.basis)));
        let angle = coefficients.iter().map(|value| value.powi(2)).sum::<f64>();
        let curvature = coefficients
            .chunks_exact(controls)
            .flat_map(|joint| joint.windows(3))
            .map(|triplet| (triplet[0] - 2.0 * triplet[1] + triplet[2]).powi(2))
            .sum::<f64>();
        let weight = frames.iter().map(|frame| frame.weight).sum::<f64>();
        rms(frames, path).powi(2) * weight + ANGLE_PENALTY * angle + CURVATURE_PENALTY * curvature
    };
    let mut error = objective(&coefficients);
    for _ in 0..12 {
        let mut normal = vec![vec![0.0; count]; count];
        let mut right = vec![0.0; count];
        for frame in frames {
            let mut angles = angles(&coefficients, &frame.basis);
            let current = predict(frame, &selected, &angles);
            let delta = frame.goal - current;
            let mut jacobian = Vec::with_capacity(count);
            for joint in 0..selected.len() {
                let step = 1.0e-4;
                angles[joint] += step;
                let derivative = (predict(frame, &selected, &angles) - current) / step;
                angles[joint] -= step;
                jacobian.extend(frame.basis.iter().map(|weight| derivative * *weight));
            }
            for (i, column) in jacobian.iter().enumerate() {
                right[i] += column.dot(delta) * frame.weight;
                for (j, other) in jacobian[..=i].iter().enumerate() {
                    normal[i][j] += column.dot(*other) * frame.weight;
                }
            }
        }
        for i in 0..count {
            right[i] -= ANGLE_PENALTY * coefficients[i];
            normal[i][i] += ANGLE_PENALTY + 1.0e-6;
        }
        for joint in 0..selected.len() {
            for i in joint * controls..(joint + 1) * controls - 2 {
                let weights = [1.0, -2.0, 1.0];
                let current = (0..3)
                    .map(|j| weights[j] * coefficients[i + j])
                    .sum::<f64>();
                for (j, weight) in weights.into_iter().enumerate() {
                    right[i + j] -= CURVATURE_PENALTY * weight * current;
                    for k in 0..=j {
                        normal[i + j][i + k] += CURVATURE_PENALTY * weight * weights[k];
                    }
                }
            }
        }
        let step = solve_normal(normal, right);
        let next = [1.0, 0.5, 0.25, 0.125].into_iter().find_map(|scale| {
            let trial: Vec<_> = coefficients
                .iter()
                .zip(&step)
                .map(|(angle, delta)| (angle + scale * delta).clamp(-limit, limit))
                .collect();
            let trial_error = objective(&trial);
            (trial_error + 1.0e-12 < error).then_some((trial, trial_error))
        });
        let Some((trial, trial_error)) = next else {
            break;
        };
        coefficients = trial;
        error = trial_error;
    }
    let predicted: Vec<_> = frames
        .iter()
        .map(|frame| predict(frame, &selected, &angles(&coefficients, &frame.basis)))
        .collect();
    Candidate {
        selected,
        rms: rms(frames, predicted.iter().copied()),
        predicted,
        coefficients,
    }
}

fn encode_track(
    work: &SceneDocument,
    bone: &str,
    frames: &[Frame],
    coefficients: &[f64],
) -> Result<RotationTrack, CoreError> {
    let mut track = work
        .reference_motion
        .as_ref()
        .expect("validated motion")
        .rotations[bone]
        .clone();
    let start = frames[0].source;
    let end = frames.last().expect("sampled window").source;
    let mut times: Vec<_> = track
        .keys
        .iter()
        .map(|key| key.seconds)
        .filter(|time| (start..=end).contains(time))
        .chain(frames.iter().map(|frame| frame.source))
        .collect();
    // Sample the continuous correction densely even when the requested FK grid
    // is coarse. Existing source keys also preserve changes in the saved pose.
    times.extend((1..=64).map(|i| start + (end - start) * (i as f32 / 65.0)));
    times.sort_by(f32::total_cmp);
    times.dedup();
    let samples = times
        .into_iter()
        .map(|seconds| {
            let pose = work.reference_pose_at_source(seconds)?;
            let original = pose
                .rotations
                .iter()
                .find(|rotation| rotation.bone == bone)
                .expect("candidate has an authored rotation");
            let phase = f64::from(seconds - start) / f64::from(end - start);
            let degrees =
                correction(coefficients, &control_weights(phase, coefficients.len())).to_degrees();
            Ok(RotationKey {
                seconds,
                degrees: wrapped_angle(original.degrees + degrees as f32),
            })
        })
        .collect::<Result<Vec<_>, CoreError>>()?;

    track
        .keys
        .retain(|key| key.seconds < start || key.seconds > end);
    let budget = MAX_TRACK_KEYS - track.keys.len();
    if budget < 3 {
        return Err(failed(format!(
            "{bone} has fewer than three key slots in this window. Widen the window to fit a bounded change."
        )));
    }
    let mut keep = vec![0, samples.len() - 1];
    // Keep the window anchors, then add keys where omitting them would create
    // the largest angular error. The untouched keys outside have priority.
    while keep.len() < budget {
        let mut largest = (0.015_f32, 0, 0);
        for (interval, bounds) in keep.windows(2).enumerate() {
            let (left, right) = (bounds[0], bounds[1]);
            let (a, b) = (&samples[left], &samples[right]);
            let swing = (b.degrees - a.degrees + 180.0).rem_euclid(360.0) - 180.0;
            for (offset, key) in samples[left + 1..right].iter().enumerate() {
                let phase = (key.seconds - a.seconds) / (b.seconds - a.seconds);
                let estimate = a.degrees + swing * phase;
                let error = ((key.degrees - estimate + 180.0).rem_euclid(360.0) - 180.0).abs();
                if error > largest.0 {
                    largest = (error, interval + 1, left + 1 + offset);
                }
            }
        }
        if largest.1 == 0 {
            break;
        }
        keep.insert(largest.1, largest.2);
    }
    track
        .keys
        .extend(keep.into_iter().map(|index| samples[index].clone()));
    track.keys.sort_by(|a, b| a.seconds.total_cmp(&b.seconds));
    Ok(track)
}

struct Crossing {
    enter: bool,
    bracket: [f64; 2],
    estimate: f64,
}

struct ContactPath {
    gaps: Vec<f64>,
    crossings: Vec<Crossing>,
}

impl ContactPath {
    fn measure(times: &[f32], positions: &[DVec3], center: DVec3, radius: f64) -> Self {
        let gaps: Vec<_> = positions
            .iter()
            .map(|point| point.distance(center) - radius)
            .collect();
        let crossings = gaps
            .windows(2)
            .enumerate()
            .filter(|(_, gap)| (gap[0] <= 0.0) != (gap[1] <= 0.0))
            .map(|(i, gap)| {
                let bracket = [work_seconds(times[i]), work_seconds(times[i + 1])];
                let estimate = if gap[1] == 0.0 {
                    bracket[1]
                } else {
                    bracket[0] + (bracket[1] - bracket[0]) * gap[0] / (gap[0] - gap[1])
                };
                Crossing {
                    enter: gap[1] <= 0.0,
                    bracket,
                    estimate,
                }
            })
            .collect();
        Self { gaps, crossings }
    }

    fn complete_press(&self) -> bool {
        self.crossings.len() >= 2
            && self
                .crossings
                .chunks_exact(2)
                .all(|pair| pair[0].estimate < pair[1].estimate)
            && self.gaps[0] > 0.0
            && *self.gaps.last().expect("sampled path") > 0.0
    }

    fn timing(&self, reference: &Self) -> Option<Vec<f64>> {
        if !self.complete_press() || self.crossings.len() != reference.crossings.len() {
            return None;
        }
        self.crossings
            .iter()
            .zip(&reference.crossings)
            .map(|(a, b)| (a.enter == b.enter).then_some(a.estimate - b.estimate))
            .collect()
    }

    fn value(&self, times: &[f32], rms: f64, reference: &Self, tolerance: f64) -> Value {
        let timing = self.timing(reference);
        let deviation = deviation(&timing);
        let nearest = self
            .gaps
            .iter()
            .enumerate()
            .min_by(|a, b| a.1.total_cmp(b.1))
            .expect("sampled path");
        let changes: Vec<_> = self
            .crossings
            .iter()
            .map(|change| {
                json!({
                    "event": if change.enter { "enter" } else { "exit" },
                    "bracket_s": change.bracket,
                    "estimated_t_s": change.estimate,
                })
            })
            .collect();
        json!({
            "weighted_rms_metres": rms,
            "nearest_surface_gap_metres": nearest.1,
            "nearest_t_s": work_seconds(times[nearest.0]),
            "changes": changes,
            "matches_reference_timing": deviation <= tolerance,
            "timing_deviation_s": timing,
            "max_abs_timing_deviation_s": deviation.is_finite().then_some(deviation),
        })
    }
}

fn deviation(timing: &Option<Vec<f64>>) -> f64 {
    timing.as_ref().map_or(f64::INFINITY, |deviations| {
        deviations
            .iter()
            .map(|value| value.abs())
            .fold(0.0, f64::max)
    })
}

pub(crate) fn fit(
    work_path: &Path,
    asset_root: &str,
    reference_path: &Path,
    start_s: f64,
    end_s: f64,
    step_s: f64,
    hand: &str,
) -> Result<Value, CoreError> {
    let (hand, candidate_joints) = match hand {
        "left" => (B1ContactHand::Left, crate::CONTACT_FIT_LEFT),
        "right" => (B1ContactHand::Right, crate::CONTACT_FIT_RIGHT),
        _ => {
            return Err(CoreError::new(
                "usage",
                "Contact fit hand must be left or right",
            ));
        }
    };
    let raw = crate::read(work_path)?;
    let reference_raw = crate::read(reference_path)?;
    let work = SceneDocument::from_json(&raw)?;
    let reference = SceneDocument::from_json(&reference_raw)?;
    let max_time = work_seconds(work.timeline_duration_seconds())
        .min(work_seconds(reference.timeline_duration_seconds()));
    if ![start_s, end_s, step_s].iter().all(|time| time.is_finite())
        || start_s < 0.0
        || end_s <= start_s
        || end_s > max_time
        || step_s < 0.001
    {
        return Err(range_error(format!(
            "Require 0 <= start < end <= {max_time}s and step >= 0.001s"
        )));
    }
    let times = sample_times(start_s, end_s, step_s).map_err(|error| range_error(error.message))?;
    if times.len() < 3 {
        return Err(range_error(
            "Contact fit requires at least one interior sample",
        ));
    }
    let sources = source_times(&work, &times, true)?;
    source_times(&reference, &times, false)?;
    let target = work.stage.contact_target.as_ref().ok_or_else(|| {
        CoreError::new(
            "contact_target_absent",
            "Save stage.contact_target in both Works before fitting",
        )
    })?;
    if reference.stage.contact_target.as_ref() != Some(target) {
        return Err(CoreError::new(
            "contact_fit_target_mismatch",
            "Both Works must have the same saved contact target ID, center and radius",
        ));
    }
    let center = DVec3::from_array(target.position_metres.map(f64::from));
    let radius = f64::from(target.radius_metres);
    let motion = work
        .reference_motion
        .as_ref()
        .expect("validated reference clip");
    let source_start = sources[0];
    let source_end = sources[sources.len() - 1];
    let tracks: Vec<_> = candidate_joints
        .into_iter()
        .filter(|&bone| {
            motion.rotations.get(bone).is_some_and(|track| {
                track
                    .keys
                    .iter()
                    .filter(|key| key.seconds < source_start || key.seconds > source_end)
                    .count()
                    <= MAX_TRACK_KEYS - 3
            })
        })
        .collect();
    if tracks.is_empty() {
        return Err(CoreError::new(
            "contact_fit_unsupported_work",
            "The window must admit an authored spine or selected-side arm track with space for at least three keys",
        ));
    }
    let goals = {
        let mut app = headless_app(asset_root, reference).map_err(failed)?;
        times
            .iter()
            .map(|&seconds| fingertip(&mut app, seconds, hand))
            .collect::<Result<Vec<_>, _>>()?
    };
    let contact_path =
        |positions: &[DVec3]| ContactPath::measure(&times, positions, center, radius);
    let goal_path = contact_path(&goals);
    if !goal_path.complete_press() {
        return Err(CoreError::new(
            "contact_fit_reference_contact",
            "The sampled reference window must start outside contact, contain a complete press and release, and end outside contact",
        ));
    }
    let mut app = headless_app(asset_root, work.clone()).map_err(failed)?;
    let controls = (times.len() / 2 + 3).clamp(4, MAX_CONTROLS);
    let mut frames = Vec::with_capacity(times.len());
    for ((&wall, &source), &goal) in times.iter().zip(&sources).zip(&goals) {
        let base = fingertip(&mut app, wall, hand)?;
        let gap = goal.distance(center) - radius;
        let weight = 1.0 + 24.0 * (-gap.max(0.0) / (radius * 0.35)).exp();
        let phase = f64::from(source - source_start) / f64::from(source_end - source_start);
        frames.push(Frame {
            wall,
            source,
            base,
            goal,
            weight,
            basis: control_weights(phase, controls),
            responses: vec![Response::default(); tracks.len()],
        });
    }

    let before: Vec<_> = frames.iter().map(|frame| frame.base).collect();
    let baseline = rms(&frames, before.iter().copied());
    let tolerance = step_s;
    let baseline_path = contact_path(&before);
    let baseline_time = deviation(&baseline_path.timing(&goal_path));
    let mut commands = Vec::new();
    let mut evaluated_subsets = 0;
    let mut predicted_matching_subsets = 0;
    let mut measured_subsets = 0;
    let mut joints = Vec::new();
    let mut predicted = before.clone();
    let mut measured = before.clone();
    let mut probe_frames = 0;
    let mut status = "already_aligned";
    let mut reason =
        "The current fingertip trajectory already matches the reference at sampled times.";
    if baseline > 1.0e-6 || baseline_time > tolerance {
        let interior = frames.len() - 1;
        for frame in &mut frames[1..interior] {
            for (index, &bone) in tracks.iter().enumerate() {
                frame.responses[index] = measure_response(
                    &mut app,
                    &work,
                    bone,
                    frame.wall,
                    frame.source,
                    frame.base,
                    hand,
                )?;
                probe_frames += 2;
            }
        }
        let mut candidates = (1..1 << tracks.len())
            .map(|subset| {
                let selected = (0..tracks.len())
                    .filter(|&index| subset & (1 << index) != 0)
                    .collect();
                let candidate = solve(&frames, selected, controls);
                let timing = deviation(&contact_path(&candidate.predicted).timing(&goal_path));
                (candidate, timing)
            })
            .collect::<Vec<_>>();
        evaluated_subsets = candidates.len();
        predicted_matching_subsets = candidates
            .iter()
            .filter(|(_, timing)| *timing <= tolerance)
            .count();
        let best = candidates
            .iter()
            .filter(|(_, timing)| *timing <= tolerance || predicted_matching_subsets == 0)
            .map(|(candidate, _)| candidate.rms)
            .fold(f64::INFINITY, f64::min);
        candidates.sort_by(|(a, a_time), (b, b_time)| {
            let count = |candidate: &Candidate| {
                if candidate.rms <= best + 0.001 {
                    candidate.selected.len()
                } else {
                    tracks.len() + 1
                }
            };
            (*a_time > tolerance)
                .cmp(&(*b_time > tolerance))
                .then_with(|| count(a).cmp(&count(b)))
                .then_with(|| a.rms.total_cmp(&b.rms))
                .then_with(|| a_time.total_cmp(b_time))
        });
        status = "partial";
        reason = "No proposed fit improved the sampled path while preserving the reference contact timing.";
        let mut best_partial = (baseline_time, baseline);
        for (candidate, _) in candidates
            .into_iter()
            .filter(|(candidate, _)| candidate.rms + 1.0e-6 < baseline)
        {
            let mut corrected = motion.clone();
            for (&index, coeff) in candidate
                .selected
                .iter()
                .zip(candidate.coefficients.chunks_exact(controls))
            {
                corrected.rotations.insert(
                    tracks[index].into(),
                    encode_track(&work, tracks[index], &frames, coeff)?,
                );
            }
            if corrected == *motion {
                continue;
            }
            let envelope = CommandEnvelope {
                command_id: format!("contact-fit-{}", work.revision),
                expected_revision: work.revision,
                command: Command::SetShapedReferenceMotion {
                    clips: work.timeline.clone(),
                    motion: corrected,
                },
            };
            let mut editor = Editor::new(work.clone())?;
            editor.apply(envelope.clone())?;
            app.world_mut().resource_mut::<EditorState>().preview = Some(editor.document().clone());
            let actual = times
                .iter()
                .map(|&seconds| fingertip(&mut app, seconds, hand))
                .collect::<Result<Vec<_>, _>>()?;
            app.world_mut()
                .resource_mut::<EditorState>()
                .cancel_preview();
            measured_subsets += 1;
            let actual_rms = rms(&frames, actual.iter().copied());
            let actual_timing = deviation(&contact_path(&actual).timing(&goal_path));
            let adequate = actual_timing <= tolerance;
            if actual_rms + 1.0e-6 >= baseline
                || (!adequate && (actual_timing, actual_rms) >= best_partial)
            {
                continue;
            }
            best_partial = (actual_timing, actual_rms);
            predicted = candidate.predicted;
            measured = actual;
            joints = candidate
                .selected
                .iter()
                .map(|&index| tracks[index])
                .collect();
            commands = vec![envelope];
            if adequate {
                status = "fit";
                reason = "The measured proposal improved the sampled path and matched the reference contact timing.";
                break;
            }
            reason = "The proposal improved the sampled path. Its measured contact timing differs from the reference.";
        }
    }
    let at = goals
        .iter()
        .enumerate()
        .min_by(|a, b| {
            a.1.distance_squared(center)
                .total_cmp(&b.1.distance_squared(center))
        })
        .expect("sampled path")
        .0;
    Ok(json!({
        "schema_version": 1,
        "status": status,
        "reason": reason,
        "work": {"revision": work.revision, "sha256": appearance_sha256(raw.as_bytes())},
        "reference_work": {"sha256": appearance_sha256(reference_raw.as_bytes())},
        "expected_revision": work.revision,
        "method": "published_b1_fingertip_finite_difference",
        "landmark": hand.landmark(),
        "space": "stage_world_xyz",
        "axes": {"up": "+Y", "forward": "+Z"},
        "target": target,
        "sampling": {
            "start_s": start_s, "end_s": end_s, "step_s": step_s, "count": times.len(),
            "single_joint_probe_frames": probe_frames,
        },
        "selected_joints": joints,
        "timing_tolerance_s": tolerance,
        "subsets": {
            "predicted": evaluated_subsets,
            "predicted_matching_timing": predicted_matching_subsets,
            "measured": measured_subsets,
        },
        "reference": goal_path.value(&times, 0.0, &goal_path, tolerance),
        "before": baseline_path.value(&times, baseline, &goal_path, tolerance),
        "predicted": contact_path(&predicted).value(
            &times, rms(&frames, predicted.iter().copied()), &goal_path, tolerance,
        ),
        "after": contact_path(&measured).value(
            &times, rms(&frames, measured.iter().copied()), &goal_path, tolerance,
        ),
        "reference_nearest_sample": {
            "t_s": work_seconds(times[at]),
            "reference_metres": goals[at].to_array(),
            "before_metres": before[at].to_array(),
            "predicted_metres": predicted[at].to_array(),
            "after_metres": measured[at].to_array(),
            "reference_minus_before_metres": (goals[at] - before[at]).to_array(),
            "before_error_metres": before[at].distance(goals[at]),
            "after_error_metres": measured[at].distance(goals[at]),
        },
        "commands": commands,
    }))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn path(points: [f64; 7]) -> ContactPath {
        let positions = points.map(|x| DVec3::new(x, 0.0, 0.0));
        ContactPath::measure(
            &[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            &positions,
            DVec3::ZERO,
            1.0,
        )
    }

    #[test]
    fn contact_requires_a_complete_press_and_matching_transitions() {
        let reference = path([2.0, 1.5, 0.8, 0.5, 0.7, 1.5, 2.0]);
        assert!(reference.complete_press());
        assert_eq!(reference.timing(&reference), Some(vec![0.0, 0.0]));
        assert!(!path([2.0; 7]).complete_press());
        assert!(!path([2.0, 1.0, 2.0, 2.0, 2.0, 2.0, 2.0]).complete_press());
        assert!(!path([1.3426227569580078, 1.0, 2.0, 2.0, 2.0, 2.0, 2.0]).complete_press());
        assert!(
            path([0.5, 0.5, 1.5, 2.0, 2.0, 2.0, 2.0])
                .timing(&reference)
                .is_none()
        );
        assert!(
            path([2.0, 0.5, 1.5, 0.5, 1.5, 2.0, 2.0])
                .timing(&reference)
                .is_none()
        );

        let late = path([2.0, 1.5, 1.5, 1.5, 0.5, 0.5, 2.0]);
        let timing = late.timing(&reference).expect("complete event sequence");
        assert!(timing.iter().all(|seconds| *seconds > 0.0));
        assert!(deviation(&Some(timing)) > 0.1);
    }

    #[test]
    fn correction_has_neutral_anchors_and_angles_wrap_canonically() {
        let controls = [0.2; 8];
        assert_eq!(
            correction(&controls, &control_weights(0.0, controls.len())),
            0.0
        );
        assert_eq!(
            correction(&controls, &control_weights(1.0, controls.len())),
            0.0
        );
        assert!(correction(&controls, &control_weights(0.0001, controls.len())) < 1.0e-6);
        assert!(correction(&controls, &control_weights(0.9999, controls.len())) < 1.0e-6);
        assert_eq!(wrapped_angle(180.0), 180.0);
        assert_eq!(wrapped_angle(-180.0), -180.0);
        assert_eq!(wrapped_angle(183.0), -177.0);
        assert_eq!(wrapped_angle(-183.0), 177.0);
    }
}

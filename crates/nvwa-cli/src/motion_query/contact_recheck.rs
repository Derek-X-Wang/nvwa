//! Recheck a saved fit against the reference contact and the prepared stance.
use super::{finite_time, headless_app, seek, work_seconds};
use crate::{CONTACT_RECHECK_USAGE, read, supports_contact_edit};
use bevy::prelude::App;
use nvwa_core::{CoreError, SceneDocument, StageContactTarget, appearance_sha256};
use nvwa_runtime::B1ContactHand;
use serde_json::{Value, json};
use std::path::Path;

const GUIDE_STEP_MS: u32 = 25;
const MAX_DURATION_S: f64 = 100.0;
const TIMING_LIMIT_MS: f64 = 1000.0 / 24.0;
const LANDING_LIMIT_MM: f64 = 0.001;
const ANGLE_LIMIT_DEG: f64 = 0.001;
type Brackets = [[u32; 2]; 2];

#[derive(Clone, Copy)]
enum Side {
    Left,
    Right,
}

impl Side {
    fn index(self) -> usize {
        match self {
            Self::Left => 0,
            Self::Right => 1,
        }
    }

    fn name(self) -> &'static str {
        match self {
            Self::Left => "left",
            Self::Right => "right",
        }
    }

    fn hand(self) -> B1ContactHand {
        match self {
            Self::Left => B1ContactHand::Left,
            Self::Right => B1ContactHand::Right,
        }
    }
}

struct Request<'a> {
    saved: &'a str,
    assets: &'a str,
    stance: &'a str,
    reference: &'a str,
    landing_s: f64,
    hand: B1ContactHand,
    sole: Side,
    support: Side,
}

impl<'a> Request<'a> {
    fn parse(args: &'a [String]) -> Result<Self, CoreError> {
        let usage = || CoreError::new("usage", CONTACT_RECHECK_USAGE);
        let ([saved, assets, stance, reference, landing_s], rest) =
            args.split_first_chunk::<5>().ok_or_else(usage)?;
        let (mut hand, mut sole, mut support) = (None, None, None);
        let mut flags = rest.iter().map(String::as_str);
        while let Some(flag) = flags.next() {
            let selection = match flag {
                "--hand" => &mut hand,
                "--sole" => &mut sole,
                "--support" => &mut support,
                _ => return Err(usage()),
            };
            if selection.is_some() {
                return Err(usage());
            }
            *selection = Some(match flags.next() {
                Some("left") => Side::Left,
                Some("right") => Side::Right,
                _ => return Err(usage()),
            });
        }
        Ok(Self {
            saved,
            assets,
            stance,
            reference,
            landing_s: finite_time(landing_s, "contact_recheck_range")?,
            hand: hand.ok_or_else(usage)?.hand(),
            sole: sole.ok_or_else(usage)?,
            support: support.ok_or_else(usage)?,
        })
    }
}

struct Work {
    document: SceneDocument,
    identity: Value,
}

impl Work {
    fn read(path: &str, label: &str) -> Result<Self, CoreError> {
        let raw = read(Path::new(path))?;
        let document = SceneDocument::from_json(&raw)?;
        if !supports_contact_edit(&document) {
            return Err(CoreError::new(
                "contact_recheck_unsupported_work",
                format!("The {label} Work must support the required published B1 measurements"),
            ));
        }
        let identity = json!({
            "revision": document.revision,
            "sha256": appearance_sha256(raw.as_bytes()),
        });
        Ok(Self { document, identity })
    }
}

struct Guide {
    states: Vec<bool>,
    crossings: Vec<usize>,
}

impl Guide {
    fn new(states: Vec<bool>) -> Self {
        let crossings = states
            .windows(2)
            .enumerate()
            .filter_map(|(i, pair)| (pair[0] != pair[1]).then_some(i))
            .collect();
        Self { states, crossings }
    }

    fn press(&self) -> Option<[usize; 2]> {
        match self.crossings.as_slice() {
            &[enter, exit] if !self.states[0] && !self.states[self.states.len() - 1] => {
                Some([enter, exit])
            }
            _ => None,
        }
    }

    fn value(&self, times: &[f64]) -> Value {
        let count = self.states.iter().filter(|&&inside| inside).count();
        let intervals = self
            .crossings
            .iter()
            .filter(|&&edge| self.states[edge + 1])
            .count()
            + usize::from(self.states[0]);
        json!({
            "samples": self.states.len(),
            "inside_samples": count,
            "intervals": intervals,
            "first_inside": self.states[0],
            "last_inside": self.states[self.states.len() - 1],
            "edge_brackets_s": self.press().map(|press| press.map(|i| [times[i], times[i + 1]])),
        })
    }
}

fn guide_times(duration_s: f64) -> Vec<f64> {
    let mut times: Vec<_> = (0..)
        .step_by(GUIDE_STEP_MS as usize)
        .map(|tick| f64::from(tick) / 1000.0)
        .take_while(|&seconds| seconds < duration_s)
        .collect();
    times.push(duration_s);
    times
}

fn clearance(
    app: &mut App,
    seconds: f64,
    hand: B1ContactHand,
    target: &StageContactTarget,
) -> Result<f64, CoreError> {
    Ok(
        super::sample_contact(app, seconds as f32, hand, target)?.distance
            - f64::from(target.radius_metres),
    )
}

fn measurement_error(message: String) -> CoreError {
    CoreError::new("contact_recheck_failed", message)
}

fn refinement_windows(
    reference: [usize; 2],
    saved: [usize; 2],
    guide_count: usize,
) -> Vec<[usize; 2]> {
    // Sample both Works around both sets of edges. A distant edge adds a
    // window without requiring a fine scan of the long span between them.
    let mut windows = [reference[0], reference[1], saved[0], saved[1]]
        .map(|i| [i.saturating_sub(1), (i + 2).min(guide_count - 1)]);
    windows.sort_unstable();
    let mut merged: Vec<[usize; 2]> = Vec::with_capacity(windows.len());
    for window in windows {
        if let Some(last) = merged.last_mut().filter(|last| last[1] >= window[0]) {
            last[1] = last[1].max(window[1]);
        } else {
            merged.push(window);
        }
    }
    merged
}

fn refine(
    times: &[f64],
    guide: &Guide,
    press: [usize; 2],
    windows: &[[usize; 2]],
    mut sample: impl FnMut(f64) -> Result<f64, CoreError>,
) -> Result<Result<Brackets, &'static str>, CoreError> {
    let mut transitions = Vec::with_capacity(2);
    let mut enter_gap = 0.0;
    for &[start, end] in windows {
        // The lower fence of every bracket has a successor, so its padded
        // lower fence is always on the regular grid.
        let start_ms = (times[start] * 1000.0).round() as u32;
        let end_ms = (times[end] * 1000.0).ceil() as u32;
        let mut previous = sample(times[start])? <= 0.0;
        if previous != guide.states[start] {
            return Ok(Err("guide_and_refinement_disagree"));
        }
        let mut last_ms = start_ms;
        for tick in start_ms + 1..=end_ms {
            let seconds = f64::from(tick) / 1000.0;
            if seconds > times[end] {
                break;
            }
            let gap = sample(seconds)?;
            let current = gap <= 0.0;
            if current && !previous {
                enter_gap = gap;
            }
            if current != previous {
                transitions.push(([tick - 1, tick], current));
            }
            previous = current;
            last_ms = tick;
        }
        if f64::from(last_ms) / 1000.0 < times[end] && previous != guide.states[end] {
            return Ok(Err("transition_reaches_off_grid_clip_end"));
        }
        if previous != guide.states[end] {
            return Ok(Err("guide_and_refinement_disagree"));
        }
    }

    let [enter, exit] = transitions.as_slice() else {
        return Ok(Err("expected_one_enter_and_one_exit_in_refinement"));
    };
    for (&(bracket, enters), coarse) in [enter, exit].into_iter().zip(press) {
        let [low, high] = bracket.map(|tick| f64::from(tick) / 1000.0);
        if enters != guide.states[coarse + 1] || low < times[coarse] || high > times[coarse + 1] {
            return Ok(Err("refined_transition_outside_guide_bracket"));
        }
    }
    // A single boundary-only sample represents a tangent. A single strictly
    // inside sample, or a sustained hold on the boundary, has a measurable span.
    if enter.0[1] == exit.0[0] && enter_gap == 0.0 {
        return Ok(Err("zero_duration_tangent"));
    }
    Ok(Ok([enter.0, exit.0]))
}

fn observe_guide(
    times: &[f64],
    mut sample: impl FnMut(f64) -> Result<f64, CoreError>,
) -> Result<Guide, CoreError> {
    let states = times
        .iter()
        .map(|&seconds| sample(seconds).map(|gap| gap <= 0.0))
        .collect::<Result<Vec<_>, _>>()?;
    Ok(Guide::new(states))
}

#[derive(Clone, Copy)]
struct Landing {
    landing: [f64; 3],
    pitch: f64,
    heading: Option<f64>,
    forefoot: f64,
    heel: f64,
    offset: [f64; 3],
}

fn subtract(a: [f64; 3], b: [f64; 3]) -> [f64; 3] {
    std::array::from_fn(|axis| a[axis] - b[axis])
}

impl Landing {
    fn delta(self, other: Self) -> Self {
        Self {
            landing: subtract(self.landing, other.landing),
            pitch: self.pitch - other.pitch,
            heading: self
                .heading
                .zip(other.heading)
                .map(|(a, b)| (a - b + 180.0).rem_euclid(360.0) - 180.0),
            forefoot: self.forefoot - other.forefoot,
            heel: self.heel - other.heel,
            offset: subtract(self.offset, other.offset),
        }
    }

    fn value(self) -> Value {
        json!({"landing_mm":self.landing, "pitch_deg":self.pitch, "heading_deg":self.heading,
               "forefoot_mm":self.forefoot, "heel_mm":self.heel, "pelvis_minus_support_mm":self.offset})
    }
}

fn observe_landing(app: &mut App, request: &Request<'_>) -> Result<Landing, CoreError> {
    let world = seek(app, request.landing_s as f32).map_err(measurement_error)?;
    let (feet, pelvis) =
        nvwa_runtime::b1_sole_and_pelvis_measurements(world).map_err(measurement_error)?;
    let foot = &feet[request.sole.index()];
    Ok(Landing {
        landing: foot.centroid_metres.map(|value| value * 1000.0),
        pitch: foot.pitch_degrees,
        heading: foot.heading_degrees,
        forefoot: 1000.0 * foot.forefoot_clearance_metres,
        heel: 1000.0 * foot.heel_clearance_metres,
        offset: subtract(pelvis, feet[request.support.index()].centroid_metres).map(|v| v * 1000.0),
    })
}

fn edge_value(saved: [u32; 2], reference: [u32; 2]) -> (Value, f64) {
    // The edge can lie anywhere in its bracket. Opposite endpoints give the
    // extremes of the signed saved-minus-reference interval.
    let signed = [
        i64::from(saved[0]) - i64::from(reference[1]),
        i64::from(saved[1]) - i64::from(reference[0]),
    ];
    let worst = signed[0].abs().max(signed[1].abs()) as f64;
    (
        json!({
            "saved_bracket_ms": saved,
            "reference_bracket_ms": reference,
            "possible_signed_delta_ms": signed,
            "bracket_midpoint_delta_ms": (signed[0] + signed[1]) as f64 / 2.0,
            "worst_case_absolute_delta_ms": worst,
        }),
        worst,
    )
}

fn contact_timing(
    times: &[f64],
    stance: &Guide,
    reference: &Guide,
    saved: &Guide,
    sample_reference: impl FnMut(f64) -> Result<f64, CoreError>,
    sample_saved: impl FnMut(f64) -> Result<f64, CoreError>,
) -> Result<(&'static str, Value), CoreError> {
    let mut value = json!({
        "guide": {
            "stance": stance.value(times),
            "reference": reference.value(times),
            "saved": saved.value(times),
        },
        "threshold_ms": TIMING_LIMIT_MS,
    });
    let status = match (reference.press(), saved.press()) {
        (Some(reference_press), Some(saved_press)) => {
            let windows = refinement_windows(reference_press, saved_press, times.len());
            let windows_s: Vec<_> = windows.iter().map(|&[a, b]| [times[a], times[b]]).collect();
            value["refinement_windows_s"] = json!(windows_s);
            let reference_edges = refine(
                times,
                reference,
                reference_press,
                &windows,
                sample_reference,
            )?;
            let saved_edges = refine(times, saved, saved_press, &windows, sample_saved)?;
            value["reference_issue"] = json!(reference_edges.err());
            value["saved_issue"] = json!(saved_edges.err());
            match (reference_edges, saved_edges) {
                (Err(_), _) | (_, Err("transition_reaches_off_grid_clip_end")) => "unassessable",
                (_, Err(_)) => "failed",
                (Ok(reference), Ok(saved)) => {
                    let (enter, enter_delta) = edge_value(saved[0], reference[0]);
                    let (exit, exit_delta) = edge_value(saved[1], reference[1]);
                    value["edges"] = json!({"enter": enter, "exit": exit});
                    if enter_delta.max(exit_delta) <= TIMING_LIMIT_MS {
                        "passed"
                    } else {
                        "failed"
                    }
                }
            }
        }
        (reference_press, saved_press) => {
            let issue = "expected_one_complete_guide_interval";
            value["reference_issue"] = json!(reference_press.is_none().then_some(issue));
            value["saved_issue"] = json!(saved_press.is_none().then_some(issue));
            if reference_press.is_none() {
                "unassessable"
            } else {
                "failed"
            }
        }
    };
    value["status"] = json!(status);
    Ok((status, value))
}

fn landing(request: &Request<'_>, stance: Landing, saved: Landing) -> (&'static str, Value) {
    let delta = saved.delta(stance);
    let within_mm = |delta: f64| delta.abs() <= LANDING_LIMIT_MM;
    let within_deg = |delta: f64| delta.abs() <= ANGLE_LIMIT_DEG;
    let checks = [
        delta.landing.into_iter().all(within_mm),
        within_mm(delta.forefoot),
        within_mm(delta.heel),
        within_deg(delta.pitch),
        delta.offset.into_iter().all(within_mm),
    ];
    let heading = delta.heading.map(within_deg);
    let status = if checks.contains(&false) || heading == Some(false) {
        "failed"
    } else if heading.is_none() {
        "unassessable"
    } else {
        "passed"
    };
    (
        status,
        json!({
            "status": status,
            "t_s": work_seconds(request.landing_s as f32),
            "requested_t_s": request.landing_s,
            "sole": request.sole.name(),
            "support": request.support.name(),
            "landmarks": {
                "landing": "whole_sole_centroid",
                "pitch_and_heading": "heel_to_forefoot_axis",
                "forefoot_and_heel": "minimum_y_in_each_sole_region",
                "pelvis_minus_support": "pelvis_rig_origin_minus_support_sole_centroid",
            },
            "thresholds": {"mm_per_axis_or_clearance": LANDING_LIMIT_MM, "degrees": ANGLE_LIMIT_DEG},
            "stance": stance.value(),
            "saved": saved.value(),
            "delta": {
                "landing_mm": delta.landing,
                "forefoot_mm": delta.forefoot,
                "heel_mm": delta.heel,
                "pitch_deg": delta.pitch,
                "heading_deg": delta.heading,
                "pelvis_minus_support_mm": delta.offset,
            },
            "checks": {
                "landing_xyz": checks[0],
                "forefoot": checks[1],
                "heel": checks[2],
                "pitch": checks[3],
                "heading": heading,
                "pelvis_minus_support_xyz": checks[4],
            },
            "heading_missing": {
                "stance": stance.heading.is_none(),
                "saved": saved.heading.is_none(),
            },
        }),
    )
}

pub(crate) fn run(args: &[String]) -> Result<Value, CoreError> {
    let request = Request::parse(args)?;
    let saved = Work::read(request.saved, "saved")?;
    let stance = Work::read(request.stance, "stance")?;
    let reference = Work::read(request.reference, "reference")?;
    let target = saved.document.stage.contact_target.clone().ok_or_else(|| {
        CoreError::new(
            "contact_target_absent",
            "Save the named contact target in each Work",
        )
    })?;
    if [&stance, &reference]
        .into_iter()
        .any(|work| work.document.stage.contact_target.as_ref() != Some(&target))
    {
        return Err(CoreError::new(
            "contact_recheck_target_mismatch",
            "All three Works must store the same contact target ID, center and radius",
        ));
    }
    let duration = saved.document.timeline_duration_seconds();
    if !duration.is_finite()
        || [&stance, &reference]
            .into_iter()
            .any(|work| work.document.timeline_duration_seconds() != duration)
    {
        return Err(CoreError::new(
            "contact_recheck_duration_mismatch",
            "All three Works must have the same finite timeline duration",
        ));
    }
    let duration_s = work_seconds(duration);
    if !(0.0 < duration_s && duration_s <= MAX_DURATION_S) {
        return Err(CoreError::new(
            "contact_recheck_range",
            format!(
                "The complete 25 ms guide requires a positive duration of at most {MAX_DURATION_S}s"
            ),
        ));
    }
    if !(0.0..=duration_s).contains(&request.landing_s) {
        return Err(CoreError::new(
            "contact_recheck_range",
            format!("Landing time must be within 0..={duration_s}s"),
        ));
    }

    let times = guide_times(duration_s);
    let (stance_guide, stance_landing) = {
        let mut app = headless_app(request.assets, stance.document).map_err(measurement_error)?;
        let guide = observe_guide(&times, |s| clearance(&mut app, s, request.hand, &target))?;
        let frame = observe_landing(&mut app, &request)?;
        (guide, frame)
    };
    let mut reference_app =
        headless_app(request.assets, reference.document).map_err(measurement_error)?;
    let mut saved_app = headless_app(request.assets, saved.document).map_err(measurement_error)?;
    let mut sample_reference = |s| clearance(&mut reference_app, s, request.hand, &target);
    let mut sample_saved = |s| clearance(&mut saved_app, s, request.hand, &target);
    let reference_guide = observe_guide(&times, &mut sample_reference)?;
    let saved_guide = observe_guide(&times, &mut sample_saved)?;
    let (timing_status, timing) = contact_timing(
        &times,
        &stance_guide,
        &reference_guide,
        &saved_guide,
        sample_reference,
        sample_saved,
    )?;
    let saved_landing = observe_landing(&mut saved_app, &request)?;
    let (landing_status, landing) = landing(&request, stance_landing, saved_landing);
    let checks = [timing_status, landing_status];
    let status = if checks.contains(&"failed") {
        "failed"
    } else if checks.contains(&"unassessable") {
        "unassessable"
    } else {
        "passed"
    };

    Ok(json!({
        "schema_version": 1,
        "status": status,
        "saved": saved.identity,
        "stance": stance.identity,
        "reference": reference.identity,
        "target": target,
        "landmark": request.hand.landmark(),
        "space": "stage_world_xyz",
        "axes": {"up": "+Y", "forward": "+Z"},
        "sampling": {
            "start_s": 0.0,
            "end_s": duration_s,
            "guide_step_ms": GUIDE_STEP_MS,
            "refinement_step_ms": 1,
            "refinement_margin_ms": GUIDE_STEP_MS,
        },
        "contact_timing": timing,
        "landing": landing,
    }))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn guide_includes_off_grid_end_and_requires_one_bounded_interval() {
        let times = guide_times(0.09);
        assert_eq!(times, [0.0, 0.025, 0.05, 0.075, 0.09]);
        for states in [
            [false; 5],
            [true, true, false, false, false],
            [false, false, false, true, true],
            [false, true, false, true, false],
        ] {
            assert!(Guide::new(states.into()).press().is_none());
        }
    }

    #[test]
    fn refinement_checks_the_margin_and_handles_a_short_press() {
        let times = guide_times(0.15);
        let guide = Guide::new(vec![false, false, false, true, false, false, false]);
        let contact = |t| (0.059..0.087).contains(&t);
        let press = guide.press().unwrap();
        let windows = refinement_windows(press, press, times.len());
        let good = refine(&times, &guide, press, &windows, |t| {
            Ok(if contact(t) { -1.0 } else { 1.0 })
        })
        .unwrap();
        assert_eq!(good, Ok([[58, 59], [86, 87]]));
        let hidden = refine(&times, &guide, press, &windows, |t| {
            Ok(if contact(t) || (0.034..0.038).contains(&t) {
                -1.0
            } else {
                1.0
            })
        })
        .unwrap();
        assert_eq!(hidden, Err("expected_one_enter_and_one_exit_in_refinement"));
    }

    #[test]
    fn one_boundary_touch_is_distinct_from_a_press_or_sustained_boundary_hold() {
        let times = guide_times(0.15);
        let guide = Guide::new(vec![false, false, false, true, false, false, false]);
        let press = guide.press().unwrap();
        let windows = refinement_windows(press, press, times.len());
        for (level, end_ms, expected) in [
            (0.0, 75, Err("zero_duration_tangent")),
            (-0.001, 75, Ok([[74, 75], [75, 76]])),
            (0.0, 76, Ok([[74, 75], [76, 77]])),
        ] {
            let actual = refine(&times, &guide, press, &windows, |t| {
                let tick = (t * 1000.0).round() as u32;
                Ok(if (75..=end_ms).contains(&tick) {
                    level
                } else {
                    1.0
                })
            })
            .unwrap();
            assert_eq!(actual, expected);
        }
    }

    #[test]
    fn timing_uses_the_furthest_pair_of_endpoints() {
        let (report, worst) = edge_value([341, 342], [300, 301]);
        assert_eq!(report["possible_signed_delta_ms"], json!([40, 42]));
        assert!(worst > TIMING_LIMIT_MS);
        assert!(edge_value([260, 261], [300, 301]).1 <= TIMING_LIMIT_MS);
    }
}

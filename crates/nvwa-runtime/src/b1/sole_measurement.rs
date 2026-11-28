use super::{
    Session,
    foot_clearance::{LEFT, PublishedBody, RIGHT, published_body},
    published_motion_frame, running,
};
use bevy::{math::DVec3, prelude::*};
use humentity::prelude::ObjVertsAsset;

// Fixed B1 source coordinates keep the same anatomy across shapes and poses.
// The bottom 10 mm of the reference foot (minimum Y = -0.81676 m) anchors
// the full sole. The plantar heel is bounded around the live source ankle
// helper (Z = -0.00091 m), from the rear sole edge Z = -0.04506 m to its
// reflection across the ankle. The forefoot begins across the reference
// gap between the arch and ball pad. The arch remains in the full sole.
const SOLE_UPPER_Y_METRES: f32 = -0.80676;
const HEEL_MAX_Z_METRES: f32 = 0.04324;
const FOREFOOT_MIN_Z_METRES: f32 = 0.08108;
const SOLE_VERTEX_COUNT: usize = 288;
const FOREFOOT_VERTEX_COUNT: usize = 245;
const HEEL_VERTEX_COUNT: usize = 35;

/// Anatomical sole geometry in stage world space (floor Y = 0).
#[derive(Debug, Clone, Copy)]
pub struct B1SoleMeasurement {
    /// Unweighted centroid of the whole anchored sole in stage XYZ metres.
    pub centroid_metres: [f64; 3],
    /// Heel-to-forefoot elevation angle in degrees. Positive means toe-up.
    pub pitch_degrees: f64,
    /// Signed stage XZ heading in degrees (+Z forward, +X positive).
    /// None when the horizontal projection is at most one micrometre.
    pub heading_degrees: Option<f64>,
    /// Minimum signed distance over the full sole, including the arch.
    pub sole_clearance_metres: f64,
    /// Minimum signed distance within the anchored forefoot patch.
    pub forefoot_clearance_metres: f64,
    /// Minimum signed distance within the anchored heel patch.
    pub heel_clearance_metres: f64,
    /// Number of unique base mesh source vertices, excluding UV seam duplicates.
    pub sole_vertex_count: usize,
    pub forefoot_vertex_count: usize,
    pub heel_vertex_count: usize,
}

/// Read both soles and the pelvis rig origin in stage XYZ metres from the same
/// fitted running or shaped reference frame.
pub fn b1_sole_and_pelvis_measurements(
    world: &World,
) -> Result<([B1SoleMeasurement; 2], [f64; 3]), String> {
    let (active, body) = sole_body(world).map_err(unsupported)?;
    Ok((
        measure_published(world, &body).map_err(unsupported)?,
        body.bone_origin(active, "pelvis").map_err(unsupported)?,
    ))
}

fn unsupported(error: String) -> String {
    format!("B1 sole measurement unsupported: {error}")
}

fn sole_body(world: &World) -> Result<(&Session, PublishedBody<'_>), String> {
    if world
        .get_resource::<super::B1DisplaySubdivisionStatus>()
        .is_some_and(|display| display.active)
    {
        return Err(
            "Sole observation requires the original Level 0 body. A Level 1 surface is displayed."
                .into(),
        );
    }
    let (active, _, _, binding) = published_motion_frame(world)?;
    running::resolved_binding(world)?;
    let body = published_body(world, active, binding)?;
    Ok((active, body))
}

fn measure_published(
    world: &World,
    body: &PublishedBody<'_>,
) -> Result<[B1SoleMeasurement; 2], String> {
    let reference = world
        .get_resource::<Assets<ObjVertsAsset>>()
        .and_then(|assets| assets.get(body.source_vertices))
        .ok_or("reference body vertices absent")?;
    let visible = body.visible_source_indices()?;

    let foot = |name: &str, ranges: &[(u16, u16)]| {
        let mut regions = SoleRegions::new();
        for &(low, high) in ranges {
            for source in low..=high {
                let i = usize::from(source);
                let rest = reference
                    .vertices
                    .get(i)
                    .filter(|point| point.is_finite())
                    .ok_or_else(|| format!("{name} reference foot position invalid at {source}"))?;
                if rest.y > SOLE_UPPER_Y_METRES {
                    continue;
                }
                let index = visible[i].ok_or_else(|| {
                    format!("{name} anchored sole source vertex {source} is not visible")
                })?;
                let point = body
                    .point(index)
                    .map_err(|error| format!("{name} anchored sole vertex {source}: {error}"))?;
                regions.add(rest.z, point.as_dvec3());
            }
        }
        let [sole, forefoot, heel] = [
            regions.sole.count,
            regions.forefoot.count,
            regions.heel.count,
        ];
        if [sole, forefoot, heel] != [SOLE_VERTEX_COUNT, FOREFOOT_VERTEX_COUNT, HEEL_VERTEX_COUNT] {
            return Err(format!(
                "{name} anchored sole coverage changed: full {sole}/{SOLE_VERTEX_COUNT}, forefoot {forefoot}/{FOREFOOT_VERTEX_COUNT}, heel {heel}/{HEEL_VERTEX_COUNT}"
            ));
        }
        regions.measure().map_err(|error| format!("{name} {error}"))
    };
    Ok([foot("left", LEFT)?, foot("right", RIGHT)?])
}

struct Region {
    sum: DVec3,
    minimum_y: f64,
    count: usize,
}

impl Region {
    fn new() -> Self {
        Self {
            sum: DVec3::ZERO,
            minimum_y: f64::INFINITY,
            count: 0,
        }
    }

    fn add(&mut self, point: DVec3) {
        self.sum += point;
        self.minimum_y = self.minimum_y.min(point.y);
        self.count += 1;
    }
}

struct SoleRegions {
    sole: Region,
    forefoot: Region,
    heel: Region,
}

impl SoleRegions {
    fn new() -> Self {
        Self {
            sole: Region::new(),
            forefoot: Region::new(),
            heel: Region::new(),
        }
    }

    fn add(&mut self, reference_z: f32, point: DVec3) {
        self.sole.add(point);
        if reference_z >= FOREFOOT_MIN_Z_METRES {
            self.forefoot.add(point);
        } else if reference_z <= HEEL_MAX_Z_METRES {
            self.heel.add(point);
        }
    }

    fn measure(&self) -> Result<B1SoleMeasurement, &'static str> {
        let forefoot_centroid = self.forefoot.sum / self.forefoot.count as f64;
        let heel_centroid = self.heel.sum / self.heel.count as f64;
        let axis = forefoot_centroid - heel_centroid;
        let horizontal_metres = axis.x.hypot(axis.z);
        if !axis.is_finite() || axis.y.hypot(horizontal_metres) <= 1e-6 {
            return Err("sole region centroids do not define a heel-to-forefoot axis");
        }
        Ok(B1SoleMeasurement {
            centroid_metres: (self.sole.sum / self.sole.count as f64).to_array(),
            pitch_degrees: axis.y.atan2(horizontal_metres).to_degrees(),
            heading_degrees: (horizontal_metres > 1e-6).then(|| {
                let heading = axis.x.atan2(axis.z).to_degrees();
                if heading == 180.0 { -180.0 } else { heading }
            }),
            sole_clearance_metres: self.sole.minimum_y,
            forefoot_clearance_metres: self.forefoot.minimum_y,
            heel_clearance_metres: self.heel.minimum_y,
            sole_vertex_count: self.sole.count,
            forefoot_vertex_count: self.forefoot.count,
            heel_vertex_count: self.heel.count,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn yaw(point: DVec3, radians: f64) -> DVec3 {
        let (sin, cos) = radians.sin_cos();
        DVec3::new(
            cos * point.x + sin * point.z,
            point.y,
            cos * point.z - sin * point.x,
        )
    }

    #[test]
    fn signed_pitch_and_floor_distances_are_invariant_under_stage_yaw() {
        for (fore_y, heel_y, expected_pitch) in
            [(0.0, 0.0, 0.0), (0.1, 0.0, 45.0), (-0.05, 0.05, -45.0)]
        {
            for radians in [0.0, 0.8, std::f64::consts::FRAC_PI_2, std::f64::consts::PI] {
                let mut regions = SoleRegions::new();
                for x in [-0.01, 0.01] {
                    regions.add(0.1, yaw(DVec3::new(x, fore_y, 0.1), radians));
                    regions.add(0.0, yaw(DVec3::new(x, heel_y, 0.0), radians));
                }
                let measurement = regions.measure().unwrap();
                assert!((measurement.pitch_degrees - expected_pitch).abs() < 1e-10);
                assert_eq!(measurement.forefoot_clearance_metres, fore_y);
                assert_eq!(measurement.heel_clearance_metres, heel_y);
                assert_eq!(measurement.sole_clearance_metres, fore_y.min(heel_y));
            }
        }
    }

    #[test]
    fn clearance_uses_regional_minima_and_centroid_counts_each_source_vertex() {
        let mut regions = SoleRegions::new();
        regions.add(0.1, DVec3::new(0.0, -0.01, 0.1));
        regions.add(0.1, DVec3::new(0.0, 0.03, 0.1));
        regions.add(0.0, DVec3::new(0.0, 0.01, 0.0));
        let measurement = regions.measure().unwrap();
        assert_eq!(measurement.sole_vertex_count, 3);
        assert_eq!(measurement.forefoot_clearance_metres, -0.01);
        assert_eq!(measurement.heel_clearance_metres, 0.01);
        let expected = DVec3::new(0.0, 0.01, 0.2 / 3.0);
        assert!((DVec3::from_array(measurement.centroid_metres) - expected).length() < 1e-10);
        assert!(measurement.pitch_degrees.abs() < 1e-10);
    }

    #[test]
    fn arch_vertex_affects_full_sole_but_cannot_replace_the_heel() {
        let mut regions = SoleRegions::new();
        // Posed Z is reversed by yaw. The reference position classifies the vertex.
        regions.add(0.1, DVec3::new(0.0, 0.0, -0.1));
        regions.add(0.0, DVec3::new(0.0, 0.1, 0.0));
        regions.add(0.065, DVec3::new(0.0, -0.02, -0.065));
        let measurement = regions.measure().unwrap();
        assert_eq!(measurement.sole_vertex_count, 3);
        assert_eq!(measurement.forefoot_vertex_count, 1);
        assert_eq!(measurement.heel_vertex_count, 1);
        assert_eq!(measurement.sole_clearance_metres, -0.02);
        assert_eq!(measurement.forefoot_clearance_metres, 0.0);
        assert_eq!(measurement.heel_clearance_metres, 0.1);
        assert!((measurement.pitch_degrees + 45.0).abs() < 1e-10);
        let expected = DVec3::new(0.0, 0.08 / 3.0, -0.165 / 3.0);
        assert!((DVec3::from_array(measurement.centroid_metres) - expected).length() < 1e-10);
    }

    #[test]
    fn heading_uses_the_signed_world_projection_despite_translation_and_pitch() {
        let origin = DVec3::new(-2.5, 1.5, 3.0);
        for (delta, expected) in [
            (DVec3::Z, 0.0),
            (DVec3::X, 90.0),
            (DVec3::NEG_X, -90.0),
            (DVec3::NEG_Z, -180.0),
            (DVec3::new(-1.0, 3.0, 1.0), -45.0),
        ] {
            let mut regions = SoleRegions::new();
            regions.add(0.0, origin);
            regions.add(0.1, origin + delta);
            assert!((regions.measure().unwrap().heading_degrees.unwrap() - expected).abs() < 1e-10);
        }
    }

    #[test]
    fn vertical_sole_preserves_pitch_and_clearance_with_undefined_heading() {
        let mut regions = SoleRegions::new();
        regions.add(0.0, DVec3::ZERO);
        regions.add(0.1, DVec3::Y);
        let result = regions.measure().unwrap();
        assert_eq!(result.pitch_degrees, 90.0);
        assert_eq!(result.heel_clearance_metres, 0.0);
        assert_eq!(result.heading_degrees, None);
    }

    #[test]
    fn coincident_centroids_have_no_pitch() {
        let mut regions = SoleRegions::new();
        regions.add(0.1, DVec3::ZERO);
        regions.add(0.0, DVec3::ZERO);
        assert!(regions.measure().is_err());
    }
}

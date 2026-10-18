//! Throwaway #79 controls; integrate only in a new root-owned preview.
//! No fit, weight, position, topology, UV, image or persistence changes.
use bevy::{math::DVec3, prelude::*};

const EYES: &str = include_str!("../62-b1-appearance-preview/assets/eyes/low-poly/low-poly.obj");
const HAIR: &str = include_str!("../62-b1-appearance-preview/assets/hair/short04/short04.obj");

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Control {
    Frozen64,
    HairCoverage,
    EyePolygonNormals,
    EyesUnlitDiagnostic,
}
impl Default for Control {
    fn default() -> Self {
        Self::Frozen64
    }
}
impl Control {
    pub const fn name(self) -> &'static str {
        match self {
            Self::Frozen64 => "frozen64",
            Self::HairCoverage => "hair_coverage",
            Self::EyePolygonNormals => "eye_polygon_normals",
            Self::EyesUnlitDiagnostic => "eyes_unlit_diagnostic",
        }
    }
    pub fn parse(value: &str) -> Result<Self, String> {
        match value {
            "frozen64" => Ok(Self::Frozen64),
            "hair_coverage" => Ok(Self::HairCoverage),
            "eye_polygon_normals" => Ok(Self::EyePolygonNormals),
            "eyes_unlit_diagnostic" => Ok(Self::EyesUnlitDiagnostic),
            _ => Err("unknown quality control".into()),
        }
    }
}

/// Apply after the existing frozen64 material is constructed. Keep all other
/// fields and handle bindings intact. Pass the actual scene camera's MSAA.
/// HairCoverage is the only candidate here; eye unlit is a diagnostic only.
pub fn apply_material(
    material: &mut StandardMaterial,
    hair: bool,
    control: Control,
    camera_msaa: Msaa,
) -> Result<(), &'static str> {
    if control == Control::HairCoverage && hair && camera_msaa == Msaa::Off {
        return Err("hair coverage comparison requires actual camera MSAA > 1");
    }
    // Re-selecting Frozen64 must undo a previous material-only control.
    material.alpha_mode = AlphaMode::Mask(0.5);
    material.unlit = false;
    if control == Control::HairCoverage && hair {
        material.alpha_mode = AlphaMode::AlphaToCoverage;
    }
    if control == Control::EyesUnlitDiagnostic && !hair {
        material.unlit = true;
    }
    Ok(())
}

/// Eye-only initial normal A/B. Keep hair's larger normal change out of this
/// comparison. Pass the existing frozen64 source_normals result as baseline.
pub fn select_normals(
    hair: bool,
    rest: &[[f64; 3]],
    frozen64_normals: &[[f64; 3]],
    control: Control,
) -> Result<Vec<[f64; 3]>, String> {
    if rest.len() != frozen64_normals.len()
        || frozen64_normals.iter().flatten().any(|x| !x.is_finite())
    {
        return Err("frozen64 normal input domain mismatch".into());
    }
    if control == Control::EyePolygonNormals && !hair {
        polygon_normals(false, rest)
    } else {
        Ok(frozen64_normals.to_vec())
    }
}

/// Read source polygons to avoid a fan triangulation weighting one quad corner
/// twice. Preserve original mesh index winding, source IDs and UV corner pairs.
/// This derives NORMAL only. It does not subdivide or change silhouette geometry.
pub fn polygon_normals(hair: bool, rest: &[[f64; 3]]) -> Result<Vec<[f64; 3]>, String> {
    let text = if hair { HAIR } else { EYES };
    let expected = if hair { 865 } else { 96 };
    if rest.len() != expected || rest.iter().flatten().any(|x| !x.is_finite()) {
        return Err("pinned fitted normal domain mismatch".into());
    }
    let mut sums = vec![DVec3::ZERO; rest.len()];
    for line in text.lines() {
        let mut fields = line.split_whitespace();
        if fields.next() != Some("f") {
            continue;
        }
        let ids = fields
            .map(|token| {
                token
                    .split('/')
                    .next()
                    .unwrap_or("")
                    .parse::<usize>()
                    .ok()
                    .and_then(|n| n.checked_sub(1))
                    .filter(|n| *n < rest.len())
                    .ok_or("pinned polygon source ID invalid")
            })
            .collect::<Result<Vec<_>, _>>()?;
        if ids.len() < 3 {
            return Err("pinned polygon has fewer than 3 corners".into());
        }
        // Sum cross-products about a local origin (Newell area vector) to keep
        // translation cancellation small. Direction is independent of fan root.
        let origin = DVec3::from_array(rest[ids[0]]);
        let mut area = DVec3::ZERO;
        for i in 0..ids.len() {
            area += (DVec3::from_array(rest[ids[i]]) - origin)
                .cross(DVec3::from_array(rest[ids[(i + 1) % ids.len()]]) - origin);
        }
        let normal = area.try_normalize().ok_or("degenerate fitted polygon")?;
        for i in 0..ids.len() {
            let p = DVec3::from_array(rest[ids[i]]);
            let prev = (DVec3::from_array(rest[ids[(i + ids.len() - 1) % ids.len()]]) - p)
                .try_normalize()
                .ok_or("zero fitted polygon edge")?;
            let next = (DVec3::from_array(rest[ids[(i + 1) % ids.len()]]) - p)
                .try_normalize()
                .ok_or("zero fitted polygon edge")?;
            let angle = prev.dot(next).clamp(-1., 1.).acos();
            if !angle.is_finite() || angle <= 0. {
                return Err("invalid fitted polygon corner angle".into());
            }
            sums[ids[i]] += normal * angle;
        }
    }
    sums.into_iter()
        .map(|n| {
            n.try_normalize()
                .map(|n| n.to_array())
                .ok_or_else(|| "invalid fitted polygon vertex normal".into())
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn material_controls_restore_and_keep_other_properties() {
        let mut material = StandardMaterial {
            perceptual_roughness: 0.7,
            double_sided: true,
            cull_mode: None,
            ..default()
        };
        apply_material(&mut material, true, Control::HairCoverage, Msaa::Sample4).unwrap();
        assert_eq!(material.alpha_mode, AlphaMode::AlphaToCoverage);
        assert_eq!(material.perceptual_roughness, 0.7);
        assert!(material.double_sided);
        assert!(material.cull_mode.is_none());
        apply_material(
            &mut material,
            false,
            Control::EyesUnlitDiagnostic,
            Msaa::Sample4,
        )
        .unwrap();
        assert!(material.unlit);
        apply_material(&mut material, false, Control::Frozen64, Msaa::Sample4).unwrap();
        assert!(!material.unlit);
        assert_eq!(material.alpha_mode, AlphaMode::Mask(0.5));
    }

    #[test]
    fn missing_msaa_rejects_before_changing_material() {
        let mut material = StandardMaterial::default();
        material.alpha_mode = AlphaMode::Blend;
        assert!(apply_material(&mut material, true, Control::HairCoverage, Msaa::Off).is_err());
        assert_eq!(material.alpha_mode, AlphaMode::Blend);
    }

    #[test]
    fn eye_normal_candidate_keeps_hair_baseline_and_rejects_bad_eye_domain() {
        let baseline = [[0., 0., 1.]];
        assert_eq!(
            select_normals(true, &[[0.; 3]], &baseline, Control::EyePolygonNormals).unwrap(),
            baseline
        );
        assert!(select_normals(false, &[[0.; 3]], &baseline, Control::EyePolygonNormals).is_err());
        assert!(polygon_normals(false, &[[f64::NAN; 3]; 96]).is_err());
    }
}

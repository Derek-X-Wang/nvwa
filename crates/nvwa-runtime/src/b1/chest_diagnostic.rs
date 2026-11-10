//! Fixed adult chest-shape trial inputs. Only the opt-in CPU diagnostic path
//! constructs this resource; ordinary Work, Studio and Web never select it.
use bevy::prelude::Resource;
use sha2::{Digest, Sha256};

#[derive(Clone)]
pub(super) struct DiagnosticTarget {
    pub name: &'static str,
    pub bytes: &'static [u8],
    pub sha256: &'static str,
    pub weight: f32,
    pub origin: &'static str,
}

#[derive(Clone, Resource)]
pub(super) struct DiagnosticChest {
    pub id: &'static str,
    pub targets: Vec<DiagnosticTarget>,
}

const POINT: &[u8] =
    include_bytes!("../../../../experiments/84-chest-diagnostic/targets/breast-point-incr.target");
const UPPER: &[u8] = include_bytes!(
    "../../../../experiments/84-chest-diagnostic/targets/breast-volume-vert-up.target"
);
const MAX_AVG: &[u8] = include_bytes!(
    "../../../../experiments/84-chest-diagnostic/targets/female-young-averagemuscle-averageweight-maxcup-averagefirmness.target"
);
const MAX_FIRM: &[u8] = include_bytes!(
    "../../../../experiments/84-chest-diagnostic/targets/female-young-averagemuscle-averageweight-maxcup-maxfirmness.target"
);
const LIFT_SOFT: &[u8] =
    include_bytes!("../../../../experiments/84-chest-diagnostic/targets/custom-lift-soft.target");
const LIFT_STRONG: &[u8] =
    include_bytes!("../../../../experiments/84-chest-diagnostic/targets/custom-lift-strong.target");

fn target(
    name: &'static str,
    bytes: &'static [u8],
    sha256: &'static str,
    weight: f32,
) -> DiagnosticTarget {
    DiagnosticTarget {
        name,
        bytes,
        sha256,
        weight,
        origin: "official_mpfb_cc0_fixed_commit",
    }
}

fn derived_target(
    name: &'static str,
    bytes: &'static [u8],
    sha256: &'static str,
) -> DiagnosticTarget {
    DiagnosticTarget {
        name,
        bytes,
        sha256,
        weight: 1.0,
        origin: "local_derived_experiment_not_official_mpfb",
    }
}

impl DiagnosticChest {
    pub(super) fn named(id: &str) -> Result<Self, String> {
        let (id, targets): (_, Vec<_>) = match id {
            "neutral" => ("neutral", vec![]),
            "point-100" => (
                "point-100",
                vec![target(
                    "breast-point-incr",
                    POINT,
                    "7f188657f2e57a8b7205a482002925c1715ded6ce47915f7808e737cc83f5538",
                    1.0,
                )],
            ),
            "point-upper-100" => (
                "point-upper-100",
                vec![
                    target(
                        "breast-point-incr",
                        POINT,
                        "7f188657f2e57a8b7205a482002925c1715ded6ce47915f7808e737cc83f5538",
                        1.0,
                    ),
                    target(
                        "breast-volume-vert-up",
                        UPPER,
                        "d2a92824cc03514cf3d6e2dc2ec64ce55645e894cf52111889abe2c2684140e6",
                        1.0,
                    ),
                ],
            ),
            "cup-35" => (
                "cup-35",
                vec![target(
                    "female-young-averagemuscle-averageweight-maxcup-averagefirmness",
                    MAX_AVG,
                    "cc1f76359a7e9224b3d7e2ea159c9b64da5a55998711babe0789d3b6fc1208df",
                    0.35,
                )],
            ),
            "cup-55" => (
                "cup-55",
                vec![target(
                    "female-young-averagemuscle-averageweight-maxcup-averagefirmness",
                    MAX_AVG,
                    "cc1f76359a7e9224b3d7e2ea159c9b64da5a55998711babe0789d3b6fc1208df",
                    0.55,
                )],
            ),
            "cup-firm-55" => (
                "cup-firm-55",
                vec![target(
                    "female-young-averagemuscle-averageweight-maxcup-maxfirmness",
                    MAX_FIRM,
                    "43aab561e082d2416188aafa41f5ec4945e65c614f2afc4a96712e76f3bea141",
                    0.55,
                )],
            ),
            "firm-lift-soft" => (
                "firm-lift-soft",
                vec![
                    target(
                        "female-young-averagemuscle-averageweight-maxcup-maxfirmness",
                        MAX_FIRM,
                        "43aab561e082d2416188aafa41f5ec4945e65c614f2afc4a96712e76f3bea141",
                        0.55,
                    ),
                    derived_target(
                        "custom-lift-soft",
                        LIFT_SOFT,
                        "2faceb6f862006bf9831473bf5edde2be64781f87cc4065f2c833fb77a19bf1a",
                    ),
                ],
            ),
            "firm-lift-strong" => (
                "firm-lift-strong",
                vec![
                    target(
                        "female-young-averagemuscle-averageweight-maxcup-maxfirmness",
                        MAX_FIRM,
                        "43aab561e082d2416188aafa41f5ec4945e65c614f2afc4a96712e76f3bea141",
                        0.55,
                    ),
                    derived_target(
                        "custom-lift-strong",
                        LIFT_STRONG,
                        "dace0504339d69cb9728a6b4a48352f66f884ddb0fb2e36c225666a171fecbd7",
                    ),
                ],
            ),
            "cup35-lift-soft" => (
                "cup35-lift-soft",
                vec![
                    target(
                        "female-young-averagemuscle-averageweight-maxcup-averagefirmness",
                        MAX_AVG,
                        "cc1f76359a7e9224b3d7e2ea159c9b64da5a55998711babe0789d3b6fc1208df",
                        0.35,
                    ),
                    derived_target(
                        "custom-lift-soft",
                        LIFT_SOFT,
                        "2faceb6f862006bf9831473bf5edde2be64781f87cc4065f2c833fb77a19bf1a",
                    ),
                ],
            ),
            _ => return Err(format!("unsupported chest diagnostic candidate: {id}")),
        };
        for item in &targets {
            if !item.weight.is_finite()
                || !(0.0..=1.0).contains(&item.weight)
                || format!("{:x}", Sha256::digest(item.bytes)) != item.sha256
            {
                return Err(format!(
                    "diagnostic target authentication failed: {}",
                    item.name
                ));
            }
        }
        Ok(Self { id, targets })
    }

    pub(super) fn evidence(&self) -> serde_json::Value {
        serde_json::json!({
            "candidate": self.id,
            "status": "experimental_not_a_published_slider",
            "official_source_commit": "d0a32e57a7f915cb2f2b95410e2117648c7bbb7e",
            "derived_recipe": "experiments/84-chest-diagnostic/generate-lift-target.py",
            "targets": self.targets.iter().map(|item| serde_json::json!({
                "name": item.name, "expanded_sha256": item.sha256, "weight": item.weight,
                "origin": item.origin,
            })).collect::<Vec<_>>(),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn only_fixed_authenticated_candidates_are_accepted() {
        for id in [
            "neutral",
            "point-100",
            "point-upper-100",
            "cup-35",
            "cup-55",
            "cup-firm-55",
            "firm-lift-soft",
            "firm-lift-strong",
            "cup35-lift-soft",
        ] {
            DiagnosticChest::named(id).unwrap();
        }
        for id in ["", "cup-100", "cup-55;point", "child", "point-101"] {
            assert!(DiagnosticChest::named(id).is_err());
        }
    }
}

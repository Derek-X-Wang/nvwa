//! Explicit compiled helper and proxy operators; no implicit coordinate conversion.
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};
type Point = [f64; 3];
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MeanPoint {
    pub id: String,
    pub vertices: Vec<usize>,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AxisScale {
    pub vertices: [usize; 2],
    pub axis: usize,
    pub denominator: f64,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProxyVertex {
    pub vertices: [usize; 3],
    pub weights: [f64; 3],
    pub offset: Point,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Garment {
    pub id: String,
    pub scales: [AxisScale; 3],
    pub vertices: Vec<ProxyVertex>,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Bone {
    pub id: String,
    pub parent: Option<String>,
    pub head: String,
    pub tail: String,
    pub roll: f64,
}
#[derive(Clone, Debug, Serialize)]
pub struct EvaluatedBone {
    pub id: String,
    pub parent: Option<String>,
    pub head: Point,
    pub tail: Point,
    pub roll: f64,
}
fn finite(p: &Point) -> bool {
    p.iter().all(|v| v.is_finite())
}
/// Match the audited MPFB centroid rule using explicit topology indices.
pub fn mean_points(body: &[Point], rules: &[MeanPoint]) -> Result<BTreeMap<String, Point>, String> {
    let mut result = BTreeMap::new();
    for r in rules {
        if r.id.is_empty() || r.vertices.is_empty() || result.contains_key(&r.id) {
            return Err("invalid/duplicate helper point".into());
        }
        let mut unique = BTreeSet::new();
        let mut mean = [0.; 3];
        for index in &r.vertices {
            let p = body
                .get(*index)
                .ok_or("helper vertex outside source topology")?;
            if !finite(p) || !unique.insert(index) {
                return Err("non-finite/duplicate helper vertex".into());
            }
            for axis in 0..3 {
                mean[axis] += p[axis];
            }
        }
        for v in &mut mean {
            *v /= r.vertices.len() as f64;
        }
        if !finite(&mean) {
            return Err("non-finite helper centroid".into());
        }
        result.insert(r.id.clone(), mean);
    }
    Ok(result)
}
/// This emits endpoints and declared roll. It does not claim Blender matrices/skinning.
pub fn bones(
    points: &BTreeMap<String, Point>,
    rules: &[Bone],
) -> Result<Vec<EvaluatedBone>, String> {
    let ids: BTreeSet<_> = rules.iter().map(|b| b.id.as_str()).collect();
    if ids.len() != rules.len() || ids.contains("") {
        return Err("invalid/duplicate bone id".into());
    }
    let mut result = Vec::new();
    for b in rules {
        if !b.roll.is_finite()
            || b.parent
                .as_ref()
                .is_some_and(|p| p == &b.id || !ids.contains(p.as_str()))
        {
            return Err("invalid bone parent/roll".into());
        }
        let mut seen = BTreeSet::new();
        let mut parent = b.parent.as_deref();
        while let Some(id) = parent {
            if !seen.insert(id) {
                return Err("bone parent cycle".into());
            }
            parent = rules
                .iter()
                .find(|b| b.id == id)
                .ok_or("bone parent missing")?
                .parent
                .as_deref();
        }
        let head = *points.get(&b.head).ok_or("bone head rule missing")?;
        let tail = *points.get(&b.tail).ok_or("bone tail rule missing")?;
        if !finite(&head) || !finite(&tail) || head == tail {
            return Err("non-finite/zero-length bone".into());
        }
        result.push(EvaluatedBone {
            id: b.id.clone(),
            parent: b.parent.clone(),
            head,
            tail,
            roll: b.roll,
        });
    }
    Ok(result)
}
/// Barycentric source triples plus componentwise scaled offsets, matching the
/// operator in MPFB ClothesService. The compiler supplies all coordinate mappings.
pub fn garment(body: &[Point], rule: &Garment) -> Result<Vec<Point>, String> {
    if rule.id.is_empty() || rule.vertices.is_empty() {
        return Err("empty compiled garment".into());
    }
    let mut scale = [0.; 3];
    for (axis, s) in rule.scales.iter().enumerate() {
        if s.axis > 2 || !s.denominator.is_finite() || s.denominator <= 0. {
            return Err("invalid garment scale rule".into());
        }
        let a = body
            .get(s.vertices[0])
            .ok_or("garment scale vertex outside source topology")?;
        let b = body
            .get(s.vertices[1])
            .ok_or("garment scale vertex outside source topology")?;
        if !finite(a) || !finite(b) {
            return Err("non-finite garment scale source".into());
        }
        scale[axis] = (a[s.axis] - b[s.axis]).abs() / s.denominator;
        if !scale[axis].is_finite() {
            return Err("non-finite garment scale".into());
        }
    }
    let mut result = Vec::with_capacity(rule.vertices.len());
    for v in &rule.vertices {
        if !finite(&v.offset) || v.weights.iter().any(|w| !w.is_finite()) {
            return Err("non-finite garment rule".into());
        }
        // Source proxies use rounded weights; do not silently renormalize them.
        let mut p = [0.; 3];
        for (axis, destination) in p.iter_mut().enumerate() {
            for (index, weight) in v.vertices.iter().zip(v.weights) {
                let point = body
                    .get(*index)
                    .ok_or("garment vertex outside source topology")?;
                if !finite(point) {
                    return Err("non-finite garment source".into());
                }
                *destination += weight * point[axis];
            }
            *destination += v.offset[axis] * scale[axis];
        }
        if !finite(&p) {
            return Err("non-finite garment result".into());
        }
        result.push(p);
    }
    Ok(result)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn handwritten_helper_control_tracks_actual_deformed_vertices() {
        let rules = [MeanPoint {
            id: "tiny-control".into(),
            vertices: vec![0, 2],
        }];
        let base = mean_points(&[[0., 0., 0.], [9., 9., 9.], [2., 4., 6.]], &rules).unwrap();
        assert_eq!(base["tiny-control"], [1., 2., 3.]);
        let changed = mean_points(&[[0., 2., 0.], [9., 9., 9.], [2., 6., 6.]], &rules).unwrap();
        assert_eq!(changed["tiny-control"], [1., 4., 3.]);
    }
    #[test]
    fn handwritten_garment_control_has_recomputed_axis_scales_and_unscaled_source_weights() {
        let g = Garment {
            id: "tiny-control".into(),
            scales: [
                AxisScale {
                    vertices: [0, 1],
                    axis: 0,
                    denominator: 2.,
                },
                AxisScale {
                    vertices: [0, 2],
                    axis: 1,
                    denominator: 2.,
                },
                AxisScale {
                    vertices: [0, 2],
                    axis: 2,
                    denominator: 3.,
                },
            ],
            vertices: vec![ProxyVertex {
                vertices: [0, 1, 2],
                weights: [0.25, 0.5, 0.25],
                offset: [1., 2., 3.],
            }],
        };
        assert_eq!(
            garment(&[[0., 0., 0.], [4., 0., 0.], [0., 6., 6.]], &g).unwrap(),
            vec![[4., 7.5, 7.5]]
        );
    }
    #[test]
    fn helper_and_proxy_fail_closed_on_bad_index_or_denominator() {
        assert!(
            mean_points(
                &[[0.; 3]],
                &[MeanPoint {
                    id: "bad".into(),
                    vertices: vec![1]
                }]
            )
            .is_err()
        );
        let g = Garment {
            id: "bad".into(),
            scales: std::array::from_fn(|_| AxisScale {
                vertices: [0, 0],
                axis: 0,
                denominator: 0.,
            }),
            vertices: vec![ProxyVertex {
                vertices: [0, 0, 0],
                weights: [1., 0., 0.],
                offset: [0.; 3],
            }],
        };
        assert!(garment(&[[0.; 3]], &g).is_err());
    }
    #[test]
    fn bone_cycle_rejected_instead_of_constructing_invalid_rest_hierarchy() {
        let points = BTreeMap::from([("a".into(), [0., 0., 0.]), ("b".into(), [0., 1., 0.])]);
        let r = vec![
            Bone {
                id: "one".into(),
                parent: Some("two".into()),
                head: "a".into(),
                tail: "b".into(),
                roll: 0.,
            },
            Bone {
                id: "two".into(),
                parent: Some("one".into()),
                head: "a".into(),
                tail: "b".into(),
                roll: 0.,
            },
        ];
        assert!(bones(&points, &r).unwrap_err().contains("cycle"));
    }
}

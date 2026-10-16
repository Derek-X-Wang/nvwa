//! Sparse signed-pair operator for the experimental compiled package.
//! The adapter must establish parameter names, source provenance and coordinate basis.
use serde::Deserialize;
use std::collections::BTreeSet;

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Delta {
    pub vertex: usize,
    pub delta: [f64; 3],
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SignedPair {
    pub parameter_id: String,
    pub negative: Vec<Delta>,
    pub positive: Vec<Delta>,
}

/// Evaluate compiled sparse deltas without altering the input basis or source arrays.
/// Each value is a signed unit strength. Zero selects neither branch.
/// These semantics are an explicit package operator, not inferred MakeHuman semantics.
pub fn evaluate(
    basis: &[[f64; 3]],
    pairs: &[SignedPair],
    values: &std::collections::BTreeMap<String, f64>,
) -> Result<Vec<[f64; 3]>, String> {
    if basis.is_empty() || basis.iter().flatten().any(|v| !v.is_finite()) {
        return Err("empty/non-finite compiled basis".into());
    }
    let mut ids = BTreeSet::new();
    if pairs.len() != values.len() {
        return Err("compiled recipe parameter count mismatch".into());
    }
    // Validate all branches, including the unselected branch, before evaluation.
    for p in pairs {
        if p.parameter_id.is_empty() || !ids.insert(p.parameter_id.as_str()) {
            return Err("empty/duplicate compiled parameter".into());
        }
        let value = values
            .get(&p.parameter_id)
            .ok_or("missing compiled parameter")?;
        if !value.is_finite() || !(-1.0..=1.0).contains(value) {
            return Err("non-finite/out-of-domain signed unit strength".into());
        }
        for branch in [&p.negative, &p.positive] {
            let mut vertices = BTreeSet::new();
            for d in branch {
                if d.vertex >= basis.len()
                    || !vertices.insert(d.vertex)
                    || d.delta.iter().any(|v| !v.is_finite())
                {
                    return Err("invalid/duplicate sparse compiled delta".into());
                }
            }
        }
    }
    let mut result = basis.to_vec();
    for p in pairs {
        let value = values[&p.parameter_id];
        let (branch, weight) = if value < 0.0 {
            (&p.negative, -value)
        } else {
            (&p.positive, value)
        };
        for d in branch {
            for (position, delta) in result[d.vertex].iter_mut().zip(d.delta) {
                *position += weight * delta;
                if !position.is_finite() {
                    return Err("non-finite compiled result".into());
                }
            }
        }
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;
    fn pair() -> SignedPair {
        SignedPair {
            parameter_id: "control_only".into(),
            negative: vec![Delta {
                vertex: 1,
                delta: [0., -4., 0.],
            }],
            positive: vec![Delta {
                vertex: 1,
                delta: [0., 2., 0.],
            }],
        }
    }
    fn values(v: f64) -> BTreeMap<String, f64> {
        BTreeMap::from([("control_only".into(), v)])
    }
    #[test]
    fn handwritten_control_signed_midpoints_and_endpoints() {
        let base = [[0., 0., 0.], [2., 0., 0.]];
        for (v, y) in [
            (-1., -4.),
            (-0.5, -2.),
            (-0.25, -1.),
            (0., 0.),
            (0.25, 0.5),
            (0.5, 1.),
            (1., 2.),
        ] {
            assert_eq!(
                evaluate(&base, &[pair()], &values(v)).unwrap(),
                vec![[0., 0., 0.], [2., y, 0.]]
            );
        }
        assert_eq!(base, [[0., 0., 0.], [2., 0., 0.]]);
    }
    #[test]
    fn handwritten_control_combination_adds_without_replacing_prior_target() {
        let a = pair();
        let mut b = pair();
        b.parameter_id = "second_control_only".into();
        b.positive[0].delta = [3., 0., 0.];
        let got = evaluate(
            &[[0., 0., 0.], [2., 0., 0.]],
            &[a, b],
            &BTreeMap::from([
                ("control_only".into(), 0.5),
                ("second_control_only".into(), 0.25),
            ]),
        )
        .unwrap();
        assert_eq!(got, vec![[0., 0., 0.], [2.75, 1., 0.]]);
    }
    #[test]
    fn validates_unselected_branch_and_preserves_basis() {
        let base = [[0., 0., 0.], [2., 0., 0.]];
        let mut p = pair();
        p.negative[0].vertex = 2;
        assert!(
            evaluate(&base, &[p], &values(0.5))
                .unwrap_err()
                .contains("invalid/duplicate sparse")
        );
        assert_eq!(base[1], [2., 0., 0.]);
    }
    #[test]
    fn rejects_duplicate_sparse_index_instead_of_silently_doubling() {
        let mut p = pair();
        p.positive.push(p.positive[0].clone());
        assert!(evaluate(&[[0.; 3]; 2], &[p], &values(0.5)).is_err());
    }
    #[test]
    fn rejects_bad_domain_and_nonfinite_inputs() {
        for v in [f64::NAN, f64::INFINITY, -1.01, 1.01] {
            assert!(evaluate(&[[0.; 3]; 2], &[pair()], &values(v)).is_err());
        }
        let mut p = pair();
        p.negative[0].delta[0] = f64::NAN;
        assert!(evaluate(&[[0.; 3]; 2], &[p], &values(0.5)).is_err());
    }
    #[test]
    fn rejects_missing_unknown_and_duplicate_parameters() {
        assert!(evaluate(&[[0.; 3]; 2], &[pair()], &BTreeMap::new()).is_err());
        assert!(
            evaluate(
                &[[0.; 3]; 2],
                &[pair()],
                &BTreeMap::from([("other".into(), 0.)])
            )
            .is_err()
        );
        let recipe = BTreeMap::from([("control_only".into(), 0.), ("other".into(), 0.)]);
        assert!(evaluate(&[[0.; 3]; 2], &[pair(), pair()], &recipe).is_err());
    }
}

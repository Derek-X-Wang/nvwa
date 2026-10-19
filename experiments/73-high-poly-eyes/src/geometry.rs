//! Experiment-local numeric mirror; source fingerprint in NUMERIC-SOURCE.json.
//! Pinned MHCLO/OBJ fitting and full final-positive skinning. Source units are metres.
//! Preserve signed helper coefficients, every source vertex/UV corner, and all positive bones.
use bevy::math::{DMat4, DVec3};
use nvwa_core::appearance_sha256;
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
type ModelVectors = Vec<[f64; 3]>;
type RenderVectors = Vec<[f32; 3]>;
type SourceWeights = Vec<Vec<f64>>;
type PositiveWeights = Vec<Vec<(usize, f64)>>;
const CAGE: usize = 19158;
const WEIGHTS: &str =
    include_str!("../../../assets/characters/mpfb-b1-v1/weights.game_engine.json");
#[derive(Clone, Debug)]
struct Row {
    helpers: Vec<usize>,
    coefficients: Vec<f64>,
    offset: [f64; 3],
}
#[derive(Clone, Debug)]
pub(super) struct Mapping {
    rows: Vec<Row>,
    scales: [(usize, usize, f64); 3],
}
#[derive(Clone, Debug)]
pub(super) struct Obj {
    pub(super) count: usize,
    pub(super) pairs: Vec<(usize, usize)>,
    pub(super) uv: Vec<[f32; 2]>,
    pub(super) indices: Vec<u32>,
}
fn finite(v: &[f64]) -> Result<(), String> {
    if v.iter().all(|x| x.is_finite()) {
        Ok(())
    } else {
        Err("nonfinite accessory input".into())
    }
}
fn number(s: &str) -> Result<f64, String> {
    let x = s.parse::<f64>().map_err(|_| "invalid number")?;
    finite(&[x])?;
    Ok(x)
}
fn id(s: &str, limit: usize) -> Result<usize, String> {
    let n = s.parse::<usize>().map_err(|_| "invalid index")?;
    if n < limit {
        Ok(n)
    } else {
        Err("index outside declared domain".into())
    }
}
pub(super) fn mapping(text: &str, count: usize) -> Result<Mapping, String> {
    let mut rows = vec![];
    let mut scales = [None; 3];
    let mut section = false;
    let mut obj = false;
    for line in text.lines() {
        let f: Vec<_> = line.split_whitespace().collect();
        if f.is_empty() || f[0].starts_with('#') {
            continue;
        }
        if f == ["verts", "0"] {
            if section {
                return Err("duplicate verts section".into());
            }
            section = true;
            continue;
        }
        if f[0] == "delete_verts" {
            return Err("accessory delete_verts unsupported".into());
        }
        if !section {
            if f[0] == "obj_file" {
                if f.len() != 2 || obj {
                    return Err("invalid obj_file".into());
                }
                obj = true;
            }
            if let Some(a) = ["x_scale", "y_scale", "z_scale"]
                .iter()
                .position(|k| *k == f[0])
            {
                if f.len() != 4 || scales[a].is_some() {
                    return Err("invalid scale rule".into());
                }
                let r = number(f[3])? * 0.1;
                if r.abs() < 1e-12 {
                    return Err("zero scale reference".into());
                }
                scales[a] = Some((id(f[1], CAGE)?, id(f[2], CAGE)?, r));
            }
            continue;
        }
        if f[0] == "material" {
            if f.len() != 2 {
                return Err("invalid material declaration".into());
            }
            continue;
        }
        let (helpers, mut coefficients, offset) = match f.len() {
            1 => (vec![id(f[0], CAGE)?], vec![1.], [0.; 3]),
            9 => (
                f[..3]
                    .iter()
                    .map(|x| id(x, CAGE))
                    .collect::<Result<Vec<_>, _>>()?,
                f[3..6]
                    .iter()
                    .map(|x| number(x))
                    .collect::<Result<Vec<_>, _>>()?,
                [
                    number(f[6])? * 0.1,
                    number(f[7])? * 0.1,
                    number(f[8])? * 0.1,
                ],
            ),
            _ => return Err("unsupported MHCLO row".into()),
        };
        let sum: f64 = coefficients.iter().sum();
        if sum.abs() <= 2f64.powi(-23) {
            return Err("zero coefficient sum".into());
        }
        for x in &mut coefficients {
            *x /= sum;
        }
        rows.push(Row {
            helpers,
            coefficients,
            offset,
        });
    }
    if rows.len() != count || !obj || scales.iter().any(Option::is_none) {
        return Err("incomplete mapping".into());
    }
    Ok(Mapping {
        rows,
        scales: scales.map(Option::unwrap),
    })
}
pub(super) fn obj(text: &str, count: usize) -> Result<Obj, String> {
    let mut vertices = 0;
    let mut tex = vec![];
    let mut pairs = vec![];
    let mut lookup = BTreeMap::new();
    let mut indices = vec![];
    let mut used = BTreeSet::new();
    for line in text.lines() {
        let f: Vec<_> = line.split_whitespace().collect();
        if f.is_empty() || f[0].starts_with('#') {
            continue;
        }
        match f[0] {
            "v" => {
                if f.len() != 4 {
                    return Err("invalid OBJ position".into());
                }
                for v in &f[1..] {
                    number(v)?;
                }
                vertices += 1;
            }
            "vn" => {
                // The high-poly original contains unreferenced normals. Validate
                // their original finite domain, then use the same fitted-source
                // normal recomputation for A and B. Face v/vt/vn remains rejected.
                if f.len() != 4 {
                    return Err("invalid OBJ normal".into());
                }
                for v in &f[1..] {
                    number(v)?;
                }
            }
            "vt" => {
                if f.len() != 3 {
                    return Err("invalid OBJ UV".into());
                }
                tex.push([number(f[1])? as f32, 1. - number(f[2])? as f32]);
            }
            "f" => {
                if f.len() < 4 {
                    return Err("invalid OBJ face".into());
                }
                let mut face = vec![];
                for token in &f[1..] {
                    let p: Vec<_> = token.split('/').collect();
                    if p.len() != 2 {
                        return Err("OBJ requires position/UV corner; supplied normals unsupported for pinned assets".into());
                    }
                    let v = id(p[0], vertices + 1)?
                        .checked_sub(1)
                        .ok_or("OBJ zero index")?;
                    let t = id(p[1], tex.len() + 1)?
                        .checked_sub(1)
                        .ok_or("OBJ zero UV")?;
                    used.insert(v);
                    let next = pairs.len() as u32;
                    let i = *lookup.entry((v, t)).or_insert_with(|| {
                        pairs.push((v, t));
                        next
                    });
                    face.push(i);
                }
                for i in 1..face.len() - 1 {
                    indices.extend([face[0], face[i], face[i + 1]]);
                }
            }
            "o" | "g" | "s" | "usemtl" | "mtllib" => {}
            _ => return Err(format!("unsupported OBJ directive {}", f[0])),
        }
    }
    if vertices != count || used != (0..count).collect() || indices.is_empty() {
        return Err("OBJ missing source coverage".into());
    }
    let uv: Vec<[f32; 2]> = pairs.iter().map(|(_, t)| tex[*t]).collect();
    if uv.iter().flatten().any(|x| !x.is_finite()) {
        return Err("OBJ UV outside finite f32 domain".into());
    }
    Ok(Obj {
        count,
        pairs,
        uv,
        indices,
    })
}
pub(super) fn cage(ids: &[u16], rest: &[[f32; 3]]) -> Result<ModelVectors, String> {
    if ids.len() != rest.len() {
        return Err("cage coverage mismatch".into());
    }
    let mut cage = vec![None; CAGE];
    for (&i, p) in ids.iter().zip(rest) {
        let p = p.map(f64::from);
        finite(&p)?;
        let slot = cage.get_mut(i as usize).ok_or("cage ID outside domain")?;
        if slot.is_some_and(|old| old != p) {
            return Err("conflicting duplicate cage position".into());
        }
        *slot = Some(p);
    }
    cage.into_iter()
        .map(|x| x.ok_or("missing full19158 cage position".into()))
        .collect()
}
pub(super) fn weights(names: &[String]) -> Result<SourceWeights, String> {
    if names.len() != 53 || names.iter().collect::<BTreeSet<_>>().len() != 53 {
        return Err("exact53 unique bones required".into());
    }
    if appearance_sha256(WEIGHTS.as_bytes())
        != "9f4a773e74ce5ba08415b4f30070338e9f75bae5971b5075b10cd6b9caa58473"
    {
        return Err("source weights hash mismatch".into());
    }
    let w: Value = serde_json::from_str(WEIGHTS).map_err(|e| e.to_string())?;
    let w = w["weights"].as_object().ok_or("source weights missing")?;
    if w.len() != 53 {
        return Err("source bone coverage".into());
    }
    let mut result = vec![];
    for name in names {
        let entries = w
            .get(name)
            .and_then(Value::as_array)
            .ok_or("actual bone not in fixed source weights")?;
        let mut row = vec![0.; CAGE];
        let mut used = BTreeSet::new();
        for e in entries {
            let i = e[0].as_u64().ok_or("weight source index")? as usize;
            let v = e[1].as_f64().ok_or("weight number")?;
            if i >= CAGE || !v.is_finite() || v < 0. || !used.insert(i) {
                return Err("invalid source weights".into());
            }
            row[i] = v;
        }
        result.push(row);
    }
    Ok(result)
}
pub(super) fn transfer(mapping: &Mapping, source: &[Vec<f64>]) -> Result<PositiveWeights, String> {
    mapping
        .rows
        .iter()
        .map(|r| {
            let mut row = vec![];
            for (j, weights) in source.iter().enumerate() {
                let v: f64 = r
                    .helpers
                    .iter()
                    .zip(&r.coefficients)
                    .map(|(h, c)| weights[*h] * c)
                    .sum();
                finite(&[v])?;
                if v > 0. {
                    row.push((j, v));
                }
            }
            let sum: f64 = row.iter().map(|x| x.1).sum();
            if sum <= 0. || !sum.is_finite() {
                return Err("no final-positive weight".into());
            }
            for (_, w) in &mut row {
                *w /= sum;
            }
            Ok(row)
        })
        .collect()
}
pub(super) fn fit(
    mapping: &Mapping,
    cage: &[[f64; 3]],
) -> Result<(ModelVectors, [f64; 3]), String> {
    let mut scales = [0.; 3];
    for (a, (lo, hi, reference)) in mapping.scales.iter().enumerate() {
        scales[a] = (cage[*hi][a] - cage[*lo][a]) / reference;
    }
    finite(&scales)?;
    let mut rest = vec![];
    for row in &mapping.rows {
        let mut p = [0.; 3];
        for (a, component) in p.iter_mut().enumerate() {
            *component = row
                .helpers
                .iter()
                .zip(&row.coefficients)
                .map(|(h, c)| cage[*h][a] * c)
                .sum::<f64>()
                + scales[a] * row.offset[a];
        }
        finite(&p)?;
        rest.push(p);
    }
    Ok((rest, scales))
}
pub(super) fn source_normals(rest: &[[f64; 3]], obj: &Obj) -> Result<ModelVectors, String> {
    let mut n = vec![DVec3::ZERO; rest.len()];
    for t in obj.indices.chunks_exact(3) {
        let a = obj.pairs[t[0] as usize].0;
        let b = obj.pairs[t[1] as usize].0;
        let c = obj.pairs[t[2] as usize].0;
        let normal = (DVec3::from_array(rest[b]) - DVec3::from_array(rest[a]))
            .cross(DVec3::from_array(rest[c]) - DVec3::from_array(rest[a]));
        if !normal.is_finite() || normal.length_squared() < 1e-24 {
            return Err("degenerate fitted accessory triangle".into());
        }
        for i in [a, b, c] {
            n[i] += normal;
        }
    }
    n.into_iter()
        .map(|n| {
            let n = n.try_normalize().ok_or("invalid fitted normal")?;
            Ok(n.to_array())
        })
        .collect()
}
pub(super) fn skin(
    rest: &[[f64; 3]],
    normals: &[[f64; 3]],
    weights: &[Vec<(usize, f64)>],
    bones: &[DMat4],
) -> Result<(RenderVectors, RenderVectors), String> {
    if rest.len() != normals.len() || rest.len() != weights.len() || bones.is_empty() {
        return Err("accessory skin row coverage mismatch".into());
    }
    if bones
        .iter()
        .any(|m| !m.is_finite() || !m.determinant().is_finite() || m.determinant().abs() < 1e-12)
    {
        return Err("invalid accessory skin matrix".into());
    }
    for row in weights {
        let sum: f64 = row.iter().map(|(_, w)| *w).sum();
        if row.is_empty()
            || !sum.is_finite()
            || (sum - 1.).abs() > 1e-8
            || row
                .iter()
                .any(|(j, w)| *j >= bones.len() || !w.is_finite() || *w <= 0.)
        {
            return Err("invalid full-positive normalized skin row".into());
        }
    }
    let normal_matrices: Vec<_> = bones.iter().map(|m| m.inverse().transpose()).collect();
    let mut positions = vec![];
    let mut outn = vec![];
    for ((p, n), row) in rest.iter().zip(normals).zip(weights) {
        let mut q = DVec3::ZERO;
        let mut normal = DVec3::ZERO;
        for (j, w) in row {
            q += bones[*j].transform_point3(DVec3::from_array(*p)) * *w;
            normal += normal_matrices[*j].transform_vector3(DVec3::from_array(*n)) * *w;
        }
        if !q.is_finite() {
            return Err("nonfinite posed accessory".into());
        }
        let normal = normal.try_normalize().ok_or("nonfinite posed normal")?;
        let q = q.as_vec3();
        let normal = normal.as_vec3();
        if !q.is_finite() || !normal.is_finite() {
            return Err("posed accessory outside finite f32 domain".into());
        }
        positions.push(q.to_array());
        outn.push(normal.to_array());
    }
    Ok((positions, outn))
}

#[cfg(test)]
mod tests {
    use super::*;
    use bevy::prelude::{Mat4, Vec3};
    #[test]
    fn original_high_poly_standalone_normals_are_finite_and_unreferenced() {
        let original = include_str!("../source/eyes/high-poly/high-poly.obj");
        assert_eq!(
            original.lines().filter(|l| l.starts_with("vn ")).count(),
            1064
        );
        assert!(original.lines().filter(|l| l.starts_with("f ")).all(|l| {
            l.split_whitespace()
                .skip(1)
                .all(|corner| corner.split('/').count() == 2)
        }));
        assert!(obj(original, 1064).is_ok());
        let malformed = original.replacen("vn -0.5529 -0.0472 0.8319", "vn NaN -0.0472 0.8319", 1);
        assert!(obj(&malformed, 1064).is_err());
        let malformed = original.replacen("vn -0.5529 -0.0472 0.8319", "vn 0 1", 1);
        assert!(obj(&malformed, 1064).is_err());
    }
    #[test]
    fn signed_final_transfer_keeps_more_than_four() {
        let m = Mapping {
            rows: vec![Row {
                helpers: vec![0, 1],
                coefficients: vec![2., -1.],
                offset: [0.; 3],
            }],
            scales: [(0, 1, 1.); 3],
        };
        let source = vec![
            vec![0.2, 0.3],
            vec![0.1, 0.],
            vec![0.1, 0.],
            vec![0.1, 0.],
            vec![0.1, 0.],
            vec![0., 0.5],
        ];
        let w = transfer(&m, &source).unwrap();
        assert_eq!(w[0].len(), 5);
        assert!((w[0][0].1 - 1. / 9.).abs() < 1e-12);
        assert!(!w[0].iter().any(|x| x.0 == 5));
    }
    #[test]
    fn cage_requires_complete_and_consistent() {
        assert!(cage(&[0, 0], &[[0., 0., 0.], [1., 0., 0.]]).is_err());
        assert!(cage(&[0], &[[0., 0., 0.]]).is_err());
    }
    #[test]
    fn bad_mappings_and_uv_reject() {
        assert!(mapping("obj_file a\nx_scale 0 1 0\nverts 0\n0", 1).is_err());
        assert!(obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3", 3).is_err());
        assert!(obj("v 0 0 0\nvt 0 0\nf 1/2 1/1 1/1", 1).is_err());
    }
    #[test]
    fn exactly_once_placement() {
        let rest = vec![[1., 2., 3.]];
        let n = vec![[0., 1., 0.]];
        let w = vec![vec![(0, 1.)]];
        let (p, _) = skin(&rest, &n, &w, &[DMat4::IDENTITY]).unwrap();
        let display = Mat4::from_translation(Vec3::new(4., 5., 6.));
        assert_eq!(
            display.transform_point3(Vec3::from_array(p[0])),
            Vec3::new(5., 7., 9.)
        );
    }
}

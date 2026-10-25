//! Offline controls for the actual publication-called short03 import.
use super::*;
use std::collections::BTreeSet;
fn fixture() -> Value {
    let path = std::env::var("NVWA89_FIXED_CAPTURE")
        .expect("root must supply the pinned default capture path");
    let raw = std::fs::read(path).unwrap();
    sha(
        &raw,
        "d79f44812cd6b840bd8d4f15d71b9f4d886ccc05bce062ea5be5232916c6f4d2",
    )
    .unwrap();
    let record: Value = serde_json::from_slice(&raw).unwrap();
    let work: Value =
        serde_json::from_str(record["report"]["work_json"].as_str().unwrap()).unwrap();
    assert_eq!(
        work,
        serde_json::from_str::<Value>(include_str!("../works/default.nvwa.json")).unwrap()
    );
    record
}
fn inputs(record: &Value) -> (Vec<[f64; 3]>, Vec<Vec<f64>>, Vec<DMat4>) {
    let base = &record["frame"]["full_base"];
    let body = base["parts"]
        .as_array()
        .unwrap()
        .iter()
        .find(|p| p["name"] == "body")
        .unwrap();
    let ids: Vec<u16> = serde_json::from_value(body["source_ids"].clone()).unwrap();
    let rest: Vec<[f32; 3]> = serde_json::from_value(body["rest_positions"].clone()).unwrap();
    let cage = geometry::cage(&ids, &rest).unwrap();
    let names = base["bones"]
        .as_array()
        .unwrap()
        .iter()
        .map(|b| b["name"].as_str().unwrap().to_owned())
        .collect::<Vec<_>>();
    let weights = geometry::weights(&names).unwrap();
    let bones = matrices(&base["bones"]).unwrap();
    (cage, weights, bones)
}
#[test]
fn actual_import_fit_transfer_normals_skin_complete_fixed_default() {
    let record = fixture();
    let (cage, weights, bones) = inputs(&record);
    let b = short03_fitted(&cage, &weights).unwrap();
    assert_eq!(
        (b.rest.len(), b.obj.pairs.len(), b.obj.indices.len() / 3),
        (1011, 1071, 1922)
    );
    assert_eq!(
        b.obj.pairs.iter().map(|p| p.0).collect::<BTreeSet<_>>(),
        (0..1011).collect()
    );
    assert_eq!(
        b.obj.pairs.iter().copied().collect::<BTreeSet<_>>().len(),
        1071
    );
    assert!(
        b.rest
            .iter()
            .chain(&b.normals)
            .flatten()
            .all(|x| x.is_finite())
    );
    assert!(
        b.normals
            .iter()
            .all(|n| ((n.iter().map(|x| x * x).sum::<f64>()) - 1.).abs() < 1e-12)
    );
    for row in &b.weights {
        assert!(!row.is_empty());
        assert!(row.iter().all(|(j, w)| *j < 53 && w.is_finite() && *w > 0.));
        assert!((row.iter().map(|x| x.1).sum::<f64>() - 1.).abs() < 1e-12);
    }
    let (p, n) = arrays(&b, &bones).unwrap();
    assert_eq!(p.len(), 1071);
    assert_eq!(n.len(), 1071);
    assert!(p.iter().chain(&n).flatten().all(|x| x.is_finite()));
    let pinned: Value =
        serde_json::from_str(include_str!("../works/b-short03-source-map.json")).unwrap();
    assert_eq!(json!(b.obj.pairs), pinned["source_uv_pairs"]);
    let pinned_uv: Vec<[f32; 2]> = serde_json::from_value(pinned["uv_0"].clone()).unwrap();
    assert_eq!(b.obj.uv, pinned_uv);
    assert_eq!(json!(b.obj.indices), pinned["indices"]);
    println!(
        "short03 actual import: source1011/render1071/triangles1922, complete finite fit/normals/full53-positive weights; maximum influences {}",
        b.weights.iter().map(Vec::len).max().unwrap()
    );
}
#[test]
fn actual_signed_fit_and_decimetre_conversion_once() {
    let record = fixture();
    let (cage, weights, _) = inputs(&record);
    let b = short03_fitted(&cage, &weights).unwrap();
    let expected_scales = [
        (cage[11998][0] - cage[5399][0]) / (1.3980 * 0.1),
        (cage[881][1] - cage[791][1]) / (2.2048 * 0.1),
        (cage[5320][2] - cage[962][2]) / (1.8461 * 0.1),
    ];
    assert_eq!(b.scales, expected_scales);
    // Row6 includes two negative helper coefficients. Compute the signed source
    // formula directly and compare the actual publication-called fitted result.
    let coeff = [1.00906, -0.00473, -0.00433];
    let ids = [7583, 7567, 11972];
    let offset = [0.02100, 0.03873, -0.01894];
    let sum: f64 = coeff.iter().sum();
    for axis in 0..3 {
        let signed = (0..3)
            .map(|k| cage[ids[k]][axis] * (coeff[k] / sum))
            .sum::<f64>()
            + b.scales[axis] * offset[axis] * 0.1;
        assert!((b.rest[6][axis] - signed).abs() < 1e-15);
    }
    let mapping =
        geometry::mapping(include_str!("../candidate/short03/short03.mhclo"), 1011).unwrap();
    let mut bad_cage = cage.clone();
    bad_cage[7583][0] = f64::NAN;
    assert!(geometry::fit(&mapping, &bad_cage).is_err());
}
#[test]
fn actual_transfer_keeps_fifth_positive_and_skins_its_contribution() {
    let mapping = geometry::mapping(
        "obj_file t\nx_scale 0 1 1\ny_scale 0 1 1\nz_scale 0 1 1\nverts 0\n0 1 0 2 -1 0 0 0 0",
        1,
    )
    .unwrap();
    let weights = geometry::transfer(
        &mapping,
        &[
            vec![0.2, 0.3],
            vec![0.1, 0.],
            vec![0.1, 0.],
            vec![0.1, 0.],
            vec![0.1, 0.],
            vec![0., 0.5],
        ],
    )
    .unwrap();
    assert_eq!(weights[0].len(), 5);
    assert!(!weights[0].iter().any(|x| x.0 == 5));
    assert!((weights[0].iter().map(|x| x.1).sum::<f64>() - 1.).abs() < 1e-12);
    let mut bones = vec![DMat4::IDENTITY; 53];
    bones[4] = DMat4::from_translation(bevy::math::DVec3::new(9., 0., 0.));
    let (p, _) = geometry::skin(&[[0., 0., 0.]], &[[0., 1., 0.]], &weights, &bones).unwrap();
    assert!(
        (p[0][0] - 2.).abs() < 1e-6,
        "fifth positive contribution must survive skinning"
    );
}
#[test]
fn actual_short03_import_rejects_truncated_nonfinite_uv_and_source_tamper() {
    let obj = include_str!("../candidate/short03/short03.obj");
    assert!(geometry::obj(obj, 1010).is_err());
    assert!(geometry::obj(&obj.replacen("vt ", "vt NaN ", 1), 1011).is_err());
    assert!(geometry::obj(&obj.replace("/", "//"), 1011).is_err());
    let map = include_str!("../candidate/short03/short03.mhclo");
    assert!(geometry::mapping(map, 1010).is_err());
    assert!(geometry::mapping(&map.replace("1.3980", "NaN"), 1011).is_err());
    assert!(
        sha(
            &[0],
            "4a9fc385718f2c46fb328ab99d33e3a946cecdb717987c8b324cf2466b59bd9c"
        )
        .is_err()
    );
    assert!(short03_image().is_ok());
}
#[test]
fn exact_original_a_replay_gate_stays_bound_to_fixed_capture() {
    let record = fixture();
    let (cage, weights, bones) = inputs(&record);
    let a = fitted(
        include_str!("../../../assets/appearances/mpfb-b1-cc0-v1/hair/short04/short04.mhclo"),
        include_str!("../../../assets/appearances/mpfb-b1-cc0-v1/hair/short04/short04.obj"),
        865,
        &cage,
        &weights,
    )
    .unwrap();
    let hair = record["frame"]["buffers"]
        .as_array()
        .unwrap()
        .iter()
        .find(|b| b["role"] == "hair")
        .unwrap();
    let mut mesh = Mesh::new(
        bevy::mesh::PrimitiveTopology::TriangleList,
        RenderAssetUsages::default(),
    );
    mesh.insert_attribute(
        Mesh::ATTRIBUTE_POSITION,
        serde_json::from_value::<Vec<[f32; 3]>>(hair["positions"].clone()).unwrap(),
    );
    mesh.insert_attribute(
        Mesh::ATTRIBUTE_NORMAL,
        serde_json::from_value::<Vec<[f32; 3]>>(hair["normals"].clone()).unwrap(),
    );
    mesh.insert_attribute(
        Mesh::ATTRIBUTE_UV_0,
        serde_json::from_value::<Vec<[f32; 2]>>(hair["uv_0"].clone()).unwrap(),
    );
    mesh.insert_indices(Indices::U32(
        serde_json::from_value(hair["indices"].clone()).unwrap(),
    ));
    verify_a(&mesh, &a, &bones).unwrap();
    mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, vec![[0., 0., 0.]; 991]);
    assert!(verify_a(&mesh, &a, &bones).is_err());
}

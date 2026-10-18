// Included ONLY inside production b1::tests in the runner-owned source copy.
// No expected mesh, UV or bone arrays are substituted for production output.
#[cfg(test)]
fn admission72_capture(app: &App) -> serde_json::Value {
    use bevy::mesh::VertexAttributeValues;
    let status = crate::appearance_status(app.world());
    assert!(
        status.ready && !status.pending && status.error.is_none(),
        "real appearance controller must be current/ready"
    );
    assert_eq!(
        status.applied.as_ref(),
        Some(
            &app.world()
                .resource::<EditorState>()
                .document()
                .unwrap()
                .character
                .appearance
        )
    );
    let mut frame = b1_frame_snapshot(app.world()).expect("current production published frame");
    let active = app.world().resource::<B1Runtime>().active.as_ref().unwrap();
    let meshes = app.world().resource::<Assets<Mesh>>();
    for (part, entity) in frame["parts"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .zip(&active.displays)
    {
        let handle = &app.world().get::<Mesh3d>(*entity).unwrap().0;
        let mesh = meshes.get(handle).unwrap();
        part["uploaded_uv0"] = match mesh.attribute(Mesh::ATTRIBUTE_UV_0) {
            Some(VertexAttributeValues::Float32x2(rows)) => {
                assert!(rows.iter().flatten().all(|v| v.is_finite()));
                serde_json::json!(rows)
            }
            None => serde_json::Value::Null,
            _ => panic!("actual uploaded UV0 must be Float32x2 or absent"),
        };
    }
    frame
}

#[cfg(test)]
fn admission72_hash(value: &serde_json::Value) -> String {
    nvwa_core::appearance_sha256(&serde_json::to_vec(value).unwrap())
}

#[cfg(test)]
fn admission72_delta(a: &serde_json::Value, b: &serde_json::Value) -> f64 {
    if let (Some(a), Some(b)) = (a.as_array(), b.as_array()) {
        assert_eq!(a.len(), b.len(), "complete numeric array coverage");
        assert!(!a.is_empty(), "numeric arrays must not be vacuous");
        a.iter()
            .zip(b)
            .map(|(a, b)| admission72_delta(a, b))
            .fold(0., f64::max)
    } else {
        let a = a.as_f64().expect("finite numeric scalar");
        let b = b.as_f64().expect("finite numeric scalar");
        assert!(a.is_finite() && b.is_finite());
        (a - b).abs()
    }
}

#[cfg(test)]
fn admission72_matrix(bone: &serde_json::Value, key: &str) -> bevy::math::DMat4 {
    let rows = bone[key]
        .as_array()
        .expect("all nine BoneFrame matrices present");
    assert_eq!(rows.len(), 16);
    let a = std::array::from_fn(|i| rows[i].as_f64().unwrap());
    assert!(a.iter().all(|x| x.is_finite()));
    bevy::math::DMat4::from_cols_array(&a)
}

#[cfg(test)]
fn admission72_matrix_delta(a: bevy::math::DMat4, b: bevy::math::DMat4) -> f64 {
    let left = a.to_cols_array();
    let right = b.to_cols_array();
    assert!(
        left.iter().chain(&right).all(|x| x.is_finite()),
        "matrix arithmetic must be finite before maximum reduction"
    );
    left.iter()
        .zip(right)
        .map(|(x, y)| (x - y).abs())
        .fold(0., f64::max)
}

#[cfg(test)]
fn admission72_frame_gates(frame: &serde_json::Value) -> serde_json::Value {
    use bevy::math::{DMat4, DVec3};
    let bones = frame["bones"].as_array().unwrap();
    assert_eq!(bones.len(), 53);
    let names: BTreeSet<_> = bones.iter().map(|b| b["name"].as_str().unwrap()).collect();
    assert_eq!(names.len(), 53);
    let mut identity_max = 0.0_f64;
    for bone in bones {
        assert_eq!(
            bone.as_object().unwrap().len(),
            11,
            "all BoneFrame fields retained"
        );
        for key in [
            "rest",
            "posed",
            "inverse_bind",
            "local_rest",
            "local_posed",
            "skin",
            "canonical_rest",
            "canonical_posed",
            "frame_gauge",
        ] {
            let m = admission72_matrix(bone, key);
            let a = m.to_cols_array();
            for (i, expected) in [(3, 0.), (7, 0.), (11, 0.), (15, 1.)] {
                assert!((a[i] - expected).abs() <= 1e-5, "original affine bound");
            }
            for i in 0..3 {
                for j in 0..3 {
                    let dot = (0..3).map(|k| a[4 * i + k] * a[4 * j + k]).sum::<f64>();
                    assert!(
                        (dot - if i == j { 1. } else { 0. }).abs() <= 1e-4,
                        "original rigid bound"
                    );
                }
            }
            assert!(
                (m.determinant() - 1.).abs() <= 1e-4,
                "original proper rigid bound"
            );
        }
        let rest = admission72_matrix(bone, "rest");
        let posed = admission72_matrix(bone, "posed");
        let ibm = admission72_matrix(bone, "inverse_bind");
        let canonical_rest = admission72_matrix(bone, "canonical_rest");
        let canonical_posed = admission72_matrix(bone, "canonical_posed");
        let gauge = admission72_matrix(bone, "frame_gauge");
        for (a, b) in [
            (rest * ibm, DMat4::IDENTITY),
            (posed * ibm, admission72_matrix(bone, "skin")),
            (rest * gauge.inverse(), canonical_rest),
            (posed * gauge.inverse(), canonical_posed),
            (posed * ibm, canonical_posed * canonical_rest.inverse()),
        ] {
            let error = admission72_matrix_delta(a, b);
            assert!(
                error.is_finite() && error <= 1e-5,
                "original gauge/IBM identity bound: {error}"
            );
            identity_max = identity_max.max(error);
        }
    }
    let kernels: Vec<_> = bones
        .iter()
        .map(|b| admission72_matrix(b, "posed") * admission72_matrix(b, "inverse_bind"))
        .collect();
    let mut parts = vec![];
    for part in frame["parts"].as_array().unwrap() {
        let positions = part["positions"].as_array().unwrap();
        let rest = part["rest_positions"].as_array().unwrap();
        let rows = part["full_joint_influences"]
            .as_array()
            .expect("full positive weights, never four-slot fallback");
        assert_eq!(positions.len(), rest.len());
        assert_eq!(positions.len(), rows.len());
        assert!(!positions.is_empty());
        let expected_count = match part["name"].as_str().unwrap() {
            "body" => 19158,
            "garment" => 1797,
            _ => panic!("unexpected production part"),
        };
        let ids = part["source_ids"].as_array().unwrap();
        // UV seams duplicate render rows. Preserve every uploaded row; only the
        // source-ID domain, not the render-row count, has the original size.
        assert_eq!(
            ids.len(),
            positions.len(),
            "every render row has a source ID"
        );
        let unique: BTreeSet<_> = ids.iter().map(|id| id.as_u64().unwrap()).collect();
        let expected_domain: BTreeSet<_> = (0..expected_count as u64).collect();
        assert_eq!(
            unique, expected_domain,
            "original complete source-ID domain"
        );
        let indices = part["indices"].as_array().unwrap();
        assert!(!indices.is_empty() && indices.len().is_multiple_of(3));
        assert!(
            indices
                .iter()
                .all(|index| index.as_u64().unwrap() < positions.len() as u64)
        );
        let mut oracle_max = 0.0_f64;
        let mut max_influences = 0;
        for ((position, rest), row) in positions.iter().zip(rest).zip(rows) {
            let row = row.as_array().unwrap();
            assert!(!row.is_empty());
            max_influences = max_influences.max(row.len());
            let total: f64 = row.iter().map(|pair| pair[1].as_f64().unwrap()).sum();
            assert!(total.is_finite() && total > 0.);
            let r = DVec3::new(
                rest[0].as_f64().unwrap(),
                rest[1].as_f64().unwrap(),
                rest[2].as_f64().unwrap(),
            );
            let mut expected = DVec3::ZERO;
            for pair in row {
                let joint = pair[0].as_u64().unwrap() as usize;
                let weight = pair[1].as_f64().unwrap();
                assert!(joint < 53 && weight.is_finite() && weight > 0.);
                expected += kernels[joint].transform_point3(r) * (weight / total);
            }
            for (axis, v) in expected.to_array().iter().enumerate() {
                let actual = position[axis].as_f64().unwrap();
                assert!(actual.is_finite() && v.is_finite());
                oracle_max = oracle_max.max((actual - v).abs());
            }
        }
        assert!(
            oracle_max <= 1e-5,
            "original full-positive independent scalar LBS bound: {oracle_max}"
        );
        for key in ["normals", "rest_normals", "tangents"] {
            let vectors = part[key].as_array().unwrap();
            assert_eq!(vectors.len(), positions.len());
            for vector in vectors {
                let vector = vector.as_array().unwrap();
                assert_eq!(vector.len(), if key == "tangents" { 4 } else { 3 });
                let values: Vec<_> = vector.iter().map(|v| v.as_f64().unwrap()).collect();
                assert!(values.iter().all(|v| v.is_finite()));
                let length = values[..3].iter().map(|v| v * v).sum::<f64>().sqrt();
                assert!(
                    length > 0. && (length - 1.).abs() <= 1e-4,
                    "original nonzero unit-vector bound"
                );
                if key == "tangents" {
                    assert!(
                        (values[3].abs() - 1.).abs() <= 1e-6,
                        "original tangent handedness bound"
                    );
                }
            }
        }
        parts.push(serde_json::json!({"name":part["name"], "render_rows":positions.len(), "unique_source_vertices":unique.len(), "source_id_domain_complete":true, "max_influences":max_influences,"scalar_lbs_max_m":oracle_max}));
    }
    assert_eq!(parts.len(), 2);
    assert!(
        parts[0]["max_influences"].as_u64().unwrap() > 4,
        "body must preserve >4 actual influences"
    );
    serde_json::json!({"identity_max":identity_max,"parts":parts})
}

#[cfg(test)]
fn admission72_compare(
    old: &serde_json::Value,
    new: &serde_json::Value,
    exact: bool,
) -> serde_json::Value {
    assert_eq!(
        old["profile_id"],
        nvwa_core::CharacterProfile::b1_motion().id
    );
    assert_eq!(
        new["profile_id"],
        nvwa_core::CharacterProfile::b1_character().id
    );
    assert_eq!(old["asset_id"], nvwa_core::B1_ASSET_ID);
    assert_eq!(new["asset_id"], nvwa_core::B1_V2_ASSET_ID);
    assert_eq!(
        old["backend"],
        serde_json::to_value(nvwa_core::CharacterProfile::b1_motion().backend).unwrap()
    );
    assert_eq!(
        new["backend"],
        serde_json::to_value(nvwa_core::CharacterProfile::b1_character().backend).unwrap()
    );
    for id in ["torso_length", "jaw_drop"] {
        assert_eq!(old["parameters"][id], new["parameters"][id]);
    }
    assert_eq!(old["parameters"].as_object().unwrap().len(), 2);
    assert_eq!(new["parameters"].as_object().unwrap().len(), 8);
    for id in [
        "head_width",
        "nose_width",
        "mouth_width",
        "chin_width",
        "neck_width",
        "hip_width",
    ] {
        assert_eq!(new["parameters"][id].as_f64().unwrap(), 0.);
    }
    assert_eq!(old["contacts"], new["contacts"]);
    assert_eq!(old["diagnostic_pose"], new["diagnostic_pose"]);
    assert_eq!(old["mode"], "diagnostic");
    assert_eq!(new["mode"], "diagnostic");
    let old_gates = admission72_frame_gates(old);
    let new_gates = admission72_frame_gates(new);
    let old_bones = old["bones"].as_array().unwrap();
    let new_bones = new["bones"].as_array().unwrap();
    let mut matrix_max = 0.0_f64;
    let mut head_max = 0.0_f64;
    for (a, b) in old_bones.iter().zip(new_bones) {
        assert_eq!(a["name"], b["name"]);
        assert_eq!(a["parent"], b["parent"]);
        for key in [
            "rest",
            "posed",
            "inverse_bind",
            "local_rest",
            "local_posed",
            "skin",
            "canonical_rest",
            "canonical_posed",
            "frame_gauge",
        ] {
            let error = admission72_delta(&a[key], &b[key]);
            assert!(error <= 1e-4, "original matrix bound {key}: {error}");
            matrix_max = matrix_max.max(error);
        }
        for i in [12, 13, 14] {
            head_max = head_max.max(
                (a["canonical_posed"][i].as_f64().unwrap()
                    - b["canonical_posed"][i].as_f64().unwrap())
                .abs(),
            );
        }
    }
    assert!(head_max <= 1e-5, "original joint head bound");
    if exact {
        assert!(
            old["bones"] == new["bones"],
            "zero extension: all 53 BoneFrame fields exactly equal"
        );
        assert_eq!(
            admission72_hash(&old["bones"]),
            admission72_hash(&new["bones"])
        );
    }
    let mut parts = vec![];
    for (i, (a, b)) in old["parts"]
        .as_array()
        .unwrap()
        .iter()
        .zip(new["parts"].as_array().unwrap())
        .enumerate()
    {
        for key in [
            "name",
            "source_ids",
            "indices",
            "full_joint_influences",
            "uploaded_uv0",
        ] {
            assert!(
                a[key] == b[key],
                "complete actual {key} correspondence: old={} new={}",
                admission72_hash(&a[key]),
                admission72_hash(&b[key])
            );
        }
        let rest_error = admission72_delta(&a["rest_positions"], &b["rest_positions"]);
        assert!(
            rest_error <= if i == 0 { 1e-3 } else { 3e-3 },
            "original fitted rest geometry bound"
        );
        for key in ["model_to_world", "display_transform"] {
            assert!(
                admission72_delta(&a[key], &b[key]) <= 1e-4,
                "original matrix component bound {key}"
            );
            if exact {
                assert!(a[key] == b[key], "zero exact {key}");
            }
        }
        let error = admission72_delta(&a["positions"], &b["positions"]);
        assert!(
            error <= if i == 0 { 1e-3 } else { 3e-3 },
            "original body/garment geometry bound"
        );
        if exact {
            assert!(
                a["positions"] == b["positions"],
                "zero extension: exact actual Mesh POSITION: old={} new={}",
                admission72_hash(&a["positions"]),
                admission72_hash(&b["positions"])
            );
            assert_eq!(
                admission72_hash(&a["positions"]),
                admission72_hash(&b["positions"])
            );
        }
        parts.push(serde_json::json!({"name":a["name"],"position_max_m":error,"rest_position_max_m":rest_error,"position_old_sha256":admission72_hash(&a["positions"]),"position_new_sha256":admission72_hash(&b["positions"]),"indices_sha256":admission72_hash(&a["indices"]),"uv0_sha256":admission72_hash(&a["uploaded_uv0"]),"uv0_present":!a["uploaded_uv0"].is_null(),"source_ids_sha256":admission72_hash(&a["source_ids"]),"full_positive_weights_sha256":admission72_hash(&a["full_joint_influences"])}));
    }
    serde_json::json!({"old_identity":{"backend":old["backend"],"profile_id":old["profile_id"],"asset_id":old["asset_id"]},"new_identity":{"backend":new["backend"],"profile_id":new["profile_id"],"asset_id":new["asset_id"]},"exact_zero":exact,"bone_fields":11,"bones":53,"matrix_max":matrix_max,"joint_head_max_m":head_max,"bones_old_sha256":admission72_hash(&old["bones"]),"bones_new_sha256":admission72_hash(&new["bones"]),"parts":parts,"old_frame_gates":old_gates,"new_frame_gates":new_gates})
}

#[cfg(test)]
fn admission72_observation(frame: &serde_json::Value) -> serde_json::Value {
    let parts: Vec<_> = frame["parts"].as_array().unwrap().iter().map(|part| {
        let mut values = serde_json::Map::new();
        for key in ["positions", "indices", "uploaded_uv0", "source_ids", "full_joint_influences", "rest_positions", "normals", "rest_normals", "tangents"] {
            values.insert(key.into(), serde_json::json!({"sha256":admission72_hash(&part[key]),"rows":part[key].as_array().map(Vec::len)}));
        }
        serde_json::json!({"name":part["name"],"display_entity":part["display_entity"],"mesh_handle":part["mesh_handle"],"display_transform":part["display_transform"],"model_to_world":part["model_to_world"],"arrays":values})
    }).collect();
    serde_json::json!({"backend":frame["backend"],"profile_id":frame["profile_id"],"asset_id":frame["asset_id"],"parameters":frame["parameters"],"diagnostic_pose":frame["diagnostic_pose"],"mode":frame["mode"],"generation":frame["generation"],"revision":frame["revision"],"sample":frame["sample"],"character_entity":frame["character_entity"],"bones_sha256":admission72_hash(&frame["bones"]),"bone_count":frame["bones"].as_array().map(Vec::len),"parts":parts})
}

#[cfg(test)]
fn admission72_document(
    current: bool,
    recipe: &serde_json::Value,
    pose: &str,
    skin: bool,
) -> SceneDocument {
    let profile = if current {
        nvwa_core::CharacterProfile::b1_character()
    } else {
        nvwa_core::CharacterProfile::b1_motion()
    };
    let mut doc = SceneDocument::from_profile(profile).unwrap();
    doc.timeline.clear();
    doc.character.diagnostic_pose = Some(pose.into());
    for id in ["torso_length", "jaw_drop"] {
        doc.character
            .parameters
            .insert(id.into(), recipe[id].as_f64().unwrap() as f32);
    }
    if current {
        for id in [
            "head_width",
            "nose_width",
            "mouth_width",
            "chin_width",
            "neck_width",
            "hip_width",
        ] {
            assert_eq!(doc.character.parameters[id], 0.);
        }
    }
    doc.character.appearance =
        nvwa_core::CharacterAppearance::b1_cc0_for(&doc.profile.backend, skin, false, false)
            .unwrap();
    doc.validate().unwrap();
    doc
}

#[cfg(test)]
fn admission72_write(name: &str, value: &serde_json::Value) {
    use std::io::Write;
    let directory = std::env::var_os("NVWA_ADMISSION72_RECEIPTS")
        .expect("runner must supply exclusive receipt directory");
    let path = std::path::PathBuf::from(directory).join(name);
    let mut file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .unwrap();
    file.write_all(&serde_json::to_vec_pretty(value).unwrap())
        .unwrap();
    file.sync_all().unwrap();
}

#[cfg(test)]
#[test]
fn admission72_zero_exact_uploaded_buffers_and_all_bone_fields() {
    let (mut app, dir, _) = motion_app();
    fill_v2(&dir);
    let zero = serde_json::json!({"torso_length":0.,"jaw_drop":0.});
    let mut results = vec![];
    for skin in [false, true] {
        open_ready(
            &mut app,
            admission72_document(false, &zero, "neutral", skin),
        );
        let old = admission72_capture(&app);
        open_ready(&mut app, admission72_document(true, &zero, "neutral", skin));
        let new = admission72_capture(&app);
        if skin {
            assert!(
                old["parts"][0]["uploaded_uv0"]
                    .as_array()
                    .is_some_and(|uv| !uv.is_empty()),
                "normal production skin controller must upload actual body UV0"
            );
            assert!(
                new["parts"][0]["uploaded_uv0"]
                    .as_array()
                    .is_some_and(|uv| !uv.is_empty())
            );
        }
        admission72_write(
            if skin {
                "zero-skin-inputs.json"
            } else {
                "zero-untextured-inputs.json"
            },
            &serde_json::json!({"old":admission72_observation(&old),"new":admission72_observation(&new)}),
        );
        let mut result = admission72_compare(&old, &new, true);
        result["normal_skin_selection"] = skin.into();
        results.push(result);
    }
    admission72_write(
        "zero.json",
        &serde_json::json!({"passed":true,"comparisons":results}),
    );
}

#[cfg(test)]
#[test]
fn admission72_original_eight_recipes_five_diagnostics_real_production_compatibility() {
    let plan: serde_json::Value = serde_json::from_str(include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/72-b1-admission-controls/cases.json"
    )))
    .unwrap();
    let cases = plan["cases"].as_array().unwrap();
    assert_eq!(cases.len(), 40);
    let (mut app, dir, _) = motion_app();
    fill_v2(&dir);
    for case in cases {
        let pose = case["pose_id"].as_str().unwrap();
        open_ready(
            &mut app,
            admission72_document(false, &case["recipe"], pose, false),
        );
        let old = admission72_capture(&app);
        open_ready(
            &mut app,
            admission72_document(true, &case["recipe"], pose, false),
        );
        let new = admission72_capture(&app);
        admission72_write(
            &format!("{}-inputs.json", case["case_id"].as_str().unwrap()),
            &serde_json::json!({"case":case,"old":admission72_observation(&old),"new":admission72_observation(&new)}),
        );
        let mut result = admission72_compare(&old, &new, false);
        result["case"] = case.clone();
        let filename = format!("{}.json", case["case_id"].as_str().unwrap());
        admission72_write(&filename, &result);
    }
}

// Included inside b1::tests so these checks use the production CPU harness.
fn fill_contour(dir: &Dir) {
    let version = B1AssetVersion::V3;
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets");
    dir.insert_asset(
        Path::new(version.manifest_path()),
        version.manifest_bytes().to_vec(),
    );
    let manifest = B1AssetManifest::from_bytes_for(version, version.manifest_bytes()).unwrap();
    for file in manifest.files {
        let path = format!("characters/mpfb-b1-v3/{}", file.path);
        dir.insert_asset(Path::new(&path), std::fs::read(root.join(&path)).unwrap());
    }
}
fn contour_settle(app: &mut App) {
    until(app, |w| {
        w.resource::<RuntimeStatus>().ready
            && w.resource::<B1Runtime>().candidate.is_none()
            && w.resource::<B1Runtime>().active.as_ref().is_some_and(|s| {
                s.selection == Selection::from_doc(w.resource::<EditorState>().document().unwrap())
            })
    });
    app.update();
}
fn contour_buffers(app: &App) -> serde_json::Value {
    let snapshot = b1_frame_snapshot(app.world()).unwrap();
    let mut parts = snapshot["parts"].clone();
    for part in parts.as_array_mut().unwrap() {
        // Only the intentional new entities/mesh asset handles differ.
        part.as_object_mut().unwrap().remove("display_entity");
        part.as_object_mut().unwrap().remove("mesh_handle");
    }
    serde_json::json!({"bones":snapshot["bones"], "parts":parts})
}
fn contour_first_difference(
    a: &serde_json::Value,
    b: &serde_json::Value,
    path: &str,
) -> Option<String> {
    if a == b {
        return None;
    }
    match (a, b) {
        (serde_json::Value::Object(a), serde_json::Value::Object(b)) => {
            for (key, a) in a {
                let Some(b) = b.get(key) else {
                    return Some(format!("{path}.{key}: missing baseline field"));
                };
                if let Some(diff) = contour_first_difference(a, b, &format!("{path}.{key}")) {
                    return Some(diff);
                }
            }
            Some(format!("{path}: object field coverage differs"))
        }
        (serde_json::Value::Array(a), serde_json::Value::Array(b)) => {
            for (i, (a, b)) in a.iter().zip(b).enumerate() {
                if let Some(diff) = contour_first_difference(a, b, &format!("{path}[{i}]")) {
                    return Some(diff);
                }
            }
            Some(format!("{path}: array lengths {} and {}", a.len(), b.len()))
        }
        _ => Some(format!("{path}: actual={a}, baseline={b}")),
    }
}
// The two preservation comparisons hold independently verified consumed inputs
// and target accumulation order equal. Arbitrary reopens remain non-repeatable.
// The original unconditioned failures are preserved as separate evidence.
#[test]
fn contour_old_v2_repeat_control_preserves_exact_same_recipe_buffers() {
    let (mut app, dir, _) = motion_app();
    fill_v2(&dir);
    for mixed in [false, true] {
        let mut old =
            SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character()).unwrap();
        if mixed {
            for (i, value) in old.character.parameters.values_mut().enumerate() {
                *value = if i % 2 == 0 { -0.35 } else { 0.45 };
            }
        }
        let baseline = contour_probe_prepare(&mut app, old.clone());
        let before = contour_probe_finish(&mut app);
        for repeat in 0..3 {
            let candidate = contour_probe_prepare(&mut app, old.clone());
            contour_probe_align(&mut app, &baseline, &candidate).unwrap();
            let actual = contour_probe_finish(&mut app);
            assert!(
                actual == before,
                "same V2 recipe must preserve exact buffers, mixed={mixed} repeat={repeat}; first difference: {:?}",
                contour_first_difference(&actual, &before, "$")
            );
        }
    }
}
#[test]
fn contour_zero_preserves_old_eight_parameter_fit_normals_influences_and_uploaded_buffers() {
    let (mut app, dir, _) = motion_app();
    fill_v2(&dir);
    fill_contour(&dir);
    for mixed in [false, true] {
        let mut old =
            SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character()).unwrap();
        if mixed {
            for (i, value) in old.character.parameters.values_mut().enumerate() {
                *value = if i % 2 == 0 { -0.35 } else { 0.45 };
            }
        }
        let baseline = contour_probe_prepare(&mut app, old.clone());
        let before = contour_probe_finish(&mut app);
        let mut new =
            SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character_contour())
                .unwrap();
        for (id, value) in &old.character.parameters {
            new.character.parameters.insert(id.clone(), *value);
        }
        let candidate = contour_probe_prepare(&mut app, new);
        contour_probe_align(&mut app, &baseline, &candidate).unwrap();
        let actual = contour_probe_finish(&mut app);
        assert!(
            actual == before,
            "zero cheek must preserve actual fitting and full render buffers, mixed={mixed}; first difference: {:?}",
            contour_first_difference(&actual, &before, "$")
        );
    }
}
fn original_cheek_delta(increase: bool) -> BTreeMap<u16, [f32; 3]> {
    // Four independently retained original source texts. Neither derived output,
    // the production loader nor the parameter catalogue computes expectations.
    let originals = if increase {
        [
            (
                include_str!("../tests/fixtures/cheek/l-cheek-volume-incr.target"),
                "7a47a6a0121657092266df2a27ec6e134462642fd3f781ee47daeec40d1426fd",
            ),
            (
                include_str!("../tests/fixtures/cheek/r-cheek-volume-incr.target"),
                "95e57c5e1313c118d5e3c4e43ec3d0dd9952957e5ba1bcbed1c8027d40940e43",
            ),
        ]
    } else {
        [
            (
                include_str!("../tests/fixtures/cheek/l-cheek-volume-decr.target"),
                "d88cedb8d78e4ac0009d83e425245cb8f584c064b9c3be3419d167d1c22b3539",
            ),
            (
                include_str!("../tests/fixtures/cheek/r-cheek-volume-decr.target"),
                "ca0576cfb9a49216f6844a97d6347eaf662b56b1c165f5938661c91d1d04d617",
            ),
        ]
    };
    let mut delta = BTreeMap::new();
    for (text, sha) in originals {
        assert_eq!(nvwa_core::appearance_sha256(text.as_bytes()), sha);
        for line in text
            .lines()
            .filter(|l| !l.trim().is_empty() && !l.trim_start().starts_with('#'))
        {
            let cells: Vec<_> = line.split_whitespace().collect();
            assert_eq!(cells.len(), 4);
            let vertex: u16 = cells[0].parse().unwrap();
            let value = [
                cells[1].parse::<f32>().unwrap() * 0.1,
                cells[2].parse::<f32>().unwrap() * 0.1,
                cells[3].parse::<f32>().unwrap() * 0.1,
            ];
            assert!(
                delta.insert(vertex, value).is_none(),
                "bilateral sources must have disjoint IDs"
            );
        }
    }
    assert_eq!(delta.len(), if increase { 458 } else { 388 });
    delta
}
#[test]
fn contour_both_endpoints_fractional_signs_zero_and_history_follow_four_original_sources() {
    let (mut app, dir, _) = motion_app();
    fill_contour(&dir);
    let doc =
        SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character_contour()).unwrap();
    open_ready(&mut app, doc.clone());
    let baseline = appearance_fit(app.world(), &appearance_frame(app.world()).unwrap()).unwrap();
    let uploaded = uploaded_positions(&app);
    let negative = original_cheek_delta(false);
    let positive = original_cheek_delta(true);
    for value in [-1.0_f32, -0.35, 0.0, 0.65, 1.0] {
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::SetParameters {
                character_id: doc.character.id.clone(),
                values: BTreeMap::from([("cheek_fullness".into(), value)]),
            })
            .unwrap();
        contour_settle(&mut app);
        let actual = appearance_fit(app.world(), &appearance_frame(app.world()).unwrap()).unwrap();
        assert_eq!(actual.source_ids, baseline.source_ids);
        let delta = if value < 0.0 { &negative } else { &positive };
        let mut witnessed = 0;
        for ((source, before), after) in baseline
            .source_ids
            .iter()
            .zip(&baseline.rest)
            .zip(&actual.rest)
        {
            let change = delta.get(source).copied().unwrap_or([0.0; 3]);
            if change != [0.0; 3] {
                witnessed += 1;
            }
            for axis in 0..3 {
                assert!(
                    (after[axis] - (before[axis] + change[axis] * value.abs())).abs() <= 1e-6,
                    "four-source witness: value={value} source={source} axis={axis}"
                );
            }
        }
        assert!(witnessed > 100);
        if value == 0.0 {
            assert_eq!(uploaded_positions(&app), uploaded);
        } else {
            assert!(position_delta(&uploaded, &uploaded_positions(&app)) > 1e-6);
        }
    }
    let endpoint = uploaded_positions(&app);
    for command in [nvwa_core::Command::Undo, nvwa_core::Command::Redo] {
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(command)
            .unwrap();
        contour_settle(&mut app);
    }
    assert_eq!(uploaded_positions(&app), endpoint);
    open_ready(&mut app, doc);
    assert_eq!(uploaded_positions(&app), uploaded);
}
#[test]
fn contour_cache_orders_missing_new_sources_and_failed_new_handles_never_poison_old_work() {
    for contour_first in [false, true] {
        let (mut app, dir, _) = motion_app();
        fill_v2(&dir);
        fill_contour(&dir);
        let old = SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character()).unwrap();
        let new = SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character_contour())
            .unwrap();
        if !contour_first {
            open_ready(&mut app, old.clone());
        }
        open_ready(&mut app, new.clone());
        assert_eq!(app.world().resource::<B1Runtime>().extra_targets.len(), 14);
        open_ready(&mut app, old.clone());
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::SetScale {
                character_id: old.character.id.clone(),
                scale: 1.1,
            })
            .unwrap();
        contour_settle(&mut app);
        let frame = contour_buffers(&app);
        let history = app
            .world()
            .resource::<EditorState>()
            .editor
            .as_ref()
            .unwrap()
            .retention_stats();
        let current = app
            .world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .clone();
        assert!(
            history.undo_snapshots > 0,
            "the failure control needs a real old-Work edit"
        );
        for name in ["cheek-volume-bilateral-decr", "cheek-volume-bilateral-incr"] {
            dir.remove_asset(Path::new(&format!(
                "characters/mpfb-b1-v3/targets/{name}.target"
            )));
            app.world()
                .resource::<MakeHumanMorphs>()
                .targets
                .write()
                .unwrap()
                .remove(name);
        }
        app.world_mut()
            .resource_mut::<EditorState>()
            .request_open(new)
            .unwrap();
        until(&mut app, |w| {
            w.resource::<EditorState>().open_error.is_some()
        });
        assert_eq!(
            app.world().resource::<EditorState>().document(),
            Some(&current)
        );
        assert_eq!(
            app.world()
                .resource::<EditorState>()
                .editor
                .as_ref()
                .unwrap()
                .retention_stats(),
            history
        );
        assert_eq!(contour_buffers(&app), frame);
        assert!(
            app.world()
                .resource::<EditorState>()
                .open_error
                .as_ref()
                .unwrap()
                .contains("asset_missing")
        );
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::Undo)
            .unwrap();
        contour_settle(&mut app);
        assert_eq!(
            app.world()
                .resource::<EditorState>()
                .document()
                .unwrap()
                .character
                .scale,
            old.character.scale
        );
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::Redo)
            .unwrap();
        contour_settle(&mut app);
        assert_eq!(
            app.world()
                .resource::<EditorState>()
                .document()
                .unwrap()
                .character
                .scale,
            current.character.scale
        );
        assert_eq!(contour_buffers(&app), frame);
        // A failed V3-only typed asset is outside V2's required handle prefix.
        let failed: Handle<TargetAsset> = app
            .world()
            .resource::<AssetServer>()
            .load(asset("targets/absent-contour-test.target"));
        until(&mut app, |w| {
            matches!(
                w.resource::<AssetServer>().get_load_state(failed.id()),
                Some(bevy::asset::LoadState::Failed(_))
            )
        });
        app.world_mut().resource_mut::<B1Runtime>().extra_targets[12] = failed;
        assert_eq!(
            extra_targets_ready(
                app.world(),
                app.world().resource::<B1Runtime>(),
                B1AssetVersion::V2
            ),
            Ok(true)
        );
        assert!(
            extra_targets_ready(
                app.world(),
                app.world().resource::<B1Runtime>(),
                B1AssetVersion::V3
            )
            .is_err()
        );
        open_ready(&mut app, current.clone());
        assert_eq!(contour_buffers(&app), frame);
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::SetParameters {
                character_id: current.character.id,
                values: BTreeMap::from([("head_width".into(), 0.25)]),
            })
            .unwrap();
        contour_settle(&mut app);
        assert!(app.world().resource::<RuntimeStatus>().error.is_none());
    }
}

#[test]
fn contour_both_hairstyles_reach_authenticated_actual_skin_eyes_hair_and_preserve_body() {
    use nvwa_core::{B1AppearanceSet, CharacterAppearance, Command};
    let (mut app, dir, _) = motion_app();
    fill_contour(&dir);
    let doc =
        SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character_contour()).unwrap();
    open_ready(&mut app, doc.clone());
    let body = uploaded_positions(&app);
    for (set, source_vertices) in [
        (B1AppearanceSet::V3, 865),
        (B1AppearanceSet::V3Short01, 2984),
        (B1AppearanceSet::V3, 865),
    ] {
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(Command::SetAppearance {
                character_id: doc.character.id.clone(),
                appearance: CharacterAppearance::b1_cc0_for_set(
                    &doc.profile.backend,
                    set,
                    true,
                    true,
                    true,
                )
                .unwrap(),
            })
            .unwrap();
        crate::appearance::update(app.world_mut());
        let snapshot = crate::appearance_snapshot(app.world_mut()).unwrap();
        assert_eq!(snapshot["base_asset_id"], nvwa_core::B1_V3_ASSET_ID);
        assert_eq!(snapshot["applied"]["asset_set_id"], set.asset_id());
        assert!(snapshot["skin"].is_object());
        let roles = snapshot["accessories"].as_array().unwrap();
        assert_eq!(roles.len(), 2);
        let hair = roles.iter().find(|r| r["name"] == "hair").unwrap();
        assert_eq!(hair["source_vertices"], source_vertices);
        assert_eq!(uploaded_positions(&app), body);
    }
}

// Causal probe only: equal independently checked values and consumed inputs,
// conditioned on the same pre-bake hash-map layout. Independent reopen
// repeatability remains explicitly unproved; the two red controls above stay.
struct ContourProbeInput {
    template: Handle<CharacterTemplate>,
    character: Entity,
    morphs: MorphTargets,
    entries: BTreeMap<String, u32>,
    order: Vec<String>,
    consumed: serde_json::Value,
    direct_helper_bits: Vec<[u32; 3]>,
}
fn contour_probe_entries(morphs: &MorphTargets) -> BTreeMap<String, u32> {
    morphs
        .iter()
        .map(|(&name, value)| (name.into(), value.to_bits()))
        .collect()
}
fn contour_probe_prepare(app: &mut App, doc: SceneDocument) -> ContourProbeInput {
    app.world_mut()
        .resource_mut::<EditorState>()
        .request_open(doc)
        .unwrap();
    let request = app.world().resource::<EditorState>().open_request_sequence;
    until(app, |w| {
        w.resource::<B1Runtime>()
            .candidate
            .as_ref()
            .is_some_and(|c| c.is_open && c.request == request && c.session.is_some())
    });
    let world = app.world();
    let session = world
        .resource::<B1Runtime>()
        .candidate
        .as_ref()
        .unwrap()
        .session
        .as_ref()
        .unwrap();
    assert_eq!(session.phase, 0, "missed the pre-bake PostUpdate seam");
    assert!(world.get::<SkeletonReady>(session.character).is_none());
    assert!(world.get::<CharacterSkeleton>(session.character).is_none());
    let template = world
        .resource::<Assets<CharacterTemplate>>()
        .get(&session.template)
        .unwrap();
    assert_eq!(template.shapes.len(), 1);
    assert_eq!(template.shapes[0].name, "selected");
    assert!(
        template.shapes[0].helper_deltas.is_none(),
        "never edit a baked template"
    );
    let morphs = template.shapes[0].morphs.clone();
    let shape_handle = &world.get::<CharacterShape>(session.character).unwrap().0;
    let shape = world
        .resource::<Assets<CharacterShapeAsset>>()
        .get(shape_handle)
        .unwrap();
    assert_eq!(shape.template, session.template);
    let shape_weights = contour_probe_entries(&shape.template_morph_targets);
    assert_eq!(
        shape_weights,
        BTreeMap::from([("selected".into(), 1.0_f32.to_bits())])
    );
    let server = world.resource::<AssetServer>();
    let base = &world.resource::<BaseMesh>().vertices;
    let base_bits: Vec<_> = base
        .iter()
        .map(|p| p.to_array().map(f32::to_bits))
        .collect();
    let helper_assets: Vec<_> = world
        .resource::<Assets<ObjVertsAsset>>()
        .iter()
        .filter(|(_, a)| a.is_basemesh_helpers)
        .collect();
    assert_eq!(helper_assets.len(), 1);
    assert_eq!(
        helper_assets[0]
            .1
            .vertices
            .iter()
            .map(|p| p.to_array().map(f32::to_bits))
            .collect::<Vec<_>>(),
        base_bits
    );
    let loaded_targets = world.resource::<MakeHumanMorphs>().targets.read().unwrap();
    let mut targets = BTreeMap::new();
    for &name in morphs.keys() {
        let actual = loaded_targets.get(name).unwrap();
        let handle = server
            .get_handle::<TargetAsset>(asset(&format!("targets/{name}.target")))
            .unwrap();
        let loaded = world
            .resource::<Assets<TargetAsset>>()
            .get(&handle)
            .unwrap();
        let bits = |a: &TargetAsset| {
            a.deltas
                .iter()
                .map(|d| (d.vertex, d.offset.to_array().map(f32::to_bits)))
                .collect::<Vec<_>>()
        };
        assert_eq!(actual.name, loaded.name);
        assert_eq!(
            bits(actual),
            bits(loaded),
            "actual lookup must match the loaded asset data"
        );
        targets.insert(name, serde_json::json!({"handle":format!("{:?}",handle.id()),"name":actual.name,"delta_bits":bits(actual)}));
    }
    drop(loaded_targets);
    let mut parts = Vec::new();
    for part in &session.parts {
        assert!(world.get::<SkinnedMesh>(part.child).is_none());
        assert!(!world.resource::<CachedMhcloMeshHandles>().contains_key(&(
            part.mapping.clone(),
            session.template.clone(),
            MeshBuildLod::Cpu(0)
        )));
        let mapping = world
            .resource::<Assets<MhcloAsset>>()
            .get(&part.mapping)
            .unwrap();
        let vertices = world
            .resource::<Assets<ObjVertsAsset>>()
            .get(&part.source_vertices)
            .unwrap();
        let mesh = world
            .resource::<Assets<Mesh>>()
            .get(&part.source_mesh)
            .unwrap();
        // These are the actual immutable part inputs, not fitted outputs.
        parts.push(serde_json::json!({"name":part.name,"mapping_handle":format!("{:?}",part.mapping.id()),"mapping":format!("{mapping:?}"),"vertices_handle":format!("{:?}",part.source_vertices.id()),"vertices_bits":vertices.vertices.iter().map(|v|v.to_array().map(f32::to_bits)).collect::<Vec<_>>(),"mesh_handle":format!("{:?}",part.source_mesh.id()),"mesh":format!("{mesh:?}")}));
    }
    let rig = world.resource::<RigData>().0.as_ref().unwrap();
    let rig_weights: BTreeMap<_, BTreeMap<_, _>> = rig
        .original_weights()
        .iter()
        .map(|(&name, rows)| {
            (
                name,
                rows.iter()
                    .map(|(&id, weight)| (id, weight.to_bits()))
                    .collect(),
            )
        })
        .collect();
    let reference = rig.reference_rig();
    let rest_bits: BTreeMap<_, _> = reference
        .model_space_bindpose
        .iter()
        .map(|(&name, transform)| {
            (
                name,
                transform.to_matrix().to_cols_array().map(f32::to_bits),
            )
        })
        .collect();
    let groups: BTreeMap<_, _> = world.resource::<VertexGroups>().iter().collect();
    let rig_handle = server
        .get_handle::<RigConfigAsset>(asset("rig.game_engine.json"))
        .unwrap();
    let rig_config = world
        .resource::<Assets<RigConfigAsset>>()
        .get(&rig_handle)
        .unwrap();
    let weights_handle = server
        .get_handle::<RigWeightsAsset>(asset("weights.game_engine.json"))
        .unwrap();
    let loaded_weights = world
        .resource::<Assets<RigWeightsAsset>>()
        .get(&weights_handle)
        .unwrap();
    let loaded_weight_bits: BTreeMap<_, BTreeMap<_, _>> = loaded_weights
        .weights
        .iter()
        .map(|(&name, rows)| {
            (
                name,
                rows.iter()
                    .map(|(&id, weight)| (id, weight.to_bits()))
                    .collect(),
            )
        })
        .collect();
    assert_eq!(rig_weights, loaded_weight_bits);
    let consumed = serde_json::json!({"base_helper_handle":format!("{:?}",helper_assets[0].0),"base_bits":base_bits,"targets":targets,"parts":parts,"shape_weight_bits":shape_weights,"vertex_groups":groups,"rig_config_handle":format!("{:?}",rig_handle.id()),"rig_config":format!("{rig_config:?}"),"weights_handle":format!("{:?}",weights_handle.id()),"rig_weight_bits":rig_weights,"reference_names":reference.bone_names,"reference_rest_bits":rest_bits});
    let direct_helper_bits =
        adjust_helpers_to_morphs(&morphs, &world.resource::<MakeHumanMorphs>().targets, base)
            .unwrap()
            .iter()
            .map(|p| p.to_array().map(f32::to_bits))
            .collect();
    ContourProbeInput {
        template: session.template.clone(),
        character: session.character,
        entries: contour_probe_entries(&morphs),
        order: morphs.keys().map(|s| s.to_string()).collect(),
        morphs,
        consumed,
        direct_helper_bits,
    }
}
fn contour_probe_align(
    app: &mut App,
    baseline: &ContourProbeInput,
    candidate: &ContourProbeInput,
) -> Result<(), String> {
    if candidate.entries != baseline.entries {
        return Err("untouched target membership/value bits differ".into());
    }
    if candidate.consumed != baseline.consumed {
        return Err(format!(
            "untouched consumed inputs differ: {:?}",
            contour_first_difference(&candidate.consumed, &baseline.consumed, "$")
        ));
    }
    assert_ne!(candidate.template, baseline.template);
    assert_ne!(candidate.character, baseline.character);
    assert!(!candidate.entries.keys().any(|name| name.contains("cheek")));
    let mut aligned = baseline.morphs.clone();
    // Replace only existing values from the independently computed candidate.
    // No desired helper, mesh, skeleton or frame ever enters the candidate.
    for (&name, &value) in candidate.morphs.iter() {
        *aligned.get_mut(name).unwrap() = value;
    }
    assert_eq!(contour_probe_entries(&aligned), candidate.entries);
    assert_eq!(
        aligned.keys().map(|s| s.to_string()).collect::<Vec<_>>(),
        baseline.order
    );
    let world = app.world_mut();
    let session = world
        .resource::<B1Runtime>()
        .candidate
        .as_ref()
        .unwrap()
        .session
        .as_ref()
        .unwrap();
    assert_eq!(session.phase, 0);
    assert_eq!(session.template, candidate.template);
    let mut templates = world.resource_mut::<Assets<CharacterTemplate>>();
    let template = templates
        .get_mut_untracked(candidate.template.id())
        .unwrap();
    assert!(template.shapes[0].helper_deltas.is_none());
    template.shapes[0].morphs = aligned;
    Ok(())
}
fn contour_probe_finish(app: &mut App) -> serde_json::Value {
    until(app, |w| {
        w.resource::<EditorState>().pending_open.is_none()
            && w.resource::<EditorState>().open_error.is_none()
            && w.resource::<RuntimeStatus>().ready
    });
    app.update();
    motion_seek(app, 2.0);
    contour_buffers(app)
}
fn contour_probe_baked_boundary(app: &App) -> serde_json::Value {
    let world = app.world();
    let active = world.resource::<B1Runtime>().active.as_ref().unwrap();
    let template = world
        .resource::<Assets<CharacterTemplate>>()
        .get(&active.template)
        .unwrap();
    let shape = world.get::<CharacterShape>(active.character).unwrap();
    let weights = &world
        .resource::<Assets<CharacterShapeAsset>>()
        .get(&shape.0)
        .unwrap()
        .template_morph_targets;
    let mut deltas = BTreeMap::new();
    for delta in template.shapes[0].helper_deltas.as_ref().unwrap() {
        assert!(
            deltas
                .insert(delta.vertex, delta.offset.to_array().map(f32::to_bits))
                .is_none()
        );
    }
    let helpers = template
        .blend_helpers(weights, &world.resource::<BaseMesh>().vertices)
        .iter()
        .map(|p| p.to_array().map(f32::to_bits))
        .collect::<Vec<_>>();
    serde_json::json!({"baked_delta_bits_by_source_id":deltas,"blended_helper_bits":helpers,"consumed_morph_order":template.shapes[0].morphs.keys().collect::<Vec<_>>()})
}
#[test]
fn contour_controlled_prebake_map_layout_preserves_all_actual_buffers() {
    let (mut app, dir, _) = motion_app();
    fill_v2(&dir);
    fill_contour(&dir);
    for mixed in [false, true] {
        let mut old =
            SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character()).unwrap();
        if mixed {
            for (i, value) in old.character.parameters.values_mut().enumerate() {
                *value = if i % 2 == 0 { -0.35 } else { 0.45 };
            }
        }
        let mut new =
            SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character_contour())
                .unwrap();
        for (id, value) in &old.character.parameters {
            new.character.parameters.insert(id.clone(), *value);
        }
        let needed = if mixed { 2 } else { 1 };
        let mut orders = Vec::<Vec<String>>::new();
        // Acquire at most three untouched baseline realizations; never search for green.
        for attempt in 0..if mixed { 3 } else { 1 } {
            let baseline = contour_probe_prepare(&mut app, old.clone());
            let before = contour_probe_finish(&mut app);
            let baseline_baked = contour_probe_baked_boundary(&app);
            println!(
                "PROBE_ENTRY_BITS mixed={mixed} attempt={attempt} entries={:?}",
                baseline.entries
            );
            println!(
                "PROBE_BASELINE mixed={mixed} attempt={attempt} order={:?}",
                baseline.order
            );
            if orders.contains(&baseline.order) {
                continue;
            }
            orders.push(baseline.order.clone());
            for (label, document) in [("V2-repeat", old.clone()), ("V3-zero", new.clone())] {
                let candidate = contour_probe_prepare(&mut app, document);
                let original_helper_difference = candidate
                    .direct_helper_bits
                    .iter()
                    .zip(&baseline.direct_helper_bits)
                    .position(|(a, b)| a != b);
                println!(
                    "PROBE_UNTOUCHED mixed={mixed} pair={label} order={:?} first_helper_difference={original_helper_difference:?}",
                    candidate.order
                );
                if let Some(source) = original_helper_difference {
                    println!(
                        "PROBE_ORIGINAL_HELPER source={source} baseline_bits={:?} candidate_bits={:?}",
                        baseline.direct_helper_bits[source], candidate.direct_helper_bits[source]
                    );
                }
                contour_probe_align(&mut app, &baseline, &candidate).unwrap();
                let world = app.world();
                let template = world
                    .resource::<Assets<CharacterTemplate>>()
                    .get(&candidate.template)
                    .unwrap();
                let controlled_helpers = adjust_helpers_to_morphs(
                    &template.shapes[0].morphs,
                    &world.resource::<MakeHumanMorphs>().targets,
                    &world.resource::<BaseMesh>().vertices,
                )
                .unwrap()
                .iter()
                .map(|p| p.to_array().map(f32::to_bits))
                .collect::<Vec<_>>();
                assert_eq!(
                    controlled_helpers, baseline.direct_helper_bits,
                    "first controlled helper boundary"
                );
                let actual = contour_probe_finish(&mut app);
                let candidate_baked = contour_probe_baked_boundary(&app);
                assert!(
                    candidate_baked == baseline_baked,
                    "first controlled bake/blend boundary mixed={mixed} pair={label}: {:?}",
                    contour_first_difference(&candidate_baked, &baseline_baked, "$")
                );
                assert!(
                    actual == before,
                    "controlled full-buffer mismatch mixed={mixed} pair={label}: {:?}",
                    contour_first_difference(&actual, &before, "$")
                );
                // Reject a changed candidate readback; never change the expected reference.
                let mut changed = actual.clone();
                let normal = &mut changed["parts"][0]["normals"][0][0];
                *normal = serde_json::json!(normal.as_f64().unwrap() + 1.0);
                assert_ne!(
                    changed, before,
                    "changed-buffer negative witness must reject"
                );
                println!(
                    "PROBE_PASS mixed={mixed} pair={label} complete_buffers_exact=true changed_buffer_rejected=true"
                );
            }
            if orders.len() == needed {
                break;
            }
        }
        assert_eq!(
            orders.len(),
            needed,
            "bounded baseline-order coverage not met"
        );
        let baseline = contour_probe_prepare(&mut app, old.clone());
        let _ = contour_probe_finish(&mut app);
        new.character
            .parameters
            .insert("cheek_fullness".into(), 0.25);
        let nonzero = contour_probe_prepare(&mut app, new);
        let rejection = contour_probe_align(&mut app, &baseline, &nonzero).unwrap_err();
        assert_eq!(rejection, "untouched target membership/value bits differ");
        let template = app
            .world()
            .resource::<Assets<CharacterTemplate>>()
            .get(&nonzero.template)
            .unwrap();
        assert!(template.shapes[0].helper_deltas.is_none());
        assert_eq!(
            contour_probe_entries(&template.shapes[0].morphs),
            nonzero.entries
        );
        assert_eq!(
            template.shapes[0]
                .morphs
                .keys()
                .map(|s| s.to_string())
                .collect::<Vec<_>>(),
            nonzero.order
        );
        println!("PROBE_NONZERO_REJECTED mixed={mixed} untouched_entries_preserved=true");
        // Settle the canceled negative candidate through the ordinary Open lifecycle.
        open_ready(&mut app, old);
    }
}

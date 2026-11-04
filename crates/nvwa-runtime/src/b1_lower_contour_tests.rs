// E-only product tests inside b1::tests. Existing contour assertions stay fixed.
fn fill_lower_contour(dir: &Dir) {
    let version = B1AssetVersion::V4;
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets");
    dir.insert_asset(
        Path::new(version.manifest_path()),
        version.manifest_bytes().to_vec(),
    );
    let manifest = B1AssetManifest::from_bytes_for(version, version.manifest_bytes()).unwrap();
    for file in manifest.files {
        let path = format!("characters/mpfb-b1-v4/{}", file.path);
        dir.insert_asset(Path::new(&path), std::fs::read(root.join(&path)).unwrap());
    }
}

fn lower_contour_align(
    app: &mut App,
    baseline: &ContourProbeInput,
    candidate: &ContourProbeInput,
) -> Result<(), String> {
    // Same established pre-bake comparison boundary, with the new zero control
    // absent. Existing nonzero cheek values are legitimate consumed inputs here.
    if candidate.entries != baseline.entries {
        return Err("untouched target membership/value bits differ".into());
    }
    if candidate.consumed != baseline.consumed {
        return Err("untouched consumed inputs differ".into());
    }
    assert_ne!(candidate.template, baseline.template);
    assert_ne!(candidate.character, baseline.character);
    assert!(
        !candidate
            .entries
            .keys()
            .any(|name| name.starts_with("chin-bones-"))
    );
    let mut aligned = baseline.morphs.clone();
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

#[test]
fn lower_contour_zero_preserves_nine_parameter_buffers_at_equal_consumed_inputs_and_order() {
    let (mut app, dir, _) = motion_app();
    fill_contour(&dir);
    fill_lower_contour(&dir);
    for mixed in [false, true] {
        let mut old =
            SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character_contour())
                .unwrap();
        if mixed {
            for (i, value) in old.character.parameters.values_mut().enumerate() {
                *value = if i % 2 == 0 { -0.35 } else { 0.45 };
            }
        }
        let mut new =
            SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character_lower_contour())
                .unwrap();
        for (id, value) in &old.character.parameters {
            new.character.parameters.insert(id.clone(), *value);
        }
        let baseline = contour_probe_prepare(&mut app, old.clone());
        let before = contour_probe_finish(&mut app);
        for document in [new.clone(), old.clone(), new.clone()] {
            let candidate = contour_probe_prepare(&mut app, document);
            lower_contour_align(&mut app, &baseline, &candidate).unwrap();
            let actual = contour_probe_finish(&mut app);
            assert!(
                actual == before,
                "zero lower contour full buffers mixed={mixed}: {:?}",
                contour_first_difference(&actual, &before, "$")
            );
            let mut changed = actual.clone();
            changed["parts"][0]["normals"][0][0] = serde_json::json!(2.0);
            assert_ne!(changed, before, "changed-buffer witness must reject");
        }
        new.character
            .parameters
            .insert("lower_face_squareness".into(), 0.5);
        let nonzero = contour_probe_prepare(&mut app, new);
        assert_eq!(
            lower_contour_align(&mut app, &baseline, &nonzero).unwrap_err(),
            "untouched target membership/value bits differ"
        );
        assert!(
            app.world()
                .resource::<Assets<CharacterTemplate>>()
                .get(&nonzero.template)
                .unwrap()
                .shapes[0]
                .helper_deltas
                .is_none()
        );
        // No claim of universal independent-reopen float repeatability.
        open_ready(&mut app, old);
    }
}

fn original_lower_contour_delta() -> BTreeMap<u16, [f32; 3]> {
    let text = include_str!("../tests/fixtures/chin/chin-bones-incr.target");
    assert_eq!(
        nvwa_core::appearance_sha256(text.as_bytes()),
        "4b1558340919c6a1241165129a318d838bf6eb1d39559e0ca0f0aa8b5ba6ba4e"
    );
    let mut result = BTreeMap::new();
    for line in text
        .lines()
        .filter(|line| !line.trim().is_empty() && !line.trim_start().starts_with('#'))
    {
        let cells: Vec<_> = line.split_whitespace().collect();
        assert_eq!(cells.len(), 4);
        let id: u16 = cells[0].parse().unwrap();
        let delta = [
            cells[1].parse::<f32>().unwrap() * 0.1,
            cells[2].parse::<f32>().unwrap() * 0.1,
            cells[3].parse::<f32>().unwrap() * 0.1,
        ];
        assert!(result.insert(id, delta).is_none());
    }
    assert_eq!(result.len(), 805);
    assert_eq!(result.values().filter(|d| **d != [0.0; 3]).count(), 571);
    result
}

#[test]
fn lower_contour_actual_output_zero_quarters_endpoint_and_history_follow_original_e() {
    let (mut app, dir, _) = motion_app();
    fill_lower_contour(&dir);
    let doc =
        SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character_lower_contour())
            .unwrap();
    open_ready(&mut app, doc.clone());
    let baseline = appearance_fit(app.world(), &appearance_frame(app.world()).unwrap()).unwrap();
    let uploaded = uploaded_positions(&app);
    let delta = original_lower_contour_delta();
    for value in [0.25_f32, 0.5, 0.75, 1.0, 0.0] {
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::SetParameters {
                character_id: doc.character.id.clone(),
                values: BTreeMap::from([("lower_face_squareness".into(), value)]),
            })
            .unwrap();
        contour_settle(&mut app);
        let actual = appearance_fit(app.world(), &appearance_frame(app.world()).unwrap()).unwrap();
        assert_eq!(actual.source_ids, baseline.source_ids);
        let mut witnessed = 0;
        for ((id, before), after) in baseline
            .source_ids
            .iter()
            .zip(&baseline.rest)
            .zip(&actual.rest)
        {
            let change = delta.get(id).copied().unwrap_or([0.0; 3]);
            if change != [0.0; 3] {
                witnessed += 1;
            }
            for axis in 0..3 {
                assert!(
                    (after[axis] - (before[axis] + change[axis] * value)).abs() <= 1e-6,
                    "original E: value={value} source={id} axis={axis}"
                );
            }
        }
        assert!(witnessed > 100);
        let active = app.world().resource::<B1Runtime>().active.as_ref().unwrap();
        let template = app
            .world()
            .resource::<Assets<CharacterTemplate>>()
            .get(&active.template)
            .unwrap();
        assert!(
            !template.shapes[0]
                .morphs
                .keys()
                .any(|name| *name == "chin-bones-decr"),
            "held A cannot be active"
        );
        if value == 0.0 {
            assert_eq!(uploaded_positions(&app), uploaded);
        } else {
            assert!(position_delta(&uploaded, &uploaded_positions(&app)) > 1e-6);
        }
    }
    let before = app
        .world()
        .resource::<EditorState>()
        .document()
        .unwrap()
        .clone();
    let frame = contour_buffers(&app);
    let history = app
        .world()
        .resource::<EditorState>()
        .editor
        .as_ref()
        .unwrap()
        .retention_stats();
    assert!(
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(nvwa_core::Command::SetParameters {
                character_id: doc.character.id.clone(),
                values: BTreeMap::from([
                    ("head_width".into(), 0.4),
                    ("lower_face_squareness".into(), -0.01)
                ]),
            })
            .is_err()
    );
    assert_eq!(
        app.world().resource::<EditorState>().document(),
        Some(&before)
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
    for command in [nvwa_core::Command::Undo, nvwa_core::Command::Redo] {
        app.world_mut()
            .resource_mut::<EditorState>()
            .apply(command)
            .unwrap();
        contour_settle(&mut app);
    }
    assert_eq!(
        app.world()
            .resource::<EditorState>()
            .document()
            .unwrap()
            .character
            .parameters["lower_face_squareness"],
        0.0
    );
}

#[test]
fn lower_contour_source_failures_retain_committed_work_history_frame_and_old_cache_readiness() {
    let (mut app, dir, _) = motion_app();
    fill_contour(&dir);
    fill_lower_contour(&dir);
    let old =
        SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character_contour()).unwrap();
    let new =
        SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character_lower_contour())
            .unwrap();
    open_ready(&mut app, new.clone());
    assert_eq!(app.world().resource::<B1Runtime>().extra_targets.len(), 16);
    open_ready(&mut app, old.clone());
    app.world_mut()
        .resource_mut::<EditorState>()
        .apply(nvwa_core::Command::SetScale {
            character_id: old.character.id.clone(),
            scale: 1.1,
        })
        .unwrap();
    contour_settle(&mut app);
    let current = app
        .world()
        .resource::<EditorState>()
        .document()
        .unwrap()
        .clone();
    let history = app
        .world()
        .resource::<EditorState>()
        .editor
        .as_ref()
        .unwrap()
        .retention_stats();
    let frame = contour_buffers(&app);
    assert!(history.undo_snapshots > 0);
    for name in ["chin-bones-decr", "chin-bones-incr"] {
        let path = format!("characters/mpfb-b1-v4/targets/{name}.target");
        let original = std::fs::read(
            Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("../../assets")
                .join(&path),
        )
        .unwrap();
        for corrupt in [false, true] {
            dir.remove_asset(Path::new(&path));
            if corrupt {
                dir.insert_asset(Path::new(&path), b"corrupt".to_vec());
            }
            app.world_mut()
                .resource_mut::<EditorState>()
                .request_open(new.clone())
                .unwrap();
            // Save uses committed document even while a candidate waits.
            assert_eq!(
                SceneDocument::from_json(
                    &app.world()
                        .resource::<EditorState>()
                        .document()
                        .unwrap()
                        .to_json()
                        .unwrap()
                )
                .unwrap(),
                current
            );
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
        }
        dir.insert_asset(Path::new(&path), original);
    }
    let failed: Handle<TargetAsset> = app
        .world()
        .resource::<AssetServer>()
        .load(asset("targets/absent-lower-contour-test.target"));
    until(&mut app, |w| {
        matches!(
            w.resource::<AssetServer>().get_load_state(failed.id()),
            Some(bevy::asset::LoadState::Failed(_))
        )
    });
    for index in [14, 15] {
        let original = app.world().resource::<B1Runtime>().extra_targets[index].clone();
        app.world_mut().resource_mut::<B1Runtime>().extra_targets[index] = failed.clone();
        assert_eq!(
            extra_targets_ready(
                app.world(),
                app.world().resource::<B1Runtime>(),
                B1AssetVersion::V3
            ),
            Ok(true)
        );
        assert!(
            extra_targets_ready(
                app.world(),
                app.world().resource::<B1Runtime>(),
                B1AssetVersion::V4
            )
            .is_err()
        );
        app.world_mut().resource_mut::<B1Runtime>().extra_targets[index] = original;
    }
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
        1.0
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
        1.1
    );
    // Rejected Open retained the history checked above. Successful Open then
    // starts a new Editor; test readiness recovery separately from that history.
    open_ready(&mut app, current.clone());
    assert_eq!(
        extra_targets_ready(
            app.world(),
            app.world().resource::<B1Runtime>(),
            B1AssetVersion::V3
        ),
        Ok(true)
    );
    open_ready(&mut app, new);
    assert_eq!(
        extra_targets_ready(
            app.world(),
            app.world().resource::<B1Runtime>(),
            B1AssetVersion::V4
        ),
        Ok(true)
    );
    assert!(app.world().resource::<RuntimeStatus>().error.is_none());
}

#[test]
fn lower_contour_exact_both_hairstyle_aliases_reach_current_cpu_appearance() {
    use nvwa_core::{B1AppearanceSet, CharacterAppearance, Command};
    let (mut app, dir, _) = motion_app();
    fill_lower_contour(&dir);
    let mut doc =
        SceneDocument::from_profile(nvwa_core::CharacterProfile::b1_character_lower_contour())
            .unwrap();
    doc.character
        .parameters
        .insert("lower_face_squareness".into(), 1.0);
    open_ready(&mut app, doc.clone());
    let body = uploaded_positions(&app);
    for (set, vertices) in [
        (B1AppearanceSet::V4, 865),
        (B1AppearanceSet::V4Short01, 2984),
        (B1AppearanceSet::V4, 865),
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
        assert_eq!(snapshot["base_asset_id"], nvwa_core::B1_V4_ASSET_ID);
        assert_eq!(snapshot["applied"]["asset_set_id"], set.asset_id());
        assert!(snapshot["skin"].is_object());
        let roles = snapshot["accessories"].as_array().unwrap();
        assert_eq!(roles.len(), 2);
        assert_eq!(
            roles.iter().find(|r| r["name"] == "hair").unwrap()["source_vertices"],
            vertices
        );
        assert_eq!(uploaded_positions(&app), body);
    }
}

#![forbid(unsafe_code)]
use nvwa_core::{CharacterProfile, Command, CommandEnvelope, CoreError, Editor, SceneDocument};
use std::path::{Path, PathBuf};

fn respond(response: impl std::fmt::Display) -> Result<(), CoreError> {
    use std::io::Write;
    let mut stdout = std::io::stdout().lock();
    writeln!(stdout, "{response}")
        .and_then(|()| stdout.flush())
        .map_err(|error| {
            CoreError::new(
                "stdout_write",
                format!(
                    "Response delivery failed: {error}; a mutating operation may already be saved; inspect the output work before retrying"
                ),
            )
        })
}

fn read(path: &Path) -> Result<String, CoreError> {
    use std::io::Read;
    let mut options = std::fs::OpenOptions::new();
    options.read(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.custom_flags(libc::O_NONBLOCK);
    }
    let file = options
        .open(path)
        .map_err(|e| CoreError::new("file_open", format!("{}: {e}", path.display())))?;
    if !file
        .metadata()
        .map_err(|e| CoreError::new("file_metadata", e.to_string()))?
        .is_file()
    {
        return Err(CoreError::new(
            "unsupported_file",
            "Only regular document files are supported",
        ));
    }
    let mut bytes = Vec::new();
    file.take(nvwa_core::MAX_JSON_BYTES as u64 + 1)
        .read_to_end(&mut bytes)
        .map_err(|e| CoreError::new("file_read", e.to_string()))?;
    if bytes.len() > nvwa_core::MAX_JSON_BYTES {
        return Err(CoreError::new("input_too_large", "Input exceeds 2 MiB"));
    }
    String::from_utf8(bytes).map_err(|e| CoreError::new("invalid_utf8", e.to_string()))
}

fn save(document: &SceneDocument, path: &Path) -> Result<(), CoreError> {
    use std::io::Write;
    let json = document.to_json()?;
    let nonce = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(|e| CoreError::new("clock", e.to_string()))?
        .as_nanos();
    let parent = path
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    let temp = parent.join(format!(".nvwa-save-{}-{nonce}.tmp", std::process::id()));
    let mut file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temp)
        .map_err(|e| CoreError::new("file_create", e.to_string()))?;
    let result = file
        .write_all(json.as_bytes())
        .and_then(|()| file.sync_all())
        .and_then(|()| std::fs::rename(&temp, path));
    if let Err(error) = result {
        let cleanup = std::fs::remove_file(&temp);
        return Err(CoreError::new(
            "file_write",
            match cleanup {
                Ok(()) => error.to_string(),
                Err(cleanup_error) => format!("{error}; temporary cleanup failed: {cleanup_error}"),
            },
        ));
    }
    Ok(())
}

fn cli_contract(document: &SceneDocument) -> Result<serde_json::Value, CoreError> {
    // Examples use the production command serializer and this work's actual IDs.
    // Each is a standalone example at the loaded revision, not a ready-made batch.
    let commands = [
        Command::SetParameters {
            character_id: document.character.id.clone(),
            values: document.character.parameters.clone(),
        },
        Command::SetScale {
            character_id: document.character.id.clone(),
            scale: document.character.scale,
        },
        Command::SetTimeline {
            clips: document.timeline.clone(),
        },
        Command::SetStage {
            stage: document.stage.clone(),
        },
        Command::Undo,
        Command::Redo,
    ];
    let examples: Vec<_> = commands
        .into_iter()
        .enumerate()
        .map(|(index, command)| CommandEnvelope {
            command_id: format!("example-{}", index + 1),
            expected_revision: document.revision,
            command,
        })
        .collect();
    // Preserve f32 JSON spellings, as with the profile below.
    let examples =
        serde_json::to_string(&examples).map_err(|e| CoreError::new("serialize", e.to_string()))?;
    let examples: serde_json::Value =
        serde_json::from_str(&examples).map_err(|e| CoreError::new("serialize", e.to_string()))?;
    Ok(serde_json::json!({
        "schema_version": 1,
        "transport": "offline_files",
        "work_schema": {"writes": nvwa_core::SCHEMA_VERSION, "reads": [1, nvwa_core::SCHEMA_VERSION], "legacy_upgrade": "schema1_to_schema2_default_white_studio_without_revision_change"},
        "entrypoints": {
            "new": ["profile.json", "output.json"],
            "inspect": ["input.json"],
            "describe-capabilities": ["input.json"],
            "validate": ["input.json", "optional_asset_root"],
            "apply": ["input.json", "command_or_array.json", "output.json"],
            "save": ["input.json", "output.json"]
        },
        "input": {
            "max_json_bytes": nvwa_core::MAX_JSON_BYTES,
            "unknown_fields": "rejected",
            "duplicate_object_keys": "rejected",
            "apply_payload": "one_command_envelope_or_array",
            "envelope_fields": {
                "command_id": "nonblank_string",
                "expected_revision": "u64",
                "command": "object_with_type_tag"
            }
        },
        "command_examples": examples,
        "examples_are": "independent_shapes_at_loaded_revision_not_a_batch",
        "set_parameters": "updates_only_named_parameters_within_profile_min_max_inclusive",
        "set_scale": "finite_greater_than_zero",
        "set_timeline": {
            "effect": "replaces_entire_timeline",
            "clip_id": "must_reference_profile_clips_id",
            "id": "nonblank_unique_timeline_entry_id",
            "start_seconds": "finite_nonnegative_wall_time",
            "duration_seconds": "finite_positive_wall_time_not_source_clip_length",
            "speed": "finite_greater_than_zero_source_time_multiplier",
            "looping": "boolean",
            "bounds": "end_and_duration_times_speed_must_be_finite",
            "overlap": "rejected",
            "gaps": "allowed_holds",
            "playback_order": "start_seconds_not_array_order"
        },
        "set_stage": {
            "effect": "atomically_replaces_entire_stage",
            "persisted_in_work": true,
            "colors": "three_finite_srgb_channels_0_to_1_inclusive",
            "lights": {"illuminance_lux": [0, 100000], "azimuth_degrees": [-180, 180], "elevation_degrees": [5, 89]},
            "ambient_brightness": [0, 2000],
            "floor": "visible_color_srgb_shadows_at_fixed_y_zero",
            "camera_units": "distance_and_target_height_relative_to_character_scale_angles_degrees",
            "runtime_presentation_scale": [0.001, 100],
            "runtime_extreme_scale": "explicit_stage_camera_error_work_preserved",
            "camera": {"azimuth_degrees": [-180, 180], "elevation_degrees": [-20, 80], "distance": [0.35, 20], "target_height": [0, 4], "fov_degrees": [15, 75]},
            "quality": ["low", "balanced", "high"],
            "bounds": "all_floats_finite_and_ranges_inclusive",
            "profiles": {
                "low": {"msaa_samples": 1, "key_shadow_maps": false, "shadow_map_size": 1024, "contact_shadows": false},
                "balanced": {"msaa_samples": 4, "key_shadow_maps": "floor_shadows_request", "shadow_map_size": 2048, "contact_shadows": false},
                "high": {"msaa_samples": 4, "key_shadow_maps": "floor_shadows_request", "shadow_map_size": 4096, "contact_shadows": false}
            },
            "fill_shadows": false,
            "quality_effects": "requested_shared_runtime_settings_actual_platform_rendering_and_performance_need_separate_acceptance"
        },
        "revision": {
            "check": "expected_revision_against_loaded_input_document",
            "advance": "each_successful_nonduplicate_command_increments_by_one_including_undo_redo",
            "batch": "later_envelopes_use_revision_after_preceding_commands",
            "concurrency": "no_cross_file_or_cross_process_compare_and_swap"
        },
        "apply": {
            "atomicity": "save_only_after_entire_batch_succeeds",
            "failure": "before_successful_save_input_and_existing_output_unchanged_no_new_output",
            "failure_scope": "input_command_validation_and_persistence_errors_before_successful_save",
            "response_transport_failure": "stdout_write_may_follow_successful_save_inspect_output_before_retry",
            "output": "array_of_revision_summary_duplicate_results_in_input_order",
            "session": "fresh_editor_per_invocation",
            "history": "undo_redo_and_successful_retry_ids_only_within_same_apply_invocation",
            "persistent_idempotency": false
        },
        "stdio": {
            "success_exit_code": 0,
            "error_exit_code": 1,
            "success_stdout": "json_except_help_text",
            "error_stderr": {"code": "string", "message": "string"},
            "stderr_delivery": "best_effort_when_stderr_writable",
            "error_stdout": "empty_before_response_delivery_may_be_partial_on_stdout_write",
            "filesystem_and_response_delivery_atomic": false
        },
        "error_recovery": {
            "revision_conflict": "inspect_actual_input_then_rebuild_request_with_current_revision_and_reconsider_intent",
            "out_of_range": "read_profile_parameter_ranges_and_timeline_constraints",
            "invalid_reference": "read_character_id_and_profile_parameter_clip_ids",
            "overlapping_timeline": "use_nonoverlapping_wall_time_spans",
            "command_id_conflict": "use_a_new_id_for_changed_payload_in_same_invocation",
            "nothing_to_undo": "history_does_not_cross_apply_invocations",
            "nothing_to_redo": "redo_requires_undo_in_same_invocation",
            "stdout_write": "output_may_already_be_saved_inspect_actual_output_before_retrying_mutation",
            "other_errors": "read_code_and_message_input_command_validation_and_persistence_failures_before_save_do_not_commit_output"
        },
        "asset_validation": "validate_with_asset_root_checks_profile_asset_hash_and_structure",
        "studio_control": false
    }))
}

fn run(args: &[String]) -> Result<(), CoreError> {
    let command = args.first().map(String::as_str).unwrap_or("help");
    let arg = |index: usize| {
        args.get(index)
            .map(PathBuf::from)
            .ok_or_else(|| CoreError::new("usage", "Missing argument; run nvwa-cli help"))
    };
    match command {
        "new" => {
            let profile = CharacterProfile::from_json(&read(&arg(1)?)?)?;
            let document = SceneDocument::from_profile(profile)?;
            save(&document, &arg(2)?)?;
            respond(serde_json::json!({"revision":document.revision,"saved":args[2]}))?;
        }
        "inspect" | "describe-capabilities" => {
            let document = SceneDocument::from_json(&read(&arg(1)?)?)?;
            if command == "inspect" {
                respond(document.to_json()?)?;
            } else {
                // Preserve the profile's existing f32 JSON representation;
                // to_value would widen floats to f64 before output encoding.
                let profile_json = serde_json::to_string(&document.profile)
                    .map_err(|e| CoreError::new("serialize", e.to_string()))?;
                let mut capabilities: serde_json::Value = serde_json::from_str(&profile_json)
                    .map_err(|e| CoreError::new("serialize", e.to_string()))?;
                capabilities["document_revision"] = serde_json::json!(document.revision);
                capabilities["character_id"] = serde_json::json!(document.character.id);
                capabilities["stage"] = serde_json::from_str(
                    &serde_json::to_string(&document.stage)
                        .map_err(|e| CoreError::new("serialize", e.to_string()))?,
                )
                .map_err(|e| CoreError::new("serialize", e.to_string()))?;
                capabilities["cli_contract"] = cli_contract(&document)?;
                capabilities["editor_retention"] = serde_json::json!({
                    "limits": nvwa_core::EDITOR_RETENTION_LIMITS,
                    "session_local": true,
                    "persisted_in_document": false,
                    "eviction": "fifo",
                    "duplicate_reads_refresh_retention": false,
                    "retained_identical_envelope": "duplicate",
                    "retained_conflicting_id": "command_id_conflict",
                    "expired_original_envelope": "revision_conflict",
                    "expired_id_reuse": "allowed_with_current_revision_and_valid_command",
                    "oversized_snapshot": "clear_destination_history_without_rejecting_edit",
                    "oversized_retry_entry": "evict_all_older_entries_then_expire_without_rejecting_edit",
                    "byte_accounting": {
                        "history": "sum_of_compact_scene_document_json_bytes",
                        "retry": "sum_of_compact_envelope_result_tuple_json_bytes",
                        "excludes": ["live_document", "temporary_candidates", "allocation_overhead"]
                    }
                });
                respond(
                    serde_json::to_string_pretty(&capabilities)
                        .map_err(|e| CoreError::new("serialize", e.to_string()))?,
                )?;
            }
        }
        "validate" => {
            let document = SceneDocument::from_json(&read(&arg(1)?)?)?;
            if let Some(root) = args.get(2) {
                // The core validated that this asset reference is a safe relative path.
                let asset = Path::new(root).join(&document.profile.asset_path);
                let bytes = std::fs::read(&asset).map_err(|e| {
                    CoreError::new("asset_missing", format!("{}: {e}", asset.display()))
                })?;
                document.profile.validate_asset_bytes(&bytes)?;
            }
            respond(
                serde_json::json!({"valid":true,"revision":document.revision,"asset_checked":args.len()>2}),
            )?;
        }
        "apply" => {
            let document = SceneDocument::from_json(&read(&arg(1)?)?)?;
            let commands_json = read(&arg(2)?)?;
            let commands: Vec<CommandEnvelope> = if commands_json.trim_start().starts_with('[') {
                CommandEnvelope::batch_from_json(&commands_json)
            } else {
                CommandEnvelope::from_json(&commands_json).map(|one| vec![one])
            }?;
            let mut editor = Editor::new(document)?;
            let mut results = Vec::new();
            for envelope in commands {
                results.push(editor.apply(envelope)?);
            }
            // Persistence is atomic for the batch. Response delivery is separate.
            let response = serde_json::to_string(&results)
                .map_err(|e| CoreError::new("serialize", e.to_string()))?;
            save(editor.document(), &arg(3)?)?;
            respond(response)?;
        }
        "save" => {
            let document = SceneDocument::from_json(&read(&arg(1)?)?)?;
            save(&document, &arg(2)?)?;
            respond(serde_json::json!({"revision":document.revision,"saved":args[2]}))?;
        }
        "help" | "--help" | "-h" => respond(
            "Nvwa offline document CLI\n  new <profile.json> <scene.json>\n  inspect <scene.json>\n  describe-capabilities <scene.json>\n  validate <scene.json> [asset-root]\n  apply <scene.json> <command-or-array.json> <output.json>\n  save <scene.json> <output.json>\nCommands: set_parameters, set_scale, set_timeline, undo, redo.\nThis edits files; it does not control a running Studio.",
        )?,
        _ => {
            return Err(CoreError::new(
                "unknown_command",
                format!("Unknown command: {command}"),
            ));
        }
    }
    Ok(())
}

fn main() -> std::process::ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match run(&args) {
        Ok(()) => std::process::ExitCode::SUCCESS,
        Err(error) => {
            use std::io::Write;
            // A closed stderr must not turn a handled failure into a panic.
            // Delivery of the structured diagnostic is necessarily best effort.
            if let Ok(json) = serde_json::to_string(&error) {
                let mut stderr = std::io::stderr().lock();
                let _ = writeln!(stderr, "{json}").and_then(|()| stderr.flush());
            }
            std::process::ExitCode::FAILURE
        }
    }
}

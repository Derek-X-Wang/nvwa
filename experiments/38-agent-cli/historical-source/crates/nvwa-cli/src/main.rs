#![forbid(unsafe_code)]
use nvwa_core::{CharacterProfile, Command, CommandEnvelope, CoreError, Editor, SceneDocument};
use std::path::{Path, PathBuf};

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
        "revision": {
            "check": "expected_revision_against_loaded_input_document",
            "advance": "each_successful_nonduplicate_command_increments_by_one_including_undo_redo",
            "batch": "later_envelopes_use_revision_after_preceding_commands",
            "concurrency": "no_cross_file_or_cross_process_compare_and_swap"
        },
        "apply": {
            "atomicity": "save_only_after_entire_batch_succeeds",
            "failure": "input_and_existing_output_unchanged_no_new_output",
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
            "error_stdout": "empty"
        },
        "error_recovery": {
            "revision_conflict": "inspect_actual_input_then_rebuild_request_with_current_revision_and_reconsider_intent",
            "out_of_range": "read_profile_parameter_ranges_and_timeline_constraints",
            "invalid_reference": "read_character_id_and_profile_parameter_clip_ids",
            "overlapping_timeline": "use_nonoverlapping_wall_time_spans",
            "command_id_conflict": "use_a_new_id_for_changed_payload_in_same_invocation",
            "nothing_to_undo": "history_does_not_cross_apply_invocations",
            "nothing_to_redo": "redo_requires_undo_in_same_invocation",
            "other_errors": "read_code_and_message_no_output_was_committed"
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
            println!(
                "{}",
                serde_json::json!({"revision":document.revision,"saved":args[2]})
            );
        }
        "inspect" | "describe-capabilities" => {
            let document = SceneDocument::from_json(&read(&arg(1)?)?)?;
            if command == "inspect" {
                println!("{}", document.to_json()?);
            } else {
                // Preserve the profile's existing f32 JSON representation;
                // to_value would widen floats to f64 before output encoding.
                let profile_json = serde_json::to_string(&document.profile)
                    .map_err(|e| CoreError::new("serialize", e.to_string()))?;
                let mut capabilities: serde_json::Value = serde_json::from_str(&profile_json)
                    .map_err(|e| CoreError::new("serialize", e.to_string()))?;
                capabilities["document_revision"] = serde_json::json!(document.revision);
                capabilities["character_id"] = serde_json::json!(document.character.id);
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
                println!(
                    "{}",
                    serde_json::to_string_pretty(&capabilities)
                        .map_err(|e| CoreError::new("serialize", e.to_string()))?
                );
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
            println!(
                "{}",
                serde_json::json!({"valid":true,"revision":document.revision,"asset_checked":args.len()>2})
            );
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
            // Persist only after the full batch succeeds. No partial output on failure.
            save(editor.document(), &arg(3)?)?;
            println!(
                "{}",
                serde_json::to_string(&results)
                    .map_err(|e| CoreError::new("serialize", e.to_string()))?
            );
        }
        "save" => {
            let document = SceneDocument::from_json(&read(&arg(1)?)?)?;
            save(&document, &arg(2)?)?;
            println!(
                "{}",
                serde_json::json!({"revision":document.revision,"saved":args[2]})
            );
        }
        "help" | "--help" | "-h" => println!(
            "Nvwa offline document CLI\n  new <profile.json> <scene.json>\n  inspect <scene.json>\n  describe-capabilities <scene.json>\n  validate <scene.json> [asset-root]\n  apply <scene.json> <command-or-array.json> <output.json>\n  save <scene.json> <output.json>\nCommands: set_parameters, set_scale, set_timeline, undo, redo.\nThis edits files; it does not control a running Studio."
        ),
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
            match serde_json::to_string(&error) {
                Ok(json) => eprintln!("{json}"),
                Err(_) => eprintln!("{error}"),
            }
            std::process::ExitCode::FAILURE
        }
    }
}

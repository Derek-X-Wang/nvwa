//! Public editor behavior at the actual production retention boundaries.
use crate::{
    Command, CommandEnvelope, CommandResult, EDITOR_RETENTION_LIMITS, Editor, SceneDocument,
    TimelineClip,
};

fn document() -> SceneDocument {
    SceneDocument::from_json(include_str!("../../../examples/default.nvwa.json")).unwrap()
}

fn envelope(editor: &Editor, id: impl Into<String>, command: Command) -> CommandEnvelope {
    CommandEnvelope {
        command_id: id.into(),
        expected_revision: editor.document().revision,
        command,
    }
}

fn scale(editor: &Editor, value: f32) -> Command {
    Command::SetScale {
        character_id: editor.document().character.id.clone(),
        scale: value,
    }
}

fn apply(id: impl Into<String>, command: Command, editor: &mut Editor) -> CommandResult {
    editor.apply(envelope(editor, id, command)).unwrap()
}

fn set_scale(editor: &mut Editor, id: impl Into<String>, value: f32) {
    apply(id, scale(editor, value), editor);
}

fn assert_bounds(editor: &Editor) {
    let stats = editor.retention_stats();
    assert!(
        stats.undo_snapshots + stats.redo_snapshots <= EDITOR_RETENTION_LIMITS.history_snapshots
    );
    assert!(stats.history_bytes <= EDITOR_RETENTION_LIMITS.history_bytes);
    assert!(stats.retry_entries <= EDITOR_RETENTION_LIMITS.retry_entries);
    assert!(stats.retry_bytes <= EDITOR_RETENTION_LIMITS.retry_bytes);
}

fn failure_leaves_session(command: CommandEnvelope, code: &str, editor: &mut Editor) {
    let before = editor.document().clone();
    let stats = editor.retention_stats();
    assert_eq!(editor.apply(command).unwrap_err().code, code);
    assert_eq!(editor.document(), &before);
    assert_eq!(editor.retention_stats(), stats);
}

#[test]
fn history_count_boundary_preserves_contiguous_undo_redo_and_branching() {
    let mut editor = Editor::new(document()).unwrap();
    for index in 1..=129 {
        set_scale(&mut editor, format!("edit-{index}"), (index + 1) as f32);
        assert_bounds(&editor);
    }
    assert_eq!(editor.retention_stats().undo_snapshots, 128);
    for index in (1..=128).rev() {
        apply(format!("undo-{index}"), Command::Undo, &mut editor);
        assert_eq!(editor.document().character.scale, (index + 1) as f32);
        assert_bounds(&editor);
    }
    assert_eq!(editor.retention_stats().redo_snapshots, 128);
    failure_leaves_session(
        envelope(&editor, "empty", Command::Undo),
        "nothing_to_undo",
        &mut editor,
    );
    for index in 1..=128 {
        apply(format!("redo-{index}"), Command::Redo, &mut editor);
        assert_eq!(editor.document().character.scale, (index + 2) as f32);
        assert_bounds(&editor);
    }
    apply("undo-before-branch", Command::Undo, &mut editor);
    set_scale(&mut editor, "branch", 0.5);
    assert_eq!(editor.retention_stats().redo_snapshots, 0);
    failure_leaves_session(
        envelope(&editor, "no-redo", Command::Redo),
        "nothing_to_redo",
        &mut editor,
    );
    apply("undo-branch", Command::Undo, &mut editor);
    assert_eq!(editor.document().character.scale, 129.0);
}

#[test]
fn retry_fifo_duplicates_conflicts_failure_and_expired_id_reuse() {
    let mut editor = Editor::new(document()).unwrap();
    let first = envelope(&editor, "first", scale(&editor, 2.0));
    editor.apply(first.clone()).unwrap();
    for index in 1..1024 {
        set_scale(&mut editor, format!("edit-{index}"), 2.0);
        // Reading the oldest entry must not refresh its FIFO position.
        let stats = editor.retention_stats();
        assert!(editor.apply(first.clone()).unwrap().duplicate);
        assert_eq!(editor.retention_stats(), stats);
    }
    assert_eq!(editor.retention_stats().retry_entries, 1024);
    failure_leaves_session(
        envelope(&editor, "first", scale(&editor, 3.0)),
        "command_id_conflict",
        &mut editor,
    );
    failure_leaves_session(
        envelope(&editor, "invalid", scale(&editor, -1.0)),
        "out_of_range",
        &mut editor,
    );
    assert!(editor.apply(first.clone()).unwrap().duplicate);
    set_scale(&mut editor, "overflow", 3.0);
    failure_leaves_session(first, "revision_conflict", &mut editor);
    set_scale(&mut editor, "first", 4.0);
    assert_eq!(editor.document().character.scale, 4.0);
    assert_eq!(editor.retention_stats().retry_entries, 1024);
    assert_bounds(&editor);
}

#[test]
fn exact_history_byte_limit_and_next_snapshot_evict_farthest_state() {
    let mut large = document();
    let base = serde_json::to_vec(&large).unwrap().len();
    large
        .profile
        .license
        .push_str(&"x".repeat(EDITOR_RETENTION_LIMITS.history_bytes - base));
    assert_eq!(
        serde_json::to_vec(&large).unwrap().len(),
        EDITOR_RETENTION_LIMITS.history_bytes
    );
    let mut editor = Editor::new(large).unwrap();
    set_scale(&mut editor, "a", 2.0);
    assert_eq!(
        editor.retention_stats().history_bytes,
        EDITOR_RETENTION_LIMITS.history_bytes
    );
    failure_leaves_session(
        envelope(&editor, "invalid-at-byte-limit", scale(&editor, -1.0)),
        "out_of_range",
        &mut editor,
    );
    set_scale(&mut editor, "b", 3.0);
    assert_eq!(editor.retention_stats().undo_snapshots, 1);
    assert_bounds(&editor);
    apply("undo", Command::Undo, &mut editor);
    assert_eq!(editor.document().character.scale, 2.0);
    failure_leaves_session(
        envelope(&editor, "undo-more", Command::Undo),
        "nothing_to_undo",
        &mut editor,
    );
    apply("redo", Command::Redo, &mut editor);
    assert_eq!(editor.document().character.scale, 3.0);
}

fn huge_timeline(editor: &Editor) -> Command {
    sized_timeline(editor, EDITOR_RETENTION_LIMITS.history_bytes + 1)
}

fn sized_timeline(editor: &Editor, id_bytes: usize) -> Command {
    Command::SetTimeline {
        clips: vec![TimelineClip {
            id: "x".repeat(id_bytes),
            clip_id: editor.document().profile.clips[0].id.clone(),
            start_seconds: 0.0,
            duration_seconds: 1.0,
            speed: 1.0,
            looping: false,
        }],
    }
}

#[test]
fn mixed_stack_byte_eviction_removes_only_farthest_reachable_states() {
    let mut editor = Editor::new(document()).unwrap();
    for (index, mib) in [2, 4, 8, 10].into_iter().enumerate() {
        apply(
            format!("size-{index}"),
            sized_timeline(&editor, mib * 1024 * 1024),
            &mut editor,
        );
        assert_bounds(&editor);
    }
    // Stored past: small, 2 MiB, 4 MiB, 8 MiB; live: 10 MiB.
    // Undo replaces the 8 MiB snapshot with the 10 MiB live snapshot. FIFO
    // drops the farthest small and 2 MiB past states, preserving adjacent 4 MiB.
    apply("undo-to-8", Command::Undo, &mut editor);
    assert_eq!(editor.document().timeline[0].id.len(), 8 * 1024 * 1024);
    assert_eq!(editor.retention_stats().undo_snapshots, 1);
    assert_eq!(editor.retention_stats().redo_snapshots, 1);
    // Undo to 4 MiB would store 8 MiB beside 10 MiB. The 10 MiB redo snapshot
    // is now oldest and farthest in the future, so only that state expires.
    apply("undo-to-4", Command::Undo, &mut editor);
    assert_eq!(editor.document().timeline[0].id.len(), 4 * 1024 * 1024);
    assert_eq!(editor.retention_stats().undo_snapshots, 0);
    assert_eq!(editor.retention_stats().redo_snapshots, 1);
    apply("redo-to-8", Command::Redo, &mut editor);
    assert_eq!(editor.document().timeline[0].id.len(), 8 * 1024 * 1024);
    failure_leaves_session(
        envelope(&editor, "no-10", Command::Redo),
        "nothing_to_redo",
        &mut editor,
    );
    assert_bounds(&editor);
}

#[test]
fn oversized_adjacent_snapshot_creates_edit_and_undo_barriers() {
    let mut editor = Editor::new(document()).unwrap();
    set_scale(&mut editor, "older", 2.0);
    apply("huge", huge_timeline(&editor), &mut editor);
    assert_eq!(editor.retention_stats().undo_snapshots, 2);
    // Removing the large live state must not retain older undo snapshots behind
    // the missing immediately preceding large snapshot.
    apply("small", Command::SetTimeline { clips: vec![] }, &mut editor);
    assert_eq!(editor.retention_stats().undo_snapshots, 0);
    failure_leaves_session(
        envelope(&editor, "no-jump", Command::Undo),
        "nothing_to_undo",
        &mut editor,
    );
    set_scale(&mut editor, "adjacent", 3.0);
    apply("undo-adjacent", Command::Undo, &mut editor);
    assert!(editor.document().timeline.is_empty());
    assert_eq!(editor.document().character.scale, 2.0);
    assert_bounds(&editor);

    let mut editor = Editor::new(document()).unwrap();
    apply("huge", huge_timeline(&editor), &mut editor);
    apply("undo-huge", Command::Undo, &mut editor);
    assert_eq!(editor.retention_stats().redo_snapshots, 0);
    failure_leaves_session(
        envelope(&editor, "no-redo-jump", Command::Redo),
        "nothing_to_redo",
        &mut editor,
    );
    assert_bounds(&editor);
}

#[test]
fn exact_retry_byte_limit_overflow_and_oversized_retry_expiry() {
    let mut editor = Editor::new(document()).unwrap();
    let mut huge_id = envelope(&editor, "large", scale(&editor, 2.0));
    let result = CommandResult {
        revision: 1,
        summary: "Set scale to 2".into(),
        duplicate: false,
    };
    let base = serde_json::to_vec(&(&huge_id, &result)).unwrap().len();
    huge_id
        .command_id
        .push_str(&"x".repeat(EDITOR_RETENTION_LIMITS.retry_bytes - base));
    assert_eq!(
        serde_json::to_vec(&(&huge_id, &result)).unwrap().len(),
        EDITOR_RETENTION_LIMITS.retry_bytes
    );
    editor.apply(huge_id.clone()).unwrap();
    assert_eq!(
        editor.retention_stats().retry_bytes,
        EDITOR_RETENTION_LIMITS.retry_bytes
    );
    assert!(editor.apply(huge_id.clone()).unwrap().duplicate);
    failure_leaves_session(
        envelope(
            &editor,
            "x".repeat(EDITOR_RETENTION_LIMITS.retry_bytes + 1),
            scale(&editor, -1.0),
        ),
        "out_of_range",
        &mut editor,
    );
    set_scale(&mut editor, "next", 3.0);
    failure_leaves_session(huge_id, "revision_conflict", &mut editor);
    let oversize = envelope(
        &editor,
        "x".repeat(EDITOR_RETENTION_LIMITS.retry_bytes + 1),
        scale(&editor, 4.0),
    );
    let id = oversize.command_id.clone();
    editor.apply(oversize.clone()).unwrap();
    assert_eq!(editor.retention_stats().retry_entries, 0);
    assert_eq!(editor.retention_stats().retry_bytes, 0);
    failure_leaves_session(oversize, "revision_conflict", &mut editor);
    // A fresh envelope with the expired ID can succeed again.
    set_scale(&mut editor, id, 5.0);
    assert_eq!(editor.document().character.scale, 5.0);
    assert_eq!(editor.retention_stats().retry_entries, 0);
    assert_bounds(&editor);
}

#[test]
fn overflow_is_atomic_and_open_starts_with_empty_session_retention() {
    let mut doc = document();
    doc.revision = u64::MAX - 1;
    let mut editor = Editor::new(doc).unwrap();
    let last = envelope(&editor, "last", scale(&editor, 2.0));
    editor.apply(last.clone()).unwrap();
    failure_leaves_session(
        envelope(&editor, "overflow", scale(&editor, 2.0)),
        "revision_overflow",
        &mut editor,
    );
    assert!(editor.apply(last).unwrap().duplicate);
    assert_eq!(editor.retention_stats().undo_snapshots, 1);
    assert_eq!(editor.retention_stats().retry_entries, 1);
    let mut editor = Editor::new(document()).unwrap();
    set_scale(&mut editor, "edit", 2.0);
    let saved = editor.document().to_json().unwrap();
    let reopened = Editor::new(SceneDocument::from_json(&saved).unwrap()).unwrap();
    assert_eq!(reopened.document(), editor.document());
    assert_eq!(reopened.retention_stats().history_bytes, 0);
    assert_eq!(reopened.retention_stats().retry_entries, 0);
}

#[test]
fn long_session_fixed_workload_stays_bounded() {
    let mut editor = Editor::new(document()).unwrap();
    let mut successful = 0;
    for index in 0..10_000 {
        let command = envelope(
            &editor,
            format!("edit-{index}"),
            scale(&editor, 1.0 + (index % 20) as f32),
        );
        editor.apply(command.clone()).unwrap();
        successful += 1;
        assert_eq!(editor.apply(command).unwrap().revision, successful);
        failure_leaves_session(
            envelope(&editor, format!("invalid-{index}"), scale(&editor, -1.0)),
            "out_of_range",
            &mut editor,
        );
        if index % 10 == 0 {
            apply(format!("undo-{index}"), Command::Undo, &mut editor);
            apply(format!("redo-{index}"), Command::Redo, &mut editor);
            successful += 2;
        }
        assert_eq!(editor.document().revision, successful);
        assert_bounds(&editor);
        if [999, 4999, 9999].contains(&index) {
            println!(
                "checkpoint edits={} successes={successful} stats={:?}",
                index + 1,
                editor.retention_stats()
            );
        }
    }
    let stats = editor.retention_stats();
    assert_eq!(stats.undo_snapshots, 128);
    assert_eq!(stats.redo_snapshots, 0);
    assert_eq!(stats.retry_entries, 1024);
    println!("long-session edits=10000 successes={successful} final={stats:?}");
}

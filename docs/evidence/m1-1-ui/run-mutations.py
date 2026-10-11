from pathlib import Path
import difflib
import hashlib
import json
import os
import signal
import subprocess

root = Path.cwd()
paths = ['crates/nvwa-studio/src/lib.rs', 'crates/nvwa-studio/src/editor_layout.rs']
original = {name: (root / name).read_bytes() for name in paths}
sha = lambda value: hashlib.sha256(value).hexdigest()
baseline = {name: sha(value) for name, value in original.items()}
directory = root / '.work/ui26/mutations'
directory.mkdir(exist_ok=False)
manifest = {'baseline_sha256': baseline, 'trials': []}

def stop(signum, frame):
    raise SystemExit(f'interrupted by signal {signum}')

signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
trials = [
    ('idle-height-clamp', paths[1], [(' && delta != 0.0', '')],
     'actual_resize_idle_window_shrink_preserves_preferred_height'),
    ('commit-every-drag-frame', paths[0], [
        ('if response.changed() {\n                        preview = Some(values.clone());',
         'if response.changed() {\n                        commit_drag = true;\n                        preview = Some(values.clone());')],
     'actual_shape_drag_is_one_command_and_undo_redo_restore_complete_work'),
    ('space-keyboard-guard', paths[0], [
        ('if !guard.keyboard\n        && !interaction.busy()', 'if !interaction.busy()')],
     'actual_work_path_focus_blocks_space_and_document_shortcuts'),
    ('command-keyboard-guard', paths[0], [
        ('if !guard.keyboard && ctx.input(|i| i.modifiers.command && i.key_pressed(egui::Key::Z))',
         'if ctx.input(|i| i.modifiers.command && i.key_pressed(egui::Key::Z))')],
     'actual_studio_layout_controls_preserve_work_history_and_guard_focused_space'),
    ('discarded-pass-side-effects', paths[0], [
        ('if ctx.will_discard() {\n        return Ok(());', 'if false && ctx.will_discard() {\n        return Ok(());')],
     'discarded_editor_pass_does_not_install_layout_or_apply_commands'),
]

try:
    for label, name, replacements, test in trials:
        source = original[name].decode()
        mutated = source
        for before, after in replacements:
            assert mutated.count(before) == 1, (label, before, mutated.count(before))
            mutated = mutated.replace(before, after)
        (root / name).write_text(mutated)
        diff = ''.join(difflib.unified_diff(source.splitlines(True), mutated.splitlines(True), fromfile=name, tofile=name))
        (directory / f'{label}.diff').write_text(diff)
        command = ['cargo', 'test', '-p', 'nvwa-studio', '--locked', '--lib', f'editor_layout::tests::{test}', '--', '--exact']
        env = os.environ.copy()
        env['CARGO_BUILD_JOBS'] = '3'
        entry = {'name': label, 'production_file': name, 'mutation_sha256': sha(mutated.encode()),
                 'baseline_sha256': baseline[name], 'target_test': test, 'command': command,
                 'log': f'.work/ui26/mutations/{label}.log', 'diff': f'.work/ui26/mutations/{label}.diff'}
        try:
            with (directory / f'{label}.log').open('w') as log:
                result = subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
            entry['exit'] = result.returncode
            output = (directory / f'{label}.log').read_text()
            entry['named_test_failed'] = f'test editor_layout::tests::{test} ... FAILED' in output
            entry['runtime_assertion'] = 'panicked at crates/nvwa-studio/src/' in output
            entry['assertion_excerpt'] = output[output.find("thread '"):output.find('\n\nfailures:', output.find("thread '"))]
        finally:
            for restore_name, value in original.items():
                (root / restore_name).write_bytes(value)
            entry['restored_sha256'] = {restore_name: sha((root / restore_name).read_bytes()) for restore_name in paths}
            entry['exact_restore'] = entry['restored_sha256'] == baseline
            manifest['trials'].append(entry)
            (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print(json.dumps(entry), flush=True)
        assert entry['exit'] == 101 and entry['named_test_failed'] and entry['runtime_assertion'] and entry['exact_restore'], label
finally:
    for name, value in original.items():
        (root / name).write_bytes(value)
    manifest['final_restored_sha256'] = {name: sha((root / name).read_bytes()) for name in paths}
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

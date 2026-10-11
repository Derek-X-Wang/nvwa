# Native handback and follow-up

This later record resolves the previously pending native gestures, Open/reload,
Web-to-native exchange and Player checks on the exact final release binary.
The original GUI checkpoint and locked handoff remain historical records.

The human confirmed continuous jaw drag, release and one Undo returning to
0.73, and separator drag with Escape returning to the starting height. The
saved handback is revision8 and matches the revision4 native redo in every
content field. The hand session's individual revision changes were not
instrumented. The snapshot alone does not prove the one-command boundary.

Actual native Open loads the Web redo. Saving `web-through-native` compares
equal in all fields, including revision4. A click edit saved as
`native-before-reload` changes only jaw0.8→0.6 and revision4→5. Reopening the
saved Web Work and saving `native-reloaded` matches the entire Web redo again.

Player was launched with the same exact native executable and the saved Web
Work. The editor is hidden. Replay reaches an animated wave; seek pauses at3.2,
Play reaches4.117, Pause holds5.077 in two separate captures, and Restart
returns to idle at0.874. The source bytes remain unchanged. These are authored
fixture clips, not AI generation.

The smaller Studio capture is1204×834 physical pixels, approximately602×385
logical content points at2×. The human reported it usable, but some toolbar and
timeline content is clipped. It does not establish the required native1024×768
geometry or full control access. A later manual resize measures 1175×704 content
points. Profile, lock, reset retaining lock, unlock, replay and seek work there.
Saving after those actions matches the entire human handback, including revision8.
The restored Studio handback before that resize was 1280×720.
Native controller drag/resize and modifier-shortcut attempts were ineffective;
no new physical native Command+A/V result is inferred. Physical IME and browser
DPR/zoom remain unverified on this candidate.

The separate [startup-size harness](../../../../../experiments/18-native-viewport-harness/REPORT.md)
now exercises the same production native UI at 1024×768. It changes only the
initial window resolution. Actual Shape/Profile, lock, reset retaining lock,
unlock, horizontal scrollbar, play/pause and seek pass. The saved Work remains
equal in every field, including revision8. Interactive capture buffers are
2048×1600 including chrome; a focused runtime observation independently reports
1024×768 physical at scale1, hence1024×768 logical. Capture pixels alone do not
establish runtime DPI. Exact packaged-binary1024 startup and a resize transition
to that exact size remain NOT-RUN. Manual packaged resize1175×704 is separate.

All 28 copied screenshots and saved Works retain original bytes, recorded in
[MANIFEST.json](MANIFEST.json). Private home paths, process metadata, failed
controller attempts and an accidentally selected default Studio are omitted.
The31 measured source inputs and exact native executable still match the build
inventory. No source change or additional build is implied by this follow-up.

```sh
python3 -B docs/evidence/m1-1-ui/gui/verify-work-snapshots.py
python3 -B docs/evidence/m1-1-ui/gui/followup/verify-followup.py
```

These commands compare recorded files. They do not drive a GUI or establish
physical input or window size. [Checkpoint](checkpoint.json) records the actual
actions, human report, identity and limits.

VERIFIED — native gestures, complete Work exchange/reload, Player and the
separately identified production-library1024×768 control check pass. Physical
input, DPI and packaged-binary exact-size limits remain explicit.

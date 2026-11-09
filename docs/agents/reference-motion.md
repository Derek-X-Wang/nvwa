# Author a reference motion with the CLI

Use `nvwa-cli describe-capabilities work.json` to check
`cli_contract.reference_motion` for support and the joint list. Start with an
existing B1 rehearsal Work, or run `nvwa-cli new-character assets base.json`.
Use the Work's current revision and a unique command ID in each command.

`nvwa-cli apply base.json motion-command.json original.json` installs one
finite clip on the existing character. This replaces the Work's current
timeline. Each track contains 2–120 keys, starting at zero, strictly increasing,
and ending at the stated duration of 3–5 seconds. Omitted joints use their
fitted rest pose.

```json
{
  "command_id": "reference-first-pass",
  "expected_revision": 0,
  "command": {
    "type": "set_reference_motion",
    "motion": {
      "duration_seconds": 4,
      "rotations": {
        "calf_l": {
          "axis": [1, 0, 0],
          "keys": [
            {"seconds": 0, "degrees": 8},
            {"seconds": 1, "degrees": 34},
            {"seconds": 2, "degrees": 8},
            {"seconds": 4, "degrees": 8}
          ]
        }
      },
      "pelvis_offsets": [
        {"seconds": 0, "offset_metres": [0, 0, 0]},
        {"seconds": 4, "offset_metres": [0, 0, 0]}
      ]
    }
  }
}
```

Rotation axes are unit vectors in each joint's canonical bone-local rest
frame. Angles are in degrees from −180 to 180. The evaluator follows the
shortest arc around the track's fixed axis between keys. Pelvis offsets are
in metres along the pelvis parent's local axes and are bounded to ±0.25 m per
axis. The evaluator linearly interpolates offsets. The Web player and CLI
sample the same evaluator. All track times are in seconds, relative to the
start of the clip.

`nvwa-cli inspect original.json` reads back the saved keys.
`nvwa-cli reference-pose original.json 0.5` returns the evaluated pose and
the Work hash. `nvwa-cli motion-query original.json assets 0 4 0.25 --samples`
with the motion-query build feature separately measures published body
geometry. Choose the joint and inspect the adjacent key times before editing.

Save the next command as `edit-command.json` and run
`nvwa-cli apply original.json edit-command.json edited.json`.

```json
{
  "command_id": "reduce-left-knee-peak",
  "expected_revision": 1,
  "command": {
    "type": "set_reference_rotation_key",
    "bone": "calf_l",
    "seconds": 1,
    "degrees": 22
  }
}
```

The command replaces one existing angle. Only the interpolation intervals
next to that key can change. Run the same sample queries against both Works.
Keep the input and output paths distinct to retain the original file.
An invalid command fails before writing the output.

Open each Work through the ordinary Studio Open action. Use the playback
controls to play at normal speed or seek. The reference timeline is authored
through the CLI. Use Studio Save As or `nvwa-cli save` for a separate copy.

The external Agent estimates poses and timing from the reference, including
marking uncertain observations. The Work stores its editable estimates.
Record source, author, license, clip range, and camera assumptions with the
reference separately from the Work.

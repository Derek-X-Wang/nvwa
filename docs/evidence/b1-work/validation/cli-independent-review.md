# Independent retained-CLI acceptance

PASS for the exercised offline CLI boundary:36 actual child invocations, both signed parameters and all five diagnostic poses. No renderer/Web/native-app acceptance is inferred. The retained binary's own help and describe-capabilities state that `new-b1`/`validate` authenticate assets; `apply`/`save` edit Work metadata only.

- CLI SHA256: `ea8182093c2bfcfb0b78e733154e612b351c78b71b12e69818e59dbbe557feec`.
- Genuine manifest SHA256: `abcdbc26e03431c740c5fce98de22902089f985823a3c655db2416d042d62b18`.
- Initial neutral schema3 Work SHA256: `91e51a4d1c8e80a01a986399ab2eeb54fc303dcf21aaa652931cff007d9538da`.
- Final saved combined-pose Work SHA256: `a062ee0d1548538cc6e61f173fc3ad0aced3312012065ca457cae91291a3810d`.

The asset tree was copied in full into one context-managed temporary directory. All missing/corrupt mutations affected that copy only. No product/source/Git/external writes, builds, UI, model, socket or server were started. All36 CLI child invocations returned and the temporary directory was confirmed removed.

## Actual command forms and results

`$TMP` denotes the removed test directory. Positive flows were `new-b1 $TMP/assets $TMP/created.nvwa.json`, `describe-capabilities <work>`, five iterations of `apply <current> $TMP/commands-N.json $TMP/applied-N.nvwa.json`, `save <applied> $TMP/saved-N.nvwa.json`, and `validate <work> $TMP/assets` before/after the roundtrips. Commands were built from the actual describe-capabilities examples using the actual character ID and current revision.

| Entry point | Exit | Result | Invocations |
| --- | ---: | --- | ---: |
| `apply` | 0 | `ok` | 5 |
| `apply` | 1 | `unsupported_pose` | 2 |
| `describe-capabilities` | 0 | `ok` | 1 |
| `new-b1` | 0 | `ok` | 1 |
| `new-b1` | 1 | `asset_hash_mismatch` | 2 |
| `new-b1` | 1 | `asset_missing` | 2 |
| `save` | 0 | `ok` | 7 |
| `save` | 1 | `invalid_json` | 1 |
| `validate` | 0 | `ok` | 12 |
| `validate` | 1 | `asset_hash_mismatch` | 1 |
| `validate` | 1 | `asset_missing` | 1 |
| `validate` | 1 | `asset_root_required` | 1 |

| Pose | torso_length | jaw_drop | Saved revision | Save roundtrip |
| --- | ---: | ---: | ---: | --- |
| neutral | -1 | 1 | 2 | Byte-identical; validates |
| shoulder | -0.5 | 0.5 | 4 | Byte-identical; validates |
| elbow | 0.25 | -0.25 | 6 | Byte-identical; validates |
| knee | 0.5 | -0.5 | 8 | Byte-identical; validates |
| combined | 1 | -1 | 10 | Byte-identical; validates |

Exact first shared-command batch (later batches use the table values/pose, distinct IDs and the revision of their input Work):

```json
[
  {
    "command": {
      "character_id": "character-1",
      "type": "set_parameters",
      "values": {
        "torso_length": -1,
        "jaw_drop": 1
      }
    },
    "command_id": "independent-parameters-0",
    "expected_revision": 0
  },
  {
    "command": {
      "character_id": "character-1",
      "pose_id": "neutral",
      "type": "set_diagnostic_pose"
    },
    "command_id": "independent-pose-0",
    "expected_revision": 1
  }
]
```

Negative cases:

- `validate <work>` without root returned `asset_root_required`; Work bytes stayed unchanged.
- Removing the actual copied `rig.game_engine.json` returned `asset_missing` from `validate` and `new-b1`. Existing output stayed byte-identical; an absent output was not created.
- Replacing one newline with one space produced same-length, syntactically valid JSON with different bytes. `validate`/`new-b1` returned `asset_hash_mismatch`, with the same output preservation/no-creation behavior.
- Restoring the genuine rig made validation succeed. Metadata-only `save` remained allowed during both asset faults and reported `asset_checked:false`, matching the documented boundary.
- `apply <work> <batch> <output>` with a valid parameter command followed by an invalid diagnostic pose returned `unsupported_pose`. It preserved the input and existing output; with an absent output path it created nothing. The successful prefix did not commit.
- `save <malformed-work> <existing-output>` returned `invalid_json` and preserved existing output.

## Retained artifact/source limits

The native receipt reports154 tests and a completed native package from run66 before cancellation of its obsolete Web phase. The separate wefty receipt records `failed` and cancellation `settled`. This is not a successful whole verification run, Web build or final-CI result. No deleted snapshot or private runner storage was inspected/recovered.

The native receipt records selected hashes/prefix comparisons; it does not establish whole-source identity. The actual retained CLI hash above is independently measured: the receipt's separate executable hash is not labeled as a CLI hash. This review uses the supplied HEAD85b6136 context without Git inspection or a rebuilt-current-head claim.

- Native receipt SHA256: `4cf82799a20409378aed5e64616915388d44789c88758e76e47b63c4266d0671`.
- Wefty receipt SHA256: `778b964a5a600a09ae656c97ae4c85114638c0e430c2e8265518d5ce808ac960`.

Today's selected source hashes compared with recorded snapshot hashes:

| File | Exact recorded snapshot hash match | Recorded prefix comparison |
| --- | --- | --- |
| `Cargo.toml` | True | None |
| `Cargo.lock` | True | None |
| `crates/nvwa-runtime/src/b1.rs` | False | True |
| `crates/nvwa-runtime/src/b1_web.rs` | False | False |
| `crates/nvwa-runtime/src/lib.rs` | True | True |
| `crates/nvwa-studio/src/lib.rs` | True | True |
| `crates/nvwa-core/src/lib.rs` | True | True |
| `crates/nvwa-core/src/b1.rs` | True | True |
| `crates/nvwa-cli/src/main.rs` | True | True |

These are comparisons against receipt text, not independent authentication of the unavailable snapshot or all-source equality. Recorded prefix claims are not upgraded to fresh proof. Runtime/Web code can differ even when this retained CLI boundary passes.

VERIFIED — Actual retained CLI create/validate/shared-command/apply/save and negative output preservation; complete temporary cleanup and exited CLI children. NOT-RUN — Renderer/GPU/native app/Web behavior, whole-source snapshot equality, current-head rebuild and final CI.

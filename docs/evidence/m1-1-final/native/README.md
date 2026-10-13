# Actual native acceptance — 2026-10-13

The running source cohort is `9df6d3a05296bed1b876edb81a7562ddfe98da83`.
The same release executable was used for the formal app and its private copy:
SHA256 `72d3df8cfdeea062282c8731b0a95cb971f90976fe881772f3e3c24afe76973a`.
The canonical GLB remains
`f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`.
No product code, dependency, formal package or original asset changed during
these checks. The copied app bundle is retained privately and is not committed.

## Observed behavior

| Case | Actual native result | Evidence |
| --- | --- | --- |
| Shape → Profile | Both real clicks change the panel. Complete saved Work bytes before/after are identical, revision0 and single looping idle. | [Shape](ui/native-shape-live.jpg), [Profile](ui/native-profile-live.jpg), [comparison](ui/tab-save-comparison.json) |
| Missing A asset | Valid Work opens with revision1/jaw0.61. A visible `Asset byte load failed: Path not found` names the isolated asset root. No old character remains; meshes/joints/players are zero. | [Missing A](isolated/a-missing.jpg) |
| Same-path recovery | Copy verified GLB bytes into the private root, then click Open with the same Work path. Ready returns with18 joints/4 morphs, real character and cleared error. Save output has zero complete-Doc differences. | [Recovered A](isolated/a-same-path-recovered.jpg), [comparison](contracts/a-whole-doc-comparison.json) |
| Missing again → different path | Reversibly rename only private A GLB, reopen A and observe the error/no character again. Open B with its existing private GLB: Ready returns, jaw0.61/nose0.27, error clears. | [Missing again](isolated/a-missing-again.jpg), [Recovered B](isolated/b-other-path-recovered.jpg) |
| Save → Open → Save | Open the actual native B Save output, observe Ready and unchanged parameters, then save again. Both complete Docs equal B; revision remains1. | [Reopened saved B](isolated/b-saved-reopened.jpg), [comparison](contracts/b-reloaded-whole-doc-comparison.json) |
| Authored sequence | Restart the saved three-row Work. Samples show idle at0.913, wave at3.783 and completed turn at9.0. | [Idle](isolated/sequence-01.jpg), [wave](isolated/sequence-07.jpg), [turn](isolated/sequence-completed-turn.jpg) |
| Temporary click action | Pause/seek to2.2 seconds in idle. Actual chest click produces wave and `Wave interaction · sequence cursor held`; controls disable and cursor stays2.2. After it ends, Play/idle2.2 returns. Save still equals the entire B input. | [Before](isolated/interaction-before.jpg), [active](isolated/interaction-active.jpg), [restored](isolated/interaction-restored.jpg), [comparison](contracts/b-after-interaction-whole-doc-comparison.json) |

The A output is1950 bytes/SHA256 `2b7c549c0ffe8244c9fccac9f17b232b806f6e584b154184efa24d3e98d399e8`.
All three B outputs are1952 bytes and byte-identical with SHA256
`3c1cc94efa5cb869bcdc0075ef14e062ad1a0c391a3e40c68083c2f749e8cf55`.
The two tabs-only outputs are1624 bytes with SHA256
`ff0b8e36adfc3ebadc5fc700a4c760f6f551273b56e85bf336563e18b63eb445`.
Tabs-only data is not substituted for the three-row recovery data.

## Data checks and history

The frozen comparator requires all object keys, array entries/order, strings,
booleans, integer identities and revision. Only declared f32 fields permit
different decimal spelling of the exact same finite IEEE-754 binary32 value.
It uses no epsilon and preserves signed zero. Four actual output comparisons
have zero differences; file comparison alone makes no GUI claim.

The initial helper incorrectly collapsed lexical `-0` into integer zero. Its
original bytes and the real CLI false-green are retained; the repaired helper
rejects that exact input. Twenty-nine synthetic comparator controls pass,
including five real JSON/CLI controls. These are separate from113 Rust product
tests. Original local receipts contain absolute paths and are historical data;
they must not be treated as evidence of execution on another checkout.

`native-checkpoint.json` is the earlier pending checkpoint. It remains unchanged.
Earlier tool actions produced stale-looking captures or no usable window; the
cause remains UNKNOWN. Those observations do not establish a product input
defect, DPI cause or shader problem. Derek physically confirmed “Profile 能切换，
角色在动”. After the requested foreground handoff, triple-click selection plus
direct typing and actual Save/Open worked. A prior unintended relative Save
showed a read-only filesystem error; that is excluded from the asset cases.

All screenshots here retain the original JPEG bytes. No images were transformed.
The [completed Cua packet](review/native-acceptance-provenance-manifest.json)
contains22 successful calls, two explicitly excluded failures and zero missing
call/completion/output pairings. Of27 screenshots,22 match the exact decoded
raw tool-output bytes; five unemitted sequence samples bind to the completed
awaited capture/write loop. Original records are reversibly compressed; their
raw and gzip hashes are in [the copy manifest](review/provenance-copy-manifest.json).
Process receipts bind the isolated launch to its exact binary. Selected records
exclude unrelated session content. Independent review replays complete Docs
and inspects the actual images. Non-Cua filesystem/process observations remain
separate root receipts; they are not claimed as additional Cua trace records.

## Reproduction and bounds

Build/package commands are in the [candidate acceptance](../ACCEPTANCE.md).
Use an awake, unlocked Mac and a complete private copy of `dist/Nvwa.app`.
Keep its `Contents/Resources/assets` directory present. Native Work paths must
be absolute; Open/Save use the text directly and open no file chooser. The
exact eight-stage procedure is in [the frozen contract](contracts/native-recovery-contract.md).
Replace its historical private prefix with the new test directory. Verify the
actual launched binary and copied GLB hashes before each fault case. Perform
asset changes only in the private bundle. A file copy alone is not recovery;
click Open and observe the real result.

From any checkout, replay the frozen evidence without launching a renderer:

```sh
python3 -B docs/evidence/m1-1-final/native/review/replay_native_archive.py --root docs/evidence/m1-1-final/native
```

Expect exit0/PASS:78 initial copy entries, five provenance copy entries,27
screenshots with the22/5 binding distinction, four complete-Doc comparisons,
tabs byte equality and three B outputs byte equality. The78-entry manifest is
an initial copying cohort, not the final directory inventory. The wrapper pins
original helper/manifest/provenance hashes, confines paths and caps reads and
decompression. It calls the unchanged comparator directly with relocated
inputs; it does not run the historical absolute-path CLI. The first actual
archive replay failed for a missing screenshot; that red and the repaired
green remain retained. Five real CLI controls cover relocated success, missing
Doc, Doc tampering, gzip tampering and a same-byte symlink outside the archive.
These integrity checks do not add another floating-point semantics test or
product test. [Independent review](review/native-portable-replay-review.json)
accepts the scoped replay; [native final review](review/native-final-review.json)
accepts the actual behavior/provenance separately.

Both task-owned native processes90585/98713 exited after actual window close.
Private A GLB was restored after consumer exit. Formal binary/canonical GLB
hashes remain unchanged. See [cleanup](cleanup-receipt.json).

VERIFIED — scoped actual native tabs, missing-asset removal, same/different-path
recovery, Save/Open whole-Doc preservation and paused click-action restoration.
NOT-RUN — physical first presentation, continuous frame/performance measurement,
exact native1024×768 in this continuation, new physical IME/drag/DPI checks,
native-window pixel experiment31, signatures and other platforms. These results
do not establish byte/task/GPU-memory limits or the original blocked#3 case.

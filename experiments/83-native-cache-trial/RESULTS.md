# Native cache trial decision

**ADOPT — MAIN PUSH ONLY**, based on one reviewed fixed-source pair. The policy
keeps caching disabled for every PR/fork and leaves every original native gate,
argument, order, profile, toolchain, source mtime and time budget unchanged.
Production-main seed and ordinary changed-source reuse are **NOT-RUN** until
organic main CI. This is feasibility evidence, not a speed distribution or a
whole-workflow saving claim.

## Actual pair

[Run 39528124355, attempt 1](https://github.com/Derek-X-Wang/nvwa/actions/runs/39528124355)
completed all four jobs successfully. Head:
`3d64d9c6ee53cd2e77664b3ae01e7f2c5e691753`; both native lanes checked out merge
`08cc5614f4650afb0730eb97ecece85f416391de`, tree
`89cd9ee99b39c1c75e4f914f07c88a1b6a66f15f`.
Both used Rust/Cargo1.95.0, macos-14 ARM64 image `20260831.0302.1`, jobs1,
incremental0 and dev/test debug0. The warm job began after both original macOS
jobs completed, with at most two heavy compiles. Queue wait is separate.

| Work/cost | Seconds |
| --- | ---: |
| Cold native total | 2,767 |
| Cold cache boundaries: prepare2 + miss2 + finish10 + save18 + lookup1 + assertion2 | 35 |
| Cold no-cache work estimate `C0 = 2767 - 35` | 2,732 |
| Warm native total, including every restore/verification cost | 1,625 |
| Warm boundaries: prepare1 + restore12 + receipt8 + finish9 (already inside total) | 30 |
| Warm improvement `2732 - 1625` | 1,107 (40.52%) |
| Net for one reuse `2732 - 1625 - 35` | 1,072 |
| Additional portable trial-control step | 186 |
| Observed one-workflow net after that control | 886 |
| Conservative two-workflow projection `1072 - 2×186` | 700 |
| Warm scheduling wait, excluded from work | 351 |

The 20%,600-second warm and600-second net thresholds pass. The extra two-run
portable-cost projection also exceeds600seconds. Its100-second headroom must
cover any new recurring production policy/control cost; that new cost was not
in the trial sample and must be measured separately before final acceptance.

Both lanes ran identical ordered native Cargo gate arguments (26 calls), all
workspace/probe/appearance/format checks, three intended semantic red101/restored
green0 witnesses with restored source hashes, and the actual matrix. Matrix
proof is613 streamed/612 checked events,594/594 grid samples,30/30 deep keys,
three body and three face settings, no failures or missing samples and complete
marker. The separate source/Web job also passed. Independent review accepted
the raw logs, command timing, source identity, storage and arithmetic.

Cold lookup proved repository-wide key-prefix absence. The complete target had
4,659 files,823 directories and no links:2,867,143,950 logical bytes. The exact
1,077-byte marker made2,867,145,027 bytes, below4,294,967,296. Save was followed by
an exact lookup-only hit. The fresh warm lane required the same key and hashed
the restored target against the producer receipt before any native gate.

| Stored receipt | Actual value |
| --- | --- |
| Cache ID | `9252497013` |
| Ref | `refs/pull/107/merge` |
| Version | `b1f7e60a336e6cc15ef119fbcd901b87f8a6d6834c6a4bed6b63ec88ed080b8f` |
| Stored/downloaded bytes | `931245357` |
| Target inventory digest | `7f397654a679b891c295680ccd80dbbe8247deea5f175e9d35d2309fdc21d669` |

Exact trial key:

```text
nvwa-native-trial-v1-08cc5614f4650afb0730eb97ecece85f416391de-89cd9ee99b39c1c75e4f914f07c88a1b6a66f15f-ff5fa51b9db081597baa1ef046f97d0d1d23c8908d388cefe78fd8b003dfac74-39528124355-1
```

After raw logs, API/usage receipts and independent review were preserved, the
owner deleted only this completed trial entry and verified zero remaining
entries at2026-10-21T03:27:04Z. It cannot seed main. Production main uses a separate
namespace and accepts only exact main-ref/version receipts.

## Reproduction and failed experiment work

Public primary evidence can be retrieved without new CI:

```sh
gh run view 39528124355 --repo Derek-X-Wang/nvwa --log
gh api repos/Derek-X-Wang/nvwa/actions/runs/39528124355/jobs
```

Job IDs: portable118987469087; source/Web118991619069;
cold118991619147; warm119005542622. Whole job/step API timestamps bound costs;
helper/timing records are nested evidence and must not be added again. The cache
API receipt is historical because the owned entry was intentionally deleted.
Per-mutation runner log files were not exported; the finish process reread them
and emitted their hashes and semantic witness receipts. Offline review could
check those receipts and runner summaries, but could not re-hash original files.

Earlier experiment failures consumed576seconds portable in run39515960788
(native/cache never ran),3,403seconds native in run39518452707 (all original gates
passed; the new verifier confused total events with grid coverage before save),
80.438seconds in a local precommit fixture capture, and224.995seconds in a
local frozen-policy check whose fixture inherited a home-directory Cargo config.
Those are one-off failed
experiment work, separate from recurring costs above. No cache writes occurred
in those failures. The portable repair preserved every original group/body and
strict report guard; controlled generated-byte variance reproduced the old
ordering failure, while actual Ubuntu generated bytes remain UNKNOWN. The
matrix repair is grounded in the real producer/event contract and retained
hosted summary, with all original coverage assertions preserved.

Production-policy review also found two boundary failures in tiny local targets:
a self-referential link could pass non-strict resolution on Python3.14, and a
link inserted after cleanup could pass a following empty-directory check. The
shipping controls reproduce both old failures through the actual restore entry;
strict resolved regular-file links and no-follow post-cleanup validation now
reject them. These are review-discovered local failure paths, not hosted
corruption. The actual trial target had zero links. Test fixtures now use owned
physical neutral temporary directories and retain explicit ancestor-config
rejection, rather than weakening the production config guard.

VERIFIED — one authentic fixed-source pair, remote persistence/integrity,
original CI/CPU gates, storage bounds and independent review. NOT-RUN — organic
main reuse, changed-source performance, statistical/whole-pipeline speed,
live desktop/Web/GPU/IME or Alpha acceptance. Existing issue3 blockers and
issue4 validation gaps are unchanged.

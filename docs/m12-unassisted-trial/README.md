# M1.2 unassisted Alpha trial packet

## Status

- **Protocol:** PREPARED.
- **Physical-human trial:** NOT-RUN.
- **Artifact packet:** PREPARED for owner review.
- **Readiness:** PARTIAL. The owner must independently review the copied trial packages and select the test machine/browser before the session.
- **Issue:** [#49](https://github.com/Derek-X-Wang/nvwa/issues/49) remains OPEN.

This packet prepares a physical human to follow the existing [M1.2 Alpha guide](../M1.2-ALPHA.md) without live product coaching. It covers one Work from creation through save, find, reopen, Studio continuation, Player use, and native/Web file exchange. The observer records the participant's actions, words, errors, recovery, and help requests. Do not add an error beyond the guide's documented task. Mark any recovery condition that does not occur as NOT-RUN.

The participant receives only [Participant brief](PARTICIPANT-BRIEF.md), a session entry sheet, and the existing Alpha guide. The entry sheet supplies the selected app, CLI, Web URL, repository working directory, pinned guide inputs, fresh trial folder, and any path substitutions. It contains setup information only; it does not coach product actions or show expected results. The observer keeps [Observer checklist](OBSERVER-CHECKLIST.md) and [Results template](RESULTS-TEMPLATE.md) private from the participant. The guide remains the procedure and source of task wording. This packet does not replace or edit it.

## Readiness and evidence boundary

The existing [native/Web handoff report](../evidence/m12-agent-loop/REPORT.md) records guided operation on its exact historical artifact cohort. The [independent operator report](../evidence/m12-alpha-operator/REPORT.md) records an agent following the guide. Neither report establishes physical-human usability.

The newer recorded runtime cohort names source commit `7cfe171ea7d0bd2ba8e777b188e68ab9cbd85bf8`. A static Git comparison found that all 54 tracked files under `crates/`, `web/`, `assets/`, `scripts/`, `.cargo/`, and the root Cargo/toolchain files have the same blob IDs at that commit and this checkout's source head. The retained native executable and Web Wasm hashes match the runtime stage and actual renderer receipts. The existing offline CLI build also has an exit-0 build receipt and matching source inputs. This supports reuse as an existing build; it does not make it a new build or a signed artifact attestation.

The native/Web records preserve source and runtime hashes plus compile output, but they do not include a complete signed build manifest for every generated Web file and bundle metadata. The preflight stores exact hashes for the candidate JavaScript, bootstrap page, profile, fixture, and wrapper so the owner can make an informed reuse decision.

The existing native, Web, and CLI files were copied into private trial-preparation packets for owner review. The native copy uses a trial-only bundle name and identifier; only its `Info.plist` and a task-local reference Work were added or changed. The selected Web candidate is the new `ready-web-v2` package: it retains the current static site and its reference Work, excludes the old `experiment-controls/` directory, and contains zero symlinks. The earlier provisional Web copy remains private audit evidence and is not the selected candidate. The CLI copy retains its existing build bytes. Exact paths, full file/symlink manifests, and before/after hashes are in the private preflight record; participant-facing material does not expose private paths.

Selected reuse identity: source commit `7cfe171ea7d0bd2ba8e777b188e68ab9cbd85bf8`; native executable SHA-256 `bc063d68bf5009aafe7ee104bafaa317e27c9c82bbbe0a8a565d97e743272b38`; Web Wasm SHA-256 `648dfe770b5f903569e77fa35c5ec2a96311931dcb6878b7d2e69e526ab429c3`; copied CLI SHA-256 `c86518413dde4afe6000dda9092e09eaaf071d7a89924f621c0e051eeb5a102e`. The current 54-path source fingerprint matches that source commit. The selected Web packet is `alpha-prep/ready-web-v2`; its private manifest SHA-256 is `878bc94335aca6280062508d94897184521a98bbcf9dad79287862b34a80f9f8` and verifies zero symlinks.

These are source-matched existing artifacts, not new builds. A narrow copied-CLI preflight inspected and validated the authored reference Work against the copied native assets, then saved and rechecked a byte-identical baseline roundtrip. A second CLI-only feasibility replay used the guide's repo-relative profile, fixtures, verifier, and a fresh private output folder. It checks command-path and file-handling feasibility only; the historical verifier audits retained evidence, not the prepared Work. Fresh compilation and clean generated-build attestation are NOT-RUN. No native app, browser, or Web server was run. The owner must review the copied packages, keep the reference Work observer-only, and select the machine/browser before the physical trial. Keep readiness PARTIAL until those checks are complete.

The current bundled character profile and fixture still match the hashes recorded by the historical handoff evidence and the newer runtime bundle. The historical reference Work is retained at [agent-input.nvwa.json](../evidence/m12-agent-loop/agent-input.nvwa.json) and [final.nvwa.json](../evidence/m12-alpha-operator/final.nvwa.json); both have the same SHA-256. A copy is included in the private packages for observer readback only. It is not a participant starting Work and must not be shown or handed to the participant. The participant must create a new Work in a fresh trial folder.

## Trial boundary

Use the supported macOS arm64 and WebGPU browser environment described by the Alpha guide. The native app, offline CLI, Web Studio page, and fresh trial folder are supplied and prepared. A session entry sheet supplies the selected local URL, repository working directory, pinned guide inputs, and exact path substitutions for the supplied artifacts and trial folder. Skip the guide's build/setup section and begin at its Work creation task. Use only the trial-owned folder and packages recorded in the results form. Save or download trial-owned Work JSON files, including the guide's `.json` paths and browser `.nvwa.json` exports, as needed for the documented handoff. Do not download or install software, model weights, dependencies, or unrelated files. If sign-in or a machine-wide change is requested, stop and record the exact prompt.

This is a usability observation. Build, runtime, issue, and historical guided evidence stay separate. A script, replay, agent run, or previously guided human observation cannot be counted as this trial.

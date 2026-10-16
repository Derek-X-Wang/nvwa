# M1.2 unassisted Alpha trial packet

## Status

- **Revised participant protocol:** PREPARED; the [Chinese participant brief](PARTICIPANT-BRIEF.md) is the task sheet.
- **Physical-human independent attempt:** PAUSED at a help request before Work creation. Complete unassisted Alpha acceptance remains NOT-RUN.
- **Guided follow-on:** participant-reported success editing and exchanging a supplied Work; see [dated results](RESULTS-2026-10-15.md). This does not complete creation or independent acceptance.
- **Next-session readiness:** PARTIAL. The revised external authoring-agent entry, app entries, empty folder, machine and browser must be reviewed before any later trial. No new trial is requested or started by this revision.
- **Issue:** [#49](https://github.com/Derek-X-Wang/nvwa/issues/49) remains OPEN.

The earlier handoff concentrated on developer reproduction. The participant asked for concrete steps. The revised packet supplies a short Chinese task: ask the prepared external agent to create a new Work using the supported offline CLI, then personally edit, save, find, reopen, use Player, and exchange the same Work between native and Web. This preserves creation from scratch; a supplied nine-second Work is not the participant input. The external agent is a task executor, not a new built-in Nvwa feature or a live product coach.

The participant receives only the [Chinese participant brief](PARTICIPANT-BRIEF.md) and a completed private [session entry sheet](ENTRY-SHEET-TEMPLATE.md). The [M1.2 Alpha guide](../M1.2-ALPHA.md) remains the developer/authoring-agent reproduction reference, including its deterministic stale-revision recovery exercise. It is not required participant reading. The observer keeps the [checklist](OBSERVER-CHECKLIST.md), [results template](RESULTS-TEMPLATE.md), prior results and reference Works private. Record any normal-use error and recovery; do not inject an error into the human task. A recovery condition that does not occur is NOT-RUN.

## Readiness and evidence boundary

The following is the retained artifact-preparation record, not a readiness claim for the revised protocol or a new runtime check. Historical hashes and reference files remain unchanged.

The existing [native/Web handoff report](../evidence/m12-agent-loop/REPORT.md) records guided operation on its exact historical artifact cohort. The [independent operator report](../evidence/m12-alpha-operator/REPORT.md) records an agent following the guide. Neither report establishes physical-human usability.

The newer recorded runtime cohort names source commit `7cfe171ea7d0bd2ba8e777b188e68ab9cbd85bf8`. A static Git comparison found that all 54 tracked files under `crates/`, `web/`, `assets/`, `scripts/`, `.cargo/`, and the root Cargo/toolchain files have the same blob IDs at that commit and this checkout's source head. The retained native executable and Web Wasm hashes match the runtime stage and actual renderer receipts. The existing offline CLI build also has an exit-0 build receipt and matching source inputs. This supports reuse as an existing build; it does not make it a new build or a signed artifact attestation.

The native/Web records preserve source and runtime hashes plus compile output, but they do not include a complete signed build manifest for every generated Web file and bundle metadata. The preflight stores exact hashes for the candidate JavaScript, bootstrap page, profile, fixture, and wrapper so the owner can make an informed reuse decision.

The existing native, Web, and CLI files were copied into private trial-preparation packets for owner review. The native copy uses a trial-only bundle name and identifier; only its `Info.plist` and a task-local reference Work were added or changed. The selected Web candidate is the new `ready-web-v2` package: it retains the current static site and its reference Work, excludes the old `experiment-controls/` directory, and contains zero symlinks. The earlier provisional Web copy remains private audit evidence and is not the selected candidate. The CLI copy retains its existing build bytes. Exact paths, full file/symlink manifests, and before/after hashes are in the private preflight record; participant-facing material does not expose private paths.

Selected reuse identity: source commit `7cfe171ea7d0bd2ba8e777b188e68ab9cbd85bf8`; native executable SHA-256 `bc063d68bf5009aafe7ee104bafaa317e27c9c82bbbe0a8a565d97e743272b38`; Web Wasm SHA-256 `648dfe770b5f903569e77fa35c5ec2a96311931dcb6878b7d2e69e526ab429c3`; copied CLI SHA-256 `c86518413dde4afe6000dda9092e09eaaf071d7a89924f621c0e051eeb5a102e`. The current 54-path source fingerprint matches that source commit. The selected Web packet is `alpha-prep/ready-web-v2`; its private manifest SHA-256 is `878bc94335aca6280062508d94897184521a98bbcf9dad79287862b34a80f9f8` and verifies zero symlinks.

These are source-matched existing artifacts, not new builds. A narrow copied-CLI preflight inspected and validated the authored reference Work against the copied native assets, then saved and rechecked a byte-identical baseline roundtrip. A second CLI-only feasibility replay used the guide's repo-relative profile, fixtures, verifier, and a fresh private output folder. It checks command-path and file-handling feasibility only; the historical verifier audits retained evidence, not the prepared Work. Fresh compilation and clean generated-build attestation are NOT-RUN. No native app, browser, or Web server was run. The owner must review the copied packages, keep the reference Work observer-only, and select the machine/browser before the physical trial. Keep readiness PARTIAL until those checks are complete.

The current bundled character profile and fixture still match the hashes recorded by the historical handoff evidence and the newer runtime bundle. The historical reference Work is retained at [agent-input.nvwa.json](../evidence/m12-agent-loop/agent-input.nvwa.json) and [final.nvwa.json](../evidence/m12-alpha-operator/final.nvwa.json); both have the same SHA-256. A copy is included in the private packages for observer readback only. It is not a participant starting Work and must not be shown or handed to the participant. The participant must create a new Work in a fresh trial folder.

## Trial boundary

Use the supported macOS arm64 and WebGPU browser environment described by the technical Alpha guide. Supply reviewed native Studio, a separately identified Player entry that starts without a reference Work, Web Studio, the offline CLI/profile, and a fresh empty trial folder. Complete the session entry sheet with participant-visible launch labels and destinations; the checked entry points are prerequisites, not something a nontechnical participant must discover through build commands.

Prepare an external authoring-agent session with the reviewed CLI, profile, writable trial folder and developer references. It waits for the participant's creation request. It must inspect capabilities, create a new Work and report the exact saved file location; it must not copy a completed reference Work, operate the participant's GUI, or give live advice for later product steps. Record its identity, fixed setup instructions, actual tool calls, outputs and any errors privately. Agent-handled CLI recovery is agent evidence, not human error-recovery evidence. Human discovery here means finding and using the supplied task entries; it does not establish unaided knowledge of CLI syntax or an unprompted product feature discovery.

Only the participant may carry out the Studio, save/find/reopen, Player and native/Web steps during the independent part. If the participant asks for help, pause that part and record the exact request. Any later live guidance is ASSISTED. Fixed written steps do not prove that every control is self-explanatory; record any resulting confusion without changing the task after it starts.

Use only trial-owned files. Saving or downloading the participant's Work JSON files for exchange is allowed. Do not download or install software, model weights, dependencies or unrelated files. Stop and record any sign-in or machine-wide-change request. No setup, app/server launch or new human trial was performed for this documentation revision.

Build, runtime and historical guided evidence stay separate. A script, replay, authoring-agent success or previously guided observation cannot be counted as independent human completion.

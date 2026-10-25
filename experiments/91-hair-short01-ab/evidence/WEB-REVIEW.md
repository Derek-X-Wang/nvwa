# Independent Web evidence review

## Prepared bundle and first A capture

Reviewer performed read-only saved-source/metadata inspection; no browser, replay, validator, test, build, or image judgment.

Wasm receipt reports exit0, no timeout,62.74155175s wrapper duration; actual Cargo log reports successful dev build in57.13s. Source freeze remains45files with manifest `0d16a3c5a6afc878c0da02820994f81dd2994b03994c05bb932c7f923cea90ca`. Raw Wasm digest in receipt and staged bundle agrees: `22961fd2a6491550ac0ceba825724f67e7ed419fb9b3a7b633c2b7f7caf4e90e`.

Fresh metadata hashing confirms bundle identity manifest `c1ff8f9e21eb8b56eb55b32f358de62f8d466a1c4962e77e155afa94722a0284`, site manifest `52e9f4a70736c7754e70af65e401f400ca8acd2d7feab6bc1b26b9e154ca7afa`, all105site files with no mismatches or extras, exact frozen index.html, and all45source hashes. This validates local saved bundle identity; root owns evidence that the browser loaded this site.

Fresh A1 raw-file readback matches the saved visible transfer manifest:

- Bytes14,258,697; SHA256 `0c3efcedd53cff1364b508272e3dd1a06843f2d175977e5edbe169bc0283119d`.
- Original report substring161,317B and frame substring14,097,360B match their separate manifest digests without reserialization.
- Report/frame/transfer request IDs all `web76-2`; ready/current/acknowledged/successful; AOriginal, source0 held, exact default Work, Combined/Textured,1280x720.
- Export declares exact A replay and matching previsibility publication; decoded A pixels equal the original short04 pin. Image metadata remains2048square,sRGB,mip1,Default sampler.

No contradiction found in this saved build-stage-A1 chain. These identity checks do not run the source validator or prove GPU contact/visual quality. Root reports B has not yet been selected and browser automation is blocked; B and restoredA evidence are therefore absent. Full A-B-A invariants and visual comparison remain NOT-RUN. Subsequent controls must still match A1's exact exported camera/stage/viewport and other envelope state; attempted canvas keyboard input cannot be assumed harmless without the final comparison.

Detailed readback is `web-A1-chain-readback.json`. No reviewer-owned processes were started.

## Completed A-B-A pilot: PASS

Fresh readback of all three original raw exports matches each saved visible transfer manifest, including the exact raw report and frame substring byte lengths and SHA256 values without reserialization. Request IDs are `web76-2`, `web76-3`, and `web76-4`; each record is ready/current/acknowledged/successful. Variants are AOriginal/BShort01/AOriginal, all use the exact default Work, held source0, Combined/Textured, and1280x720. Camera objects are exactly equal across all three.

| Export | Bytes | SHA256 |
| --- | ---: | --- |
| A1 | 14258697 | `0c3efcedd53cff1364b508272e3dd1a06843f2d175977e5edbe169bc0283119d` |
| B | 15115517 | `65e83b68559a211b799c72bdcb4dbd745f453d7b02cf3ead9764fd824fd1a6db` |
| A2 | 14258697 | `778b609086a84220a3d9b264304a844a67b0cec92ded77ec15d28800e55bc38d` |

Root's frozen full validator receipt and output show exit0/no timeout in4.11963675s, complete nonasset envelope equality and exact A restoration. Under explicit root authorization, reviewer independently ran existing `check_record(B, 'b')` once, plus existing comparison/restoration projections. B passed; actual positions, normals, UVs, rest positions and scales had zero replay error; source-normal maximum difference was1.1102230246251565e-16 under the unchanged existing tolerance. This uses authenticated short01 maps/UVs/indices, full-positive53-bone weights, actual diffuse-pixel identity and unchanged material/image policy. No new algorithm, framework, capture, or tolerance was introduced.

Both independent projection comparisons passed: A1 equals A2 except the existing request/stability exclusions; A/B entire nonasset envelopes equal under the original declared B field exclusions. All45 frozen source hashes still match manifest `0d16a3c5a6afc878c0da02820994f81dd2994b03994c05bb932c7f923cea90ca`. The earlier attempted canvas keyboard input did not leave an exported camera/envelope difference in these records.

Reviewer also viewed original `A2-observation.jpg`. It visibly restores the original short04 appearance and shows ready/current request `web76-4`. Visual correspondence supports restoration observation; exact data equality is supplied by the record projection, not a claim of pixel-identical screenshots.

**Final bounded pilot gate: PASS.** The prior independently formed visual judgment remains: B exposes forehead and both eyes, shows a clear more-natural front boundary than A, and has no obvious new frontal fit failure in this one view. This supports proposing a separately bounded wider acceptance stage. Full acceptance/adoption, motion and shape cohorts, side/back contact, true GPU contact metrics, native visual acceptance, and genuine CLI/Work persistence for B remain NOT-RUN. Production A remains the established source. No inference about those gaps is drawn from these passes.

Detailed final record is `final-ABA-readback.json`. Reviewer introduced no persistent processes. Root owns remaining live browser/server and build-target lifecycle; their final cleanup was not independently verified in this final readback.

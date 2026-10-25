# Independent R2 scope review

Decision: **ACCEPT_PILOT_SCOPE**. No material plan correction is required. This accepts one bounded counterfactual construction and comparison under the proposal's existing stop rules. It is not acceptance of a candidate, visual quality, contact improvement, production adoption, or a sole-cause explanation.

Reviewed 2026-10-24 in the assigned hairline79-geometry checkout. Reviewer writes only this task's `review/` directory. Applied the agent-orchestration worker intake: no delegation, peer contact, external writes or human requests. No new correction, source-rule reconstruction, deformation metric, render, build, CLI execution, download, inference or CI was performed by the reviewer.

## Evidence and judgment

I read `root/TASK.md`, `main/PROPOSAL.md`, `main/proposed-region.json`, `main/CHECKPOINT.md`, selected facts from both retained-data JSON reports, original source authoring code, the original fixture ADR, relevant existing parser/validator code and verification policy. I directly viewed the retained actual `experiments/50-upper-arm-neutral-ab/results/web-candidate-canvas.png`. Its image-right upper cap has a small visible irregularity, consistent with the proposed physical-left target. Its size and the lack of exact pixel-to-face ownership limit causal attribution; neither prevents one controlled counterfactual. No additional source scene or GPU face-ID framework is needed for this pilot.

The source generator is explicit: body transforms are applied at `tools/blender/generate_fixture.py:83`; source bone segments are authored at lines 150–162; segment distance at 165–167; the hard arm-route selection is at 179–180, torso selection at 183–184, and Gaussian/normalization/pruning at 185–191. Export uses `export_yup=True` at line 305. Source z is height; the proposal's glTF `(x,y,z)=(author x,author z,-author y)` is coherent. The chosen range stays below the head-route and height-route boundary. It contains both sides of the x=.285 source routing discontinuity.

Fresh read-only metadata checks authenticated:

- Candidate50 GLB SHA256 `2779b012405a915cbc84b38dc18e5eb7a91215661b54ac0c7753ecebb49feae7`.
- Generator SHA256 `bc54eec314ccba2ca2a77499b03d96b1ec9afb8c38cfbb9ac9e1fb04f5736f0e`.
- Node22 is the continuous clothed surface, mesh4, skin0. Primitive1 uses POSITION36, JOINTS_0 38 and WEIGHTS_0 39. Those two skin accessors have no other primitive users.
- Selecting the serialized positions with the proposed open bounds reproduces exactly the 96 frozen vertex IDs. Their incident topology reproduces exactly the 259 frozen face IDs.
- There are no exact-position duplicate groups touching this selection within primitive1, and no selected positions repeated in the other four body primitives. Thus no existing exact-position material/normal seam copy is left unchanged while its selected copy moves. This is a precise exact-position observation, not a global topology or near-coincident-surface proof.
- The GLB contains the saved `genuine44_calibrated47` animation with 90 input samples, plus original idle/turn/wave animations. All of their bytes remain under preservation, not only the named motion.

The retained edge evidence is appropriately narrow: at key89, 6497→6508 changes from 9.638 mm rest length to 68.360 mm posed length, and 8998→9001 from 9.594 to 64.612 mm. The saved endpoints cross the source boundary and use nearly disjoint arm/torso influences. I read these deformed values from retained observations; I did not recalculate them. Fresh inspection of the original serialized endpoint weights corroborates their routing separation. This makes a source-route discontinuity a plausible, falsifiable contributor to cap deformation. It does not prove those edges own the visible notch or exclude source motion, rig geometry, shading, anatomical twist, or runtime contributions.

## Accepted scope and implementation cautions

The exact single operation in PROPOSAL is coherent: fixed source-coordinate smoothstep blending between the two original routing distributions, one application, no motion-key input, no per-key fit, sweep, topology change, new contact engine or threshold adjustment. Only the 96 primitive1 JOINTS_0/WEIGHTS_0 records may change. Preserve all other BIN bytes and whole GLB JSON, including all local poses, original animations, rest/bind hierarchy, geometry, normals, morphs, indices, materials and opposite shoulder. New Work identity/path/hash is the declared derivative bookkeeping exception.

These are execution requirements already implied by the proposal, not a new plan cycle:

1. **Reconstruction first, fail closed.** Compare source-rule reconstruction with saved weights by actual joint identity, with omitted/zero slots treated consistently, on all selected vertices before constructing the new blend. Source vectors use Blender/mathutils arithmetic originally, whereas a portable reconstruction may differ slightly. The existing 2e-6 tolerance must cover the actual difference; if it does not, stop. Do not silently move the coordinate frame, substitute posed joints for source segment endpoints, change constants, or loosen tolerance.
2. **Slot indices are not node indices.** For this skin: slot9→node7→upper_arm.R, slot10→node6→forearm.R, slot11→node5→hand.R, slot3→node8→chest, slot4→node1→neck, slot2→node9→spine and slot1→node16→pelvis. Rank ties using actual node indices as proposed, then serialize through the inverse skin.joints mapping. Zero-weight padding must still use a valid slot. A wrong slot can remain numerically in range while naming the wrong bone; compare reconstructed identities, not four array positions alone.
3. **Four-slot reduction is fixture-local.** Recording and limiting every discarded positive weight, rejecting any per-vertex mass over 1%, renormalizing and checking serialized float32 sums at 2e-6 are coherent. This may reject the one pilot; rejection must end it without another band, support set, limit or candidate. Nothing changes B1's full-positive influence policy, production importer or GPU policy.
4. **New band edges remain a real appearance risk.** The smoothstep envelope reaches the unchanged routes at x boundaries and saved weights at y boundaries, but discrete four-slot truncation and retained source normals can still create visible artifacts. The unchanged 259 incident faces include triangles crossing the selection boundary. Observe them in the already-declared matched Web comparison; no extra repair or instrumentation loop is authorized.

## Acceptance interpretation

Strict shortening of the two named edges and a decrease of the maximum deformed edge length over the SAME frozen 39 edges at key89 are a mechanism diagnostic. They are not an appearance pass. Preserve the other six fixed key observations and the original 259-face source domain; do not reselect a more favorable subset after construction.

The original surface analysis uses at least .8 named-node influence at every vertex. A weight blend may remove faces from arm/torso partitions. Report exact membership changes and keep all old failures; fewer crossings with changed membership cannot be described as better contact or reduced penetration. The proposal already says this correctly. The selected source-face domain does not create a new penetration evaluator.

Actual CLI validation/save/reload, the unchanged independent parser/FK/skin/runtime comparison controls, exact preservation and the reconstruction/discard stops remain required. Old50's full source-direction and frozen-byte identity gates remain attached to old50. A derivative-specific allowed-byte comparison can enforce the new scope without weakening or relabeling old50's predicate.

Only after a valid offline result should one actual current-main Web control/candidate comparison at key89 and key0 proceed, using the same declared camera/stage and exact sampled motion. A visible cap improvement with no new visible band crease, volume loss or other defect is necessary. If the images are ambiguous at this scale, or there is no visible gain, retain NO-ADOPT/HOLD. No low numeric count substitutes for that judgment. A positive pilot can only proceed to existing broader acceptance; it cannot clear M2 or any retained HOLD/FAIL by itself. Unseen keys, hidden surfaces, anatomy/roll, semantic motion and human quality remain unverified.

## Secondary hair report review

Read `hair/INVENTORY.md` and `hair/local-receipt.json` only; no fresh source hunt. Their claim boundaries are coherent. Four exact missing archive paths and bounded direct-root inspection support local availability UNKNOWN, not global absence. They distinguish fresh short04 byte/header/topology checks from historical short03 identity and license records; zero new network bytes used from unknown bytes needed now; and source readiness from visual superiority/admission. Current A remains short04. No download, extraction or future comparison is authorized by the inventory. I did not independently rerun its hashes or filesystem search.

All #80 HOLD, 99-point backup/full21-before-fit, #112 original FAIL, #3 blocked, #4 gaps, old hair failures and experiment86 NO-ADOPT states remain unchanged.

**VERIFIED —** proposal/source/GLB scope consistency, exact selected vertex/face IDs, slot mapping, no exact-position duplicates touching the selected body region, and retained actual image read.

**NOT-RUN —** source-rule numerical reproduction, new candidate construction/evaluation, tests, CLI, build, current Web, native UI, CI, contacts/admission and visual improvement. No process, service, tab, port, download or child agent created. Report retained; reviewer writes stopped on return.

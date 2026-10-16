# B1 posed character gate v1

Owner/integrator: root. Baseline: research branch commit `4c68ce814dfcba7539cbc2349e0760f1df97bd06` on product `1a91178e894bad13bf51223b33b49cf33ea91a1c`. User explicitly authorized this bounded pose/desktop/Web stage, independent review, CI and autonomous merge after green gates. No new download/model run/extra machine or paid resource is authorized.

## Isolation and ownership

- Root: this contract, pose definition freeze, integration, CI/PR/merged-main verification.
- Reference worker: `56-b1-pose-reference/reference/` only, Blender/MPFB actual offline geometry/weights/rest/pose reference. No graphics rendering.
- Runtime worker: `57-b1-pose-runtime/` only, isolated copy of pinned B1, recorded necessary adapter/fix patches, actual CPU skeleton/skinning execution and same-source numeric comparison. Owns the shared actual B1 runtime source used by 58.
- Viewer worker: `58-b1-desktop-web/` only, shared native/Wasm prototype and explicit browser asset loading, consuming 57's actual B1 library and original approved inputs. No baked GLB/JSON playback may be reported as B1 library execution on Web. It may first scaffold using the immutable old B1 dependency, then switch to 57's owned copy.
- Preserve all 53–55 files and their outputs/recipes. A remains the existing source-compiled numeric control; it is not silently upgraded to a skinning implementation. No edits to the human checkout, product/root Cargo/lock or old assets.
- Native Codex control plane: four slots incl. root. At most two compilation jobs, one graphics task; no formal performance acceptance while heavy tasks compete. Workers request graphics token from root. Use only cached dependencies, network-offline Cargo. Checks >~5 minutes use local-only wefty per current skill; a logged non-sandbox capture failure permits direct fallback. No sharing a real-checkout build directory with a wefty snapshot.

## Shared inputs and poses

Approved original source/common manifest SHA256 `2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7`; private staging `.work/character-approved-20261016`. Existing B1 source is `55-source-character-runtime/derived-b1`, with exactly the recorded small-delta threshold patch. It may be copied into 57 after verifying every identity; 55 stays immutable. New source changes require a minimal recorded diff and actual failure/repair evidence, not a replacement kernel.

The eight existing body recipes remain fixed. Use neutral, shoulder, elbow, knee and combined diagnostic poses from `poses.json`, expressed in Blender bone-local rest frames (quaternion postrotation/matrix_basis), not inferred from bone names. These are authored test poses, never AI-generated motion. First verify actual source roll/rest convention; do not copy expected rest matrices into candidate computation.

Reference case fields: common/pose/source/driver hashes, body recipe ID, pose ID, exact command, source-ID body/garment positions, original untruncated deform weights, 53 bone names/parents/rest matrices and posed matrices, body/rig/garment world transforms, actual evaluation flags. Body capture retains complete cage before visibility MASK modifiers, as in 53, with masks restored. Garment is really fitted and skinned by MPFB. Large arrays remain ignored, compact hashes/metrics are tracked.

Before full pose runs, declare all conversion and tolerances. Compare rest/pose conventions explicitly. Numerical checks: rigid matrix components <=`1e-4`, joint-head metres <=`1e-5`, actual candidate CPU vs independently evaluated candidate-weight skinning <=`1e-5` metres. Full MPFB posed geometry quality gate: maximum component error <=`1e-3` metres body and <=`3e-3` metres garment, over every corresponding source ID. Report RMS and full coverage too. These predeclared quality limits are distinct from kernel numeric parity and may fail. Do not lower them after observing results. Weight truncation/normalization differences must be quantified against the full MPFB reference, never hidden by replacing its weights. Normals/tangents must be present, finite and correctly transformed; angle/appearance acceptance remains separately measured/inspected.

## Runtime/renderer contract and evidence

57 provides the actual B1 source crate at `57-b1-pose-runtime/derived/` (ignored) plus a tracked deterministic preparation script/patches; 58 depends on that exact source. For browser loading, add the smallest explicit target-path loading route to that copy, preserving actual target/macro/helper/mesh/rig algorithms. No `load_folder` readiness claim in HTTP. Root relays all coordination; workers never message peers.

58 must actually execute B1 on both platforms, expose body recipe + diagnostic pose selection and live changes, render the real body+garment+skin, record exact source/build/input/selected-frame identities and export/inspect actual runtime matrices/skinned vertex data. Build, actual launch, interaction, numeric frame match, graphics and resource observations are separate claims. No fake readiness, static image or pre-baked animation substitute.

Save/exchange is a scoped prototype JSON state (recipe+pose+camera if present), clearly distinct from production Nvwa Work. Verify same JSON restored in both platforms and reject invalid input while preserving active state; production Work adoption remains a later decision unless independently implemented and reviewed.

Required negative evidence includes a wrong matrix/bone mapping or omitted skin deformation that the real comparator catches, and a browser explicit-target omission that fails visibly rather than reporting ready. Keep original errors, nonzero codes and artifacts. Missing outputs remain NOT-RUN/unsupported. Runtime/visual failures can lead to a bounded HOLD; useful experiments may still be published after correct tests/review/CI, but no failing character is admitted to product.

#3 remains blocked; #4 retains its prior gaps; old M2 motion-quality HOLD stays unchanged. The final decision distinguishes experiment publication from product character/dependency admission. No final backend selected solely from green numeric tests.

## Bounded bridge contrast, authorized after actual failures

The unchanged four-influence route produced actual errors: duplicate padding changed `.5/.5` to `.75/.25` (about 90 mm); zero padding repairs that defect, but truncation still exceeds the fixed body quality limit. Separately, Humentity intentionally preserves base bone rotation when fitting body shapes, while MPFB refits it. Raw matrix equality therefore fails for some morphed bodies; this is a frame-convention difference, not sufficient evidence that the source's documented animation policy is invalid.

Two independent experimental factors are authorized, with original failures retained:

1. Compute canonical fitted frame `F` from the candidate's existing endpoint/roll algorithm over actual morphed helpers. Keep actual bind `C` and its policy. Source-derived gauge `Q = inverse(F) * C` converts canonical local pose `R` to `inverse(Q) * R * Q`. Compare canonicalized actual matrices `C * inverse(Q)` and `P * inverse(Q)` to the reference, retaining raw matrices and `Q`; independently assert physical skin equivalence. No expected/reference matrix is a generation input. All matrix/vertex tolerances remain unchanged.
2. A separately labeled `b1-full-weight-cpu` bridge aggregates actual RigWeights/Mhclo contributions, retains all **positive final aggregate influences** without the four-slot cap, and normalizes them for the shared original Rust CPU adapter. It must use actual source data, not reference weights. The recorded pre-normalization rows are already positive-filtered; they are not every signed raw contribution. The same code may update native/Web render mesh positions, normals and tangents, disabling GPU skin/morph to prevent double deformation. This is an added CPU bridge, not stock B1 GPU support or unchanged signed-transfer parity. The original four-slot GPU route remains measured and may remain HOLD.

First probe neutral/combined and body-positive/combined; only then expand the successful contrast to all 40 cases and both actual renderers. Keep each factor's failure/patch/result identities separate. No new source format, eight-influence GPU rewrite, download or expansion of parameter/pose scope is included. A four-slot quality HOLD cannot be silently replaced with a full-weight result under the same route name. Product admission still awaits full, reviewed native/Web evidence and an explicit bounded decision.

## Display visibility and framing

The full numerical body cage stays unchanged, including covered vertices and helpers. The viewer may omit helper faces and body faces covered by the **actual approved garment's parsed `delete_verts` rule**, matching the source clothing visibility policy. Record the exact source rule, mask counts and displayed index counts; do not handpick hidden problem vertices, inflate clothing, or remove vertices from the numerical comparison. A visibility mask does not prove collision or cloth physics quality. Frame the complete actual character bounds rather than assuming the old fixture's ground origin. Preserve the initial clipping and poke-through captures before this display correction.

## Transfer-policy clarification from actual display validation

The source permits signed Mhclo interpolation coefficients. Its legacy four-slot output retains negative aggregate garment weights at some vertices. The CPU bridge's existing `> 0` aggregate filter is a separate policy from removing the four-slot cap; MPFB reference transfer instead retains aggregates `> 0.001`. The measured geometry gate applies to this explicit positive-influence bridge. Keep the signed legacy attributes inspectable and record them without clamping; they are unused by the CPU display. Body full distributions contain no negative weights, while garment distribution differences and their resulting errors remain reported. Do not describe the bridge as retaining every raw influence or reproducing the unchanged signed-transfer policy.

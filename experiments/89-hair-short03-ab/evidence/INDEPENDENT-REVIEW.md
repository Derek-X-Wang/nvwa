# Final actual evidence review

Final verdict: **Technical A/B/A validation PASS; visual NO-GO / STOP-HOLD. Keep original A. Do not expand to full acceptance.** The B fringe covers the viewer-left eye/eyebrow. Complete restoration is now verified below. Earlier pending notes describe intermediate checkpoints only.

## A1 and bundle checkpoint

PASS for A1 export integrity and staged bundle identity. No blocker found. This is not yet A/B/A validation or visual judgment.

- Raw A1 JSON14,258,697 bytes, SHA2560c3efcedd53cff1364b508272e3dd1a06843f2d175977e5edbe169bc0283119d, matches the actual transfer manifest.
- Extracted exact raw report and frame JSON segments without reserialization. Report161,317 bytes SHA7c2329da0f01ac6b16810ff84ba056493f60ff4f220aae74aa5e6040c3f0466b and frame14,097,360 bytes SHA2207f21a6f77adc7f874ca7dcdcd744d7acc185ef31431b430b228b7afd7e708 both match.
- Requestweb76-2 is ready/current/acknowledged/succeeded; AOriginal source865/render991/triangles1050; original decoded diffuse identity; held source0; stable_updates2; viewport1280x720. Candidate sample equals full-base sample. A replay and previsibility match flags are true; full source-replay validation waits for complete A/B/A.
- All105 staged site files independently hash-match SITE-MANIFEST.json. All four pkg output sizes/hashes match BUNDLE-IDENTITY.json. Native/Web receipt hashes, stage receipt hash, and site manifest hash match their bundle bindings. The raw Wasm and bindgen outputs match the already reviewed compilation/staging chain. Staged index equals frozen experiment index.
- Stage receipt state predates root browser work and correctly says no actual Web run at that time. It is not used to deny or prove the later capture.

Limits: browser-served identity is supported by root's sole-controller capture provenance and immutable staged bundle; reviewer did not operate/reinspect the browser. B/A2, full numeric/invariant validation, exact restoration and neutral screenshot judgment are pending. No preferred visual winner has been assigned. No builds, network, candidate construction or UI actions by reviewer.

## B record and independent image judgment

**Quality verdict: NO-GO / STOP-HOLD. Do not expand to full acceptance.** Inspected original A1.jpg and B.jpg directly at 1280x720 with view_image; neither image was cropped or altered. No author or root preferred winner was supplied.

B's side-swept silhouette appears smoother than A's short upright hair. However, its fringe visibly covers the viewer-left eye/eyebrow and much of that side of the forehead/temple. A leaves both eyes visible. This is a material face-coverage regression. B hides much of the frontal scalp edge, so that hidden area cannot establish a repaired hairline. The exposed viewer-right part/temple has a relatively smooth edge, but that alone is not an obvious overall quality gain without regression. Different hairstyle/color is not treated as repair or as evidence of human preference.

No obvious floating card or open scalp gap is visible in B's exposed area at this ordinary size. This does not prove scalp contact or absence of intersections behind the fringe/back of head. There is no basis for declaring hidden fit repaired from this single view.

B export integrity: raw14,323,573 bytes SHA25604b08cef8ccb21b3181eb1fc1cea131ac0bdfe7f101cbef413b4d905df6c6355; raw report/frame segment lengths and SHA values match B-manifest exactly. Requestweb76-3 ready/current/succeeded; BShort03 source1011/render1071/triangles1922; authenticated B diffuse cb89a3dfe767b31d8fa9f337a46363d60958c6e31a65d403b04f3026ec3df2f9; A replay and previsibility flags true; held source0.

Reviewer independently executed the already frozen `check_record(B, 'b')` and A1/B comparison projection once (no build, capture, network or source changes). PASS: all compared non-asset envelope fields exact; position, posed-normal, UV, source-rest and source-scale replay error0; source-normal max error1.1102230246251565e-16. This includes authenticated B input/count/map/weights/pixels and fixed material/image policy checks.

A2 restoration is still pending. Completing that restoration evidence is appropriate; additional quality views/cohort or tuning are not justified by this result.

Screenshot identities:
- A1.jpg: da49f26c59cacad2f6db805461bc94ceac73709a1a98c5439d959831771ee2a9
- B.jpg: d63688a1723e269e07c275ac861fba81fd7a70c143fcc7762bc78a8592e1ff09

## A2 and final closeout

Reviewer independently verified A2 raw export14,258,697 bytes SHA256778b609086a84220a3d9b264304a844a67b0cec92ded77ec15d28800e55bc38d. Exact raw report/frame segment byte lengths and SHA values match A2-manifest. Requestweb76-4 is ready/current/acknowledged/succeeded; AOriginal original diffuse restored; held source0; A replay and previsibility flags true.

Reviewer directly computed the frozen restoration projection on A1 and A2: **exact equality** after only established request_id and stable_updates exclusions. This includes original hair arrays/pixels/material/image policy, bound state, body/eyes/clothing, Work, camera/stage and actual bones. Inspected unchanged A2-observation.jpg: original A selected, source0 and ready/current visible. Its expanded control panel is an observation of restored state, not a new matched quality cohort or a replacement for the neutral A1/B comparison.

Root's frozen validate.py output inspected: PASS on A1/B/A2, exit0,7.46050275s within240s. All three records report zero positions/posed normals/UV/source-rest/source-scale replay error and1.1102230246251565e-16 source-normal error. Stderr is empty. Reviewer did not repeat the full validator, build or test suites; independent B replay and exact A1/A2 equality were already checked separately. Final44 frozen source hashes still match.

The retained evidence contains the one scoped source0 A/B/A sequence and no added quality cohort/full-acceptance claim. Final quality decision remains NO-GO because B introduces obvious eye coverage, despite passing source identity, fit arithmetic, policy invariants and exact restoration. Do not tune the asset/material/camera or expand capture from this result.

VERIFIED — exact three-export integrity, frozen source/build/bundle chain, authenticated B source replay/material policy, unchanged non-asset state, exact A restoration, and visible B face-coverage regression.

NOT-RUN — head-width-plus, wider pose/view cohort,20 filtered Rust controller tests, native UI, GPU depth/contact/intersection, source-intended fit, CLI/Work-save, full acceptance or adoption. M2/#80 HOLD and historical failures remain unchanged.

A2 observation SHA256: acb4e6be0183d4637ab07abc74a92b7f4c1e5304be3feecbac8c6f09f2d9520b

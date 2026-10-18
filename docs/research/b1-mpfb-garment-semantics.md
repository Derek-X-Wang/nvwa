# Sportsuit fitting: bounded MPFB and Rust source differences

The selected sportsuit stretch is faithfully reproduced under Nvwa's retained Rust fitting and full-positive skinning contract. A source comparison found a small coefficient-fit difference and a different weight-retention policy from MPFB2.0.18. Scale-span signs coincide in all30 retained cases. These findings do not establish MPFB runtime equivalence, an author-intended body recipe, a unique visual cause or a repair. Garment quality remains HOLD.

This report paraphrases a bounded source audit and its independent arithmetic review. It contains no copied MPFB program implementation. No MPFB/Blender execution, new capture, download, extraction, asset replacement or production-policy change was performed for this report. The program GPL scope and graphical-asset CC0 scope remain separate.

## Exact source identity

The inspected source is MPFB2.0.18, fixed commit `d0a32e57a7f915cb2f2b95410e2117648c7bbb7e`. Its retained addon archive SHA256 is `c075b3e9b94b8e5556a5f03f4653602d02ea306de08126e8f55ed6dee28a2dad`. Each of the following source files was hash-checked against the retained extraction receipt. The addon entry point identifies its source directories as `src/mpfb/entities` and `src/mpfb/services`; the links use that recorded repository prefix and the fixed commit, rather than a guessed branch path. No fresh HTTP retrieval was used to produce this report.

| Official source permalink | Inspected responsibility | SHA256 of retained file |
| --- | --- | --- |
| [MHCLO parser](https://github.com/makehumancommunity/mpfb2/blob/d0a32e57a7f915cb2f2b95410e2117648c7bbb7e/src/mpfb/entities/clothes/mhclo.py#L119-L169) | Raw signed coefficients, offsets and reference parsing | `909ea98e31e04dfe8eb7c54849f74aa7365be0676a102c8c30e0e6c64b3eb9d8` |
| [Clothes fitting service](https://github.com/makehumancommunity/mpfb2/blob/d0a32e57a7f915cb2f2b95410e2117648c7bbb7e/src/mpfb/services/clothesservice.py#L121-L234) | Current shape-key mix, component spans and offset fitting | `20b60daeb862e35652035b9e94d1830f1bd2d86706b1e6056f0f2cee43c8d40b` |
| [OBJ import and base scale](https://github.com/makehumancommunity/mpfb2/blob/d0a32e57a7f915cb2f2b95410e2117648c7bbb7e/src/mpfb/services/objectservice.py#L770-L849) | Blender import and scale path | `4a90898fc83d237446355d2c9b8f30b90f056be0d2325b3989b30b341d075211` |

The same fixed fitting-service file contains [weight interpolation](https://github.com/makehumancommunity/mpfb2/blob/d0a32e57a7f915cb2f2b95410e2117648c7bbb7e/src/mpfb/services/clothesservice.py#L426-L489). Reading that method does not establish subsequent Blender armature/modifier behavior or optional custom weight/subrig behavior.

The retained Rust comparison uses the [MHCLO loader](../../vendor/humentity/src/loaders/mhclo.rs), [helper-based mesh fitter](../../vendor/humentity/src/assets.rs), [sparse helper adjustment](../../vendor/humentity/src/morphs.rs), [full-positive skinning adapter](../../crates/nvwa-b1-adapter/src/lib.rs), and [experiment70 analyzer](../../experiments/70-b1-garment-defect/diagnose.py). The analyzer SHA256 is `84c36d5a68c94c61503661d5096967608d47a15225f1c043084a957d6ee5b2d3`. Its [retained30 report](../../experiments/70-b1-garment-defect/evidence/interop-retained30/report.json) SHA256 is `988db631fcacd2995798ccadd83b92b4b973da55ffef241c2b0a314f9127ae93`. Those records remain historical evidence.

The raw `clothes/female_sportsuit01/female_sportsuit01.mhclo` SHA256 is `6df057d3116db93afbbbb6d692f92cce84aa16db699f47dd14e825d07c6fd42f`. The [converted production mapping](../../assets/characters/mpfb-b1-v1/garment/female_sportsuit01.mhclo) SHA256 is `700e8cb224a2c27a30220efa2ed7077e6a6901f5fcd74a1ee610f3e0370776e7`. Exact decimal checks retained all1797 helper triples, coefficients, source IDs and axes; every offset and all three reference distances were multiplied by0.1. Raw and converted identities must not be interchanged.

## Shared fitting intent and coordinate limits

MPFB uses the body's current shape-key mix, rather than fitting only to unmorphed basis vertices. Its position fit combines signed helper coefficients and a scaled offset. The retained Rust path also adjusts the helper cage using the selected sparse targets before fitting. Experiment70 compares against the same actual frame's complete fitted-rest body cage. This establishes how current-helper fitting is represented in the compared paths; it does not independently authenticate the original artist's body recipe or a complete MPFB macro/body mix.

The MPFB parser maps source Y-up offsets into Blender coordinates as `(x,−z,y)`. Its fit uses the corresponding source x/y/z reference spans through Blender's component ordering. Returning to the source frame restores the source component pairing. Rust retains source Y-up coordinates with metre-space offsets and reference distances; the existing target loader applies its single0.1 unit conversion. This is static coordinate bookkeeping. No executed Blender OBJ import, scale application, armature output or dynamic parity result follows from it.

## Raw versus normalized signed coefficients

MPFB keeps the raw signed position coefficients. The retained Rust loader divides each triple by its signed sum, and experiment70 reconstructs that Rust contract independently. Signed helper coefficients may extrapolate; they must not be confused with final skin weights or clipped individually.

The source mapping has1797 rows. Thirty contain a negative coefficient. Of all rows,467 have an exact decimal coefficient sum different from1; the largest absolute deviation is0.00001.

The selected shoulder triangle is source triangle200, corners `[246,244,182]`, at torso+1/jaw0 and arm source time2. Vertices246 and182 have coefficient sum1.00000. Vertex244 uses helpers `[17238,17235,16971]` and raw coefficients `[0.22500,0.54890,0.22611]`, whose sum is1.00001.

For a fixed cage and identical positive scale spans, write `S` for the raw coefficient sum, `p` for the normalized fitted-rest point and `o` for its scaled offset. The raw-coefficient point minus the normalized point is `(S−1) × (p−o)`. This is a data-arithmetic comparison, not execution of MPFB's program.

The independent decimal review gives the following selected244 delta in metres:

`[1.7077925124649327e-6, 5.6185692945476336e-6, −2.8630496174852573e-7]`

The largest coordinate component is **5.61857µm**; this is not a vector-length bound. Vertices246 and182 have zero exact-sum effect in this calculation. The result is conditional on the retained actual/replayed rest data, not an exact official-reference output.

| Quantity | Retained normalized fit | Coefficient-only analytical substitution |
| --- | ---: | ---: |
| Selected triangle rest area | `1.884345974021258e-5m²` | `1.883480946724231e-5m²` |
| Rest area relative to retained fit | 1 | `0.9995409403002671` |
| Rest-area change | — | **−0.045906%** |

The existing posed area is `0.0004146623110947154m²`, with actual posed/rest ratio `22.005635738420796`. Holding that same posed area fixed solely to illustrate the denominator change gives `22.015742278460543`, approximately **22.0157×**. This denominator-only ratio is **not a full MPFB posed simulation**. A different fitter/weight/modifier route could change the numerator; that result was not computed. The micrometre-scale coefficient effect does not establish a cause or repair of the roughly22× stretch.

The original audit's last digits differ slightly because it used floating-point rather than exact-decimal coefficient-sum arithmetic. The independent review found the difference consistent with that arithmetic choice; the scale and conclusion are unchanged.

## Absolute versus signed component spans

The sportsuit reference pairs/distances are source x `(5399,11998,1.3980)`, y `(791,881,2.2048)`, and z `(962,5320,1.8461)`. Their retained metre-space denominators are0.13980,0.22048 and0.18461 respectively.

MPFB uses absolute component distances divided by the reference distance. Rust/70 use the ordered signed high-minus-low component span. All30 retained reports have the same **positive** x/y/z scale ratios:

`[1.05865523538876, 1.0566942729001814, 1.0411678472620896]`

Therefore the absolute-versus-signed distinction has zero algebraic effect for these30 records. It is a real general-domain difference if an ordered component span changes sign. No result for arbitrary cages or every new eight-parameter recipe is inferred from these retained cases.

## Weight interpolation is deliberately different

Both paths aggregate the signed helper contributions **per bone** before choosing final bone influences. In the inspected MPFB method, each aggregate is divided by the raw coefficient sum and retained only when the resulting average is **strictly greater than0.001**. This method does not itself apply Rust's final positive-row normalization. Subsequent Blender modifier behavior, custom weights or subrig paths remain outside the executed evidence.

The admitted Rust contract retains **every strictly positive final bone aggregate**, has no top-four cap, and normalizes the complete positive row for linear blend skinning (LBS). Snapshots retain the original positive aggregate rows; the raw exported values must not be assumed already normalized. Experiment70 reproduces this explicit contract. A difference from MPFB does not by itself make that contract erroneous or justify silently replacing it.

Independent source arithmetic found363 vertices with409 positive bone averages at or below0.001 that the inspected MPFB interpolation method would omit. At selected vertex182, `spine_01` averages about`0.00011838968072479474`; the current normalized full-positive row retains about`0.00011838967746542639`. Vertices244/246 have no such small positive average. For these positive coefficient sums, uniform coefficient normalization cancels in the final normalized positive row; the cutoff and treatment of the remaining row are a separate policy difference.

These counts establish a source-level distinction. They do not show that an MPFB pose removes the stretch, reproduce Blender normalization, or support deleting small weights from the admitted Rust policy. No official-reference posed arrays were produced.

## Disposition

HM08, Female/Sport tags, generic body data and scale-reference distances do not identify the sportsuit author's exact body parameter recipe/helper rest cage. MPFB's current-mix fitter explains how it fits an available body; it does not recover the author's original body. That reference remains UNKNOWN.

No coefficient clipping, offset removal, weight cutoff, body deletion, pose removal, threshold relaxation or camera/material concealment is selected. No replacement is admitted; the [replacement plan](b1-source-replacement-plan.md) remains a future bounded comparison. Actual new eight-parameter endpoint cohorts are **NOT-RUN** at this report's handoff. Build success is not cohort, visual or source-equivalence evidence.

#79/#80 and M2 quality remain HOLD. #3 remains blocked, and #4 retains first-present/cold/GPU-memory measurement gaps.

VERIFIED — retained source/receipt hashes,1797-row conversion and coefficient sums, source-level coordinate/fit/weight distinctions, all30 retained scale signs, selected analytical delta/rest area and363/409 cutoff counts, with independent source/arithmetic review. NOT-RUN — official MPFB/Blender fit or armature execution, fresh reference or replacement captures, MPFB/Rust dynamic equivalence, authoring-cage authentication, a unique complete visual cause, GPU/render/performance or replacement admission.

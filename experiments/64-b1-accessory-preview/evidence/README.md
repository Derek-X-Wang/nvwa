# Retained actual-run evidence

This packet records the bounded native/Web preview from 2026-10-17 local time (2026-10-18 UTC). See [results and reproduction](../RESULTS.md). It does not admit production appearance, physical hair, gaze or new AI-generated motion.

| Packet | Meaning |
| --- | --- |
| `run.json` | Build identities, coverage, exclusions and limits |
| `web-build-receipt.json`, `native-build-receipt.json` | Original source/artifact byte hashes from the offline build |
| `web-matrix-*-manifest.json`, `native-matrix-manifest.json` | All 108 actual held CPU records, command/receipt/raw-artifact hashes |
| `web-matrix-summary.json`, `native-matrix-summary.json` | Independent source arithmetic and matched cross-platform differences |
| `*-lifecycle-summary.json`, `*-lifecycle-manifest.json` | Successful lifecycle captures, restoration, Save and explicit exclusions |
| `*-saved-work.nvwa.json` | Ordinary actual Save files; no preview appearance is persisted |
| `reviews/`, `review-index.json` | Independent review reports; path prefixes normalized, original report hashes retained |

Full arrays and original observed channel/Store bytes remain in retained local task evidence. The manifests authenticate those records; they do not pretend the raw data is bundled here. Reproduce new captures with the public [collector](../collection/README.md) and [source checker](../verification/README.md). Same-producer binding is not an independent world-freshness oracle, and CPU mesh arrays are not GPU readback.

The native matrix used collector r3. Its one later failed error-recovery collection is preserved and excluded. The published r4 collector fixes that pre-send-old-error race and passed both 14 pipeline controls and a fresh actual native recovery. Initial extra Web capture `w64-accessories-01` is excluded from the 54-case matrix because the original Store text was not saved independently.

The six Web screenshots below are unmodified copies from actual CUA captures. More held-frame screenshots remain local. Native screenshots cover representative held states, not every native matrix frame. Their original pixels were independently reviewed locally and are intentionally omitted from this public packet because the Work field and some notifications show local filesystem paths. [The native visual inventory](native-visual-inventory.json) retains basenames, hashes, byte counts and observations. It authenticates retained local files, but does not make those historical native pixels publicly inspectable. Reproduce a new native run with the public tools to inspect those states.

| Web screenshot | Observation |
| --- | --- |
| [Face](screenshots/web/08-web-final-face-recovered.png) | Actual recovered preview |
| [Back](screenshots/web/04-web-back.png) | Actual hair and nape |
| [Arm playing](screenshots/web/w64-arm-live-4.png) | A frame from actual continuous arm playback |
| [Knee and shape edit](screenshots/web/05-web-shape-during-knee.png) | Actual changing torso during playback |
| [Malformed Work](screenshots/web/06-web-invalid-open-retains.png) | Error with current body retained |
| [Actual HTTP 404](screenshots/web/07-web-real-missing-asset.png) | Missing owned manifest; exact bytes restored before reopen |

Failure-period screenshots establish visible behavior, not a successful fresh numeric snapshot during the failure. Formal visual quality, GPU measurements, authored head motion, eye movement and appearance persistence remain unaccepted. #79 stays open; #3 and #4 are unchanged.

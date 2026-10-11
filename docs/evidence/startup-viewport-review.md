# Independent measurement review

Scope: experiments12 native startup/RSS,13 passive viewport diagnostics and14 separate Web bootstrap; product code, dependencies and lockfile unchanged. Sol implemented; a fresh read-only Astra/high session performed cross-model R2 review and targeted rereview. The reviewer ran no builds, tests, UI or GPU tasks.

Initial findings:

- P2: copied `index.html.gz` still contained the original page, so gzip delivery could omit viewport diagnostics. Fixed by regenerating the sidecar with zero timestamp, validating decompression, and recording both intentional changes in manifest2. The other19 files remain identical. Actual served gzip identity matches patched HTML.
- P2: Web protocol hashed raw files but did not bind served gzip responses. Fixed with local sidecar/raw equality, gzip-negotiated response checks, encoded/decoded hashes, separate preflight traffic and a post-run freeze check.

Root also reproduced a Python3.9 installer failure from `hashlib.file_digest`. Chunked hashing repaired it; actual3.9 installation, independent hashes and deterministic gzip repeatability passed. Failed attempts are retained in experiment13 and viewport evidence.

Targeted rereview accepted all fixes with no remaining actionable findings. Frozen installer SHA256 `f1f8856ba28aa4a3d5a8e4d399633e19b0f2bfcc17795e52e94f13592ab0e08c`; protocol `7cf4e8ec73438eaf18bd6cfe8940e60e309d785b68faa70c4ccf15e9f7419f84`; unchanged Web bootstrap `5f6b1522435a424c55b8a2201abe2f7f68894617e832dc258fbbfb8f8f9f8f24`.

Report review confirmed separate clocks, explicit later pixel proof, competing-compilation limits, different Studio/Player workloads, completed animation and unavailable stable-performance conclusions. Root subsequently performed the live viewport actions and image inspection; these remain root-owned verification, not independent reviewer execution.

PARTIAL — R2 source/protocol review and targeted rereview complete. Actual product runs, image review and viewport acceptance have root evidence; exact first presentation, cold caches, GPU timing/memory and isolated stable performance are unverified.

After review, only the protocol reproduction path changed from the archived worker directory to the integration directory; code/measurement behavior remained identical. The protocol hash above identifies the reviewed version. Current publication hashes are in the evidence manifest. Root added the same-Work continuous-idle execution without changing collector or product code.

Final targeted evidence review also accepted the matched continuous-idle records and claims, with no material finding. It verified identity, mode/size,600 samples, active looping,9.366/18.000ms p95 and216.77MiB sampledRSS; no independent execution/image review was claimed.

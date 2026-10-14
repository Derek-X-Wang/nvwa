# Actual acquisition and verification report

**VERIFIED source integrity; PARTIAL source candidates; coverage UNKNOWN.** Three exact package revisions produced three original terms candidates across two packages. The third package remains a narrow observed-absence result. No sealed baseline gap was closed. Fresh independent review, hosted CI, licensing applicability, whole-expression/full-instrument coverage, first-party license choice, signing and distribution approval are NOT-RUN.

## Immutable inputs and source joins

Baseline36 manifest SHA-256: `2b551ed8c7fa22b347424c1056a3b6e5c935baaf7f4df7ebae4eb3e44ccb24fd`.

Capture schema1 SHA-256: `5b3bef8b98e9d54b31909ff3f8b46beebd2f1f4e8a0a84e3af8154d710135313`.

Checkout observed during collection: `b7d2263abee0511f162886e25af61dcc22bac42b`; parent-supplied merged main: `159289c91673227928553a04f6a150520543022b`. No checkout, Git or baseline mutation was performed. The live check matched all 43 original input hashes, including the frozen production source inputs, baseline manifest, original classifier and nine published crate metadata files. Absolute source paths are retained for this explicit optional comparison; the portable verifier never follows them.

| Package | Exact primary source commit | Published path | Unique original-manifest path / Git blob |
| --- | --- | --- | --- |
| profiling@1.0.18 | [8271551172eb6fa4cba47369aedd93790c623df9](https://github.com/aclysma/profiling/tree/8271551172eb6fa4cba47369aedd93790c623df9) | `profiling` | `profiling/Cargo.toml` / `f1a1a97cfa6e3b1bcafc6f53c91671cecf319f43` |
| svg_fmt@0.4.5 | [93f414cd572b5c2781df93dbdc068ed13443d05a](https://github.com/nical/rust_debug/tree/93f414cd572b5c2781df93dbdc068ed13443d05a) | `svg_fmt` | `svg_fmt/Cargo.toml` / `a73a5830cc6cd883569ab17cee2a066ce5eb9ed8` |
| hexf-parse@0.2.1 | [4225763d744183d720f575ae96d04161b4d08ea0](https://github.com/lifthrasiir/hexf/tree/4225763d744183d720f575ae96d04161b4d08ea0) | **ABSENT/UNKNOWN**, unchanged | `parse/Cargo.toml` / `2833f557b25322ab20cc78254e057f132c6e6a0e` |

Registry source IDs and all normalized/original manifest and VCS byte hashes are retained per package in `capture.json`, joined to the independently SHA-pinned baseline. The exact tree roots are respectively `09fcac6c87b5d809c4460ed61b49cfc1e37d65aa`, `db29c95a22ef973d637a0df790f14194a037dad8`, and `1b8ce25c30e5a111acdd7ca390bb452af1e796e9`. Their 42, 42 and 15 entries were reconstructed as Git trees, not accepted merely because copied fields agree.

## Actual legal bytes

| Package/source path | Bytes | SHA-256 | Git blob ID |
| --- | ---: | --- | --- |
| [profiling LICENSE-APACHE](https://raw.githubusercontent.com/aclysma/profiling/8271551172eb6fa4cba47369aedd93790c623df9/LICENSE-APACHE) | 10,818 | `10d30a673cd5e9349bdc02aeb48f14b3386d27d0da32df8f0a555d4aa16aa551` | `139dce95d473c201a8561ef17536314d8b8cda65` |
| [profiling LICENSE-MIT](https://raw.githubusercontent.com/aclysma/profiling/8271551172eb6fa4cba47369aedd93790c623df9/LICENSE-MIT) | 1,093 | `c8167fdeeed46d3f244d3f85c5bf998ce889343691c32be2c61a8bc4b5c08333` | `6a84e059ad8b43e03c2b06bc2af4dc1d8442808d` |
| [svg_fmt root LICENSE](https://raw.githubusercontent.com/nical/rust_debug/93f414cd572b5c2781df93dbdc068ed13443d05a/LICENSE) | 1,070 | `7e98bed7f100747aaae7d82ab94fbe6b76fd6b84b09a3aaa413bff8196d0fbb1` | `9ad7b40bcf7bb89a9866e5e2e8fdb370fb528e36` |

These original bytes are preserved without line-ending or copyright edits. The copied classifier screens recognizable terms and preserves genuine short/mixed license candidates; its result is not a complete license-instrument or applicability determination. Raw declarations remain `MIT OR Apache-2.0`, `MIT/Apache-2.0`, and `CC0-1.0` respectively. Svg's root MIT text does not supply the Apache branch or choose an interpretation of its slash declaration. Hexf's missing published path remains absent, separate from independently resolved source location.

Tree filenames were inspected recursively; `LICENSE*`, `LICENCE*`, and `COPYING*` blobs were sought only in the resolved package directory and its repository ancestors. Hexf has none there. This does not claim absence of terms in README, source headers, other filenames or nested bodies: those content scopes remain NOT-RUN. No source was substituted from a latest branch, template or unrelated donor.

## Requests and controls

Exactly **9 HTTP requests, 9 HTTP 200, 0 failed requests**, comprising three exact commit API records, three recursive tree API records and three raw legal-file responses. Total response bodies: 38,945 bytes; largest: 10,818 bytes. Request UTC range: 2026-10-14 05:27:51.797893 through 05:29:00.157444 UTC. Each used a 10-second timeout, 262,144-byte cap, public unauthenticated primary host, no automatic retry and no redirect following. Headers/statuses/UTC and raw bodies are indexed in `requests.json` and `capture.json`; no failed response was discarded (none occurred).

The actual production verifier seam was exercised with **16 mutation families**, each expected red followed by restored green, plus baseline green: **33 runs per interpreter**, all passed on local Python 3.14, 3.11 and 3.12 (**99 subprocess runs**). Every available stdout/stderr and summary is retained in `evidence/controls`, `evidence/python-3.11` and `evidence/python-3.12`. There were no unexpected control errors or failed restorations.

The mutations cover actual legal-byte tampering even with mirrored hashes, commit/VCS substitution, source URL/path substitution, actual Rust code promoted as terms, actual manifest declaration promoted as terms, omitted absence findings, false hexf coverage approval, invented published path, an ambiguous original-manifest blob in a rehashed tree, flattened slash expression, promoted expression coverage, missing body, omitted captured source, altered Git tree, changed baseline gap cohort, and changed registry source ID. Named error expectations require semantic failures in addition to the frozen capture hash failure. Raw failed controls remain visible; assertions do not suppress errors or drop requirements.

Guarded portability tests passed on **Python 3.11 and 3.12**, each calling the real verifier with **68 reads**, all restricted to the isolated retained packet or pinned classifier code. External source/cache/old-packet reads were zero; verifier writes, network and subprocess access were forbidden. A separate Python 3.11 `--live` check verified all 43 original input hashes. The default Python 3.12 verifier passed with live comparison NOT-RUN. No dependency installs or compatibility-only syntax claims were used.

The new offline CI job runs the same verifier, guarded portability test and 33-run mutation controls on Ubuntu 24.04 with preinstalled Python. Workflow triggers, permission, timeout, exact checkout pin and cancellation were locally inspected. **Hosted workflow execution remains NOT-RUN**; it is distinct from existing Rust/diagnostic jobs. See README for neutral reproduction commands and the explicit merge authority boundary.

## Conclusion and handoff

The three retained legal files are useful pinned-source candidates for fresh independent review. Hexf's actual source path is resolved without changing its incomplete published metadata, and its text gap remains UNKNOWN. Svg's missing branch/whole-expression coverage remains UNKNOWN. The frozen baseline still reports **23 missing-text packages and 47 gap records**; acquisition counts are separate. No claim is made that the other 300 package terms are complete, applicable or sufficient for a binary.

Only experiment37, its new private work directory and the explicitly authorized new workflow were written. No earlier experiment, package, asset, root document, Cargo file, source cache, CI workflow or Git state was changed. All finite verification helpers completed and were reaped; mutation copies were removed. No server or persistent helper was started. Fresh review and subsequent exact-head/exact-main CI belong to the parent agent. Release, signing, clean-machine/platform/hardware, final membership, first-party licensing, distribution and legal approval remain unresolved or NOT-RUN.

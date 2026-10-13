# Bounded stalled character loads (#23)

The production runtime admits at most **four tracked character root requests**.
The count includes the current root and retired roots until the AssetServer
removes their IDs. One latest document open can wait without a root handle or a
source retrieval. Further opens replace that pending document. This permits a
new independent character path while up to three older paths remain stalled.

A same-path request still waits for all earlier root/dependency publications and
root cache removal. A free capacity slot does not override that fence. At full
capacity, `RuntimeStatus.phase` displays `Waiting for earlier character loads
(4/4)…`. After 30 seconds of waiting, its existing error field displays
`Character load capacity reached (4/4); waiting for earlier loads to finish`.
No timeout pretends to cancel a load. The latest request starts automatically
when retirement and Bevy tracking free a slot; opening another document replaces
only the pending request. The old visible scene is removed on document open.

The limit applies to requests created by the production `load_character` system.
It is **not** a byte budget, an exact count of Bevy loader tasks, a cap on a GLTF
root's dependency fan-out, or a GPU-memory lifetime guarantee. External explicit
AssetServer reloads and unrelated assets do not become bounded by this policy.
An indefinitely stalled set of four roots can keep the latest request waiting
indefinitely. The finite retention and visible wait/error state are intentional;
there is no unsafe cancellation or silent fallback to an older scene.

## CPU reproduction

`loading_tests::stalled_distinct_paths_keep_at_most_four_admitted_roots` uses the
actual production loading system, CharacterGlbLoader, and pinned Bevy GLTF
loader. Twelve distinct-path opens hold their source-reader snapshots. It counts
tracked root requests, AssetServer roots in Loading state, source reads, held
readers, loaded CharacterGlb roots, and loaded GLTF assets. A failure releases a
capacity slot; only the latest pending path starts, validates its bytes, and
becomes ready. Later stale success cannot replace its scene fingerprint.

`loading_tests::stalled_http_tests::loopback_http_stalled_distinct_paths_bound_admission_and_recover_latest`
uses a small test-only AssetReader over real TCP HTTP. The fixture binds only
`127.0.0.1:0` (an OS-assigned ephemeral port), holds HTTP responses for twelve
open attempts, caps response reads, and sets socket/test deadlines. Drop cleanup
releases every gate and joins accept, response, and reader threads, reporting
joined thread counts and zero held gates. Accepted sockets explicitly use
blocking IO with deadlines; the reader rejects an incomplete Content-Length. The adapter
is a transport reproduction through the production loader, not a browser or
production Bevy HTTP transport acceptance result.

Additional production-called regressions cover full-capacity visible waiting
and its 30-second error, latest pending document coalescing, same-path fencing
after another path frees a slot, stale success/failure preserving the current
waiting/error state, capacity release, failure/retry recovery, and immediate old
scene removal. Existing integrity and retrieval tests remain in place.

A named test-only transport mutation leaves accepted sockets nonblocking. It
reproduces a WouldBlock write and an exact truncated-body digest, without
changing production validation. Optional `NVWA_STALLED_HTTP_TRACE_DIR` retains
bounded attempted, sent, and received bodies in a private directory;
`NVWA_STALLED_HTTP_NONBLOCKING_MUTATION=1` enables the mutation. These environment
variables affect only the test adapter.

Results and exact fresh source/executable identities are recorded in
`evidence.md`. Historical protected receipts
outside this experiment are not changed.

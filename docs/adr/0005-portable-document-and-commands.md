# Portable documents own character state

The Rust core owns a versioned document with stable string IDs, a character profile, a recipe and animation references. Studio and the offline CLI call the same typed, atomic commands; stored JSON carries no Bevy entities or GPU handles. This costs explicit validation and runtime mirroring, but permits cross-platform work exchange without engine serialization coupling.

Use snapshot undo for this bounded single-character M0: one drag previews a validated clone and commits once, while undo/redo change the revision monotonically. Tests cover failures, idempotent retries, conflicting reuse, revisions and equivalent command paths. History and remembered command IDs remain session-local and unbounded; an inverse-operation or persistent-log design was not benchmarked and is not adopted.

Platform file completions distinguish `Opened(String)` from `Saved`, including empty files. Native imports cap reads at 2 MiB + 1 and reject nonregular handles; Unix opens are nonblocking so a FIFO cannot freeze the UI. Native saves use an exclusive, unique adjacent temporary file before rename. Browser file callbacks carry data through a single-flight mailbox; the browser download API confirms initiation, not a durable filesystem write.

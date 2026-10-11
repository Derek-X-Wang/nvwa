# Static Player test server

`tools/test-support/player-error-server.py` is a test-only Python standard-library server for local static Player fetch and error-recovery checks. It binds only to `127.0.0.1:9202`, within Nvwa's reserved 9200–9299 range. It serves the existing [Web bundle](../../../dist/web/) at `/` and under `/published/`, and the actual [M1 work fixture](../../../examples/m1-sequence.nvwa.json) at `/examples/m1-sequence.nvwa.json`.

The same routes work below `/published/`. For example, the fixture is also available at `/published/examples/m1-sequence.nvwa.json`. Redirects preserve that prefix. Static files, including the already-built GLB and WASM, come from `dist/web`; this server adds no runtime service, dependency, or asset.

## Test endpoints

Use the work endpoint URLs with the Player's published-work loading flow. The endpoint paths below can also be prefixed with `/published`.

| Endpoint | Response |
| --- | --- |
| `/examples/m1-sequence.nvwa.json` | Valid checked-in M1 work. |
| `/fixtures/invalid-json.nvwa.json` | Truncated JSON. |
| `/fixtures/invalid-utf8.nvwa.json` | JSON-like bytes with invalid UTF-8. |
| `/fixtures/oversized.nvwa.json` | Exactly 2 MiB + 1 byte: the valid work bytes plus whitespace. The HTTP/1.0 response omits `Content-Length` and ends by closing the connection. |
| `/fixtures/redirect.nvwa.json` | HTTP 302 redirect to the valid work endpoint. |
| `/fixtures/stalled.nvwa.json` | HTTP 200 with a declared body length, then no body for 35 seconds, then the valid work bytes. The stall is finite. |
| `/fixtures/wrong-asset-sha256.nvwa.json` | Valid work with a 64-character all-zero asset hash. The asset path still points to the shipped GLB. |
| `/fixtures/missing-glb.nvwa.json` | Valid work whose asset path points to `fixtures/__m1_missing_asset__.glb`; that file is absent. |

The server does not start as part of this change. The root agent owns launch and cleanup. To start it for the browser run:

```sh
python3 tools/test-support/player-error-server.py
```

Open the Player from `http://127.0.0.1:9202/` or `http://127.0.0.1:9202/published/`. The server is same-origin and loopback-only. Do not expose it to a LAN or public network. The 35-second endpoint tests bounded body-read behavior; the browser run should confirm the Player reports an error and remains usable, then opens the valid fixture.

These routes only provide deterministic responses. They do not prove product error handling, recovery, or Player correctness. The root agent must observe those outcomes in the actual browser Player. The subdirectory route maps `/published/` requests to the same bundle; if the browser loads any root-absolute resource URLs, those are also served from `/` by the normal mapping.

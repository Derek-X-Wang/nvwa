#!/usr/bin/env python3
"""Read-only, bounded acceptance check for the archived fresh Web picker case.

This checks durable receipts/provenance; it never starts/replays a browser,
renderer, server, or Cargo. --self-test rejects semantic tampering in memory,
beyond the archive's file-hash checks. Optional --frozen-web checks real Wasm.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

FIXTURE = "f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6"
WASM = "d890dfee73e9eeeee6ce3d82f255c79979e8c8b6bed90243c6101f8e1c1763a8"
SCRIPT = "f2724fd7d667c4511835e3d4235de055d0505219d583a7f5ea321e228c6128f7"
TRACE = "d0fc22abc235afb73f7aa58c69f9eb459d1c22dede9db97a00804cea8e250427"
CANONICAL = "cacf849f0918648a1a970452d0c33f195c5ad89fd7f6d9e58669d587d0789768"
SESSION = "01a128c5-1bff-70a0-bd65-0dfff0529c44"
CODE_HASHES = [
    "c2def105c82234885856498790bb8de6f6525aab5f5ed8d0e0b45852af85bd44",
    "aada4bae16771bb68f9b058d87c0d31fe9184c4de44fd21012c4354987de38ca",
    "7bd19f64f898e779a1c0015494bf4f9c72029dc90eb170f0eaef6ad82656e2c9",
    "057a7bc4bac712d79bc691e75ccf46fc2d13979c621fbeb5947b591e12cf75e9",
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bounded_bytes(path, maximum=2 * 1024 * 1024):
    require(path.is_file() and path.stat().st_size <= maximum, f"File absent/over budget: {path.name}")
    return path.read_bytes()


def json_file(path):
    return json.loads(bounded_bytes(path))


def json_lines(path):
    lines = bounded_bytes(path).splitlines()
    require(len(lines) <= 512, "JSONL event budget")
    return [json.loads(line) for line in lines]


def semantic_equal(left, right):
    # Numeric spelling may change during Rust serialization; JSON booleans must
    # never compare equal to numbers. Every object field/list element matters.
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(semantic_equal(v, right[k]) for k, v in left.items())
    if isinstance(left, list):
        return len(left) == len(right) and all(semantic_equal(a, b) for a, b in zip(left, right))
    return left == right


def load_archive(root):
    hashes = json_file(root / "archive-hashes.json")["files"]
    require(len(hashes) <= 80, "Archive file count budget")
    require(sum(v["bytes"] for v in hashes.values()) <= 16 * 1024 * 1024, "Archive total size budget")
    for name, receipt in hashes.items():
        path = (root / name).resolve()
        require(root.resolve() in path.parents, "Archive traversal")
        data = bounded_bytes(path)
        require(len(data) == receipt["bytes"] and sha(data) == receipt["sha256"], f"Archive hash mismatch: {name}")
    for name in [f"picker-{n:02}.jpg" for n in range(3, 13)] + ["web-stall-recovered.jpg"]:
        require(name in hashes and bounded_bytes(root / name).startswith(b'\xff\xd8'), f"Missing archived JPEG: {name}")
    trace_bytes = bounded_bytes(root / "web-stall-cua-exact-trace.jsonl")
    require(sha(trace_bytes) == TRACE, "Exact Cua transcript digest")
    trace_manifest = json_file(root / "web-stall-cua-exact-trace-manifest.json")
    lines = trace_bytes.splitlines(keepends=True)
    require(len(lines) == len(trace_manifest["line_receipts"]) == 12, "Exact transcript line count")
    for line, receipt in zip(lines, trace_manifest["line_receipts"]):
        require(sha(line) == receipt["sha256"], "Verbatim transcript-line digest")
        require(json.loads(line)["ordinal"] + 1 == receipt["line"], "Transcript ordinal/line receipt")
    require(sha(bounded_bytes(root / "canonical-work.nvwa.json")) == CANONICAL, "Canonical Work digest")
    return {
        "raw": json_lines(root / "web-stall-picker-case.jsonl"),
        "actions": json_file(root / "web-stall-picker-actions.json"),
        "saved": json_file(root / "web-stall-saved-work.nvwa.json"),
        "saved_sha": sha(bounded_bytes(root / "web-stall-saved-work.nvwa.json")),
        "canonical": json_file(root / "canonical-work.nvwa.json"),
        "selected": {f"{n:02}": json_file(root / "selected-works" / f"stall-{n:02}.nvwa.json") for n in range(1, 13)},
        "selected_sha": {f"{n:02}": sha(bounded_bytes(root / "selected-works" / f"stall-{n:02}.nvwa.json")) for n in range(1, 13)},
        "acceptance": json_file(root / "web-stall-acceptance.json"),
        "artifacts": json_file(root / "artifact-identities.json"),
        "artifact_verification": json_file(root / "artifact-verification.json"),
        "console": json_file(root / "web-stall-console.json"),
        "trace": [json.loads(line) for line in lines], "trace_manifest": trace_manifest,
        "download": json_file(root / "web-stall-download.json"),
        "failed": json_file(root / "failed-path-attempt" / "web-stall-first-attempt.json"),
        "failed_raw": json_lines(root / "failed-path-attempt" / "web-stall-case.jsonl"),
    }


def check_provenance(bundle):
    records, manifest = bundle["trace"], bundle["trace_manifest"]
    require(manifest["trace_sha256"] == TRACE and manifest["source_session_id"] == SESSION, "Source transcript identity")
    require(len(records) == 12 and len(manifest["calls"]) == 4, "Four complete Cua call triples")
    codes = []
    for number in range(4):
        call, completed, output = records[number * 3:number * 3 + 3]
        payload, completion, result = call["payload"], completed["payload"], output["payload"]
        expected_id = manifest["calls"][number]["call_id"]
        require(payload["type"] == "function_call" and payload["namespace"] == "mcp__cua_repl" and payload["name"] == "js", "Actual Cua call")
        require(completion["type"] == "item_completed" and completion["thread_id"] == SESSION, "Completed event source")
        item = completion["item"]
        require(item["status"] == "completed" and item["result"]["isError"] is False, "Cua call incomplete/error")
        require(payload["call_id"] == item["id"] == result["call_id"] == expected_id, "Cua call/output ID mismatch")
        require(result["type"] == "function_call_output", "Cua output record")
        args = json.loads(payload["arguments"])
        require(item["arguments"] == args, "Call/completion argument mismatch")
        code = args["code"]
        require(sha(code.encode()) == CODE_HASHES[number], "Exact awaited Cua call shape changed")
        codes.append(code)
        # Creation exposes native surface metadata. Later multi-operation Cua
        # results wrap their snapshot in text; their exact output still names
        # tab 52, and the pinned code uses the original binding throughout.
        if number == 0:
            surface = item["result"]["_meta"]["codex/toolSurface"]
            require(surface["browserId"] == "2" and surface["openTabIds"] == ["52"], "Original browser binding")
        text = '\n'.join(v.get("text", "") for v in result["output"] if v.get("type") == "input_text")
        require("Browser tab: 52" in text and not re.search(r"Traceback|TimeoutError|Error:", text), "Output error or different tab")
    require(codes[0].count("createBrowserTab") == 1 and "var nvwaPickerTab = await" in codes[0], "Single startup binding")
    require(all("createBrowserTab" not in code for code in codes[1:]), "Extra app creation")
    require("for(var n=3;n<=12;n++)" in codes[2], "Exact 03–12 chooser endpoints")
    require("var choosing=nvwaPickerTab.playwright.waitForEvent('filechooser'" in codes[2]
            and "await nvwaPickerTab.click([511,12]);var chosen=await choosing;await chosen.setFiles(file);" in codes[2], "Await every actual chooser/selection")
    require("catch" not in codes[2] and "break" not in codes[2] and "return" not in codes[2], "No loop catch/early exit")
    require("waitForEvent('download'" in codes[3] and "await nvwaWorkDownload" in codes[3], "Actual Save/download provenance")


def validate(bundle):
    check_provenance(bundle)
    raw, actions, canonical = bundle["raw"], bundle["actions"], bundle["canonical"]
    require(len(raw) <= 512 and all(a["elapsed_seconds"] <= b["elapsed_seconds"] for a, b in zip(raw, raw[1:])), "Finite ordered events")
    require(raw[0]["event"] == "started" and raw[-1]["event"] == "cleanup", "Complete server lifecycle")
    require(sum(v["event"] == "started" for v in raw) == sum(v["event"] == "cleanup" for v in raw) == 1, "One case lifecycle")
    manifest = raw[0]["manifest"]
    require(manifest["script_sha256"] == SCRIPT and manifest["fixture_sha256"] == FIXTURE and manifest["fixture_bytes"] == 3827840, "Exact server/fixture identity")
    require(manifest["canonical_work_sha256"] == CANONICAL and manifest["hold_seconds"] == 105 and manifest["watchdog_seconds"] == 120, "Actual case inputs/watchdogs")
    for n in range(1, 13):
        index = f"{n:02}"
        expected = copy.deepcopy(canonical); expected["profile"]["asset_path"] = f"fixtures/stall-{index}.glb"
        require(semantic_equal(bundle["selected"][index], expected), f"Canonical selected Work {index}")
        require(bundle["selected_sha"][index] == manifest["diagnostic_work_sha256"][index], "Selected files equal declared HTTP variants")
    require(len(actions) == 12 and [v["path"] for v in actions] == [f"stall-{n:02}.nvwa.json" for n in range(1, 13)], "Twelve accepted Work sequence")
    require(actions[0]["kind"] == "URL startup" and all(v["kind"] == "GUI file chooser" for v in actions[1:]), "Eleven actual chooser selections")
    # Work02's compact timestamp was initialized at the later loop start.
    # Its exact Cua completion, not this convenience timestamp, proves selection.
    require(all(a["hostEpochMs"] < b["hostEpochMs"] for a, b in zip(actions[2:], actions[3:])), "03–12 ordered chooser receipts")
    require(bundle["download"]["hostEpochMs"] > actions[-1]["hostEpochMs"], "Save after latest selected Work")
    forbidden = {"unexpected_asset_while_four_held", "connection_rejected", "control_rejected"}
    require(not any(v["event"] in forbidden or v.get("invalid_reasons") or v.get("exception") for v in raw), "Invalid server case event")
    releases = [v for v in raw if v["event"] == "released"]
    require([v["index"] for v in releases] == ["01", "02", "03", "04"] and all(v["reason"] == "stdin" for v in releases), "Explicit release of all four; no automatic release")
    release_time = releases[0]["elapsed_seconds"]
    gets = [v for v in raw if v["event"] == "asset_get"]
    require([v["index"] for v in gets] == ["01", "02", "03", "04", "12"], "No fifth-before-release or intermediate fetch")
    require(all(v["count"] == 1 and v["total"] == n for n, v in enumerate(gets, 1)), "Exactly one retrieval per admitted path")
    require([v["index"] for v in gets if v["elapsed_seconds"] < release_time] == ["01", "02", "03", "04"], "Four requests before release")
    require(gets[-1]["elapsed_seconds"] > releases[-1]["elapsed_seconds"], "Only latest request after release")
    pre = [v for v in raw if v["event"] == "status" and v["elapsed_seconds"] < release_time][-1]
    require(pre["held_bodies"] == pre["active_connections"] == 4 and pre["asset_gets"] == {f"{n:02}": 1 for n in range(1, 5)}, "Durable four-held observation")
    closes = [v for v in raw if v["event"] == "connection_closed" and v.get("index")]
    require(not any(v["elapsed_seconds"] < release_time for v in closes), "No premature held closure")
    require([v["index"] for v in closes] == ["01", "02", "03", "04", "12"] and all(v["reason"] == "response complete" and v["body_bytes_sent"] == 3827840 for v in closes), "Five complete fixture responses")
    requests = [v for v in raw if v["event"] == "request" and v["method"] == "GET"]
    require(sum(v["path"] == "" for v in requests) == sum(v["path"] == "nvwa_studio.js" for v in requests) == sum(v["path"] == "nvwa_studio_bg.wasm" for v in requests) == 1, "One actual app startup")
    require([v["path"] for v in requests if v["path"].startswith("works/")] == ["works/stall-01.nvwa.json"], "Startup HTTP Work only; picker files are not HTTP Work GETs")
    cleanup = raw[-1]
    require(cleanup["accepted"] == cleanup["closed"] == 14 and cleanup["active_connections"] == cleanup["held_bodies"] == cleanup["response_threads"] == 0, "Unclean sockets/threads")
    require(cleanup["reason"] == "stdin quit" and cleanup["case_status"] == "ended" and cleanup["secondary_termination_reasons"] == [] and cleanup["product_bound_claim_allowed"] is True and cleanup["elapsed_seconds"] < 120, "Clean explicit completion")
    expected = copy.deepcopy(canonical); expected["profile"]["asset_path"] = "fixtures/stall-12.glb"
    require(semantic_equal(bundle["saved"], expected), "Saved entire Doc differs from latest canonical variant")
    summary = bundle["acceptance"]
    require(summary["status"] == "PASS" and summary["pre_release"] == pre and summary["cleanup"] == cleanup and summary["asset_get_order"] == [v["index"] for v in gets], "Summary contradicts raw observations")
    require(summary["final_work_semantic_equality"] is True and summary["saved_work_sha256"] == bundle["saved_sha"] and summary["expected_work_sha256"] == bundle["selected_sha"]["12"], "Whole-Doc/serialization receipt")
    require(bundle["saved_sha"] != bundle["selected_sha"]["12"], "Record semantic equality separately from byte equality")
    require(bundle["artifacts"]["artifacts"]["dist/web/nvwa_studio_bg.wasm"]["sha256"] == bundle["artifact_verification"]["sha256"] == WASM, "Fresh candidate Wasm identity")
    console = bundle["console"]
    require(sum("Creating new window Nvwa" in v["message"] for v in console) == 1 and any("BrowserWebGpu" in v["message"] for v in console), "One renderer/window receipt")
    require(not any(v["level"] == "error" for v in console), "Console error")
    require(bundle["failed"]["status"] == "NOT-RUN" and [v["index"] for v in bundle["failed_raw"] if v["event"] == "asset_get"] == ["01"], "Failed path-edit attempt must stay excluded")
    return {"accepted_works": 12, "startup_work_http_gets": 1, "gui_chooser_selections": 11,
            "pre_release_asset_gets": 4, "after_release_only": "12", "five_full_transfers": True,
            "release_scope": "all four together", "release_seconds": release_time,
            "cleanup_seconds": cleanup["elapsed_seconds"], "sockets_closed": 14,
            "whole_document_semantic_equality": True, "serialized_bytes_equal": False,
            "wasm_sha256": WASM, "cua_trace_sha256": TRACE}


def check_repairs(root, index_override=None):
    index = json_file(root / "archive-index.json") if index_override is None else index_override
    require(set(index["original_manifests"]) == {
        "web-server-reason-fix-manifest.json", "web-server-monotonic-reason-manifest.json"
    }, "Exact original repair manifest inventory required")
    require(set(index["cohorts"]) == {"previous_nine", "new_nine"}, "Both exact repair cohorts required")
    checked = 0
    legacy = json_file(root / "web-server-reason-fix-manifest.json")
    monotonic = json_file(root / "web-server-monotonic-reason-manifest.json")
    require(monotonic["previous_nine_receipts_preserved"] == legacy["receipts"], "Canonical original manifests disagree")
    original_cohorts = {"previous_nine": legacy["receipts"], "new_nine": monotonic["new_cohort"]}
    require(all(len(records) == 9 for records in original_cohorts.values()), "Original eighteen-receipt inventory required")
    for name, expected in index["original_manifests"].items():
        require(sha(bounded_bytes(root / name)) == expected, "Original repair manifest digest")
    for cohort, records in index["cohorts"].items():
        require(set(records) == set(original_cohorts[cohort]), "Complete exact canonical repair receipt set required")
        for name, entry in records.items():
            require(entry["receipt"] == name, "Canonical receipt link required")
            receipt = json_file(root / name)
            require(receipt == original_cohorts[cohort][name], "Original manifest/curated receipt mismatch")
            require(sha(bounded_bytes(root / name)) == entry["receipt_sha256"], "Repair receipt digest")
            if "raw" in entry:
                require(sha(bounded_bytes(root / entry["raw"])) == entry["raw_sha256"], "Repair raw digest")
                require(json_lines(root / entry["raw"])[-1] == receipt["cleanup"], "Repair receipt/raw cleanup mismatch")
            else:
                require(len(receipt["tests"]) == 6 and "method" in receipt["scope"], "Clearly labeled socket-free method controls")
            checked += 1
    require(checked == 18, "All eighteen repair receipts required")
    return checked


def negative_controls(bundle):
    tests = []
    mutations = {
        "fifth-before-release": lambda b: b["raw"].insert(next(i for i, v in enumerate(b["raw"]) if v["event"] == "released"), {"event": "asset_get", "index": "05", "count": 1, "total": 5, "held_bodies": 4, "elapsed_seconds": 47.0}),
        "wrong-entire-saved-doc": lambda b: b["saved"]["timeline"][0].update({"speed": 99}),
        "missing-gui-chooser": lambda b: b["actions"].pop(5),
        "unclean-sockets": lambda b: (b["raw"][-1].update({"closed": 13}), b["acceptance"]["cleanup"].update({"closed": 13})),
        "failed-cua-completion": lambda b: b["trace"][7]["payload"]["item"].update({"status": "failed"}),
        "mismatched-cua-output-id": lambda b: b["trace"][8]["payload"].update({"call_id": "wrong-call"}),
        "cua-loop-error": lambda b: b["trace"][7]["payload"]["item"]["result"].update({"isError": True}),
        "wrong-wasm": lambda b: b["artifacts"]["artifacts"]["dist/web/nvwa_studio_bg.wasm"].update({"sha256": "0" * 64}),
        "failed-attempt-miscounted": lambda b: b["actions"][3].update({"kind": "GUI Open"}),
    }
    def unawaited(b):
        args = json.loads(b["trace"][6]["payload"]["arguments"])
        args["code"] = args["code"].replace("await chosen.setFiles(file)", "chosen.setFiles(file)")
        b["trace"][6]["payload"]["arguments"] = json.dumps(args)
        b["trace"][7]["payload"]["item"]["arguments"] = args
    mutations["unawaited-file-selection"] = unawaited
    for name, mutate in mutations.items():
        changed = copy.deepcopy(bundle); mutate(changed)
        try:
            validate(changed)
        except (ValueError, KeyError, IndexError) as error:
            tests.append({"name": name, "rejected": True, "reason": str(error)})
        else:
            raise ValueError(f"Negative control accepted: {name}")
    return tests


def repair_inventory_negative_controls(root):
    original = json_file(root / "archive-index.json")
    mutations = {
        "missing-new-cohort": lambda data: data["cohorts"].pop("new_nine"),
        "missing-both-cohorts": lambda data: data.update(cohorts={}),
        "missing-one-receipt": lambda data: data["cohorts"]["new_nine"].pop("late-exception-final-green.receipt.json"),
        "missing-original-manifest-entry": lambda data: data["original_manifests"].pop("web-server-reason-fix-manifest.json"),
        "extra-cohort": lambda data: data["cohorts"].update(unexpected=copy.deepcopy(data["cohorts"]["new_nine"])),
        "extra-original-manifest-entry": lambda data: data["original_manifests"].update({"archive-index.json": "0" * 64}),
    }
    controls = []
    for name, mutate in mutations.items():
        changed = copy.deepcopy(original); mutate(changed)
        try:
            check_repairs(root, changed)
        except (ValueError, KeyError) as error:
            controls.append({"name": name, "rejected": True, "reason": str(error)})
        else:
            raise ValueError(f"Repair omission accepted: {name}")
    return controls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path(__file__).parent / "web-acceptance")
    parser.add_argument("--repairs", type=Path, default=Path(__file__).parent / "adapter-repair")
    parser.add_argument("--frozen-web", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    bundle = load_archive(args.archive)
    result = {"status": "PASS", "scope": "read-only durable archive consistency/provenance; not browser replay", "case": validate(bundle), "adapter_repair_records": check_repairs(args.repairs)}
    if args.frozen_web:
        path = args.frozen_web / "nvwa_studio_bg.wasm"
        require(sha(bounded_bytes(path, 128 * 1024 * 1024)) == WASM, "Actual frozen Wasm mismatch")
        result["actual_frozen_wasm_checked"] = True
    if args.self_test:
        result["negative_controls"] = negative_controls(bundle)
        result["negative_control_count"] = len(result["negative_controls"])
        result["repair_inventory_negative_controls"] = repair_inventory_negative_controls(args.repairs)
        result["repair_inventory_negative_control_count"] = len(result["repair_inventory_negative_controls"])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

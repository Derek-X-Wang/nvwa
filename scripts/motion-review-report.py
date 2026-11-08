"""Summarize recorded Agent runs and real playback without rerunning either."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess

USAGE_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens")


def read_json(path):
    return json.loads(path.read_bytes())


def json_lines(path):
    with path.open(encoding="utf-8") as source:
        for line in source:
            yield json.loads(line)


def seconds(value):
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError("Expected a finite, nonnegative time")
    return result


def run_report(events, rollout, calls, batch_receipts):
    threads = []
    completed = []
    items = {}
    for event in json_lines(events):
        kind = event["type"]
        if kind == "thread.started":
            threads.append(event["thread_id"])
        elif kind == "turn.completed":
            completed.append(event["usage"])
        elif kind == "turn.failed":
            raise ValueError("Worker turn failed")
        elif kind in {"item.started", "item.completed"}:
            item = event["item"]
            if item["type"] in {"command_execution", "mcp_tool_call", "web_search"}:
                items[item["id"]] = item
    if len(threads) != 1 or len(completed) != 1:
        raise ValueError("Expected one worker thread and one completed turn")
    usage = completed[0]
    for key in USAGE_KEYS:
        if type(usage[key]) is not int or usage[key] < 0:
            raise ValueError(f"Invalid token count: {key}")
    if usage["cached_input_tokens"] > usage["input_tokens"]:
        raise ValueError("Cached input exceeds total input")

    rollouts = []
    tool_requests = Counter()
    images = 0
    for record in json_lines(rollout):
        payload = record.get("payload", {})
        if record["type"] == "session_meta":
            rollouts.append(payload["id"])
        if record["type"] != "response_item" or payload.get("type") not in {
            "function_call", "custom_tool_call", "web_search_call"
        }:
            continue
        name = payload.get("name", payload["type"])
        tool_requests[name] += 1
        code = payload.get("input", "")
        if "view_image" in name or (isinstance(code, str) and "view_image(" in code):
            images += 1
    if rollouts != threads:
        raise ValueError("Worker event and rollout thread IDs differ")

    application_calls = list(json_lines(calls))
    observation_wall = sum(seconds(call["wall_s"]) for call in application_calls
                           if call["tool"] in {"query", "frames"})
    render_frames = 0
    render_seconds = 0.0
    failed_batches = 0
    if len({path.resolve() for path in batch_receipts}) != len(batch_receipts):
        raise ValueError("Render batch receipts must be unique")
    for path in batch_receipts:
        receipt = read_json(path)
        if receipt["format"] != "nvwa-motion-review":
            raise ValueError("Expected a motion review batch receipt")
        render_frames += sum(frame["status"] == "rendered" for frame in receipt["frames"])
        render_seconds += seconds(receipt["elapsed_seconds"])
        failed_batches += receipt["status"] != "rendered"

    meta = read_json(events.with_name("meta.json"))
    return {
        "schema_version": 1, "kind": "agent_motion_review_run", "thread": threads[0],
        "model": meta["model"], "effort": meta["effort"], "token_usage": usage,
        "total_tokens": usage["input_tokens"] + usage["output_tokens"],
        "uncached_input_tokens": usage["input_tokens"] - usage["cached_input_tokens"],
        "agent_tool_requests": sum(tool_requests.values()),
        "tool_requests_by_name": dict(tool_requests),
        "execution_items_by_type": dict(Counter(item["type"] for item in items.values())),
        "failed_command_items": sum(item["type"] == "command_execution"
                                    and item.get("status") == "failed" for item in items.values()),
        "image_view_tool_requests": images,
        "application_cli_calls": len(application_calls),
        "application_cli_calls_by_tool": dict(Counter(call["tool"] for call in application_calls)),
        "application_cli_failed_calls": sum(call["code"] != 0 for call in application_calls),
        "observation_wall_s": round(observation_wall, 3),
        "renderer": {"batches_supplied": len(batch_receipts), "failed_batches": failed_batches,
                     "rendered_frames": render_frames, "batch_wall_s": round(render_seconds, 3)},
    }


def comparison(numeric, screenshots):
    if any(report["kind"] != "agent_motion_review_run" for report in (numeric, screenshots)):
        raise ValueError("Expected two Agent run reports")
    if numeric["thread"] == screenshots["thread"]:
        raise ValueError("Expected independent worker threads")
    if (numeric["model"], numeric["effort"]) != (screenshots["model"], screenshots["effort"]):
        raise ValueError("Matched comparison requires the same model and effort")
    changes = {}
    for key in ("total_tokens", "uncached_input_tokens", "agent_tool_requests",
                "application_cli_calls", "observation_wall_s"):
        left, right = numeric[key], screenshots[key]
        changes[key] = {
            "numeric": left, "screenshots": right, "numeric_fewer": round(right - left, 3),
            "numeric_reduction_pct": round((right - left) * 100 / right, 2) if right else None,
        }
    return {"schema_version": 1, "kind": "agent_motion_review_comparison",
            "numeric": numeric, "screenshots": screenshots, "comparison": changes}


def playback_report(capture_receipt, recording, observed_end):
    receipt = read_json(capture_receipt)
    with recording.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if digest != receipt["sha256"]:
        raise ValueError("Recording hash differs from capture receipt")
    probe = json.loads(subprocess.run([
        "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,nb_read_frames:format=duration",
        "-of", "json", str(recording.resolve()),
    ], check=True, capture_output=True, timeout=30).stdout)
    stream, = probe["streams"]
    frames = int(stream["nb_read_frames"])
    duration = seconds(probe["format"]["duration"])
    if frames <= 0 or duration == 0:
        raise ValueError("Recording has no timed video frames")
    if (stream["width"], stream["height"]) != (receipt["width"], receipt["height"]):
        raise ValueError("Recording dimensions differ from capture receipt")
    diagnostic = receipt.get("diagnostic") or {}
    return {
        "schema_version": 1, "kind": "normal_playback_observation",
        "recording_sha256": digest, "view_work_sha256": receipt["startup"]["work_sha256"],
        "wasm_sha256": receipt["wasm_sha256"],
        "trusted_play": receipt["pointer"]["trusted"] is True,
        "player_end": {"observed_seconds": None if observed_end is None else seconds(observed_end),
                       "source": "operator_observation" if observed_end is not None else "unavailable"},
        "recording": {"duration_s": duration, "frames": frames,
                      "mean_frames_per_s": round(frames / duration, 2)},
        "paused_diagnostic_after_play": {"status": diagnostic.get("status", "unavailable")},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Count tokens, tools, application calls and render work")
    for name in ("events", "rollout", "calls"):
        run.add_argument(name, type=Path)
    run.add_argument("--batch-receipt", type=Path, action="append", default=[])
    compare = commands.add_parser("compare", help="Compare numeric and screenshot run reports")
    compare.add_argument("numeric", type=Path)
    compare.add_argument("screenshots", type=Path)
    playback = commands.add_parser("playback", help="Measure a recording and preserve the endpoint evidence")
    playback.add_argument("receipt", type=Path)
    playback.add_argument("recording", type=Path)
    playback.add_argument("--player-end-s", help="Endpoint actually observed in the Player")
    args = parser.parse_args()
    try:
        if args.command == "run":
            report = run_report(args.events, args.rollout, args.calls, args.batch_receipt)
        elif args.command == "compare":
            report = comparison(read_json(args.numeric), read_json(args.screenshots))
        else:
            report = playback_report(args.receipt, args.recording, args.player_end_s)
    except (OSError, KeyError, TypeError, ValueError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

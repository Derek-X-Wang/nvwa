#!/usr/bin/env python3
"""Bounded fresh-process collector. Python stdlib; never builds or purges caches."""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import signal
import struct
import subprocess
import sys
import threading
import time
import zlib


ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
FLAGS = {"--benchmark", "--smoke", "--smoke-seconds", "--capture", "--timeout", "--work"}


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def file_identity(path):
    path = Path(path).resolve(strict=True)
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    after = path.stat()
    keys = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if any(getattr(before, key) != getattr(after, key) for key in keys):
        raise ValueError(f"Input changed while hashing: {path}")
    return {"path": str(path), "sha256": digest.hexdigest(), "bytes": after.st_size,
            "device": after.st_dev, "inode": after.st_ino, "mtime_ns": after.st_mtime_ns}


def parse_evidence(line):
    clean = ANSI.sub("", line)
    if "NVWA_EVIDENCE " not in clean:
        return None
    record = json.loads(clean.split("NVWA_EVIDENCE ", 1)[1])
    if not isinstance(record, dict):
        raise ValueError("NVWA_EVIDENCE payload must be a JSON object")
    return record


def parse_rss(text, child_pid, parent_pid):
    """ps uses KiB on macOS/Linux. Reject a reused PID with another parent."""
    fields = text.split()
    if len(fields) != 3:
        return None
    pid, ppid, kib = (int(value) for value in fields)
    if pid != child_pid or ppid != parent_pid or kib < 0:
        return None
    return kib * 1024


def collect_process(command, cwd, output, timeout_seconds, interval_seconds, environment):
    """Own exactly one Popen child. No process-name/group kill or inherited rusage."""
    output = Path(output)
    started = time.monotonic_ns()
    report = {"command": command, "cwd": str(cwd), "spawn_call_utc": utc_now(),
              "spawn_call_monotonic_ns": started, "pid": None, "exit_code": None,
              "timed_out": False, "cancelled": False, "collector_errors": [],
              "runtime_events": [], "malformed_evidence": [], "rss_samples": [],
              "rss_kind": "sampled exact child PID+PPID RSS; not true lifetime peak, descendants, GPU or total unified memory",
              "rss_sample_interval_seconds": interval_seconds}
    process = None
    threads = []
    lock = threading.Lock()
    event_handle = (output / "events.jsonl").open("w")
    old_sigterm = None

    def cancel_on_sigterm(signum, _frame):
        report["cancellation_signal"] = signum
        raise KeyboardInterrupt

    if threading.current_thread() is threading.main_thread():
        old_sigterm = signal.signal(signal.SIGTERM, cancel_on_sigterm)

    def reader(stream, name):
        # Raw bytes survive decoding failure, malformed evidence and launch failure.
        with (output / f"{name}.log").open("wb") as log:
            try:
                for raw in iter(stream.readline, b""):
                    received = time.monotonic_ns()
                    log.write(raw)
                    log.flush()
                    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                    event = {"stream": name, "received_monotonic_ns": received,
                             "seconds_since_spawn_call": (received - started) / 1e9, "line": line}
                    with lock:
                        event_handle.write(json.dumps(event) + "\n")
                        event_handle.flush()
                        try:
                            record = parse_evidence(line)
                            if record is not None:
                                report["runtime_events"].append({**event, "record": record})
                        except (ValueError, json.JSONDecodeError) as error:
                            report["malformed_evidence"].append({**event, "error": str(error)})
            except Exception as error:
                with lock:
                    report["collector_errors"].append(f"{name} reader: {error}")
            finally:
                stream.close()

    def stop_owned_child():
        if process is not None and process.poll() is None:
            report["termination"] = {"target_pid": process.pid, "terminate_monotonic_ns": time.monotonic_ns()}
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                report["termination"]["kill_monotonic_ns"] = time.monotonic_ns()
                process.kill()
                process.wait(timeout=2)

    try:
        process = subprocess.Popen(command, cwd=cwd, env=environment,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        report["pid"] = process.pid
        report["parent_pid"] = os.getpid()
        report["spawn_return_monotonic_ns"] = time.monotonic_ns()
        for stream, name in ((process.stdout, "stdout"), (process.stderr, "stderr")):
            thread = threading.Thread(target=reader, args=(stream, name), daemon=True)
            threads.append(thread)
            thread.start()
        deadline = started + int(timeout_seconds * 1e9)
        next_sample = time.monotonic()
        while process.poll() is None:
            if time.monotonic_ns() >= deadline:
                report["timed_out"] = True
                stop_owned_child()
                break
            if time.monotonic() >= next_sample:
                sample_start = time.monotonic_ns()
                try:
                    sampled = subprocess.run(["ps", "-p", str(process.pid), "-o", "pid=,ppid=,rss="],
                                             capture_output=True, text=True, timeout=1)
                    rss = parse_rss(sampled.stdout, process.pid, os.getpid())
                    # Do not attribute a ps result after child exit/PID recycling.
                    if process.poll() is None and rss is not None:
                        report["rss_samples"].append({"sample_start_monotonic_ns": sample_start,
                            "sample_end_monotonic_ns": time.monotonic_ns(),
                            "seconds_since_spawn_call": (sample_start - started) / 1e9, "rss_bytes": rss})
                    elif sampled.returncode not in (0, 1):
                        report["collector_errors"].append(f"ps failed ({sampled.returncode}): {sampled.stderr.strip()}")
                except (OSError, ValueError, subprocess.TimeoutExpired) as error:
                    report["collector_errors"].append(f"RSS sample unavailable: {error}")
                next_sample = time.monotonic() + interval_seconds
            time.sleep(min(0.01, interval_seconds))
        report["exit_observed_monotonic_ns"] = time.monotonic_ns()
        report["exit_observed_utc"] = utc_now()
        report["exit_code"] = process.wait(timeout=2)
    except KeyboardInterrupt:
        report["cancelled"] = True
        report.setdefault("cancellation_signal", signal.SIGINT)
        stop_owned_child()
        report["exit_observed_monotonic_ns"] = time.monotonic_ns()
        report["exit_code"] = process.returncode if process else None
    except Exception as error:
        report["collector_errors"].append(f"process collector: {type(error).__name__}: {error}")
        stop_owned_child()
        report["exit_observed_monotonic_ns"] = time.monotonic_ns()
        report["exit_code"] = process.returncode if process else None
    finally:
        if old_sigterm is not None:
            signal.signal(signal.SIGTERM, old_sigterm)
        for thread in threads:
            thread.join(timeout=2)
            if thread.is_alive():
                report["collector_errors"].append("log pipe remained open after exact child exited; reader wait bounded")
        # A descendant retaining an inherited pipe is outside the child-only scope.
        # Leave its daemon reader alone; never kill unrelated/descendant processes.
        if not any(thread.is_alive() for thread in threads):
            event_handle.close()
    report["total_wall_seconds_to_exit_observation"] = (
        report.get("exit_observed_monotonic_ns", time.monotonic_ns()) - started) / 1e9
    samples = report["rss_samples"]
    report["sampled_peak_child_rss_bytes"] = max((sample["rss_bytes"] for sample in samples), default=None)
    report["rss_sample_count"] = len(samples)
    report["exit_observation_kind"] = "monotonic parent poll/wait observation; exact kernel exit instant unavailable"
    report["log_receipt_kind"] = "parent monotonic pipe receipt; app/log buffering included; not exact presentation"
    return report


def inspect_png(path, spawn_wall_ns):
    """Validate common Bevy 8-bit RGB(A) PNGs and reject all-black pixels."""
    path = Path(path)
    result = {"path": str(path), "exists": path.is_file(), "valid_png": False,
              "fresh": False, "all_rgb_black": None, "visual_character_review": "NOT-RUN"}
    if not path.is_file():
        return result
    result["identity"] = file_identity(path)
    result["fresh"] = path.stat().st_mtime_ns >= spawn_wall_ns
    try:
        data = path.read_bytes()
        if len(data) > 20_000_000 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("missing PNG signature or capture exceeds 20 MB bound")
        offset, compressed, header, ended = 8, bytearray(), None, False
        while offset + 12 <= len(data):
            length = struct.unpack(">I", data[offset:offset + 4])[0]
            kind = data[offset + 4:offset + 8]
            chunk = data[offset + 8:offset + 8 + length]
            if offset + 12 + length > len(data):
                raise ValueError("truncated PNG chunk")
            crc = struct.unpack(">I", data[offset + 8 + length:offset + 12 + length])[0]
            if zlib.crc32(kind + chunk) & 0xffffffff != crc:
                raise ValueError("PNG chunk CRC mismatch")
            if kind == b"IHDR":
                if header is not None or length != 13:
                    raise ValueError("invalid PNG IHDR")
                header = struct.unpack(">IIBBBBB", chunk)
            elif kind == b"IDAT":
                compressed.extend(chunk)
            elif kind == b"IEND":
                ended = True
                break
            offset += length + 12
        if header is None or not ended:
            raise ValueError("PNG header/end missing")
        width, height, depth, color, compression, filtering, interlace = header
        result.update(width=width, height=height, bit_depth=depth, color_type=color)
        if (width, height) != (1280, 720):
            raise ValueError("capture must have physical dimensions 1280x720")
        if depth != 8 or color not in (2, 6) or compression or filtering or interlace:
            raise ValueError("pixel verification supports only noninterlaced 8-bit RGB/RGBA PNG")
        bpp = 3 if color == 2 else 4
        stride = width * bpp
        expected = (stride + 1) * height
        decompressor = zlib.decompressobj()
        pixels = decompressor.decompress(compressed, expected + 1)
        if len(pixels) != expected or not decompressor.eof or decompressor.unused_data:
            raise ValueError("PNG pixel stream has incorrect size or end")
        previous = bytearray(stride)
        all_black = True
        for row_number in range(height):
            start = row_number * (stride + 1)
            method = pixels[start]
            row = bytearray(pixels[start + 1:start + 1 + stride])
            if method > 4:
                raise ValueError("invalid PNG filter")
            for index in range(stride):
                left = row[index - bpp] if index >= bpp else 0
                above = previous[index]
                upper_left = previous[index - bpp] if index >= bpp else 0
                predictor = 0
                if method == 1:
                    predictor = left
                elif method == 2:
                    predictor = above
                elif method == 3:
                    predictor = (left + above) // 2
                elif method == 4:
                    p = left + above - upper_left
                    distances = (abs(p - left), abs(p - above), abs(p - upper_left))
                    predictor = (left, above, upper_left)[distances.index(min(distances))]
                row[index] = (row[index] + predictor) & 255
                if index % bpp < 3 and row[index] != 0:
                    all_black = False
            previous = row
        result.update(valid_png=True, all_rgb_black=all_black)
    except (ValueError, OSError, zlib.error, struct.error) as error:
        result["error"] = str(error)
    return result


def runtime_failures(record, revision):
    problems = []
    for key in ("ready", "capture_callback"):
        if record.get(key) is not True:
            problems.append(f"runtime {key} is not true")
    if record.get("error") is not None or record.get("timeout") is not False:
        problems.append("runtime error or timeout")
    if record.get("build_profile") != "release":
        problems.append("runtime is not release")
    if record.get("document_revision") != revision:
        problems.append("runtime document revision differs from work input")
    window = record.get("physical_window") or {}
    if (window.get("width"), window.get("height"), window.get("scale_factor")) != (1280, 720, 1.0):
        problems.append("runtime physical window differs from 1280x720 scale1")
    if (record.get("gpu") or {}).get("backend") != "Metal":
        problems.append("runtime did not identify Metal")
    for key in ("meshes", "skins", "joints", "players"):
        if not isinstance(record.get(key), int) or record[key] <= 0:
            problems.append(f"runtime {key} missing or zero")
    if record.get("frame_timing_kind") != "main_loop_cadence_not_gpu_timestamp":
        problems.append("runtime cadence boundary missing")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path,
                        help="Source/asset checkout belonging to supplied binary; no rebuild occurs")
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="New directory; existing directories rejected")
    parser.add_argument("--seconds", type=float, choices=(1.0, 15.0), default=1.0)
    parser.add_argument("--timeout", type=float, default=110.0, help="Parent wall timeout (5..180s)")
    parser.add_argument("--app-timeout", type=float, default=90.0, help="Supported app timeout (5..120s)")
    parser.add_argument("--sample-interval", type=float, default=0.1, help="RSS sample interval (0.05..1s)")
    parser.add_argument("--isolation-note", required=True, help="Root operator's actual GPU/jobs/session state")
    parser.add_argument("--cache-note", required=True, help="Actual cache state; no cold-cache claim inferred")
    args = parser.parse_args(argv)
    for value, low, high, name in ((args.timeout, 5, 180, "timeout"),
                                  (args.app_timeout, 5, 120, "app-timeout"),
                                  (args.sample_interval, .05, 1, "sample-interval")):
        if not math.isfinite(value) or not low <= value <= high:
            parser.error(f"--{name} must be between {low} and {high}")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {"protocol": "native-fresh-process-v1", "created_utc": utc_now(),
              "status": "FAILED", "failure_reasons": [], "isolation_note": args.isolation_note,
              "cache_note": args.cache_note, "cache_classification": "fresh process; OS/shader caches not controlled",
              "host": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
              "measurement_limits": ["NOT-RUN exact first presentation or GPU completion timing",
                  "NOT-RUN OS/shader cold-cache startup", "NOT-RUN visual character review by collector",
                  "sampled child RSS omits unsampled peaks, descendants and GPU/unified allocations",
                  "readiness and app capture clocks start at first Bevy update; not process/first-frame clocks",
                  "cadence counters begin after readiness plus 1s; recent up to 600; not displayed FPS",
                  "15s capture delay follows readiness; finite work may already have completed"]}
    try:
        binary, root, work = (path.resolve(strict=True) for path in (args.binary, args.source_root, args.work))
        source = root / "crates/nvwa-studio/src/lib.rs"
        text = source.read_text()
        parser_text = text.split("fn parse_native_args(", 1)[1].split("fn parse_web_pairs(", 1)[0]
        supported = set(re.findall(r'"(--[a-z-]+)"', parser_text))
        report["source_supported_flags"] = sorted(supported)
        if not FLAGS <= supported:
            raise ValueError(f"Source does not support required flags: {sorted(FLAGS - supported)}")
        document = json.loads(work.read_text())
        asset_path = Path(document["profile"]["asset_path"])
        if asset_path.is_absolute() or ".." in asset_path.parts:
            raise ValueError("Fixture path must remain within source-root/assets")
        fixture = root / "assets" / asset_path
        identities = {key: file_identity(path) for key, path in
                      (("binary", binary), ("work", work), ("fixture", fixture), ("launch_source", source))}
        report["input_identities_before"] = identities
        report["work_boundary"] = {"revision": document["revision"],
            "character_id": document["character"]["id"], "profile_id": document["profile"]["id"],
            "timeline_count": len(document["timeline"]), "fixture_claimed_sha256": document["profile"]["asset_sha256"]}
        if identities["fixture"]["sha256"] != document["profile"]["asset_sha256"]:
            raise ValueError("Fixture SHA256 differs from work profile")
        image = output / "capture.png"
        command = [str(binary), "--benchmark", "--smoke", "--smoke-seconds", str(args.seconds),
                   "--capture", str(image), "--timeout", str(args.app_timeout), "--work", str(work)]
        environment = dict(os.environ)
        environment["RUST_LOG"] = "info,wgpu=warn,naga=warn"
        environment["NO_COLOR"] = "1"
        # Native asset selection otherwise honors an inherited override or build path.
        environment["NVWA_ASSET_ROOT"] = str(root / "assets")
        report["environment_overrides"] = {key: environment[key] for key in ("RUST_LOG", "NO_COLOR", "NVWA_ASSET_ROOT")}
        report["requested_smoke_seconds_after_readiness"] = args.seconds
        spawn_wall_ns = time.time_ns()
        report["process"] = collect_process(command, root, output, args.timeout, args.sample_interval, environment)
        process = report["process"]
        report["capture"] = inspect_png(image, spawn_wall_ns)
        after = {key: file_identity(identity["path"]) for key, identity in identities.items()}
        report["input_identities_after"] = after
        report["inputs_unchanged"] = identities == after
        failures = report["failure_reasons"]
        if not report["inputs_unchanged"]:
            failures.append("input identity changed during probe")
        if process["exit_code"] != 0 or process["timed_out"] or process["cancelled"]:
            failures.append("child failed, timed out or was cancelled")
        failures.extend(process["collector_errors"])
        if not process["rss_samples"]:
            failures.append("exact-child RSS unavailable")
        if process["malformed_evidence"]:
            failures.append("malformed NVWA_EVIDENCE retained in logs")
        events = process["runtime_events"]
        if len(events) != 1:
            failures.append(f"expected one NVWA_EVIDENCE event; observed {len(events)}")
        if events:
            event = events[-1]
            record = event["record"]
            report["runtime"] = record
            failures.extend(runtime_failures(record, document["revision"]))
            if record.get("timeline_count") != len(document["timeline"]):
                failures.append("runtime timeline differs from work input")
            if record.get("capture_file_bytes") != report["capture"].get("identity", {}).get("bytes"):
                failures.append("runtime capture byte count differs from output PNG")
            report["capture_evidence_receipt_upper_bound_seconds"] = event["seconds_since_spawn_call"]
            report["capture_evidence_boundary"] = "receipt of screenshot callback+fresh-file completion event; requested readiness warmup and pipe buffering included; visual proof requires operator PNG review"
        capture = report["capture"]
        if not capture["fresh"] or not capture["valid_png"]:
            failures.append("capture missing, stale or invalid")
        if capture["all_rgb_black"] is True:
            failures.append("all-black image cannot establish visible character; locked/offscreen session possible")
        # Actual binary rejection appears as a runtime launch error or retained log.
        for name in ("stdout", "stderr"):
            log = output / f"{name}.log"
            if log.exists() and "Unknown launch argument:" in log.read_text(errors="replace"):
                failures.append("actual binary rejected launch flag; source/binary compatibility unverified")
        report["status"] = "COLLECTED_REQUIRES_VISUAL_REVIEW" if not failures else "FAILED"
    except KeyboardInterrupt:
        report["failure_reasons"].append("cancelled before/after child collection")
    except Exception as error:
        report["failure_reasons"].append(f"{type(error).__name__}: {error}")
    report["completed_utc"] = utc_now()
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "report": str(output / "report.json"),
                      "failure_reasons": report["failure_reasons"]}, indent=2))
    process = report.get("process", {})
    if process.get("cancelled"):
        return 130
    if process.get("timed_out"):
        return 124
    child_exit = process.get("exit_code")
    if isinstance(child_exit, int) and child_exit != 0:
        return child_exit if 0 < child_exit < 256 else 1
    return 0 if report["status"] == "COLLECTED_REQUIRES_VISUAL_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())

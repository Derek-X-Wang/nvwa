#!/usr/bin/env python3
"""One bounded, loopback-only real-fixture HTTP fault case. No browser control.

python3 web_stall_server.py --root /FROZEN/WEB --work /CANONICAL.nvwa.json \
  --fixture /FROZEN/WEB/assets/fixtures/nvwa-humanoid.glb --log /PRIVATE/case.jsonl

Root controls via this process's stdin: status; release 01; release all; quit.
The first four distinct diagnostic GLB bodies wait; extra asset requests are
counted and served, so the server does not simulate the product admission cap.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import mimetypes
import os
from pathlib import Path
import re
import selectors
import socket
import sys
import time
from urllib.parse import unquote, urlsplit

SHA256 = "f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6"
ASSET_RE = re.compile(r"(?:assets/)?fixtures/stall-(0[1-9]|1[0-2])\.glb")
WORK_RE = re.compile(r"works/stall-(0[1-9]|1[0-2])\.nvwa\.json")
MAX_CONNECTIONS, MAX_REQUESTS, MAX_HEADER = 20, 128, 8192
MAX_STATIC_BYTES, CHUNK = 256 * 1024 * 1024, 64 * 1024


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--port", type=int, default=9204, choices=[9204])
    parser.add_argument("--hold-seconds", type=float, default=90)
    parser.add_argument("--watchdog-seconds", type=float, default=120)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    if not (0 < args.hold_seconds < args.watchdog_seconds <= 120):
        parser.error("Require 0 < hold-seconds < watchdog-seconds <= 120")
    return args


def verified_inputs(args):
    root = args.root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("--root must be a directory")
    if args.fixture.stat().st_size != 3827840:
        raise ValueError("Fixture must be the exact 3,827,840-byte original rig")
    fixture = args.fixture.read_bytes()
    if hashlib.sha256(fixture).hexdigest() != SHA256:
        raise ValueError("Fixture SHA-256 mismatch")
    if args.work.stat().st_size > 1024 * 1024:
        raise ValueError("Canonical Work exceeds bounded input size")
    canonical_bytes = args.work.read_bytes()
    canonical = json.loads(canonical_bytes)
    if (canonical["schema_version"] != 1
            or canonical["profile"]["asset_sha256"] != SHA256
            or canonical["profile"]["id"] != "nvwa-original-humanoid-v1"
            or canonical["profile"]["license"] != "CC0-1.0 (original Nvwa test fixture only)"):
        raise ValueError("Canonical Work must preserve the original rig/hash/license")
    works = {}
    hashes = {}
    for number in range(1, 13):
        index = f"{number:02}"
        work = copy.deepcopy(canonical)
        work["profile"]["asset_path"] = f"fixtures/stall-{index}.glb"
        restored = copy.deepcopy(work)
        restored["profile"]["asset_path"] = canonical["profile"]["asset_path"]
        assert restored == canonical, "Only profile.asset_path may change"
        body = (json.dumps(work, ensure_ascii=False, indent=2) + "\n").encode()
        works[index] = body
        hashes[index] = hashlib.sha256(body).hexdigest()
    return root, fixture, works, {
        "root": str(root), "canonical_work": str(args.work.resolve()),
        "canonical_work_sha256": hashlib.sha256(canonical_bytes).hexdigest(),
        "fixture": str(args.fixture.resolve()), "fixture_bytes": len(fixture),
        "fixture_sha256": SHA256, "diagnostic_work_sha256": hashes,
        "work_paths": [f"works/stall-{n:02}.nvwa.json" for n in range(1, 13)],
        "port": args.port, "max_held_bodies": 4, "max_connections": MAX_CONNECTIONS,
        "max_requests": MAX_REQUESTS, "watchdog_seconds": args.watchdog_seconds,
        "hold_seconds": args.hold_seconds, "response_threads": 0,
    }


class Connection:
    def __init__(self, stream, now):
        self.socket = stream
        self.input = bytearray()
        self.output = b""
        self.source = None
        self.parsed = False
        self.held = False
        self.index = None
        self.hold_deadline = None
        self.deadline = now + 5  # Header deadline. Response deadline follows.
        self.sent = 0
        self.sending_body = False


class Case:
    def __init__(self, args, root, fixture, works, manifest):
        self.args, self.root, self.fixture, self.works = args, root, fixture, works
        self.selector = selectors.DefaultSelector()
        self.listener = socket.socket()
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind exactly this loopback socket. Never discover/kill another process.
        self.listener.bind(("127.0.0.1", args.port))
        self.listener.listen(MAX_CONNECTIONS)
        self.listener.setblocking(False)
        self.selector.register(self.listener, selectors.EVENT_READ, "listener")
        self.connections = {}
        self.assets, self.work_gets, self.first_four = {}, {}, set()
        self.released, self.requests, self.accepted, self.closed = set(), 0, 0, 0
        self.started = time.monotonic()
        self.deadline = self.started + args.watchdog_seconds
        self.stopping, self.stdin_bytes = False, bytearray()
        self.termination_reason = None
        self.secondary_termination_reasons = []
        self.case_status = "running"
        self.invalid_reasons = []
        self.exception = None
        args.log.parent.mkdir(parents=True, exist_ok=True)
        self.log = args.log.open("x", buffering=1)
        self.stdin_registered = False
        if sys.stdin.isatty() or not sys.stdin.closed:
            try:
                self.selector.register(sys.stdin, selectors.EVENT_READ, "stdin")
                self.stdin_registered = True
            except (OSError, ValueError):
                pass  # Watchdogs still provide finite cleanup without stdin.
        self.emit("started", pid=os.getpid(), manifest=manifest)

    def emit(self, event, **data):
        record = {"event": event, "elapsed_seconds": round(time.monotonic() - self.started, 4), **data}
        line = json.dumps(record, sort_keys=True)
        self.log.write(line + "\n")
        print(line, flush=True)

    def invalidate(self, reason, status="invalid"):
        if reason not in self.invalid_reasons:
            self.invalid_reasons.append(reason)
        if self.case_status != "unavailable":
            self.case_status = status

    def terminate(self, reason, status):
        if self.termination_reason is None:
            self.termination_reason = reason
        elif status != "ended" or reason != self.termination_reason:
            if reason not in self.secondary_termination_reasons:
                self.secondary_termination_reasons.append(reason)
        # Every failure downgrades state, including one after a normal quit in
        # the same selected batch. A later normal stop cannot erase a failure.
        if status != "ended":
            self.invalidate(reason, status)
        elif self.case_status == "running":
            self.case_status = "ended"
        self.stopping = True

    def held(self):
        return sum(c.held for c in self.connections.values())

    def status(self):
        self.emit("status", asset_gets=self.assets, work_gets=self.work_gets,
                  requests=self.requests, active_connections=len(self.connections),
                  held_bodies=self.held(), accepted=self.accepted, closed=self.closed,
                  reason=self.termination_reason, secondary_termination_reasons=self.secondary_termination_reasons,
                  case_status=self.case_status,
                  invalid_reasons=self.invalid_reasons, exception=self.exception,
                  product_bound_claim_allowed=not self.invalid_reasons)

    def close(self, connection, reason):
        fd = connection.socket.fileno()
        if fd not in self.connections:
            return
        if connection.held and reason != "server cleanup":
            self.invalidate("held connection closed before release", "unavailable")
        self.selector.unregister(connection.socket)
        connection.socket.close()
        if connection.source:
            connection.source.close()
        del self.connections[fd]
        self.closed += 1
        self.emit("connection_closed", index=connection.index, body_bytes_sent=connection.sent, reason=reason)

    def release(self, index, reason):
        if reason == "hold watchdog":
            self.invalidate("automatic hold release", "unavailable")
        self.released.add(index)
        for connection in list(self.connections.values()):
            if connection.held and connection.index == index:
                connection.held = False
                self.selector.modify(connection.socket, selectors.EVENT_READ | selectors.EVENT_WRITE, connection)
                self.emit("released", index=index, reason=reason, held_bodies=self.held())

    def response(self, connection, code, body=b"", mime="text/plain", source=None, hold=None):
        size = len(body) if source is None else os.fstat(source.fileno()).st_size
        connection.source = io.BytesIO(body) if source is None else source
        connection.output = (f"HTTP/1.1 {code}\r\nContent-Length: {size}\r\nContent-Type: {mime}\r\n"
                             "Cache-Control: no-store\r\nConnection: close\r\n\r\n").encode()
        connection.deadline = min(self.deadline, time.monotonic() + self.args.hold_seconds + 15)
        if hold:
            connection.held = True
            connection.hold_deadline = time.monotonic() + self.args.hold_seconds
            assert self.held() <= 4
            self.emit("body_held", index=hold, held_bodies=self.held())
        self.selector.modify(connection.socket, selectors.EVENT_READ | selectors.EVENT_WRITE, connection)

    def request(self, connection):
        connection.parsed = True
        self.requests += 1
        if self.requests > MAX_REQUESTS:
            self.terminate("request budget exhausted", "invalid")
            return
        try:
            method, raw_path, _ = bytes(connection.input).split(b"\r\n", 1)[0].decode("ascii").split(" ", 2)
            path = unquote(urlsplit(raw_path).path).lstrip("/")
        except (ValueError, UnicodeError):
            self.response(connection, "400 Bad Request")
            return
        self.emit("request", method=method, path=path)
        if method not in {"GET", "HEAD"}:
            self.response(connection, "405 Method Not Allowed")
            return
        work_match, asset_match = WORK_RE.fullmatch(path), ASSET_RE.fullmatch(path)
        if work_match:
            index = work_match.group(1)
            if method == "GET":
                self.work_gets[index] = self.work_gets.get(index, 0) + 1
                if sum(self.work_gets.values()) > 12:
                    self.response(connection, "429 Case Work Budget Reached")
                    self.terminate("work budget exhausted", "invalid")
                    return
            self.response(connection, "200 OK", self.works[index], "application/json")
        elif asset_match:
            index = asset_match.group(1)
            connection.index = index
            if method == "GET":
                self.assets[index] = self.assets.get(index, 0) + 1
                if self.held() == 4 and not self.released:
                    self.invalidate("unexpected asset while four held")
                    self.emit("unexpected_asset_while_four_held", index=index,
                              total=sum(self.assets.values()), product_bound_claim_allowed=False)
                if sum(self.assets.values()) > 12:
                    self.response(connection, "429 Case Asset Budget Reached")
                    self.terminate("asset budget exhausted", "invalid")
                    return
                if len(self.first_four) < 4:
                    self.first_four.add(index)
            hold = index if method == "GET" and index in self.first_four and index not in self.released and self.held() < 4 else None
            self.response(connection, "200 OK", self.fixture, "model/gltf-binary", hold=hold)
            self.emit("asset_get", index=index, count=self.assets.get(index, 0), total=sum(self.assets.values()), held_bodies=self.held())
        else:
            target = (self.root / (path or "index.html")).resolve()
            if self.root not in target.parents or not target.is_file() or target.stat().st_size > MAX_STATIC_BYTES:
                self.response(connection, "404 Not Found")
            else:
                self.response(connection, "200 OK", mime=mimetypes.guess_type(target.name)[0] or "application/octet-stream", source=target.open("rb"))
        if method == "HEAD":
            connection.source.close()
            connection.source = io.BytesIO(b"")

    def service(self, connection, mask):
        try:
            if mask & selectors.EVENT_READ:
                incoming = connection.socket.recv(2048)
                if not incoming:
                    self.close(connection, "client closed")
                    return
                if connection.parsed:
                    self.close(connection, "extra request data")
                    return
                connection.input.extend(incoming)
                if len(connection.input) > MAX_HEADER:
                    self.invalidate("header budget exhausted")
                    self.close(connection, "header budget")
                    return
                if b"\r\n\r\n" in connection.input:
                    self.request(connection)
            if mask & selectors.EVENT_WRITE and connection.parsed:
                if not connection.output:
                    if connection.held:
                        self.selector.modify(connection.socket, selectors.EVENT_READ, connection)
                        return
                    chunk = connection.source.read(CHUNK)
                    if not chunk:
                        self.close(connection, "response complete")
                        return
                    connection.output = chunk
                    connection.sending_body = True
                count = connection.socket.send(connection.output)
                if connection.sending_body:
                    connection.sent += count
                connection.output = connection.output[count:]
        except BlockingIOError:
            pass
        except (OSError, ValueError) as error:
            self.close(connection, f"IO error: {error}")

    def control(self):
        chunk = os.read(sys.stdin.fileno(), 4096)
        if not chunk:
            self.selector.unregister(sys.stdin)
            self.stdin_registered = False
            return
        self.stdin_bytes.extend(chunk)
        if len(self.stdin_bytes) > 4096:
            self.emit("control_rejected", reason="input budget")
            self.terminate("stdin input budget exhausted", "invalid")
            return
        while b"\n" in self.stdin_bytes:
            line, _, remaining = self.stdin_bytes.partition(b"\n")
            self.stdin_bytes = bytearray(remaining)
            command = line.decode("ascii", errors="replace").strip()
            if command == "status":
                self.status()
            elif command == "quit":
                self.terminate("stdin quit", "ended")
            elif command == "release all":
                for number in range(1, 13):
                    self.release(f"{number:02}", "stdin")
            elif re.fullmatch(r"release (0[1-9]|1[0-2])", command):
                self.release(command.split()[1], "stdin")
            else:
                self.emit("control_rejected", command=command)

    def run(self):
        try:
            while not self.stopping and time.monotonic() < self.deadline:
                for key, mask in self.selector.select(0.1):
                    if key.data == "listener":
                        stream, _ = self.listener.accept()
                        self.accepted += 1
                        if len(self.connections) >= MAX_CONNECTIONS or self.accepted > MAX_REQUESTS:
                            stream.close()
                            self.closed += 1
                            self.emit("connection_rejected", reason="connection budget")
                            self.invalidate("connection budget exhausted")
                            if self.accepted > MAX_REQUESTS:
                                self.terminate("connection budget exhausted", "invalid")
                            continue
                        stream.setblocking(False)
                        connection = Connection(stream, time.monotonic())
                        self.connections[stream.fileno()] = connection
                        self.selector.register(stream, selectors.EVENT_READ, connection)
                    elif key.data == "stdin":
                        self.control()
                    else:
                        self.service(key.data, mask)
                now = time.monotonic()
                for connection in list(self.connections.values()):
                    if connection.held and now >= connection.hold_deadline:
                        self.release(connection.index, "hold watchdog")
                    if now >= connection.deadline:
                        self.invalidate("connection watchdog", "unavailable")
                        self.close(connection, "connection watchdog")
        except BaseException as error:
            self.exception = {"type": type(error).__name__, "message": str(error)}
            self.terminate("exception", "unavailable")
        finally:
            if self.termination_reason is None:
                self.terminate("overall watchdog", "unavailable")
            for index in list(self.first_four):
                self.release(index, "cleanup")
            for connection in list(self.connections.values()):
                self.close(connection, "server cleanup")
            self.selector.unregister(self.listener)
            self.listener.close()
            self.selector.close()
            self.emit("cleanup", active_connections=0, held_bodies=0, response_threads=0,
                      accepted=self.accepted, closed=self.closed, asset_gets=self.assets,
                      work_gets=self.work_gets, reason=self.termination_reason,
                      secondary_termination_reasons=self.secondary_termination_reasons,
                      case_status=self.case_status,
                      invalid_reasons=self.invalid_reasons, exception=self.exception,
                      product_bound_claim_allowed=not self.invalid_reasons and self.case_status == "ended")
            assert self.accepted == self.closed
            self.log.close()
        return 0 if not self.invalid_reasons and self.case_status == "ended" else 2


def main():
    args = parse_args()
    root, fixture, works, manifest = verified_inputs(args)
    manifest["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if args.preflight:
        print(json.dumps({"event": "preflight", "manifest": manifest}, sort_keys=True))
        return
    return Case(args, root, fixture, works, manifest).run()


if __name__ == "__main__":
    raise SystemExit(main())

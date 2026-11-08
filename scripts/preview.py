"""Serve one authenticated Work for an agent-controlled real Web preview.

Print the browser URL on stderr, then one terminal JSON result on stdout.
Open that URL with the agent's browser tool; this command does not drive a GUI.
"""
import argparse
import base64
import binascii
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import secrets
import struct
import subprocess
import sys
import threading
import time
from urllib.parse import unquote, urlsplit
import zlib

MAX_BODY = 16 * 1024 * 1024
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'


class PreviewServer(ThreadingHTTPServer):
    # Browser preconnections must not hold the owner past the capture deadline.
    daemon_threads = True

    def __init__(self, address, handler, deadline):
        self.deadline = deadline
        super().__init__(address, handler)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(max(0.01, min(5.0, self.deadline - time.monotonic())))
        return connection, address


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def f32(value):
    """The existing Rust camera/seek API uses IEEE-754 single precision."""
    try:
        effective = struct.unpack('>f', struct.pack('>f', value))[0]
    except (OverflowError, struct.error) as error:
        raise ValueError('Preview value is outside the finite f32 domain') from error
    if not math.isfinite(effective):
        raise ValueError('Preview value is outside the finite f32 domain')
    return effective


def png_dimensions(raw):
    """Reject incomplete/corrupt transfers, including a missing final IEND."""
    if not raw.startswith(PNG_SIGNATURE):
        raise ValueError('Expected actual PNG bytes')
    offset = 8
    dimensions = None
    image_data = False
    while offset + 12 <= len(raw):
        length = struct.unpack('>I', raw[offset:offset + 4])[0]
        kind = raw[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(raw):
            raise ValueError('Truncated PNG chunk')
        data = raw[offset + 8:end - 4]
        crc = struct.unpack('>I', raw[end - 4:end])[0]
        if zlib.crc32(kind + data) & 0xffffffff != crc:
            raise ValueError('PNG chunk CRC mismatch')
        if dimensions is None:
            if kind != b'IHDR' or length != 13:
                raise ValueError('PNG must begin with IHDR')
            dimensions = struct.unpack('>II', data[:8])
        image_data |= kind == b'IDAT' and length > 0
        offset = end
        if kind == b'IEND':
            if length != 0 or offset != len(raw) or not image_data:
                raise ValueError('Invalid PNG completion')
            return dimensions
    raise ValueError('Missing PNG IEND')


def accept_result(payload, request):
    if not isinstance(payload, dict):
        raise ValueError('Capture result must be an object')
    if payload.get('status') != 'rendered':
        raise ValueError(str(payload.get('error', 'Renderer did not complete')))
    runtime = payload.get('runtime', {})
    if not isinstance(runtime, dict):
        raise ValueError('Rendered runtime must be an object')
    expected = {'schema_version':1,'status':'rendered',
                'work_sha256':request['work_sha256'],'document_revision':request['document_revision'],
                'camera':request['effective_camera'],'playing':False,'capture_callback':True}
    different = {key:{'expected':value,'received':runtime.get(key)}
                 for key,value in expected.items() if runtime.get(key) != value}
    if runtime.get('playing') is not False or runtime.get('capture_callback') is not True:
        different['readiness_type'] = {'expected':'false/true booleans','received':'wrong or missing'}
    if different:
        raise ValueError('Rendered identity differs from request: ' + json.dumps(different))
    seconds = runtime.get('seconds')
    if (not isinstance(seconds, (float, int)) or isinstance(seconds, bool)
            or not math.isfinite(seconds) or seconds != request['effective_seconds']):
        raise ValueError('Rendered time differs from request')
    clearance = runtime.get('foot_clearance')
    if request['foot_clearance_required']:
        if (not isinstance(clearance, dict) or clearance.get('unit') != 'cm'
                or clearance.get('method') != 'b1_visible_body_foot_min_stage_y'
                or type(clearance.get('floor_stage_y_m')) not in (int, float)
                or clearance['floor_stage_y_m'] != 0
                or any(type(value) not in (int, float) or not -math.inf < value < math.inf
                       for value in (clearance.get('left_cm'), clearance.get('right_cm')))):
            raise ValueError('Expected finite signed B1 foot clearance in centimetres')
    elif 'foot_clearance' not in runtime or clearance is not None:
        raise ValueError('Static B1 preview must report unavailable foot clearance')
    prefix = 'data:image/png;base64,'
    encoded = payload.get('png_data_url', '')
    if not isinstance(encoded, str) or not encoded.startswith(prefix):
        raise ValueError('Actual canvas PNG data URL required')
    try:
        raw = base64.b64decode(encoded[len(prefix):], validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError('Invalid PNG transfer encoding') from error
    if png_dimensions(raw) != (1280, 720):
        raise ValueError('Expected actual 1280x720 preview')
    return raw, runtime


def verify_build(root):
    receipt = json.loads((root / 'build-receipt.json').read_bytes())
    repo = Path(__file__).resolve().parent.parent
    for relative, expected in receipt['source_sha256'].items():
        path = (repo / relative).resolve()
        if not path.is_relative_to(repo) or sha(path.read_bytes()) != expected:
            raise ValueError('Preview build source changed: ' + relative)
    for name, expected in receipt['output_sha256'].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or sha(path.read_bytes()) != expected:
            raise ValueError('Preview build output changed: ' + name)
    for name in ('preview.html', 'nvwa_preview.js', 'nvwa_preview_bg.wasm'):
        if name not in receipt['output_sha256']:
            raise ValueError('Incomplete preview build receipt: ' + name)
    return receipt


def serve(args):
    if not math.isfinite(args.seconds) or args.seconds < 0:
        raise ValueError('seconds must be finite and nonnegative')
    effective_seconds = f32(args.seconds)
    root = args.preview_root.resolve(strict=True)
    build = verify_build(root)
    assets = args.assets.resolve(strict=True)
    work_raw = args.work.read_bytes()
    if len(work_raw) > MAX_BODY:
        raise ValueError('Work exceeds 16 MiB')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    work_path = output / 'work.nvwa.json'
    work_path.write_bytes(work_raw)
    checked = subprocess.run([str(args.cli.resolve(strict=True)), 'validate', str(work_path), str(assets)],
                             capture_output=True, text=True, timeout=30)
    (output / 'validation.json').write_text(json.dumps({
        'exit_code':checked.returncode, 'stdout':checked.stdout, 'stderr':checked.stderr}, indent=2)+'\n')
    if checked.returncode:
        raise ValueError('CLI asset validation failed: ' + checked.stderr.strip())
    work = json.loads(work_raw)
    camera = work['stage']['camera']
    request = {'schema_version':1, 'seconds':args.seconds, 'effective_seconds':effective_seconds,
               'work_sha256':sha(work_raw), 'document_revision':work['revision'], 'camera':camera,
               'foot_clearance_required':work['profile']['backend']['schema_version'] != 1,
               'effective_camera':{key:f32(value) for key,value in camera.items()}}
    (output / 'request.json').write_text(json.dumps(request, indent=2)+'\n')
    token = secrets.token_urlsafe(24)
    prefix = '/' + token + '/'
    deadline = time.monotonic() + args.timeout
    result = {}
    result_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, code, data, content_type='application/json'):
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = unquote(urlsplit(self.path).path)
            if not path.startswith(prefix):
                self.send(404, b'{}')
                return
            name = path[len(prefix):]
            if name == 'request.json':
                self.send(200, json.dumps(request).encode())
            elif name == 'work.nvwa.json':
                self.send(200, work_raw)
            else:
                base = assets if name.startswith('assets/') else root
                relative = name[len('assets/'):] if base == assets else name
                target = (base / relative).resolve()
                if not target.is_relative_to(base) or not target.is_file():
                    self.send(404, b'{}')
                    return
                suffix = target.suffix
                mime = {'.html':'text/html', '.js':'text/javascript', '.wasm':'application/wasm',
                        '.json':'application/json', '.png':'image/png'}.get(suffix,'application/octet-stream')
                self.send(200, target.read_bytes(), mime)

        def do_POST(self):
            if (self.path != prefix + 'finish' or result or time.monotonic() >= deadline
                    or self.headers.get('Origin') != origin):
                self.send(403, b'{}')
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if size <= 0 or size > MAX_BODY:
                    raise ValueError('Invalid capture body size')
                payload = json.loads(self.rfile.read(size))
                raw, runtime = accept_result(payload, request)
            except (ValueError, KeyError, OSError) as error:
                with result_lock:
                    if not result and time.monotonic() < deadline:
                        result.update(status='failed', error=str(error), request=request)
                self.send(422, json.dumps({'status':'failed','error':str(error)}).encode())
                return
            with result_lock:
                accepted = not result and time.monotonic() < deadline
                if accepted:
                    (output / 'actual.png').write_bytes(raw)
                    result.update(status='rendered', request=request, runtime=runtime,
                                  png_sha256=sha(raw), image=str(output / 'actual.png'),
                                  work=str(work_path), wasm_sha256=build['output_sha256']['nvwa_preview_bg.wasm'],
                                  image_kind='actual_canvas_after_screenshot_callback_with_held_pose',
                                  scope='Visual preview; not performance, quality-HOLD release or motion generation')
            self.send(200 if accepted else 409, json.dumps({'accepted':accepted}).encode())

    server = PreviewServer(('127.0.0.1', args.port), Handler, deadline)
    server.timeout = 0.5
    origin = f'http://127.0.0.1:{server.server_port}'
    url = origin + prefix + 'preview.html?player=1'
    print(json.dumps({'event':'open_browser', 'url':url, 'output':str(output)}), file=sys.stderr, flush=True)
    try:
        while not result and time.monotonic() < deadline:
            server.handle_request()
        with result_lock:
            if not result:
                result.update(status='failed', error='Browser/render capture timed out', request=request)
    finally:
        server.server_close()
    (output / 'receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    return 0 if result['status'] == 'rendered' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--seconds', type=float, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New output directory; never overwrites')
    parser.add_argument('--preview-root', type=Path, required=True, help='Output of build-preview-web.sh')
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--cli', type=Path, required=True, help='Existing nvwa-cli executable')
    parser.add_argument('--port', type=int, default=9208)
    parser.add_argument('--timeout', type=float, default=90, help='Total browser wait, 1..120 seconds')
    args = parser.parse_args()
    try:
        if not math.isfinite(args.timeout) or not 1 <= args.timeout <= 120:
            raise ValueError('timeout must be finite, 1..120 seconds')
        return serve(args)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(json.dumps({'status':'failed','error':str(error)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

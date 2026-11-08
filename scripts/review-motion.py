"""Capture an ordered B1 motion review through the existing real Web preview.

Requires Python 3.12+, an explicitly selected installed Chrome executable, and
an already built preview. Each frame owns a fresh headless Chrome process and
profile. This wrapper does not install software or implement a renderer.
"""
import argparse
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import sys
import time
from urllib.parse import urlsplit

from motion_clearance import write_clearance
from preview import f32, verify_build

PREVIEW = Path(__file__).with_name('preview.py')
CAMERA_AZIMUTH = {'front': 0.0, 'side': 90.0}
MAX_FRAMES = 24
TERM_GRACE = 2.0
KILL_GRACE = 2.0


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@contextmanager
def defer_cancellation():
    """Finish bounded cleanup before reporting any cancellation received there."""
    received = []
    def remember(signum, _frame):
        received.append(signum)
    previous = {signum: signal.signal(signum, remember)
                for signum in (signal.SIGINT, signal.SIGTERM)}
    try:
        yield received
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def stop_group(process, audit_path):
    """Signal only our start_new_session group; only ESRCH proves its absence."""
    started = time.monotonic()
    with audit_path.open('a') as audit:
        def operation(signum, phase):
            event = {'pgid': process.pid, 'operation': 'signal0' if signum == 0 else signal.Signals(signum).name,
                     'phase': phase, 'errno': None, 'direct_child_returncode': process.poll()}
            try:
                os.killpg(process.pid, signum)
                state = 'present' if signum == 0 else 'delivered'
            except ProcessLookupError as error:
                state = 'absent'
                event.update(errno=error.errno, error=str(error))
            except OSError as error:
                # Permission denial, including signal0 EPERM, is not absence.
                state = 'unknown'
                event.update(errno=error.errno, error=str(error))
            event.update(state=state, elapsed_seconds=time.monotonic() - started)
            if signum != 0:
                event['signal_delivered'] = state == 'delivered'
            audit.write(json.dumps(event) + '\n')
            audit.flush()
            return state

        for phase, signum, grace in (('term', signal.SIGTERM, TERM_GRACE), ('kill', signal.SIGKILL, KILL_GRACE)):
            if operation(0, phase + '-before') == 'absent':
                return
            if operation(signum, phase + '-delivery') == 'absent':
                return
            deadline = time.monotonic() + grace
            while True:
                if operation(0, phase + '-wait') == 'absent':
                    return
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                time.sleep(min(0.02, remaining))
    raise RuntimeError(f'Cannot prove owned process group {process.pid} absent after bounded TERM/KILL; see {audit_path.name}')


def camera_independent_work(document):
    # Compare typed JSON values via canonical JSON: Python equality alone would
    # accept an unrelated bool-to-number change (False == 0).
    retained = dict(document)
    retained.pop('revision', None)
    retained['stage'] = dict(retained['stage'])
    retained['stage'].pop('camera')
    return json.dumps(retained, sort_keys=True, separators=(',', ':'), allow_nan=False)


def read_work(path):
    raw = path.read_bytes()
    document = json.loads(raw)
    json.dumps(document, allow_nan=False)
    if (not isinstance(document, dict) or not isinstance(document.get('stage'), dict)
            or not isinstance(document['stage'].get('camera'), dict)
            or type(document.get('revision')) is not int):
        raise ValueError('Expected a Work with a stage camera and integer revision: ' + str(path))
    camera_independent_work(document)
    return raw, document


def requested_views(args, base_path, raw, base):
    if args.view:
        names = set()
        for supplied in args.view:
            name, separator, path = supplied.partition('=')
            if (not separator or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,47}', name)
                    or name in names):
                raise ValueError('Each view requires a unique safe NAME=WORK')
            names.add(name)
            source = Path(path).resolve(strict=True)
            view_raw, document = read_work(source)
            if camera_independent_work(document) != camera_independent_work(base):
                raise ValueError('Review view differs from base Work outside camera/revision: ' + name)
            yield name, source, view_raw, document
        return

    for name in args.camera or ['saved']:
        if name == 'saved' and all(value is None for value in (args.azimuth, args.elevation, args.distance)):
            yield name, base_path, raw, base
            continue
        camera = dict(base['stage']['camera'])
        if name in CAMERA_AZIMUTH:
            camera['azimuth_degrees'] = CAMERA_AZIMUTH[name]
        for key, value in (('azimuth_degrees', args.azimuth), ('elevation_degrees', args.elevation),
                           ('distance', args.distance)):
            if value is not None:
                camera[key] = value
        document = dict(base, stage=dict(base['stage'], camera=camera))
        yield name, base_path, (json.dumps(document, allow_nan=False) + '\n').encode(), document


def range_times(args, view_count):
    if args.end is None or args.step is None:
        raise ValueError('A range requires --start, --end and --step')
    try:
        start, end, step = map(Decimal, (args.start, args.end, args.step))
    except InvalidOperation as error:
        raise ValueError('Range times must be decimal seconds') from error
    if (not all(value.is_finite() for value in (start, end, step))
            or not 0 <= start < end or not step > 0):
        raise ValueError('Range requires finite seconds with 0 <= start < end and step > 0')
    if f32(float(start)) >= f32(float(end)):
        raise ValueError('Range endpoints have duplicate effective preview times')
    if not math.isfinite(float(step)) or float(step) == 0:
        raise ValueError('Range step must be a representable positive number of seconds')

    times = []
    effective = -1.0
    for index in range(MAX_FRAMES // view_count):
        # Decimal inputs keep values like 5.975 and 6.000 on the intended grid.
        value = min(start + index * step, end)
        seconds = float(value)
        next_effective = f32(seconds)
        if next_effective <= effective:
            raise ValueError('Range produces duplicate or unordered effective preview times')
        times.append(seconds)
        effective = next_effective
        if value == end:
            return times
    raise ValueError('Review requires one or two views and at most 24 total frames')


def open_url(event):
    url = event.get('url')
    if not isinstance(url, str):
        raise ValueError('Preview open_browser event has no URL')
    parsed = urlsplit(url)
    if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1'
            or parsed.username is not None or parsed.password is not None
            or parsed.port is None or parsed.query != 'player=1' or parsed.fragment
            or not re.fullmatch(r'/[A-Za-z0-9_-]+/preview\.html', parsed.path)):
        raise ValueError('Preview did not supply an exact authenticated loopback URL')
    return url


def capture_frame(args, frame, work, output, total_deadline):
    directory = output / 'frames' / f"{frame['index']:02d}-{frame['view']}"
    directory.mkdir(parents=True)
    capture = directory / 'capture'
    profile = directory / 'chrome-profile'
    preview_command = [sys.executable, '-B', str(PREVIEW.resolve()),
                       '--work', work['snapshot'], '--seconds', str(frame['requested_seconds']),
                       '--output', str(capture), '--preview-root', str(args.preview_root),
                       '--assets', str(args.assets), '--cli', str(args.cli),
                       '--port', str(args.port), '--timeout', str(args.timeout)]
    write_json(directory / 'preview-command.json', preview_command)
    processes = {}
    cleanup = {}
    result = dict(frame, status='failed', directory=str(directory))
    deadline = min(total_deadline, time.monotonic() + args.timeout)
    try:
        with ((directory / 'preview.stdout.log').open('wb') as stdout_log,
              (directory / 'preview.stderr.log').open('wb') as stderr_log,
              (directory / 'chrome.stdout.log').open('wb') as chrome_stdout,
              (directory / 'chrome.stderr.log').open('wb') as chrome_stderr,
              selectors.DefaultSelector() as selector):
            preview = subprocess.Popen(preview_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       start_new_session=True)
            processes['preview'] = preview
            write_json(directory / 'processes.json', {'preview': preview.pid})
            for pipe, name in ((preview.stdout, 'stdout'), (preview.stderr, 'stderr')):
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ, name)
            pending = b''
            while selector.get_map() or preview.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Total review deadline exceeded' if deadline == total_deadline
                                       else 'Frame preview/browser deadline exceeded')
                for key, _ in selector.select(min(0.1, max(0.0, deadline - time.monotonic()))):
                    data = os.read(key.fileobj.fileno(), 65536)
                    if not data:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                        continue
                    (stdout_log if key.data == 'stdout' else stderr_log).write(data)
                    if key.data != 'stderr':
                        continue
                    pending += data
                    while b'\n' in pending:
                        line, pending = pending.split(b'\n', 1)
                        try:
                            event = json.loads(line)
                        except (ValueError, UnicodeError):
                            continue
                        if not isinstance(event, dict) or event.get('event') != 'open_browser':
                            continue
                        if 'chrome' in processes:
                            raise ValueError('Preview emitted a duplicate open_browser event')
                        if event.get('output') != str(capture):
                            raise ValueError('Preview open_browser event refers to another output')
                        url = open_url(event)
                        profile.mkdir()
                        chrome_command = [str(args.chrome), '--headless=new',
                                          '--user-data-dir=' + str(profile),
                                          '--no-first-run', '--no-default-browser-check',
                                          '--disable-background-networking',
                                          '--disable-breakpad', '--disable-crash-reporter',
                                          '--window-size=1280,720', '--force-device-scale-factor=1', url]
                        write_json(directory / 'chrome-command.json', chrome_command)
                        processes['chrome'] = subprocess.Popen(
                            chrome_command, stdout=chrome_stdout, stderr=chrome_stderr,
                            start_new_session=True)
                        write_json(directory / 'processes.json', {name: proc.pid for name, proc in processes.items()})
                chrome = processes.get('chrome')
                if chrome is not None and chrome.poll() is not None and preview.poll() is None:
                    raise RuntimeError(f'Owned Chrome exited before preview completed: {chrome.returncode}')
            stdout_log.flush()
            stderr_log.flush()
            if preview.returncode != 0:
                raise RuntimeError(f'Preview exited {preview.returncode}; see preview.stderr.log')
            if 'chrome' not in processes:
                raise RuntimeError('Preview completed without an open_browser event')
        terminal = json.loads((directory / 'preview.stdout.log').read_bytes())
        receipt = json.loads((capture / 'receipt.json').read_bytes())
        if not isinstance(receipt, dict) or terminal != receipt or receipt.get('status') != 'rendered':
            raise ValueError('Preview terminal result and successful receipt disagree')
        request = receipt.get('request', {})
        if (not isinstance(request, dict) or request.get('work_sha256') != work['sha256']
                or request.get('document_revision') != work['revision']
                or request.get('camera') != work['camera']
                or type(request.get('seconds')) not in (int, float)
                or request['seconds'] != frame['requested_seconds']):
            raise ValueError('Preview receipt differs from this frame Work/camera/time')
        image = capture / 'actual.png'
        if (receipt.get('image') != str(image) or receipt.get('work') != str(capture / 'work.nvwa.json')
                or sha((capture / 'work.nvwa.json').read_bytes()) != work['sha256']
                or sha(image.read_bytes()) != receipt.get('png_sha256')):
            raise ValueError('Preview receipt files or hashes differ from this frame')
        result.update(status='rendered', capture=receipt, receipt=str(capture / 'receipt.json'))
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as error:
        result.update(status='failed', error=str(error))
    finally:
        with defer_cancellation() as cancelled:
            # Chrome stops first so it cannot access a server being stopped.
            for name in ('chrome', 'preview'):
                process = processes.get(name)
                if process is None:
                    continue
                cleanup[name] = {'pid': process.pid, 'pgid': process.pid, 'audit': str(directory / 'cleanup.jsonl')}
                try:
                    stop_group(process, directory / 'cleanup.jsonl')
                    cleanup[name]['process_group_absent'] = True
                except (OSError, RuntimeError) as error:
                    cleanup[name].update(process_group_absent=False, error=str(error))
                    result.update(status='failed', error='Owned process cleanup failed: ' + str(error))
                for pipe in (process.stdout, process.stderr):
                    if pipe is not None:
                        pipe.close()
            if profile.exists() and ('chrome' not in processes or cleanup.get('chrome', {}).get('process_group_absent')):
                try:
                    shutil.rmtree(profile)
                except OSError as error:
                    result.update(status='failed', error='Owned Chrome profile cleanup failed: ' + str(error))
        if cancelled:
            result.update(status='failed', error=f'Review interrupted by signal {cancelled[-1]} during cleanup',
                          cleanup_cancelled_signals=cancelled)
        result['cleanup'] = cleanup
        result['chrome_profile_removed'] = not profile.exists()
        write_json(directory / 'frame.json', result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chrome', type=Path, required=True, help='Exact installed Chrome executable')
    parser.add_argument('--work', type=Path, required=True, help='Original Work; retained unchanged')
    cameras = parser.add_mutually_exclusive_group()
    cameras.add_argument('--camera', action='append', choices=['saved', *CAMERA_AZIMUTH],
                         help='Use saved camera (default), front (0°), or side (90°); repeat for two views')
    cameras.add_argument('--view', action='append', metavar='NAME=WORK',
                         help='One or two saved camera-copy Works; repeat in desired view order')
    parser.add_argument('--azimuth', type=float, help='Temporary orbit angle in degrees, with the saved camera')
    parser.add_argument('--elevation', type=float, help='Temporary camera elevation in degrees')
    parser.add_argument('--distance', type=float, help='Temporary camera distance in character-relative units')
    timing = parser.add_mutually_exclusive_group(required=True)
    timing.add_argument('--seconds', type=float, action='append',
                        help='Explicit time; repeat in desired order for each view')
    timing.add_argument('--start', help='First sample in seconds; use with --end and --step')
    parser.add_argument('--end', help='Last sample in seconds, always included in range mode')
    parser.add_argument('--step', help='Sample spacing in seconds for range mode')
    parser.add_argument('--output', type=Path, required=True, help='New result directory; never overwrites')
    parser.add_argument('--preview-root', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--port', type=int, default=9208)
    parser.add_argument('--timeout', type=float, default=90, help='Per-frame deadline, 1..90 seconds')
    parser.add_argument('--total-timeout', type=float, default=600, help='Total deadline, greater than 0 and at most 600 seconds')
    args = parser.parse_args(argv)
    receipt = {'schema_version': 1, 'format': 'nvwa-motion-review', 'status': 'failed', 'frames': [],
               'scope': 'Ordered actual Web preview frames; no claim of whole-motion smoothness or quality-HOLD release'}
    output = args.output.resolve()
    created = False
    started = time.monotonic()
    def interrupted(signum, _frame):
        # selectors treats InterruptedError as a retryable interrupted syscall.
        # Use RuntimeError so an owner cancellation reaches our cleanup path.
        raise RuntimeError(f'Review interrupted by signal {signum}')
    previous_handlers = {signum: signal.signal(signum, interrupted)
                         for signum in (signal.SIGINT, signal.SIGTERM)}
    try:
        output.mkdir(parents=True, exist_ok=False)
        created = True
        if sys.version_info < (3, 12) or os.name != 'posix':
            raise ValueError('This supported path requires Python 3.12+ and POSIX process groups')
        if not math.isfinite(args.timeout) or not 1 <= args.timeout <= 90:
            raise ValueError('timeout must be finite, 1..90 seconds')
        if not math.isfinite(args.total_timeout) or not 0 < args.total_timeout <= 600:
            raise ValueError('total-timeout must be finite, greater than 0 and at most 600 seconds')
        if not 0 <= args.port <= 65535:
            raise ValueError('port must be between 0 and 65535')
        view_count = len(args.view or args.camera or ['saved'])
        if not 1 <= view_count <= 2:
            raise ValueError('Review requires one or two views and at most 24 total frames')
        if args.start is not None:
            args.seconds = range_times(args, view_count)
            receipt['sampling'] = {
                'start_seconds': args.seconds[0], 'end_seconds': args.seconds[-1],
                'step_seconds': float(args.step),
            }
        elif args.end is not None or args.step is not None:
            raise ValueError('--end and --step require range mode (--start)')
        if view_count * len(args.seconds) > MAX_FRAMES:
            raise ValueError('Review requires one or two views and at most 24 total frames')
        if args.camera and len(set(args.camera)) != view_count:
            raise ValueError('Each camera preset may be requested once')
        overrides = (args.azimuth, args.elevation, args.distance)
        if any(value is not None for value in overrides) and args.view:
            raise ValueError('Camera overrides cannot be combined with camera-copy Works')
        if any(value is not None and not math.isfinite(value) for value in overrides):
            raise ValueError('Camera overrides must be finite')
        if args.azimuth is not None and args.camera not in (None, ['saved']):
            raise ValueError('An explicit azimuth requires the saved camera')
        if any(not math.isfinite(seconds) or seconds < 0 for seconds in args.seconds):
            raise ValueError('seconds must be finite and nonnegative; renderer also checks the timeline endpoint')
        for name in ('chrome', 'cli'):
            path = getattr(args, name).resolve(strict=True)
            if not path.is_file() or not os.access(path, os.X_OK):
                raise ValueError(name + ' must name an existing executable file')
            setattr(args, name, path)
        for name in ('assets', 'preview_root'):
            path = getattr(args, name).resolve(strict=True)
            if not path.is_dir():
                raise ValueError(name + ' must name an existing directory')
            setattr(args, name, path)
        try:
            verify_build(args.preview_root)
        except (OSError, KeyError, TypeError, ValueError) as error:
            raise ValueError(
                f'Preview build preflight failed: {error}. '
                'Rebuild with bash scripts/build-preview-web.sh <new-preview-root>.'
            ) from error
        base_path = args.work.resolve(strict=True)
        raw, base = read_work(base_path)
        (output / 'base.nvwa.json').write_bytes(raw)
        receipt['base_work'] = {'input': str(base_path), 'snapshot': str(output / 'base.nvwa.json'),
                                'sha256': sha(raw), 'revision': base['revision']}
        validation_command = [str(args.cli), 'validate', str(output / 'base.nvwa.json'), str(args.assets)]
        validation = {'command': validation_command}
        checked = subprocess.Popen(validation_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
        try:
            validation_stdout, validation_stderr = checked.communicate(
                timeout=max(0.001, min(30, started + args.total_timeout - time.monotonic())))
            validation.update(exit_code=checked.returncode, stdout=validation_stdout.decode(errors='replace'),
                              stderr=validation_stderr.decode(errors='replace'))
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            validation['error'] = str(error)
            raise
        finally:
            with defer_cancellation() as cancelled:
                validation.update(pid=checked.pid, pgid=checked.pid, cleanup_audit=str(output / 'base-cleanup.jsonl'))
                try:
                    stop_group(checked, output / 'base-cleanup.jsonl')
                    validation['process_group_absent'] = True
                except (OSError, RuntimeError) as error:
                    validation.update(process_group_absent=False, cleanup_error=str(error))
                    raise
                finally:
                    for pipe in (checked.stdout, checked.stderr):
                        if pipe is not None:
                            pipe.close()
                    validation['cleanup_cancelled_signals'] = cancelled
                    write_json(output / 'base-validation.json', validation)
            if cancelled:
                raise RuntimeError(f'Review interrupted by signal {cancelled[-1]} during base validation cleanup')
        if checked.returncode:
            raise ValueError('Original base Work CLI validation failed; see base-validation.json')
        views = []
        (output / 'views').mkdir()
        for name, source, view_raw, document in requested_views(args, base_path, raw, base):
            snapshot = output / 'views' / (name + '.nvwa.json')
            snapshot.write_bytes(view_raw)
            views.append({'name': name, 'input': str(source), 'snapshot': str(snapshot),
                          'sha256': sha(view_raw), 'revision': document['revision'],
                          'camera': document['stage']['camera']})
        receipt.update(views=views, requested_seconds=args.seconds, expected_frame_count=len(views) * len(args.seconds),
                       chrome=str(args.chrome), per_frame_timeout=args.timeout, total_timeout=args.total_timeout)
        write_json(output / 'request.json', receipt)
        for view in views:
            for seconds in args.seconds:
                frame = {'index': len(receipt['frames']), 'view': view['name'], 'requested_seconds': seconds,
                         'view_work_sha256': view['sha256'], 'view_document_revision': view['revision']}
                if time.monotonic() >= started + args.total_timeout:
                    raise TimeoutError('Total review deadline exceeded before next frame')
                result = capture_frame(args, frame, view, output, started + args.total_timeout)
                receipt['frames'].append(result)
                write_json(output / 'receipt.json', receipt)
                if result['status'] != 'rendered':
                    raise RuntimeError('Frame ' + str(frame['index']) + ' failed: ' + result['error'])
        if args.start is not None:
            receipt['foot_clearance'] = write_clearance(output, receipt['frames'], receipt['sampling'])
        receipt['status'] = 'rendered'
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as error:
        receipt.update(status='failed', error=str(error))
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
    receipt['elapsed_seconds'] = time.monotonic() - started
    if created:
        write_json(output / 'receipt.json', receipt)
    print(json.dumps(receipt, allow_nan=False), flush=True)
    return 0 if receipt['status'] == 'rendered' else 1


if __name__ == '__main__':
    raise SystemExit(main())

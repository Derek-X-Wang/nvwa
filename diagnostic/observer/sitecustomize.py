"""Opt-in, throwaway observation; never imported by the source fixture itself."""
import time as _time
_observer_begin = _time.monotonic_ns()
import os as _os
import sys as _sys
import atexit as _atexit

if _os.environ.get('NVWA73_GATE_OBSERVER') == 'exp73-eight-child-v1':
    _target = _os.environ['NVWA73_GATE_TARGET']
    _directory = _os.path.dirname(_target)
    _fd = _os.open(_os.environ['NVWA73_GATE_EVENTS'], _os.O_WRONLY | _os.O_APPEND)
    _pid = _os.getpid()
    _labels = {}
    _gate_code = None
    _callback_ns = 0
    _audit_calls = 0
    _exec_calls = 0
    _unwind_calls = 0
    _event_count = 0
    _tool = _sys.monitoring.PROFILER_ID
    _events = _sys.monitoring.events

    def _emit(event, label, detail='-'):
        global _event_count
        now = _time.monotonic_ns()
        _os.write(_fd, f'{event}\t{label}\t{now}\t{_pid}\t{detail}\n'.encode('ascii'))
        _event_count += 1

    _emit('observer_start', 'sitecustomize', str(_sys.flags.optimize))

    def _start(code, offset):
        global _callback_ns
        begin = _time.monotonic_ns()
        try:
            label = _labels[code]
            _emit('gate_entry' if code is _gate_code else 'module_entry', label)
            if code is _gate_code:
                # Exception-unwind is a global-only event in CPython 3.14.
                # Enable it only while this one selected gate method is active.
                _sys.monitoring.set_events(_tool, _events.PY_UNWIND)
        finally:
            _callback_ns += _time.monotonic_ns() - begin

    def _returned(code, offset, value):
        global _callback_ns
        begin = _time.monotonic_ns()
        try:
            if code is _gate_code:
                _sys.monitoring.set_events(_tool, 0)
                _emit('gate_exit', 'selected_gate', 'return')
            else:
                _emit('module_return', _labels[code])
        finally:
            _callback_ns += _time.monotonic_ns() - begin

    def _unwound(code, offset, error):
        global _callback_ns, _unwind_calls
        begin = _time.monotonic_ns()
        try:
            _unwind_calls += 1
            if code is _gate_code:
                _sys.monitoring.set_events(_tool, 0)
                _emit('gate_exit', 'selected_gate', type(error).__name__)
        finally:
            _callback_ns += _time.monotonic_ns() - begin

    def _find_gate(code):
        global _gate_code
        if code.co_qualname == 'SourceContract.test_frozen_source_inputs':
            if _gate_code is not None:
                raise RuntimeError('duplicate selected gate code')
            _gate_code = code
            _labels[code] = 'selected_gate'
            _sys.monitoring.set_local_events(_tool, code, _events.PY_START | _events.PY_RETURN)
        for value in code.co_consts:
            if hasattr(value, 'co_code'):
                _find_gate(value)

    def _audit(event, args):
        global _callback_ns, _audit_calls, _exec_calls
        _audit_calls += 1
        if event != 'exec':
            return
        begin = _time.monotonic_ns()
        try:
            _exec_calls += 1
            code = args[0]
            filename = code.co_filename
            if filename not in (_target, _directory + '/frozen_context.py', _directory + '/cpu_probe.py'):
                return
            label = _os.path.basename(filename)
            _labels[code] = label
            _emit('module_exec', label)
            _sys.monitoring.set_local_events(_tool, code, _events.PY_START | _events.PY_RETURN)
            if filename == _target:
                _find_gate(code)
        finally:
            _callback_ns += _time.monotonic_ns() - begin

    def _finished():
        _emit('process_atexit', 'child')
        # Measured callback bodies exclude fast-path non-exec audit callbacks,
        # interpreter event dispatch, and the footer's own work.
        _emit('observer_stats', 'callback_body_ns', str(_callback_ns))
        _emit('observer_stats', 'audit_calls', str(_audit_calls))
        _emit('observer_stats', 'exec_callbacks', str(_exec_calls))
        _emit('observer_stats', 'unwind_callbacks', str(_unwind_calls))
        _emit('observer_stats', 'events_before_footer_end', str(_event_count))
        _os.close(_fd)

    _sys.monitoring.use_tool_id(_tool, 'nvwa73-isolated-gate-observer')
    _sys.monitoring.register_callback(_tool, _events.PY_START, _start)
    _sys.monitoring.register_callback(_tool, _events.PY_RETURN, _returned)
    _sys.monitoring.register_callback(_tool, _events.PY_UNWIND, _unwound)
    _sys.addaudithook(_audit)
    _atexit.register(_finished)
    _emit('observer_ready', 'setup_ns', str(_time.monotonic_ns() - _observer_begin))

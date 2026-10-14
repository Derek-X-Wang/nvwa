#!/usr/bin/env python3
"""Exercise the real verifier with only retained data and explicit I/O guards."""
import argparse
import builtins
import io
import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
from unittest.mock import patch

from verify import verify


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scratch', type=Path, required=True)
    args = parser.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='portable-', dir=args.scratch) as temporary:
        packet = Path(temporary).resolve()
        for directory in ('inputs', 'http'):
            shutil.copytree(source / directory, packet / directory)
        for name in ('capture.json', 'requests.json'):
            shutil.copyfile(source / name, packet / name)
        allowed_classifier = source / 'source_types.py'
        original_open = builtins.open
        original_io_open = io.open
        reads = []

        def guard(opener):
            def checked(file, mode='r', *positional, **keywords):
                if isinstance(file, int):
                    raise AssertionError('unexpected descriptor I/O')
                target = Path(file).resolve()
                if any(letter in mode for letter in ('w', 'a', '+', 'x')):
                    raise AssertionError('verifier attempted a write')
                if not target.is_relative_to(packet) and target != allowed_classifier:
                    raise AssertionError('nonportable external read: ' + str(target))
                reads.append(str(target))
                return opener(file, mode, *positional, **keywords)
            return checked

        def forbidden(*args, **kwargs):
            raise AssertionError('offline verifier attempted network/process access')

        with patch('builtins.open', guard(original_open)), patch('io.open', guard(original_io_open)), patch.object(socket, 'socket', forbidden), patch.object(socket, 'create_connection', forbidden), patch.object(subprocess, 'Popen', forbidden):
            result = verify(packet)
        assert result['status'] == 'VERIFIED-SOURCE-INTEGRITY/UNAPPROVED-COVERAGE', result
        assert result['live_comparison'] == 'NOT-RUN', result
        assert reads and all(Path(path).is_relative_to(packet) or Path(path) == allowed_classifier for path in reads)
        print(json.dumps({'status': 'VERIFIED', 'production_verifier_called': True, 'read_operations': len(reads), 'source_cache_and_old_packet_reads': 0, 'network_and_process_access': 'guarded forbidden', 'temporary_packet_removed_on_exit': True, 'coverage': 'UNKNOWN; integrity only'}))


if __name__ == '__main__':
    main()

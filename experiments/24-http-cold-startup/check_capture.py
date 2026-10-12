#!/usr/bin/env python3
"""Validate diagnostic structure; PASS is not browser startup acceptance."""
import argparse
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit


def number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError('invalid nonnegative finite number: ' + field)
    return value


def validate(capture, expected_run):
    if capture.get('schema') != 'nvwa-http-startup-browser-v1':
        raise ValueError('unknown diagnostic schema')
    if not re.fullmatch(r'[0-9a-f]{32}', expected_run) or capture.get('runId') != expected_run:
        raise ValueError('run identity mismatch')
    url = urlsplit(capture.get('url', ''))
    if url.scheme != 'http' or url.netloc != '127.0.0.1:9201' or url.path != f'/run/{expected_run}/index.html':
        raise ValueError('navigation URL does not match run')
    if capture.get('clock') != 'Performance monotonic milliseconds since navigation timeOrigin':
        raise ValueError('unexpected clock; Bevy clock cannot be mixed with navigation')
    stop = number(capture.get('snapshotAtMs'), 'snapshotAtMs')
    if number(capture.get('installedAtMs'), 'installedAtMs') > stop:
        raise ValueError('installation is after snapshot')
    number(capture.get('timeOriginEpochMs'), 'timeOriginEpochMs')
    nav = capture.get('navigation')
    if not isinstance(nav, list) or len(nav) != 1 or nav[0].get('entryType') != 'navigation':
        raise ValueError('one real navigation entry required')
    resources = capture.get('resources')
    if not isinstance(resources, list):
        raise ValueError('resource entries required')
    for row in nav + resources:
        for field in ('startTime', 'duration', 'responseEnd', 'transferSize', 'encodedBodySize', 'decodedBodySize'):
            number(row.get(field), field)
        start, duration, end = row['startTime'], row['duration'], row['responseEnd']
        if start > stop or end > stop + 1 or end < start:
            raise ValueError('inconsistent resource timing boundary')
        if row.get('entryType') == 'resource' and abs((start + duration) - end) > 1:
            raise ValueError('resource duration differs from responseEnd')
        for field in ('fetchStart', 'requestStart', 'responseStart'):
            value = row.get(field)
            if value is not None and number(value, field) > end:
                raise ValueError(field + ' after responseEnd')
        for field in ('transferSize', 'encodedBodySize', 'decodedBodySize'):
            if row[field] != int(row[field]):
                raise ValueError('fractional byte count')
    for milestone in capture.get('milestones', []):
        if milestone.get('name') != 'boot-status-hidden-observed':
            raise ValueError('unsupported milestone')
        if number(milestone.get('observedAtMs'), 'observedAtMs') > stop:
            raise ValueError('milestone after snapshot')
    return {'runId': expected_run, 'navigationEntries': len(nav), 'resourceEntries': len(resources),
            'scope': 'structure and finite timing validation only; first presentation and cold state NOT-RUN'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.capture.read_text()), args.run)
    except (ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    print('PASS', json.dumps(result))


if __name__ == '__main__':
    main()

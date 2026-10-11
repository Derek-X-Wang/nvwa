#!/usr/bin/env python3
"""Check and summarize the retained real HTTP A/B capture, not a browser driver."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    records = [json.loads(line) for line in args.capture.read_text().splitlines()]
    assert all(row['interrupted'] is None for row in records)
    summary = {'measurement': 'HTTP response body bytes actually written; excludes headers/TCP overhead',
               'cache_policy': 'no-store; fresh baseline/candidate URLs; no cold compiler/GPU claim'}
    for prefix, count in [('baseline', 2), ('candidate', 1)]:
        rows = [row for row in records if row['path'].startswith('/' + prefix + '/')
                and '/nvwa-fault.glb' not in row['path']]
        glb = [row for row in rows if row['path'].endswith('/nvwa-humanoid.glb')]
        assert len(glb) == count
        assert all(row['status'] == 200 and row['content_encoding'] == 'gzip'
                   and row['body_bytes_written'] == row['declared_bytes'] == 1129081 for row in glb)
        summary[prefix] = {'glb_requests': len(glb),
                           'glb_body_bytes': sum(row['body_bytes_written'] for row in glb),
                           'all_response_body_bytes': sum(row['body_bytes_written'] for row in rows),
                           'all_response_count': len(rows)}
    fault = [row for row in records if row['path'].endswith('/nvwa-fault.glb')]
    assert [row['status'] for row in fault] == [404, 200, 200, 200]
    assert [row['body_bytes_written'] for row in fault] == [469, 1129081, 1129082, 1129081]
    summary['fault_open_sequence'] = ['missing rejected', 'same-path valid recovery',
                                      'modified hash rejected', 'same-path valid recovery']
    summary['glb_body_bytes_saved'] = summary['baseline']['glb_body_bytes'] - summary['candidate']['glb_body_bytes']
    summary['all_response_body_bytes_saved'] = summary['baseline']['all_response_body_bytes'] - summary['candidate']['all_response_body_bytes']
    summary['limits'] = 'GUI outcome is separately evidenced by screenshots; parser checks retained capture only.'
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()

"""Measure segments in a captured Nvwa preview PNG using image pixels."""
import argparse
import json
import math
from pathlib import Path
import re

from preview import png_dimensions, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path, help='Single-frame capture/receipt.json')
    parser.add_argument('--segment', action='append', required=True, metavar='NAME=X1,Y1:X2,Y2',
                        help='Two image pixel coordinates (origin at top left); repeat for more segments')
    args = parser.parse_args()
    try:
        receipt = json.loads(args.receipt.read_bytes())
        if not isinstance(receipt, dict) or receipt.get('status') != 'rendered':
            raise ValueError('Expected a successful single-frame preview receipt')
        image = args.receipt.with_name('actual.png')
        raw = image.read_bytes()
        digest = sha(raw)
        if digest != receipt.get('png_sha256'):
            raise ValueError('PNG hash differs from the capture receipt')
        width, height = png_dimensions(raw)
        segments = {}
        for entry in args.segment:
            match = re.fullmatch(r'([A-Za-z0-9_-]+)=(\d+),(\d+):(\d+),(\d+)', entry, re.ASCII)
            if match is None:
                raise ValueError('Each segment must be NAME=X1,Y1:X2,Y2')
            name, *coordinates = match.groups()
            x1, y1, x2, y2 = map(int, coordinates)
            if name in segments:
                raise ValueError('Segment names must be unique')
            if not (x1 < width and x2 < width and y1 < height and y2 < height):
                raise ValueError('Segment points must be within the captured image')
            segments[name] = {
                'from': [x1, y1], 'to': [x2, y2],
                'horizontal_px': abs(x2 - x1), 'vertical_px': abs(y2 - y1),
                'distance_px': math.hypot(x2 - x1, y2 - y1),
            }
        print(json.dumps({
            'status': 'measured', 'unit': 'px', 'image': str(image.resolve()),
            'png_sha256': digest, 'image_size_px': [width, height], 'segments': segments,
        }))
    except (OSError, ValueError) as error:
        print(json.dumps({'status': 'failed', 'error': str(error)}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

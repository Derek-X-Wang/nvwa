"""Reproduce the frozen alpha-only engineering rejection; no rendering."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
from png_alpha import rgba_png, require, sha

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / 'assets/appearances/mpfb-b1-cc0-v1/hair/short04/short04_diffuse.png'
PNG_SHA = '0bef7fc0e403db5a40fabb2111ebfa6f7e8158e204c6e56b8da98e9ef527846e'
RGBA_SHA = 'c7ba27fdb3c6c3872f9e0c2c1ddc1b7f042d9fe8211ad0034d1dcb0e5d030bdb'


def best_scale(means, target, source_n):
    histogram = [0] * 256
    for value in means:
        require(0 <= value <= 255, 'alpha domain')
        histogram[value] += 1
    tail = [sum(histogram[c:]) for c in range(256)]
    options = [(abs(tail[c]*source_n-target*len(means)),
                Fraction(abs(128-c), c), c, 128, c) for c in range(1, 256)]
    options.append((target*len(means), Fraction(1), 256, 0, 1))
    error, _, _, numerator, denominator = min(options)
    corrected = sum(min(255, (v*numerator+denominator//2)//denominator) >= 128 for v in means)
    require(error == abs(corrected*source_n-target*len(means)), 'scale application mismatch')
    return numerator, denominator, corrected, error, histogram


def analyze_alpha(alpha, width):
    require(isinstance(width, int) and 1 < width <= 2048 and width & (width-1) == 0,
            'power-of-two width in 2..2048 required')
    require(len(alpha) == width*width and all(0 <= v <= 255 for v in alpha), 'alpha dimensions/domain')
    target, source_n = sum(v >= 128 for v in alpha), len(alpha)
    values, size, block, levels = list(alpha), width, 1, []
    while size > 1:
        next_size = size//2
        values = [values[y*2*size+x*2]+values[y*2*size+x*2+1]+
                  values[(y*2+1)*size+x*2]+values[(y*2+1)*size+x*2+1]
                  for y in range(next_size) for x in range(next_size)]
        block *= 4
        size = next_size
        means = [(value+block//2)//block for value in values]
        numerator, denominator, corrected, error, histogram = best_scale(means, target, source_n)
        divisor = source_n*len(means)
        levels.append(dict(index=len(levels)+1, width=size, texels=len(means),
                           raw_pass_texels=sum(v >= 128 for v in means),
                           corrected_pass_texels=corrected,
                           alpha_scale_numerator=numerator, alpha_scale_denominator=denominator,
                           coverage_error_numerator=error, coverage_error_denominator=divisor,
                           signed_coverage_difference=(corrected*source_n-target*len(means))/divisor,
                           raw_alpha_histogram=histogram,
                           frozen_guard_pass=size < 64 or error*1000 <= divisor))
    return dict(target_pass_texels=target, source_texels=source_n,
                all_frozen_guards_pass=all(row['frozen_guard_pass'] for row in levels), levels=levels)


def analyze_source(raw):
    require(sha(raw) == PNG_SHA, 'source PNG hash mismatch')
    width, height, rgba, filters = rgba_png(raw)
    require((width, height) == (2048, 2048) and sha(rgba) == RGBA_SHA, 'decoded source mismatch')
    result = analyze_alpha(rgba[3::4], width)
    return dict(schema='hairline69-alpha-preflight-v1',
                status='CPU_PASS_NOT_QUALITY' if result['all_frozen_guards_pass'] else 'CPU_REJECTED',
                scope='global alpha arithmetic only; no RGB filtering, image upload, rendering, local hairline, GPU, quality or source-only root-cause proof',
                source=dict(basename='short04_diffuse.png', png_sha256=sha(raw), png_bytes=len(raw),
                            decoded_rgba_sha256=sha(rgba), width=width, height=height,
                            png_row_filters=filters),
                policy=dict(algorithm='short04-coverage-mips-v1', shader_mask_cutoff=0.5,
                            alpha8_pass_minimum=128, maximum_guarded_error_numerator=1,
                            maximum_guarded_error_denominator=1000, guard_minimum_width=64), **result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = analyze_source(args.source.read_bytes())
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    except (ValueError, OSError, IndexError) as error:
        message = type(error).__name__ if isinstance(error, OSError) else str(error)
        parser.exit(2, 'preflight error: '+message+'\n')
    print(json.dumps(dict(status=report['status'], failed_levels=[row['index'] for row in report['levels'] if not row['frozen_guard_pass']])))
    return 0 if report['all_frozen_guards_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

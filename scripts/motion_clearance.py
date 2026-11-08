"""Summarize foot clearance from completed motion-review frame receipts."""
import csv
import json

NEAR_FLOOR_CM = 0.5
STABLE_CM = 0.001
FEET = ('left', 'right')


def sustained_interval(samples, key, within, minimum_samples=1):
    first = len(samples)
    while first and within(samples[first - 1][key]):
        first -= 1
    if len(samples) - first < minimum_samples:
        return None

    def point(sample):
        return {field: sample[field] for field in ('requested_seconds', 'effective_seconds', 'receipt')} | {
            'clearance_cm': sample[key],
        }

    return {
        'previous_sample': point(samples[first - 1]) if first else None,
        'first_sample': point(samples[first]),
        'sample_count': len(samples) - first,
    }


def foot_intervals(samples, foot):
    key = foot + '_cm'
    final = samples[-1][key]
    return {
        'near_floor': sustained_interval(samples, key, lambda cm: abs(cm) <= NEAR_FLOOR_CM),
        'stable_near_floor': sustained_interval(
            samples, key, lambda cm: abs(cm) <= NEAR_FLOOR_CM and abs(cm - final) <= STABLE_CM,
            minimum_samples=2,
        ),
        'final_clearance_cm': final,
    }


def clearance_svg(view, samples):
    left, top, width, height = 75, 65, 645, 215
    start, end = samples[0]['effective_seconds'], samples[-1]['effective_seconds']
    values = [sample[foot + '_cm'] for sample in samples for foot in FEET]
    low, high = min(-NEAR_FLOOR_CM, *values), max(NEAR_FLOOR_CM, *values)
    padding = (high - low) * 0.08
    low, high = low - padding, high + padding

    def x(seconds):
        return left + width * (seconds - start) / (end - start)

    def y(cm):
        return top + height * (high - cm) / (high - low)

    # View names are CLI presets or validated safe identifiers.
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="750" height="345" viewBox="0 0 750 345">',
        '<rect width="750" height="345" fill="white"/>',
        '<g font-family="sans-serif" font-size="13" fill="#243243">',
        f'<text x="22" y="29" font-size="20">Foot clearance (cm) · {view}</text>',
        '<text x="475" y="29" fill="#1c6498">● Left</text>',
        '<text x="545" y="29" fill="#aa481d">● Right</text>',
        f'<rect x="{left}" y="{y(NEAR_FLOOR_CM):.2f}" width="{width}" '
        f'height="{y(-NEAR_FLOOR_CM)-y(NEAR_FLOOR_CM):.2f}" fill="#e3f1e8"/>',
    ]
    for index in range(5):
        cm = low + index * (high - low) / 4
        row = y(cm)
        parts.append(f'<path d="M{left} {row:.2f}h{width}" stroke="#d6dde4"/>')
        parts.append(f'<text x="{left-8}" y="{row+4:.2f}" text-anchor="end">{cm:.3g}</text>')
    parts.append(f'<path d="M{left} {y(0):.2f}h{width}" stroke="#637182" stroke-dasharray="5 4"/>')
    for foot, color in zip(FEET, ('#1c6498', '#aa481d'), strict=True):
        points = [(x(sample['effective_seconds']), y(sample[foot + '_cm'])) for sample in samples]
        polyline = ' '.join(f'{px:.2f},{py:.2f}' for px, py in points)
        parts.append(f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="2"/>')
        for px, py in points:
            parts.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="2.5" fill="{color}"/>')
    parts.extend([
        f'<text x="{left}" y="300">{samples[0]["requested_seconds"]:.9g} s</text>',
        f'<text x="{left+width}" y="300" text-anchor="end">{samples[-1]["requested_seconds"]:.9g} s</text>',
        '<text x="22" y="326">Dots are captured poses. Green band spans ±0.5 cm from the floor.</text>',
        '</g></svg>',
    ])
    return '\n'.join(parts) + '\n'


def write_clearance(output, frames, sampling):
    by_view = {}
    for frame in frames:
        capture = frame['capture']
        runtime = capture['runtime']
        clearance = runtime.get('foot_clearance')
        if clearance is None:
            raise ValueError('Range analysis requires measured B1 foot clearance in each frame')
        sample = {
            'view': frame['view'],
            'requested_seconds': frame['requested_seconds'],
            'effective_seconds': runtime['seconds'],
            'left_cm': clearance['left_cm'], 'right_cm': clearance['right_cm'],
            'image': capture['image'], 'receipt': frame['receipt'],
        }
        by_view.setdefault(frame['view'], []).append(sample)

    csv_path = output / 'foot-clearance.csv'
    summary_path = output / 'foot-clearance.json'
    views = {}
    for name, samples in by_view.items():
        curve = output / f'foot-clearance-{name}.svg'
        curve.write_text(clearance_svg(name, samples), encoding='utf-8')
        views[name] = {
            'curve': str(curve), 'samples': samples,
            'feet': {foot: foot_intervals(samples, foot) for foot in FEET},
        }
    with csv_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            'view', 'requested_seconds', 'effective_seconds', 'left_cm', 'right_cm', 'image', 'receipt',
        ])
        writer.writeheader()
        for samples in by_view.values():
            writer.writerows(samples)
    summary = {
        'schema_version': 1, 'sampling': sampling, 'unit': 'cm',
        'near_floor_tolerance_cm': NEAR_FLOOR_CM, 'stable_tolerance_cm': STABLE_CM,
        'stable_min_samples': 2, 'views': views,
    }
    summary_path.write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return {'summary': str(summary_path), 'csv': str(csv_path)}

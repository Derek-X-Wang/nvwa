"""Bounded same-key CPU skin surface-crossing evidence, using actual weights.

This measures an explicit partition of the retained fixture mesh. Names choose
joint sets only; they are not evidence of anatomical correctness. A lack of
crossings is not proof of no penetration (containment/coplanarity are excluded).
"""
import argparse
import json
from pathlib import Path
import time

from evaluator import Asset, KEYS, digest, require

EPS = 1e-8
MASS = .8
GROUPS = {'left_arm_weighted': {4, 3, 2}, 'right_arm_weighted': {7, 6, 5},
          'torso_weighted': {16, 9, 8}}


def subtract(a, b):
    return [x-y for x, y in zip(a, b)]


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def segment_triangle(start, end, triangle):
    """Moller-Trumbore; strict segment and strict triangle interior only."""
    direction = subtract(end, start)
    edge1, edge2 = subtract(triangle[1], triangle[0]), subtract(triangle[2], triangle[0])
    p = cross(direction, edge2)
    det = dot(edge1, p)
    if abs(det) <= 1e-14:
        return None
    offset = subtract(start, triangle[0])
    u = dot(offset, p)/det
    if not EPS < u < 1-EPS:
        return None
    q = cross(offset, edge1)
    v = dot(direction, q)/det
    if not EPS < v or not u+v < 1-EPS:
        return None
    t = dot(edge2, q)/det
    if not EPS < t < 1-EPS:
        return None
    return [start[i]+t*direction[i] for i in range(3)]


def crossing(a, b):
    for source, target in ((a, b), (b, a)):
        for i in range(3):
            point = segment_triangle(source[i], source[(i+1) % 3], target)
            if point is not None:
                return point
    return None


def bounds(triangles):
    return ([min(t['bounds'][0][a] for t in triangles) for a in range(3)],
            [max(t['bounds'][1][a] for t in triangles) for a in range(3)])


def overlaps(a, b):
    return all(a[0][i] <= b[1][i] and b[0][i] <= a[1][i] for i in range(3))


def tree(triangles):
    box = bounds(triangles)
    if len(triangles) <= 8:
        return {'bounds': box, 'triangles': triangles}
    axis = max(range(3), key=lambda i: box[1][i]-box[0][i])
    ordered = sorted(triangles, key=lambda t: t['bounds'][0][axis]+t['bounds'][1][axis])
    half = len(ordered)//2
    return {'bounds': box, 'children': [tree(ordered[:half]), tree(ordered[half:])]}


def intersections(a, b, budget_deadline):
    count, examples, pairs = 0, [], 0
    stack = [(a, b)]
    while stack:
        x, y = stack.pop()
        pairs += 1
        if pairs % 1000 == 0:
            require(time.monotonic() < budget_deadline, 'surface bounded wall time exceeded')
        if not overlaps(x['bounds'], y['bounds']):
            continue
        if 'children' in x:
            stack.extend((c, y) for c in x['children'])
        elif 'children' in y:
            stack.extend((x, c) for c in y['children'])
        else:
            for at in x['triangles']:
                for bt in y['triangles']:
                    if overlaps(at['bounds'], bt['bounds']):
                        point = crossing(at['points'], bt['points'])
                        if point is not None:
                            count += 1
                            if len(examples) < 3:
                                examples.append({'arm_triangle': at['id'], 'torso_triangle': bt['id'], 'crossing_point_m': point})
    return {'strict_crossing_triangle_pairs': count, 'examples': examples, 'bvh_pairs_visited': pairs}


def analyze(keys=KEYS, budget_seconds=45):
    deadline = time.monotonic()+budget_seconds
    asset = Asset()
    owner = 22
    node = asset.nodes[owner]
    skin = asset.doc['skins'][node['skin']]
    primitives = asset.doc['meshes'][node['mesh']]['primitives']
    partitions = []
    counts = {name: 0 for name in GROUPS}
    for primitive_index, primitive in enumerate(primitives):
        attrs = primitive['attributes']
        joints, weights = asset.accessor(attrs['JOINTS_0']), asset.accessor(attrs['WEIGHTS_0'])
        indices = [i[0] for i in asset.accessor(primitive['indices'])]
        require(primitive.get('mode', 4) == 4 and len(indices) % 3 == 0, 'triangle mesh')
        flags = {}
        for name, joint_set in GROUPS.items():
            flags[name] = [sum(w for slot, w in zip(js, ws) if skin['joints'][slot] in joint_set) >= MASS for js, ws in zip(joints, weights)]
        for i in range(0, len(indices), 3):
            triangle = indices[i:i+3]
            for name in GROUPS:
                if all(flags[name][v] for v in triangle):
                    partitions.append((name, primitive_index, i//3, triangle))
                    counts[name] += 1
    require(all(counts.values()), 'nonempty weight partitions')
    samples = []
    for key in keys:
        require(time.monotonic() < deadline, 'surface bounded wall time exceeded')
        vertices = [asset.skin_vertices(key, owner, i) for i in range(len(primitives))]
        groups = {name: [] for name in GROUPS}
        for name, primitive, tri_index, indices in partitions:
            points = [vertices[primitive][i] for i in indices]
            groups[name].append({'id': {'mesh_node': owner, 'primitive': primitive, 'triangle_index': tri_index, 'vertex_indices': indices},
                                 'points': points,
                                 'bounds': ([min(p[a] for p in points) for a in range(3)], [max(p[a] for p in points) for a in range(3)])})
        trees = {name: tree(triangles) for name, triangles in groups.items()}
        samples.append({'key_index': key, 'time_seconds': asset.times[key], 'pairs': {
            name+'_vs_torso': intersections(trees[name], trees['torso_weighted'], deadline)
            for name in ('left_arm_weighted', 'right_arm_weighted')}})
    return {'status': 'MEASURED', 'space': 'serialized expected scene, CPU linear blend skinning', 'glb_sha256': digest(asset.path),
            'criterion': 'Noncoplanar strict triangle surface crossing between arm-weighted and torso-weighted partitions. Each triangle vertex has >=0.8 actual total skin weight in its named node-index set. Segment t and triangle barycentrics strictly interior with epsilon1e-8; determinant abs>1e-14. Weight-transition triangles excluded.',
            'joint_node_sets': {name: sorted(value) for name, value in GROUPS.items()}, 'partition_triangle_counts': counts,
            'samples': samples,
            'limits': ['not anatomical quality', 'not runtime/GPU deformation readback', 'not signed penetration depth or enclosed-volume test',
                       'coplanarity, containment, transition triangles, and lower-weight surfaces excluded; zero crossings cannot prove no intersection']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    parser.add_argument('--budget-seconds', type=float, default=45.)
    args = parser.parse_args()
    result = analyze(budget_seconds=args.budget_seconds)
    data = json.dumps(result, indent=2, allow_nan=False)+'\n'
    if args.output:
        args.output.write_text(data)
    else:
        print(data, end='')


if __name__ == '__main__':
    main()

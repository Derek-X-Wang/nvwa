"""Independent bounded-distance diagnostics, not an authoring/contact policy.

The closest point minimizes over the triangle interior and its three closed
segments. It never uses an unbounded plane as the distance to a triangle.
"""
import math


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sub(a, b):
    return [x-y for x, y in zip(a, b)]


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def norm(a):
    return math.sqrt(dot(a, a))


def interpolate(points, weights):
    return [sum(p[k]*w for p, w in zip(points, weights)) for k in range(3)]


def vector(value):
    return (isinstance(value, (list, tuple)) and len(value) == 3 and
            all(type(x) in (float, int) and math.isfinite(x) for x in value))


def closest(point, vertices):
    """Return bounded q, barycentric weights, and squared distance (binary64).

    Degenerate triangles refuse: they cannot supply an oriented face plane.
    The diagnostic must report such input, never silently remove that face.
    """
    need(vector(point) and len(vertices) == 3 and all(map(vector, vertices)),
         'nonfinite/malformed triangle query')
    a, b, c = vertices
    ab, ac = sub(b, a), sub(c, a)
    area = cross(ab, ac)
    area2 = dot(area, area)
    need(math.isfinite(area2) and area2 > 1e-24, 'degenerate triangle')
    candidates = []
    # Project onto the supporting plane only to test the bounded interior.
    ap = sub(point, a)
    v = dot(cross(ap, ac), area)/area2
    w = dot(cross(ab, ap), area)/area2
    bary = [1-v-w, v, w]
    if all(x >= 0 for x in bary):
        candidates.append((interpolate(vertices, bary), bary))
    for i, j in ((0, 1), (1, 2), (2, 0)):
        edge = sub(vertices[j], vertices[i])
        size = dot(edge, edge)
        need(size > 0, 'zero length edge')
        t = max(0., min(1., dot(sub(point, vertices[i]), edge)/size))
        bary = [0., 0., 0.]
        bary[i], bary[j] = 1-t, t
        candidates.append((interpolate(vertices, bary), bary))
    q, bary = min(candidates, key=lambda value: dot(sub(point, value[0]), sub(point, value[0])))
    return q, bary, dot(sub(point, q), sub(point, q))


def face_query(point, vertices):
    q, bary, d2 = closest(point, vertices)
    n = cross(sub(vertices[1], vertices[0]), sub(vertices[2], vertices[0]))
    n = [x/norm(n) for x in n]
    return {'point': q, 'barycentric': bary, 'distance_squared_m2': d2,
            'bounded_distance_m': math.sqrt(d2), 'normal': n,
            'supporting_plane_projection_m': dot(sub(point, q), n)}


def nearest(point, vertices, triangles, tie_m2=1e-12):
    """Exhaustive query; retain every distance tie, never the easiest face."""
    need(triangles and math.isfinite(tie_m2) and tie_m2 >= 0, 'invalid query surface/tie')
    best, hits = math.inf, []
    for ti, tri in enumerate(triangles):
        result = face_query(point, [vertices[s] for s in tri['sources']])
        d2 = result['distance_squared_m2']
        if d2 < best:
            best = d2
            hits = [hit for hit in hits if hit['distance_squared_m2'] <= best+tie_m2]
        if d2 <= best+tie_m2:
            hits.append({'triangle0': ti, **tri, **result})
    return hits


def feature(hit, epsilon=1e-10):
    active = [s for s, w in zip(hit['sources'], hit['barycentric']) if w > epsilon]
    need(active, 'missing closest feature')
    return {'kind': {1: 'vertex', 2: 'edge', 3: 'interior'}[len(active)],
            'sources': sorted(active)}


def proper_segment_crossing(p, q, vertices, epsilon=1e-9):
    """Strict segment/triangle crossing control; touching is not proper crossing.

    This proves why point clearance alone cannot replace crossing checks. It is
    not the original garment intersection gate or a complete collision detector.
    """
    need(vector(p) and vector(q), 'invalid crossing segment')
    a, b, c = vertices
    n = cross(sub(b, a), sub(c, a))
    length = norm(n)
    need(length > 1e-12, 'degenerate crossing triangle')
    n = [x/length for x in n]
    dp, dq = dot(sub(p, a), n), dot(sub(q, a), n)
    if not ((dp > epsilon and dq < -epsilon) or (dq > epsilon and dp < -epsilon)):
        return False
    t = dp/(dp-dq)
    point = [p[k]+t*(q[k]-p[k]) for k in range(3)]
    _, bary, d2 = closest(point, vertices)
    return d2 <= epsilon**2 and all(w > epsilon for w in bary)

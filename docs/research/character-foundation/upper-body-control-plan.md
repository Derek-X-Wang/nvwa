# Upper-body control experiment

The next B1 profile must preserve the shipped v6 bytes and add a new finite asset identity. Values are signed source-target weights, not centimetres or garment measurements.

First candidate group, from pinned MPFB 2.0.18 commit `d0a32e57a7f915cb2f2b95410e2117648c7bbb7e`:

- `measure-bust-circ`: chest/bust circumference; changes neighbouring torso surfaces.
- `measure-shoulder-dist`: shoulder span; check clavicle and arm attachment in neutral and raised poses.
- `measure-upperarm-circ`: bilateral upper-arm circumference; check sleeve fit and elbow transition.

These three source categories have unsided decrease and increase targets. They are candidates, not accepted controls. Before shipping, compare zero against v6 exactly, test signed endpoint geometry, inspect both front and side views, and compare shoulder/elbow/wrist bone frames under static and diagnostic poses. Reject the group if garment crossings or asymmetric joints appear. Keep hands, breast volume/position, upper-arm length, forearm, and elbow shape as later independent stages. Elbow flex is a pose, not a morphology slider.

The source catalogue lists hand scale and finger controls as separate left/right targets. A bilateral slider needs an audited merge and gripping/prop tests; adding a control with no effective visible and rig result would be misleading.

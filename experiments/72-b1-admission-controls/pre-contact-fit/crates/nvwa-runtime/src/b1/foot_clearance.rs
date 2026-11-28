use super::published_motion_frame;
use bevy::{mesh::VertexAttributeValues, prelude::*};
use serde_json::{Value, json};

// Body source IDs below the matching ankle's rest centre in the shared,
// authenticated B1 base.obj. Positive source X is the character's left.
// These masks exclude garment and joint helper vertices.
const LEFT: &[(u16, u16)] = &[
    (11411, 11415),
    (11517, 11666),
    (12368, 12818),
    (12820, 12828),
    (12830, 12831),
    (12836, 12836),
    (12839, 12840),
    (12846, 12884),
    (12886, 12921),
    (12924, 12926),
    (12928, 12931),
    (12933, 12934),
    (12936, 12938),
    (12941, 12941),
    (12943, 12944),
    (12947, 12949),
    (12951, 12953),
    (12968, 12968),
    (12970, 12970),
    (12977, 12977),
    (12986, 12986),
    (12988, 12988),
    (13015, 13024),
    (13030, 13035),
    (13037, 13331),
];
const RIGHT: &[(u16, u16)] = &[
    (4793, 4797),
    (4899, 5048),
    (5771, 6221),
    (6223, 6231),
    (6233, 6234),
    (6239, 6239),
    (6242, 6243),
    (6249, 6287),
    (6289, 6324),
    (6327, 6329),
    (6331, 6334),
    (6336, 6337),
    (6339, 6341),
    (6344, 6344),
    (6346, 6347),
    (6350, 6352),
    (6354, 6356),
    (6371, 6371),
    (6373, 6373),
    (6380, 6380),
    (6389, 6389),
    (6391, 6391),
    (6418, 6427),
    (6434, 6439),
    (6441, 6735),
];

/// Read stage geometry from a successfully published CPU frame, without a renderer.
pub fn b1_foot_clearance(world: &World) -> Result<Value, String> {
    let (active, _, _, binding) = published_motion_frame(world)?;
    let body = active
        .parts
        .iter()
        .position(|part| part.name == "body")
        .ok_or("Published B1 body is absent")?;
    let entity = active.displays[body];
    let handle = &world
        .get::<Mesh3d>(entity)
        .ok_or("B1 body display absent")?
        .0;
    let meshes = world.resource::<Assets<Mesh>>();
    let mesh = meshes.get(handle).ok_or("B1 body mesh absent")?;
    let Some(VertexAttributeValues::Float32x3(positions)) =
        mesh.attribute(Mesh::ATTRIBUTE_POSITION)
    else {
        return Err("Published body positions absent".into());
    };
    let transform = world
        .get::<GlobalTransform>(entity)
        .ok_or("B1 body transform absent")?
        .to_matrix();
    if binding.display_transforms.get(body) != Some(&transform.to_cols_array()) {
        return Err("B1 body transform differs from publication".into());
    }
    let mut left = f32::INFINITY;
    let mut right = f32::INFINITY;
    let indices = mesh.indices().ok_or("B1 body indices absent")?;
    if !indices
        .iter()
        .eq(active.display_indices[body].iter().copied())
    {
        return Err("B1 body triangles differ from publication".into());
    }
    for i in indices.iter() {
        let id = *active.source_ids[body]
            .get(i)
            .ok_or("Published B1 source ID absent")?;
        let minimum = if LEFT.iter().any(|&(lo, hi)| (lo..=hi).contains(&id)) {
            &mut left
        } else if RIGHT.iter().any(|&(lo, hi)| (lo..=hi).contains(&id)) {
            &mut right
        } else {
            continue;
        };
        let position = positions.get(i).ok_or("Published B1 foot vertex absent")?;
        let stage = transform.transform_point3(Vec3::from_array(*position));
        if !stage.is_finite() {
            return Err("Published B1 foot vertex is not finite in stage space".into());
        }
        *minimum = minimum.min(stage.y);
    }
    if !left.is_finite() || !right.is_finite() {
        return Err("Published B1 body has no visible geometry for one or both feet".into());
    }
    Ok(json!({
        "unit": "cm",
        "method": "b1_visible_body_foot_min_stage_y",
        "floor_stage_y_m": 0,
        "left_cm": f64::from(left) * 100.0,
        "right_cm": f64::from(right) * 100.0,
    }))
}

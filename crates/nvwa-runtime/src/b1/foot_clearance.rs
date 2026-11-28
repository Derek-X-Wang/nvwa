use super::{PublishedBinding, Session, published_motion_frame};
use bevy::{
    mesh::{Indices, VertexAttributeValues},
    prelude::*,
};
use humentity::prelude::ObjVertsAsset;
use serde_json::{Value, json};

// Body source IDs below the matching ankle's rest centre in the shared,
// authenticated B1 base.obj. Positive source X is the character's left.
// These masks exclude garment and joint helper vertices.
pub(super) const LEFT: &[(u16, u16)] = &[
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
pub(super) const RIGHT: &[(u16, u16)] = &[
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

pub(super) struct PublishedBody<'a> {
    positions: &'a [[f32; 3]],
    indices: &'a Indices,
    sources: &'a [u16],
    pub(super) source_vertices: &'a Handle<ObjVertsAsset>,
    transform: Mat4,
}

impl PublishedBody<'_> {
    pub(super) fn point(&self, index: usize) -> Result<Vec3, String> {
        let local = self
            .positions
            .get(index)
            .ok_or("Published B1 foot vertex absent")?;
        let stage = self.transform.transform_point3(Vec3::from_array(*local));
        if !stage.is_finite() {
            return Err("Published B1 foot vertex is not finite in stage space".into());
        }
        Ok(stage)
    }

    pub(super) fn bone_origin(&self, active: &Session, name: &str) -> Result<[f64; 3], String> {
        // These matrices are the rig frames that produced the uploaded mesh.
        let bone = active
            .last_bones
            .iter()
            .find(|bone| bone.name == name)
            .ok_or("B1 published foot-query rig landmark absent")?;
        let point = Mat4::from_cols_array(&bone.posed).w_axis.truncate();
        let stage = self.transform.transform_point3(point);
        if !stage.is_finite() {
            return Err("B1 published rig landmark is not finite in stage space".into());
        }
        Ok(stage.to_array().map(f64::from))
    }

    pub(super) fn visible_source_indices(&self) -> Result<Vec<Option<usize>>, String> {
        // The approved base.obj body's source IDs precede the joint helper vertices.
        // Use the first visible display vertex for each ID to count UV seams once.
        let mut visible = vec![None; 13380];
        for i in self.indices.iter() {
            let source = *self.sources.get(i).ok_or("Published B1 source ID absent")?;
            let slot = visible
                .get_mut(usize::from(source))
                .ok_or("Published B1 body triangle references a joint helper")?;
            *slot = Some(slot.map_or(i, |previous: usize| previous.min(i)));
        }
        Ok(visible)
    }
}

pub(super) fn published_body<'a>(
    world: &'a World,
    active: &'a Session,
    binding: &PublishedBinding,
) -> Result<PublishedBody<'a>, String> {
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
    let indices = mesh.indices().ok_or("B1 body indices absent")?;
    if !indices
        .iter()
        .eq(active.display_indices[body].iter().copied())
    {
        return Err("B1 body triangles differ from publication".into());
    }
    Ok(PublishedBody {
        positions,
        indices,
        sources: &active.source_ids[body],
        source_vertices: &active.parts[body].source_vertices,
        transform,
    })
}

/// Read stage geometry from a successfully published CPU frame, without a renderer.
pub fn b1_foot_clearance(world: &World) -> Result<Value, String> {
    let (active, _, _, binding) = published_motion_frame(world)?;
    let body = published_body(world, active, binding)?;
    let mut left = f32::INFINITY;
    let mut right = f32::INFINITY;
    for i in body.indices.iter() {
        let id = *body.sources.get(i).ok_or("Published B1 source ID absent")?;
        let minimum = if LEFT.iter().any(|&(lo, hi)| (lo..=hi).contains(&id)) {
            &mut left
        } else if RIGHT.iter().any(|&(lo, hi)| (lo..=hi).contains(&id)) {
            &mut right
        } else {
            continue;
        };
        *minimum = minimum.min(body.point(i)?.y);
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

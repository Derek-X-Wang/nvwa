//! Original diagnostic adapter around the actual Humentity ECS skeleton and mesh.
//! CPU LBS readback follows source crowd_skin.wgsl; it is not a claimed source CPU kernel.
use bevy::mesh::VertexAttributeValues;
use bevy::prelude::*;
use humentity::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct BoneRotation {
    pub bone: String,
    pub axis: [f32; 3],
    pub degrees: f32,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct DiagnosticPose {
    pub pose_id: String,
    pub rotations: Vec<BoneRotation>,
}
#[derive(Debug, Clone, Serialize)]
pub struct BoneFrame {
    pub name: String,
    pub parent: Option<String>,
    /// Column-major MakeHuman Y-up model-space matrices in metres.
    pub rest: [f32; 16],
    pub posed: [f32; 16],
    pub inverse_bind: [f32; 16],
    pub local_rest: [f32; 16],
    pub local_posed: [f32; 16],
    pub skin: [f32; 16],
    pub canonical_rest: Option<[f32; 16]>,
    pub canonical_posed: Option<[f32; 16]>,
    pub frame_gauge: Option<[f32; 16]>,
}
#[derive(Debug, Clone, Serialize)]
pub struct SkinFrame {
    /// Actual skeleton display-root global transform, removed for these model-local arrays.
    pub model_to_world: [f32; 16],
    /// Actual source reference-rig order, matching the full LOD joint indices.
    pub bones: Vec<BoneFrame>,
    pub positions: Vec<[f32; 3]>,
    pub rest_positions: Vec<[f32; 3]>,
    pub normals: Vec<[f32; 3]>,
    pub rest_normals: Vec<[f32; 3]>,
    pub tangents: Vec<[f32; 4]>,
    pub joint_indices: Vec<[u16; 4]>,
    pub joint_weights: Vec<[f32; 4]>,
    /// Original transferred influences BEFORE normalization; None on the original four-slot route.
    pub full_joint_influences: Option<Vec<Vec<(u16, f32)>>>,
}
/// Reset to the candidate's actual fitted rest, then postrotate in Blender bone-local frame.
/// Call app.update() afterwards to execute actual Bevy hierarchy propagation.
pub fn apply_pose(
    world: &mut World,
    character: Entity,
    pose: &DiagnosticPose,
) -> Result<(), String> {
    let skeleton = world
        .get::<CharacterSkeleton>(character)
        .ok_or("skeleton absent")?;
    let rig = world.resource::<RigData>().0.as_ref().ok_or("rig absent")?;
    let reference = rig.reference_rig();
    let mut rows = Vec::new();
    let rotations: BTreeMap<_, _> = pose
        .rotations
        .iter()
        .map(|r| (r.bone.as_str(), r))
        .collect();
    if rotations.len() != pose.rotations.len() {
        return Err("duplicate pose bone".into());
    }
    for rotation in &pose.rotations {
        if !reference.bone_names.contains(&rotation.bone.as_str())
            || !rotation.degrees.is_finite()
            || rotation.axis.iter().any(|x| !x.is_finite())
            || Vec3::from_array(rotation.axis).length() < 1e-6
        {
            return Err("invalid pose rotation".into());
        }
    }
    for (i, &name) in reference.bone_names.iter().enumerate() {
        let parent = &reference.bone_parents[name];
        let parent_rest = reference
            .bone_name_to_index
            .get(parent.as_str())
            .map(|i| skeleton.model_space_inv_bindposes[*i].inverse())
            .unwrap_or(Mat4::IDENTITY);
        let local = parent_rest.inverse() * skeleton.model_space_inv_bindposes[i].inverse();
        let rotation = rotations
            .get(name)
            .map(|r| {
                Quat::from_axis_angle(Vec3::from_array(r.axis).normalize(), r.degrees.to_radians())
            })
            .unwrap_or(Quat::IDENTITY);
        rows.push((
            skeleton.bone_map[name],
            Transform::from_matrix(local * Mat4::from_quat(rotation)),
        ));
    }
    for (entity, transform) in rows {
        *world
            .get_mut::<Transform>(entity)
            .ok_or("bone transform absent")? = transform;
    }
    Ok(())
}
/// Read actual propagated ECS matrices; cancel only the display skeleton-root transform.
pub fn bone_frames(world: &World, character: Entity) -> Result<Vec<BoneFrame>, String> {
    let skeleton = world
        .get::<CharacterSkeleton>(character)
        .ok_or("skeleton absent")?;
    let rig = world.resource::<RigData>().0.as_ref().ok_or("rig absent")?;
    let reference = rig.reference_rig();
    let root_inverse = world
        .get::<GlobalTransform>(skeleton.skeleton_entity)
        .ok_or("root global absent")?
        .to_matrix()
        .inverse();
    let mut frames = Vec::new();
    for (i, &name) in reference.bone_names.iter().enumerate() {
        let entity = skeleton.bone_map[name];
        let inv = skeleton.model_space_inv_bindposes[i];
        let rest = inv.inverse();
        let posed = root_inverse
            * world
                .get::<GlobalTransform>(entity)
                .ok_or("bone global absent")?
                .to_matrix();
        let parent_name = &reference.bone_parents[name];
        let parent = reference.bone_name_to_index.get(parent_name.as_str());
        let parent_rest = parent
            .map(|i| skeleton.model_space_inv_bindposes[*i].inverse())
            .unwrap_or(Mat4::IDENTITY);
        frames.push(BoneFrame {
            name: name.into(),
            parent: parent.map(|_| parent_name.clone()),
            rest: rest.to_cols_array(),
            posed: posed.to_cols_array(),
            inverse_bind: inv.to_cols_array(),
            local_rest: (parent_rest.inverse() * rest).to_cols_array(),
            local_posed: world
                .get::<Transform>(entity)
                .ok_or("bone local absent")?
                .to_matrix()
                .to_cols_array(),
            skin: (posed * inv).to_cols_array(),
            canonical_rest: None,
            canonical_posed: None,
            frame_gauge: None,
        });
    }
    Ok(frames)
}
/// Evaluate the actual built mesh's four influences after its single diagnostic morph.
/// Position/normal/tangent formulas mirror Humentity's source shader; the separate
/// Python comparator independently evaluates candidate-weight arithmetic in f64.
pub fn skin_mesh_frame(world: &World, character: Entity, mesh: &Mesh) -> Result<SkinFrame, String> {
    let bones = bone_frames(world, character)?;
    let base = get_vertex_positions(mesh);
    let morph = mesh.morph_targets().ok_or("morph absent")?;
    if morph.len() != base.len() {
        return Err("expected exactly one morph".into());
    }
    let joint_indices = match mesh.attribute(Mesh::ATTRIBUTE_JOINT_INDEX) {
        Some(VertexAttributeValues::Uint16x4(v)) => v.clone(),
        _ => return Err("joint indices absent".into()),
    };
    let joint_weights = match mesh.attribute(Mesh::ATTRIBUTE_JOINT_WEIGHT) {
        Some(VertexAttributeValues::Float32x4(v)) => v.clone(),
        _ => return Err("joint weights absent".into()),
    };
    let base_normals = match mesh.attribute(Mesh::ATTRIBUTE_NORMAL) {
        Some(VertexAttributeValues::Float32x3(v)) => {
            v.iter().copied().map(Vec3::from_array).collect::<Vec<_>>()
        }
        _ => return Err("normals absent".into()),
    };
    let base_tangents = match mesh.attribute(Mesh::ATTRIBUTE_TANGENT) {
        Some(VertexAttributeValues::Float32x4(v)) => v,
        _ => return Err("tangents absent".into()),
    };
    let mut positions = Vec::new();
    let mut rest_positions = Vec::new();
    let mut normals = Vec::new();
    let mut rest_normals = Vec::new();
    let mut tangents = Vec::new();
    for i in 0..base.len() {
        let skin = blend_skin_matrix(
            &bones,
            joint_indices[i].iter().copied().zip(joint_weights[i]),
        )?;
        let p = base[i] + morph[i].position;
        let n = base_normals[i] + morph[i].normal;
        let t = Vec3::from_array([
            base_tangents[i][0],
            base_tangents[i][1],
            base_tangents[i][2],
        ]) + morph[i].tangent;
        rest_positions.push(p.to_array());
        positions.push(skin.transform_point3(p).to_array());
        rest_normals.push(n.to_array());
        normals.push(skin.transform_vector3(n).normalize_or_zero().to_array());
        let tangent = skin.transform_vector3(t).normalize_or_zero();
        tangents.push([tangent.x, tangent.y, tangent.z, base_tangents[i][3]]);
    }
    let skeleton = world
        .get::<CharacterSkeleton>(character)
        .ok_or("skeleton absent")?;
    let model_to_world = world
        .get::<GlobalTransform>(skeleton.skeleton_entity)
        .ok_or("root global absent")?
        .to_matrix()
        .to_cols_array();
    Ok(SkinFrame {
        model_to_world,
        bones,
        positions,
        rest_positions,
        normals,
        rest_normals,
        tangents,
        joint_indices,
        joint_weights,
        full_joint_influences: None,
    })
}

/// Source-derived change of each bone-local frame, Q = F^-1 C.
pub fn canonical_frame_gauges(world: &World, character: Entity) -> Result<Vec<Mat4>, String> {
    let shape = world
        .get::<CharacterShape>(character)
        .ok_or("shape absent")?;
    let shapes = world.resource::<Assets<CharacterShapeAsset>>();
    let shape = shapes.get(&shape.0).ok_or("shape asset absent")?;
    let template = world
        .resource::<Assets<CharacterTemplate>>()
        .get(&shape.template)
        .ok_or("template absent")?;
    let helpers = template.blend_helpers(
        &shape.template_morph_targets,
        &world.resource::<BaseMesh>().vertices,
    );
    let rig = world.resource::<RigData>().0.as_ref().ok_or("rig absent")?;
    let fitted = rig.endpoint_roll_frames(&helpers, world.resource::<VertexGroups>());
    let skeleton = world
        .get::<CharacterSkeleton>(character)
        .ok_or("skeleton absent")?;
    Ok(fitted
        .iter()
        .zip(&skeleton.model_space_inv_bindposes)
        .map(|(f, ibm)| f.inverse() * ibm.inverse())
        .collect())
}
/// Canonical Blender-local postrotation expressed in the actual fixed candidate frame.
pub fn apply_pose_canonical(
    world: &mut World,
    character: Entity,
    pose: &DiagnosticPose,
) -> Result<(), String> {
    // Reuse validation/reset before replacing the diagnostic rotations with conjugates.
    apply_pose(world, character, pose)?;
    let gauges = canonical_frame_gauges(world, character)?;
    let rig = world.resource::<RigData>().0.as_ref().ok_or("rig absent")?;
    let skeleton = world
        .get::<CharacterSkeleton>(character)
        .ok_or("skeleton absent")?;
    let mut rows = Vec::new();
    let mut seen = std::collections::BTreeSet::new();
    for r in &pose.rotations {
        if !seen.insert(&r.bone)
            || !r.degrees.is_finite()
            || r.axis.iter().any(|x| !x.is_finite())
            || Vec3::from_array(r.axis).length() < 1e-6
        {
            return Err("invalid canonical pose".into());
        }
        let i = rig
            .bone_index(&r.bone)
            .ok_or("canonical pose bone absent")?;
        let entity = skeleton.bone_map[r.bone.as_str()];
        let local = world
            .get::<Transform>(entity)
            .ok_or("bone local absent")?
            .to_matrix();
        let rotation = Mat4::from_quat(Quat::from_axis_angle(
            Vec3::from_array(r.axis).normalize(),
            r.degrees.to_radians(),
        ));
        rows.push((
            entity,
            Transform::from_matrix(
                local * rotation.inverse() * gauges[i].inverse() * rotation * gauges[i],
            ),
        ));
    }
    for (entity, transform) in rows {
        *world
            .get_mut::<Transform>(entity)
            .ok_or("bone local absent")? = transform;
    }
    Ok(())
}
/// Preserve raw candidate frames and expose the source-derived canonical gauge.
pub fn skin_mesh_frame_canonical(
    world: &World,
    character: Entity,
    mesh: &Mesh,
) -> Result<SkinFrame, String> {
    let mut frame = skin_mesh_frame(world, character, mesh)?;
    let gauges = canonical_frame_gauges(world, character)?;
    for (bone, q) in frame.bones.iter_mut().zip(gauges) {
        bone.canonical_rest =
            Some((Mat4::from_cols_array(&bone.rest) * q.inverse()).to_cols_array());
        bone.canonical_posed =
            Some((Mat4::from_cols_array(&bone.posed) * q.inverse()).to_cols_array());
        bone.frame_gauge = Some(q.to_cols_array());
    }
    Ok(frame)
}

fn blend_skin_matrix(
    bones: &[BoneFrame],
    influences: impl IntoIterator<Item = (u16, f32)>,
) -> Result<Mat4, String> {
    let mut skin = Mat4::ZERO;
    for (joint, weight) in influences {
        let bone = bones
            .get(joint as usize)
            .ok_or("joint index out of range")?;
        skin += Mat4::from_cols_array(&bone.skin) * weight;
    }
    Ok(skin)
}
/// Original Humentity helper-to-proxy weight transfer, before top-four truncation.
/// It reads only candidate RigWeights/Mhclo data. Every positive final aggregate is retained before normalization; signed nonpositive aggregates are omitted.
pub fn full_proxy_influences(
    world: &World,
    mhclo: &MhcloAsset,
    source_ids: &[u16],
) -> Result<Vec<Vec<(u16, f32)>>, String> {
    let rig = world.resource::<RigData>().0.as_ref().ok_or("rig absent")?;
    let names = &rig.reference_rig().bone_names;
    let weights = rig.original_weights();
    let mut result = Vec::with_capacity(source_ids.len());
    for &source_id in source_ids {
        let helper = mhclo
            .helper_map
            .get(source_id as usize)
            .ok_or("source id absent from Mhclo")?;
        let mut influences = Vec::new();
        for (i, &name) in names.iter().enumerate() {
            let Some(bone_weights) = weights.get(name) else {
                continue;
            };
            let mut weight = 0.0;
            match helper {
                MhcloVertexMap::SingleVertex(vertex) => {
                    if let Some(&w) = bone_weights.get(vertex)
                        && w > 0.0
                    {
                        weight = w;
                    }
                }
                MhcloVertexMap::Triangle {
                    helper_verts,
                    helper_weights,
                    ..
                } => {
                    for k in 0..3 {
                        if let Some(&w) = bone_weights.get(&helper_verts[k])
                            && w > 0.0
                        {
                            weight += w * helper_weights[k];
                        }
                    }
                }
            }
            if weight > 0.0 {
                influences.push((i as u16, weight));
            }
        }
        result.push(influences);
    }
    Ok(result)
}
/// Additive full-weight CPU contrast. Requires apply_pose_canonical then propagation.
/// Uses identical source-derived bones/morph data and the shared Rust LBS arithmetic.
pub fn skin_mesh_frame_full_weights(
    world: &World,
    character: Entity,
    mesh: &Mesh,
    mhclo: &MhcloAsset,
    source_ids: &[u16],
) -> Result<SkinFrame, String> {
    let mut frame = skin_mesh_frame_canonical(world, character, mesh)?;
    if source_ids.len() != frame.positions.len() {
        return Err("full influence source mapping length mismatch".into());
    }
    let influences = full_proxy_influences(world, mhclo, source_ids)?;
    let morph = mesh.morph_targets().ok_or("morph absent")?;
    let base_tangents = match mesh.attribute(Mesh::ATTRIBUTE_TANGENT) {
        Some(VertexAttributeValues::Float32x4(v)) => v,
        _ => return Err("tangents absent".into()),
    };
    for (i, row) in influences.iter().enumerate() {
        let sum: f32 = row.iter().map(|(_, w)| *w).sum();
        if !sum.is_finite() || sum <= 0.0 {
            return Err("nonpositive full influence sum".into());
        }
        let skin = blend_skin_matrix(&frame.bones, row.iter().map(|(j, w)| (*j, *w / sum)))?;
        frame.positions[i] = skin
            .transform_point3(Vec3::from_array(frame.rest_positions[i]))
            .to_array();
        frame.normals[i] = skin
            .transform_vector3(Vec3::from_array(frame.rest_normals[i]))
            .normalize_or_zero()
            .to_array();
        let tangent = Vec3::from_array([
            base_tangents[i][0],
            base_tangents[i][1],
            base_tangents[i][2],
        ]) + morph[i].tangent;
        let tangent = skin.transform_vector3(tangent).normalize_or_zero();
        frame.tangents[i] = [tangent.x, tangent.y, tangent.z, base_tangents[i][3]];
    }
    frame.full_joint_influences = Some(influences);
    Ok(frame)
}

/// Product-owned copies of the approved authored diagnostic poses.
pub mod poses;

pub mod motion;

/// Fitted canonical frames cached for one shape, never rebuilt by the frame clock.
pub struct PreparedRig {
    rows: Vec<(String, Entity, Mat4, Mat4)>,
}
impl PreparedRig {
    pub fn new(world: &World, character: Entity) -> Result<Self, String> {
        let frames = bone_frames(world, character)?;
        let gauges = canonical_frame_gauges(world, character)?;
        let skeleton = world
            .get::<CharacterSkeleton>(character)
            .ok_or("skeleton absent")?;
        Ok(Self {
            rows: frames
                .iter()
                .zip(gauges)
                .map(|(b, q)| {
                    (
                        b.name.clone(),
                        skeleton.bone_map[b.name.as_str()],
                        Mat4::from_cols_array(&b.local_rest),
                        q,
                    )
                })
                .collect(),
        })
    }
    pub fn apply(&self, world: &mut World, pose: &DiagnosticPose) -> Result<(), String> {
        let mut rotations = BTreeMap::new();
        for r in &pose.rotations {
            let axis = Vec3::from_array(r.axis);
            if !r.degrees.is_finite()
                || !axis.is_finite()
                || axis.length() < 1e-6
                || !self.rows.iter().any(|(n, ..)| n == &r.bone)
                || rotations.insert(r.bone.as_str(), r).is_some()
            {
                return Err("invalid prepared canonical pose".into());
            }
        }
        let rows: Vec<_> = self
            .rows
            .iter()
            .map(|(name, entity, rest, gauge)| {
                let rotation = rotations
                    .get(name.as_str())
                    .map(|r| {
                        Mat4::from_quat(Quat::from_axis_angle(
                            Vec3::from_array(r.axis).normalize(),
                            r.degrees.to_radians(),
                        ))
                    })
                    .unwrap_or(Mat4::IDENTITY);
                (
                    *entity,
                    Transform::from_matrix(if rotation == Mat4::IDENTITY {
                        *rest
                    } else {
                        *rest * gauge.inverse() * rotation * *gauge
                    }),
                )
            })
            .collect();
        for (entity, transform) in rows {
            *world
                .get_mut::<Transform>(entity)
                .ok_or("bone transform absent")? = transform;
        }
        Ok(())
    }
    pub fn frames(&self, world: &World, character: Entity) -> Result<Vec<BoneFrame>, String> {
        let mut frames = bone_frames(world, character)?;
        if frames.len() != self.rows.len() {
            return Err("prepared bone count mismatch".into());
        }
        for (bone, (_, _, _, q)) in frames.iter_mut().zip(&self.rows) {
            bone.canonical_rest =
                Some((Mat4::from_cols_array(&bone.rest) * q.inverse()).to_cols_array());
            bone.canonical_posed =
                Some((Mat4::from_cols_array(&bone.posed) * q.inverse()).to_cols_array());
            bone.frame_gauge = Some(q.to_cols_array());
        }
        Ok(frames)
    }
}

/// Complete fitted morph and full positive influence data shared by every frame.
pub struct PreparedSkin {
    frame: SkinFrame,
    rest_tangents: Vec<[f32; 4]>,
    normalized: Vec<Vec<(u16, f32)>>,
}
impl PreparedSkin {
    pub fn new(
        world: &World,
        character: Entity,
        mesh: &Mesh,
        mapping: &MhcloAsset,
        ids: &[u16],
    ) -> Result<Self, String> {
        let frame = skin_mesh_frame_full_weights(world, character, mesh, mapping, ids)?;
        let influences = frame
            .full_joint_influences
            .as_ref()
            .ok_or("full influences absent")?;
        let normalized = influences
            .iter()
            .map(|row| {
                let sum: f32 = row.iter().map(|(_, w)| *w).sum();
                row.iter().map(|(j, w)| (*j, *w / sum)).collect()
            })
            .collect();
        let morph = mesh.morph_targets().ok_or("morph absent")?;
        let base = match mesh.attribute(Mesh::ATTRIBUTE_TANGENT) {
            Some(VertexAttributeValues::Float32x4(v)) => v,
            _ => return Err("tangents absent".into()),
        };
        let rest_tangents = base
            .iter()
            .zip(morph)
            .map(|(t, m)| {
                [
                    t[0] + m.tangent.x,
                    t[1] + m.tangent.y,
                    t[2] + m.tangent.z,
                    t[3],
                ]
            })
            .collect();
        Ok(Self {
            frame,
            rest_tangents,
            normalized,
        })
    }
    pub fn evaluate(&self, bones: &[BoneFrame]) -> Result<SkinFrame, String> {
        let mut frame = self.frame.clone();
        frame.bones = bones.to_vec();
        for (i, row) in self.normalized.iter().enumerate() {
            let skin = blend_skin_matrix(bones, row.iter().copied())?;
            frame.positions[i] = skin
                .transform_point3(Vec3::from_array(frame.rest_positions[i]))
                .to_array();
            frame.normals[i] = skin
                .transform_vector3(Vec3::from_array(frame.rest_normals[i]))
                .normalize_or_zero()
                .to_array();
            let rest = self.rest_tangents[i];
            let tangent = skin
                .transform_vector3(Vec3::new(rest[0], rest[1], rest[2]))
                .normalize_or_zero();
            frame.tangents[i] = [tangent.x, tangent.y, tangent.z, rest[3]];
        }
        if frame
            .positions
            .iter()
            .flatten()
            .chain(frame.normals.iter().flatten())
            .chain(frame.tangents.iter().flatten())
            .any(|v| !v.is_finite())
            || bones.iter().flat_map(|b| b.posed).any(|v| !v.is_finite())
        {
            return Err("nonfinite full-positive skin frame".into());
        }
        Ok(frame)
    }
}

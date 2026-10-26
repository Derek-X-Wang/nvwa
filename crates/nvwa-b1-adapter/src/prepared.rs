use super::*;

/// Fitted B1 rigid rotations cached for one shape, never rebuilt by the frame clock.
/// Internal bone scale is one; character display scale belongs to the skeleton root.
pub struct PreparedRig {
    rows: Vec<PreparedBone>,
}

struct PreparedBone {
    name: String,
    entity: Entity,
    translation: Vec3,
    rest_rotation: Quat,
    gauge_rotation: Quat,
}

// This guards decoded construction roundoff, not authored scale intent or output
// acceptance. Exact source scale and inverse-bind checks establish that intent.
const CONSTRUCTION_ROUNDOFF: f32 = 2e-5;

fn rigid_rotation(matrix: Mat4) -> Result<Quat, String> {
    let axes = [matrix.x_axis, matrix.y_axis, matrix.z_axis];
    if !matrix.is_finite()
        || axes.iter().any(|axis| axis.w.abs() > CONSTRUCTION_ROUNDOFF)
        || (matrix.w_axis.w - 1.0).abs() > CONSTRUCTION_ROUNDOFF
    {
        return Err("invalid prepared rigid frame".into());
    }
    let basis = Mat3::from_mat4(matrix);
    let gram = basis.transpose() * basis;
    if gram
        .to_cols_array()
        .iter()
        .zip(Mat3::IDENTITY.to_cols_array())
        .any(|(a, b)| (a - b).abs() > CONSTRUCTION_ROUNDOFF)
        || (basis.determinant() - 1.0).abs() > CONSTRUCTION_ROUNDOFF
    {
        return Err("nonrigid prepared frame".into());
    }
    let rotation = Quat::from_mat3(&basis).normalize();
    if !rotation.is_finite() {
        return Err("invalid prepared frame rotation".into());
    }
    Ok(rotation)
}

fn supported_reference(name: &str, count: usize) -> Result<(), String> {
    if name != "game_engine" || count != 53 {
        return Err("prepared rig requires the full B1 game_engine construction".into());
    }
    Ok(())
}

fn model_rotation(reference: Transform, fitted: Mat4, inverse_bind: Mat4) -> Result<Quat, String> {
    // Humentity rigs.rs::fitted_model_space_bindposes creates these transforms
    // from a fitted head position and the reference rotation, with scale ONE.
    // game_engine has no default-rig toe rewrite. Reconstruct the SAME f32
    // inverse bind, before normalizing anything. An epsilon cannot distinguish
    // an authored tiny scale from roundoff: even a one-bit bind change fails.
    if reference.scale != Vec3::ONE
        || !reference.translation.is_finite()
        || !reference.rotation.is_finite()
        || (reference.rotation.length_squared() - 1.0).abs() > CONSTRUCTION_ROUNDOFF
    {
        return Err("unsupported prepared reference scale or rotation".into());
    }
    rigid_rotation(fitted)?;
    rigid_rotation(inverse_bind)?;
    let source_model = Transform::from_translation(fitted.w_axis.truncate())
        .with_rotation(reference.rotation)
        .to_matrix();
    if source_model.inverse() != inverse_bind {
        return Err("prepared inverse bind differs from unit-scale B1 construction".into());
    }
    Ok(reference.rotation.normalize())
}

impl PreparedRig {
    pub fn new(world: &World, character: Entity) -> Result<Self, String> {
        let rig = world
            .get_resource::<RigData>()
            .and_then(|rig| rig.0.as_ref())
            .ok_or("rig absent")?;
        let reference = rig.reference_rig();
        supported_reference(&reference.rig_name, reference.bone_names.len())?;
        let skeleton = world
            .get::<CharacterSkeleton>(character)
            .ok_or("skeleton absent")?;
        if skeleton.model_space_inv_bindposes.len() != reference.bone_names.len()
            || skeleton.bone_map.len() != reference.bone_names.len()
        {
            return Err("prepared bone coverage mismatch".into());
        }
        // Match the helper/head construction used by the fitted skeleton.
        let shape = world
            .get::<CharacterShape>(character)
            .ok_or("shape absent")?;
        let shapes = world.resource::<Assets<CharacterShapeAsset>>();
        let shape = shapes.get(&shape.0).ok_or("shape asset absent")?;
        let templates = world.resource::<Assets<CharacterTemplate>>();
        let template = templates.get(&shape.template).ok_or("template absent")?;
        let helpers = template.blend_helpers(
            &shape.template_morph_targets,
            &world.resource::<BaseMesh>().vertices,
        );
        let fitted = rig.endpoint_roll_frames(&helpers, world.resource::<VertexGroups>());
        if fitted.len() != reference.bone_names.len() {
            return Err("prepared fitted frame count mismatch".into());
        }
        let mut model_rotations = BTreeMap::new();
        for (i, &name) in reference.bone_names.iter().enumerate() {
            let source = reference
                .model_space_bindpose
                .get(name)
                .ok_or("prepared reference frame absent")?;
            let entity = skeleton.bone_map.get(name).ok_or("prepared bone absent")?;
            if world.get::<Transform>(*entity).is_none()
                || world.get::<GlobalTransform>(*entity).is_none()
                || !reference.bone_parents.contains_key(name)
                || reference.bone_name_to_index.get(name) != Some(&i)
            {
                return Err("prepared bone binding absent or inconsistent".into());
            }
            model_rotations.insert(
                name,
                model_rotation(*source, fitted[i], skeleton.model_space_inv_bindposes[i])?,
            );
        }
        let frames = bone_frames(world, character)?;
        let mut rows = Vec::with_capacity(frames.len());
        for (i, bone) in frames.iter().enumerate() {
            let rest = Mat4::from_cols_array(&bone.local_rest);
            rigid_rotation(rest)?;
            let model = model_rotations[bone.name.as_str()];
            let parent_name = reference.bone_parents[bone.name.as_str()].as_str();
            let parent = if parent_name == "Human.rig" {
                Quat::IDENTITY
            } else {
                *model_rotations
                    .get(parent_name)
                    .ok_or("prepared parent absent")?
            };
            let fitted_rotation = rigid_rotation(fitted[i])?;
            rows.push(PreparedBone {
                name: bone.name.clone(),
                entity: skeleton.bone_map[bone.name.as_str()],
                // Keep the original recovered rest translation, including root.
                translation: rest.w_axis.truncate(),
                rest_rotation: (parent.conjugate() * model).normalize(),
                gauge_rotation: (fitted_rotation.conjugate() * model).normalize(),
            });
        }
        Ok(Self { rows })
    }

    pub fn apply(&self, world: &mut World, pose: &DiagnosticPose) -> Result<(), String> {
        let mut rotations = BTreeMap::new();
        for r in &pose.rotations {
            let axis = Vec3::from_array(r.axis);
            let length = axis.length();
            if !r.degrees.is_finite()
                || !axis.is_finite()
                || !length.is_finite()
                || length < 1e-6
                || !self.rows.iter().any(|row| row.name == r.bone)
                || rotations.contains_key(r.bone.as_str())
            {
                return Err("invalid prepared canonical pose".into());
            }
            let rotation = Quat::from_axis_angle(axis / length, r.degrees.to_radians());
            if !rotation.is_finite() {
                return Err("invalid prepared canonical pose rotation".into());
            }
            rotations.insert(r.bone.as_str(), rotation.normalize());
        }
        // Validate every target before any writes. Invalid input or a missing
        // component must leave the entire previous pose intact.
        for row in &self.rows {
            if world.get::<Transform>(row.entity).is_none() {
                return Err("bone transform absent".into());
            }
        }
        for row in &self.rows {
            let rotation = rotations
                .get(row.name.as_str())
                .filter(|rotation| **rotation != Quat::IDENTITY)
                .map(|rotation| {
                    (row.rest_rotation
                        * row.gauge_rotation.conjugate()
                        * *rotation
                        * row.gauge_rotation)
                        .normalize()
                })
                .unwrap_or(row.rest_rotation);
            *world.get_mut::<Transform>(row.entity).unwrap() = Transform {
                translation: row.translation,
                rotation,
                scale: Vec3::ONE,
            };
        }
        Ok(())
    }

    pub fn frames(&self, world: &World, character: Entity) -> Result<Vec<BoneFrame>, String> {
        let mut frames = bone_frames(world, character)?;
        if frames.len() != self.rows.len() {
            return Err("prepared bone count mismatch".into());
        }
        for (bone, row) in frames.iter_mut().zip(&self.rows) {
            if bone.name != row.name {
                return Err("prepared bone order mismatch".into());
            }
            let gauge = Mat4::from_quat(row.gauge_rotation);
            let inverse = Mat4::from_quat(row.gauge_rotation.conjugate());
            bone.canonical_rest =
                Some((Mat4::from_cols_array(&bone.rest) * inverse).to_cols_array());
            bone.canonical_posed =
                Some((Mat4::from_cols_array(&bone.posed) * inverse).to_cols_array());
            bone.frame_gauge = Some(gauge.to_cols_array());
        }
        Ok(frames)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture() -> (World, PreparedRig) {
        let mut world = World::new();
        let rows = ["parent", "child"]
            .into_iter()
            .enumerate()
            .map(|(i, name)| PreparedBone {
                name: name.into(),
                entity: world.spawn(Transform::from_xyz(9.0, 8.0, 7.0)).id(),
                translation: Vec3::new(0.12, 0.3 + i as f32, -0.2),
                rest_rotation: Quat::from_euler(EulerRot::XYZ, 0.3, -0.4, 0.6).normalize(),
                gauge_rotation: Quat::from_euler(EulerRot::XYZ, -0.7, 0.2, 0.8).normalize(),
            })
            .collect();
        (world, PreparedRig { rows })
    }

    fn pose(rotations: Vec<BoneRotation>) -> DiagnosticPose {
        DiagnosticPose {
            pose_id: "test".into(),
            rotations,
        }
    }

    fn rotation(bone: &str, axis: [f32; 3], degrees: f32) -> BoneRotation {
        BoneRotation {
            bone: bone.into(),
            axis,
            degrees,
        }
    }

    fn transforms(world: &World, rig: &PreparedRig) -> Vec<Transform> {
        rig.rows
            .iter()
            .map(|row| *world.get::<Transform>(row.entity).unwrap())
            .collect()
    }

    #[test]
    fn prepared_construction_rejects_unknown_and_scale_bearing_reference() {
        assert!(supported_reference("game_engine", 53).is_ok());
        assert!(supported_reference("default", 53).is_err());
        assert!(supported_reference("game_engine", 52).is_err());
        let reference = Transform::from_rotation(Quat::from_rotation_y(0.7));
        let fitted =
            Mat4::from_rotation_translation(Quat::from_rotation_z(0.2), Vec3::new(0.1, 1.2, -0.3));
        let source =
            Transform::from_translation(fitted.w_axis.truncate()).with_rotation(reference.rotation);
        let inverse_bind = source.to_matrix().inverse();
        assert!(model_rotation(reference, fitted, inverse_bind).is_ok());

        // A deliberately authored scale smaller than the roundoff guard must
        // still fail. The exact source contract, not the tolerance, rejects it.
        let tiny_scale = f32::from_bits(1.0_f32.to_bits() + 1);
        for scale in [Vec3::splat(tiny_scale), Vec3::new(1.1, 0.9, 1.0)] {
            assert!(model_rotation(reference.with_scale(scale), fitted, inverse_bind).is_err());
            assert!(
                model_rotation(
                    reference,
                    fitted,
                    source.with_scale(scale).to_matrix().inverse()
                )
                .is_err()
            );
        }
    }

    #[test]
    fn prepared_construction_rejects_shear_reflection_singular_and_nonfinite() {
        let mut shear = Mat4::IDENTITY;
        shear.y_axis.x = 0.01;
        let mut nonfinite = Mat4::IDENTITY;
        nonfinite.x_axis.x = f32::NAN;
        let mut projective = Mat4::IDENTITY;
        projective.x_axis.w = 0.01;
        for invalid in [
            shear,
            Mat4::from_scale(Vec3::new(-1.0, 1.0, 1.0)),
            Mat4::from_scale(Vec3::new(0.0, 1.0, 1.0)),
            nonfinite,
            projective,
        ] {
            assert!(rigid_rotation(invalid).is_err());
            assert!(model_rotation(Transform::IDENTITY, invalid, Mat4::IDENTITY).is_err());
            assert!(model_rotation(Transform::IDENTITY, Mat4::IDENTITY, invalid).is_err());
        }
        // Even a shear below the numerical guard cannot alter the stored bind.
        let mut tiny_shear = Mat4::IDENTITY;
        tiny_shear.y_axis.x = 1e-7;
        assert!(rigid_rotation(tiny_shear).is_ok());
        assert!(model_rotation(Transform::IDENTITY, Mat4::IDENTITY, tiny_shear).is_err());
    }

    #[test]
    fn prepared_apply_keeps_order_translation_unit_scale_and_cached_rest() {
        let (mut world, rig) = fixture();
        let display = world
            .spawn(Transform::from_xyz(4.0, -2.0, 3.0).with_scale(Vec3::splat(1.7)))
            .id();
        let display_before = *world.get::<Transform>(display).unwrap();
        let input = pose(vec![rotation("child", [1.0, 2.0, -3.0], 71.0)]);
        rig.apply(&mut world, &input).unwrap();
        let row = &rig.rows[1];
        let actual = *world.get::<Transform>(row.entity).unwrap();
        let delta =
            Quat::from_axis_angle(Vec3::new(1.0, 2.0, -3.0).normalize(), 71_f32.to_radians());
        let expected = Mat4::from_quat(row.rest_rotation)
            * Mat4::from_quat(row.gauge_rotation.conjugate())
            * Mat4::from_quat(delta)
            * Mat4::from_quat(row.gauge_rotation);
        for (a, b) in Mat4::from_quat(actual.rotation)
            .to_cols_array()
            .iter()
            .zip(expected.to_cols_array())
        {
            assert!(
                (a - b).abs() < 1e-6,
                "canonical multiplication order changed"
            );
        }
        assert_eq!(actual.translation, row.translation);
        assert_eq!(actual.scale, Vec3::ONE);
        assert!((actual.rotation.length_squared() - 1.0).abs() < 3e-7);
        assert_eq!(*world.get::<Transform>(display).unwrap(), display_before);
        let first = transforms(&world, &rig);
        rig.apply(&mut world, &input).unwrap();
        assert_eq!(transforms(&world, &rig), first, "poses must not integrate");
        rig.apply(&mut world, &pose(Vec::new())).unwrap();
        for row in &rig.rows {
            let actual = world.get::<Transform>(row.entity).unwrap();
            assert_eq!(actual.rotation, row.rest_rotation);
            assert_eq!(actual.translation, row.translation);
            assert_eq!(actual.scale, Vec3::ONE);
        }
    }

    #[test]
    fn prepared_apply_rejects_invalid_pose_atomically() {
        let (mut world, rig) = fixture();
        let valid = rotation("parent", [1.0, 0.0, 0.0], 20.0);
        let before = transforms(&world, &rig);
        for invalid in [
            rotation("absent", [1.0, 0.0, 0.0], 10.0),
            rotation("child", [0.0, 0.0, 0.0], 10.0),
            rotation("child", [f32::NAN, 0.0, 0.0], 10.0),
            rotation("child", [f32::INFINITY, 0.0, 0.0], 10.0),
            rotation("child", [f32::MAX, f32::MAX, 0.0], 10.0),
            rotation("child", [1.0, 0.0, 0.0], f32::NAN),
            rotation("child", [1.0, 0.0, 0.0], f32::INFINITY),
            valid.clone(),
        ] {
            assert!(
                rig.apply(&mut world, &pose(vec![valid.clone(), invalid]))
                    .is_err()
            );
            assert_eq!(transforms(&world, &rig), before);
        }
        // A valid first row must not be written before a later missing target.
        world.entity_mut(rig.rows[1].entity).remove::<Transform>();
        assert!(rig.apply(&mut world, &pose(vec![valid])).is_err());
        assert_eq!(
            *world.get::<Transform>(rig.rows[0].entity).unwrap(),
            before[0]
        );
    }
}

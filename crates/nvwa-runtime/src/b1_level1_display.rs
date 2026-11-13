//! Optional display-only Level 1 surface. The original skinned body stays the
//! authoritative publication and CPU readback; this mesh can be switched off.
use super::level1_geometry::{Level1Plan, Level1Workspace};
use super::*;
use bevy::mesh::{PrimitiveTopology, VertexAttributeValues};

/// Opt-in visual subdivision for B1. Changing this resource at runtime is safe;
/// `false` restores the original mesh on the next PostUpdate.
#[derive(Resource, Default, Clone, Copy)]
pub struct B1DisplaySubdivision {
    pub enabled: bool,
}

#[derive(Resource, Default, Clone)]
pub struct B1DisplaySubdivisionStatus {
    pub active: bool,
    pub error: Option<String>,
    pub vertices: usize,
    pub triangles: usize,
}

#[derive(Resource, Default)]
pub(super) struct Level1DisplayState(pub(super) Option<Overlay>, Option<(Entity, u64, String)>);

pub(super) struct Overlay {
    owner: Entity,
    original: Handle<Mesh>,
    original_visibility: Option<Visibility>,
    pub(super) entity: Entity,
    pub(super) mesh: Handle<Mesh>,
    plan: Level1Plan,
    work: Level1Workspace,
    cage: Vec<Vec3>,
    ids: Vec<u16>,
    lookup: Vec<usize>,
    render_geometry_ids: Vec<usize>,
    pub(super) last_serial: u64,
    triangle_count: usize,
}

impl Level1DisplayState {
    fn clear(&mut self, world: &mut World) {
        if let Some(overlay) = self.0.take() {
            let _ = world.despawn(overlay.entity);
            world
                .resource_mut::<Assets<Mesh>>()
                .remove(overlay.mesh.id());
            if let Ok(mut body) = world.get_entity_mut(overlay.owner) {
                if let Some(visibility) = overlay.original_visibility {
                    body.insert(visibility);
                } else {
                    body.remove::<Visibility>();
                }
            }
        }
    }
}

fn uv_values(mesh: &Mesh) -> Result<&[[f32; 2]], String> {
    match mesh.attribute(Mesh::ATTRIBUTE_UV_0) {
        Some(VertexAttributeValues::Float32x2(values))
            if values.iter().flatten().all(|v| v.is_finite()) =>
        {
            Ok(values)
        }
        _ => Err("B1 Level 1 requires finite source UV_0".into()),
    }
}

fn midpoint(a: [f32; 2], b: [f32; 2]) -> [f32; 2] {
    [(a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5]
}

fn gather_cage(
    ids: &[u16],
    lookup: &[usize],
    positions: &[[f32; 3]],
    cage: &mut [Vec3],
) -> Result<(), String> {
    if positions.len() != ids.len() || cage.len() != lookup.len() {
        return Err("B1 Level 1 source position/ID coverage changed".into());
    }
    for (dst, &src) in cage.iter_mut().zip(lookup) {
        *dst = Vec3::from_array(*positions.get(src).ok_or("B1 source lookup invalid")?);
    }
    for (position, &id) in positions.iter().zip(ids) {
        let id = id as usize;
        if id < cage.len() && (Vec3::from_array(*position) - cage[id]).length() > 1e-6 {
            return Err("B1 Level 1 UV-seam source positions diverged".into());
        }
    }
    Ok(())
}

fn create_overlay(world: &mut World, s: &Session) -> Result<Overlay, String> {
    let owner = *s.displays.first().ok_or("B1 body display absent")?;
    let original = s
        .display_meshes
        .first()
        .ok_or("B1 body mesh absent")?
        .clone();
    let original_visibility = world.get::<Visibility>(owner).copied();
    let part = s.parts.first().ok_or("B1 source body absent")?;
    let ids = source_ids(world, part)?;
    let source = world
        .resource::<Assets<Mesh>>()
        .get(&part.mesh)
        .ok_or("B1 fitted body mesh absent")?;
    let uv = uv_values(source)?;
    if ids.len() != uv.len() {
        return Err("B1 Level 1 source ID/UV coverage mismatch".into());
    }
    let raw: Vec<usize> = source
        .indices()
        .ok_or("B1 source body indices absent")?
        .iter()
        .collect();
    if raw.len() % 6 != 0 {
        return Err("B1 source quad fan absent".into());
    }
    let covered: BTreeSet<u16> = world
        .resource::<Assets<MhcloAsset>>()
        .get(&s.parts[1].mapping)
        .ok_or("B1 garment mapping absent")?
        .delete_verts
        .iter()
        .copied()
        .collect();
    let mut faces = Vec::new();
    let mut face_uv = Vec::new();
    let mut visible = Vec::new();
    for quad in raw.chunks_exact(6) {
        if quad[0] != quad[3] || quad[2] != quad[4] {
            return Err("B1 Level 1 source quad order changed".into());
        }
        let corners = [quad[0], quad[1], quad[2], quad[5]];
        let mut face = [0usize; 4];
        let mut corners_uv = [[0.0f32; 2]; 4];
        for k in 0..4 {
            face[k] = *ids.get(corners[k]).ok_or("B1 Level 1 source ID absent")? as usize;
            corners_uv[k] = *uv.get(corners[k]).ok_or("B1 Level 1 UV absent")?;
        }
        if face.iter().any(|&v| v >= 13_380) {
            continue;
        }
        visible.push(!face.iter().all(|v| covered.contains(&(*v as u16))));
        faces.push(face);
        face_uv.push(corners_uv);
    }
    let plan = Level1Plan::new(13_380, faces)?;
    let mut lookup = vec![usize::MAX; 13_380];
    for (i, &id) in ids.iter().enumerate() {
        let id = id as usize;
        if id < lookup.len() && lookup[id] == usize::MAX {
            lookup[id] = i;
        }
    }
    if lookup.contains(&usize::MAX) {
        return Err("B1 Level 1 source cage ID missing".into());
    }

    // Keep one geometry vertex per UV island. A render vertex key contains the
    // geometric limit point and that original quad's bilinear UV. This retains
    // original texture seams while sharing geometry across matching UVs.
    let mut keyed = BTreeMap::<(u32, u32, u32), u32>::new();
    let mut render_geometry_ids = Vec::new();
    let mut render_uv = Vec::new();
    let mut indices = Vec::new();
    for (fi, (corners_uv, face_visible)) in face_uv.iter().zip(&visible).enumerate() {
        if !face_visible {
            continue;
        }
        let center = [
            corners_uv.iter().map(|v| v[0]).sum::<f32>() * 0.25,
            corners_uv.iter().map(|v| v[1]).sum::<f32>() * 0.25,
        ];
        let face_triangles = &plan.triangles[fi * 24..(fi + 1) * 24];
        for k in 0..4 {
            let t = &face_triangles[k * 6..(k + 1) * 6];
            let geometry = [t[0], t[1], t[2], t[5]];
            let tex = [
                corners_uv[k],
                midpoint(corners_uv[k], corners_uv[(k + 1) % 4]),
                center,
                midpoint(corners_uv[k], corners_uv[(k + 3) % 4]),
            ];
            for corner in [0, 1, 2, 0, 2, 3] {
                let g = geometry[corner];
                let u = tex[corner];
                let key = (g, u[0].to_bits(), u[1].to_bits());
                let index = *keyed.entry(key).or_insert_with(|| {
                    let index = render_geometry_ids.len() as u32;
                    render_geometry_ids.push(g as usize);
                    render_uv.push(u);
                    index
                });
                indices.push(index);
            }
        }
    }
    if indices.is_empty() {
        return Err("B1 Level 1 visible body empty".into());
    }
    let mut work = plan.workspace();
    let mut cage = vec![Vec3::ZERO; 13_380];
    let original_mesh = world
        .resource::<Assets<Mesh>>()
        .get(&original)
        .ok_or("B1 published original body absent")?;
    let source_positions = match original_mesh.attribute(Mesh::ATTRIBUTE_POSITION) {
        Some(VertexAttributeValues::Float32x3(v)) => v,
        _ => return Err("B1 published original positions absent".into()),
    };
    gather_cage(&ids, &lookup, source_positions, &mut cage)?;
    plan.update(&cage, &mut work)?;
    let positions: Vec<[f32; 3]> = render_geometry_ids
        .iter()
        .map(|&i| work.positions[i].to_array())
        .collect();
    let normals: Vec<[f32; 3]> = render_geometry_ids
        .iter()
        .map(|&i| work.normals[i].to_array())
        .collect();
    let mut mesh = Mesh::new(
        PrimitiveTopology::TriangleList,
        RenderAssetUsages::default(),
    );
    mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, positions);
    mesh.insert_attribute(Mesh::ATTRIBUTE_NORMAL, normals);
    mesh.insert_attribute(Mesh::ATTRIBUTE_UV_0, render_uv);
    mesh.insert_indices(Indices::U32(indices.clone()));
    // Current B1 StandardMaterials do not bind a normal map; the display
    // surface uses its recomputed normals and UVs without per-frame tangents.
    let transform = *world
        .get::<Transform>(owner)
        .ok_or("B1 original transform absent")?;
    let global = *world
        .get::<GlobalTransform>(owner)
        .ok_or("B1 original global transform absent")?;
    let material = world
        .get::<MeshMaterial3d<StandardMaterial>>(owner)
        .ok_or("B1 original material absent")?
        .clone();
    let material_asset = world.resource::<Assets<StandardMaterial>>();
    let material_asset = material_asset
        .get(&material.0)
        .ok_or("B1 material asset absent")?;
    if material_asset.normal_map_texture.is_some() {
        return Err("B1 Level 1 does not admit a normal-mapped material without tangents".into());
    }
    let handle = world.resource_mut::<Assets<Mesh>>().add(mesh);
    let entity = world
        .spawn((
            Mesh3d(handle.clone()),
            material,
            bevy::camera::visibility::NoFrustumCulling,
            transform,
            global,
            Visibility::Inherited,
        ))
        .id();
    Ok(Overlay {
        owner,
        original,
        original_visibility,
        entity,
        mesh: handle,
        plan,
        work,
        cage,
        ids,
        lookup,
        render_geometry_ids,
        last_serial: s.serial,
        triangle_count: indices.len() / 3,
    })
}

fn update_overlay(world: &mut World, overlay: &mut Overlay, s: &Session) -> Result<(), String> {
    if overlay.last_serial != s.serial {
        let mesh = world
            .resource::<Assets<Mesh>>()
            .get(&overlay.original)
            .ok_or("B1 published original body absent")?;
        let positions = match mesh.attribute(Mesh::ATTRIBUTE_POSITION) {
            Some(VertexAttributeValues::Float32x3(v)) => v,
            _ => return Err("B1 published original positions absent".into()),
        };
        gather_cage(&overlay.ids, &overlay.lookup, positions, &mut overlay.cage)?;
        overlay.plan.update(&overlay.cage, &mut overlay.work)?;
        let positions: Vec<[f32; 3]> = overlay
            .render_geometry_ids
            .iter()
            .map(|&i| overlay.work.positions[i].to_array())
            .collect();
        let normals: Vec<[f32; 3]> = overlay
            .render_geometry_ids
            .iter()
            .map(|&i| overlay.work.normals[i].to_array())
            .collect();
        let mut meshes = world.resource_mut::<Assets<Mesh>>();
        let mut mesh = meshes
            .get_mut(&overlay.mesh)
            .ok_or("B1 Level 1 mesh absent")?;
        mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, positions);
        mesh.insert_attribute(Mesh::ATTRIBUTE_NORMAL, normals);
        overlay.last_serial = s.serial;
    }
    let transform = *world
        .get::<Transform>(overlay.owner)
        .ok_or("B1 original transform absent")?;
    let global = *world
        .get::<GlobalTransform>(overlay.owner)
        .ok_or("B1 original global absent")?;
    let material = world
        .get::<MeshMaterial3d<StandardMaterial>>(overlay.owner)
        .ok_or("B1 original material absent")?
        .clone();
    let material_asset = world.resource::<Assets<StandardMaterial>>();
    let material_asset = material_asset
        .get(&material.0)
        .ok_or("B1 material asset absent")?;
    if material_asset.normal_map_texture.is_some() {
        return Err("B1 Level 1 does not admit a normal-mapped material without tangents".into());
    }
    world
        .entity_mut(overlay.entity)
        .insert((transform, global, material, Visibility::Inherited));
    world.entity_mut(overlay.owner).insert(Visibility::Hidden);
    Ok(())
}

/// Runs after the normal B1 publication and appearance update. Errors restore
/// the original body, while the original buffers remain untouched throughout.
pub(super) fn publish(world: &mut World) {
    let mut state = world
        .remove_resource::<Level1DisplayState>()
        .unwrap_or_default();
    let runtime = world.remove_resource::<B1Runtime>().unwrap_or_default();
    let enabled = world.resource::<B1DisplaySubdivision>().enabled;
    let mut status = B1DisplaySubdivisionStatus::default();
    if !enabled || runtime.active.is_none() {
        state.clear(world);
        state.1 = None;
    } else if let Some(s) = runtime.active.as_ref() {
        if let Some((owner, serial, error)) = &state.1 {
            if *owner == s.displays[0] && *serial == s.serial {
                status.error = Some(error.clone());
                world.insert_resource(runtime);
                world.insert_resource(state);
                *world.resource_mut::<B1DisplaySubdivisionStatus>() = status;
                return;
            }
        }
        state.1 = None;
        let result = (|| {
            if state
                .0
                .as_ref()
                .is_some_and(|o| o.owner != s.displays[0] || o.original != s.display_meshes[0])
            {
                state.clear(world);
            }
            if state.0.is_none() {
                state.0 = Some(create_overlay(world, s)?);
            }
            let overlay = state.0.as_mut().unwrap();
            update_overlay(world, overlay, s)?;
            status.active = true;
            status.vertices = overlay.render_geometry_ids.len();
            status.triangles = overlay.triangle_count;
            Ok::<(), String>(())
        })();
        if let Err(error) = result {
            state.clear(world);
            state.1 = Some((s.displays[0], s.serial, error.clone()));
            status.error = Some(error);
        }
    }
    world.insert_resource(runtime);
    world.insert_resource(state);
    *world.resource_mut::<B1DisplaySubdivisionStatus>() = status;
}

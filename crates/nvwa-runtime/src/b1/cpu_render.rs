//! Bounded, windowless export of the actual published B1 body and garment.
//! No RenderPlugin, WindowPlugin, GPU adapter, experimental oracle or alternate
//! morph/rig/garment implementation is installed here.
use super::level1_geometry::Level1Plan;
use super::*;
use bevy::asset::{AssetMetaCheck, io::memory::Dir};
use std::time::{Duration, Instant};

pub struct CpuImage {
    pub pixels: Vec<u8>,
    /// Canonical little-endian production mesh buffers and stage transforms.
    pub geometry_bytes: Vec<u8>,
    pub parts: Vec<(String, usize, usize)>,
    pub covered_pixels: usize,
    pub view: [f32; 16],
    pub projection: [f32; 16],
    pub near: f32,
    pub far: f32,
    /// True only when the complete fitted body is rendered without garments.
    pub body_reference: bool,
}

pub fn validate_export_work(doc: &SceneDocument) -> Result<(), String> {
    doc.validate().map_err(|e| e.to_string())?;
    if (doc.profile != nvwa_core::CharacterProfile::b1_character()
        && doc.profile != nvwa_core::CharacterProfile::b1_character_waist()
        && doc.profile != nvwa_core::CharacterProfile::b1_character_legs()
        && doc.profile != nvwa_core::CharacterProfile::b1_character_upper_body()
        && doc.profile != nvwa_core::CharacterProfile::b1_character_hip_contour()
        && doc.profile != nvwa_core::CharacterProfile::b1_character_arm_proportions()
        && doc.profile != nvwa_core::CharacterProfile::b1_character_hand_size()
        && doc.profile != nvwa_core::CharacterProfile::b1_character_shoulder_form()
        && doc.profile != nvwa_core::CharacterProfile::b1_character_forearm_form()
        && doc.profile != nvwa_core::CharacterProfile::b1_character_upper_arm_muscle())
        || !doc.timeline.is_empty()
        || doc.character.appearance != nvwa_core::CharacterAppearance::None
    {
        return Err("CPU export requires a supported B1 motion or static body profile, an empty timeline and appearance none; use set_diagnostic_pose to select a saved static pose".into());
    }
    crate::stage::camera_geometry(&doc.stage.camera, doc.character.scale)?;
    Ok(())
}

fn headless_app(bytes: BTreeMap<String, Vec<u8>>) -> App {
    let dir = Dir::default();
    for (path, bytes) in bytes {
        dir.insert_asset(Path::new(&path), bytes);
    }
    let mut app = App::new();
    register_b1_asset_source(&mut app);
    app.register_asset_source(
        AssetSourceId::Default,
        AssetSourceBuilder::new(move || Box::new(MemoryAssetReader { root: dir.clone() })),
    )
    .add_plugins((
        MinimalPlugins,
        AssetPlugin {
            meta_check: AssetMetaCheck::Never,
            ..default()
        },
        bevy::transform::TransformPlugin,
        bevy::world_serialization::WorldSerializationPlugin,
        bevy::scene::ScenePlugin,
        bevy::mesh::MeshPlugin,
        bevy::image::ImagePlugin::default(),
        AnimationPlugin,
    ))
    .init_asset::<StandardMaterial>()
    .init_resource::<EditorState>()
    .init_resource::<CharacterAsset>()
    .init_resource::<RuntimeStatus>()
    .init_resource::<Playback>();
    install(&mut app);
    app.finish();
    app.cleanup();
    app
}

/// The caller supplies its bounded asset snapshot. The production runtime
/// authenticates those immutable bytes again before fitting or publishing.
pub fn render_silhouette(
    doc: &SceneDocument,
    bytes: BTreeMap<String, Vec<u8>>,
    width: u32,
    height: u32,
) -> Result<CpuImage, String> {
    render_inner(doc, bytes, width, height, false, false)
}

/// Opt-in Level 1 surface for the static CPU silhouette. The fitted and
/// skinned source frame remains authoritative and the garment is unchanged.
pub fn render_silhouette_level1(
    doc: &SceneDocument,
    bytes: BTreeMap<String, Vec<u8>>,
    width: u32,
    height: u32,
) -> Result<CpuImage, String> {
    render_inner(doc, bytes, width, height, false, true)
}

/// Render the same fitted and posed B1 body as the published frame, restoring
/// triangles hidden by both upper and lower garments. This is a static image
/// reference, not a mesh/rig export or continuous-animation claim.
pub fn render_body_reference(
    doc: &SceneDocument,
    bytes: BTreeMap<String, Vec<u8>>,
    width: u32,
    height: u32,
) -> Result<CpuImage, String> {
    render_inner(doc, bytes, width, height, true, false)
}

/// Opt-in Level 1 static full-body reference image; no mesh export.
pub fn render_body_reference_level1(
    doc: &SceneDocument,
    bytes: BTreeMap<String, Vec<u8>>,
    width: u32,
    height: u32,
) -> Result<CpuImage, String> {
    render_inner(doc, bytes, width, height, true, true)
}

fn level1_body(
    part: &PublishedCpuPart,
    full_body: bool,
) -> Result<(Vec<[f32; 3]>, Vec<usize>), String> {
    let complete = part
        .full_body_indices
        .as_ref()
        .ok_or("complete fitted body topology absent")?;
    if complete.len() % 6 != 0 || part.indices.len() % 6 != 0 {
        return Err("B1 Level 1 source quad fan absent".into());
    }
    let source = &part.source_ids;
    let mut faces = Vec::new();
    let mut selected = Vec::new();
    let visible: BTreeSet<[usize; 6]> = part
        .indices
        .chunks_exact(6)
        .map(|q| q.try_into().expect("six indices"))
        .collect();
    for quad in complete.chunks_exact(6) {
        if quad[0] != quad[3] || quad[2] != quad[4] {
            return Err("B1 Level 1 source quad order changed".into());
        }
        let mut face = [0; 4];
        for (slot, &index) in [quad[0], quad[1], quad[2], quad[5]].iter().enumerate() {
            face[slot] = *source.get(index).ok_or("B1 Level 1 source ID absent")? as usize;
        }
        if face.iter().any(|&v| v >= 13_380) {
            return Err("B1 Level 1 source ID outside cage".into());
        }
        selected.push(full_body || visible.contains(quad));
        faces.push(face);
    }
    let plan = Level1Plan::new(13_380, faces)?;
    let mut cage = vec![Vec3::ZERO; 13_380];
    let mut seen = vec![false; 13_380];
    for (&id, &position) in source.iter().zip(&part.frame.positions) {
        let id = id as usize;
        if id >= cage.len() {
            continue;
        }
        let position = Vec3::from_array(position);
        if seen[id] && (cage[id] - position).length() > 1e-6 {
            return Err("B1 Level 1 UV-seam source positions diverged".into());
        }
        cage[id] = position;
        seen[id] = true;
    }
    if seen.iter().any(|&v| !v) {
        return Err("B1 Level 1 source cage ID missing".into());
    }
    let mut work = plan.workspace();
    plan.update(&cage, &mut work)?;
    let indices = selected
        .iter()
        .enumerate()
        .flat_map(|(fi, &show)| {
            if show {
                plan.triangles[fi * 24..(fi + 1) * 24]
                    .iter()
                    .map(|&v| v as usize)
                    .collect::<Vec<_>>()
            } else {
                Vec::new()
            }
        })
        .collect();
    Ok((
        work.positions.into_iter().map(|p| p.to_array()).collect(),
        indices,
    ))
}

fn render_inner(
    doc: &SceneDocument,
    bytes: BTreeMap<String, Vec<u8>>,
    width: u32,
    height: u32,
    body_reference: bool,
    level1: bool,
) -> Result<CpuImage, String> {
    validate_export_work(doc)?;
    if !(64..=2048).contains(&width) || !(64..=2048).contains(&height) {
        return Err("CPU export dimensions must each be 64..=2048".into());
    }
    let (camera, near, far) =
        crate::stage::camera_geometry(&doc.stage.camera, doc.character.scale)?;
    let view = camera.to_matrix().inverse();
    // Same reverse-Z infinite RH perspective used by Bevy's PerspectiveProjection.
    let projection = Mat4::perspective_infinite_reverse_rh(
        doc.stage.camera.fov_degrees.to_radians(),
        width as f32 / height as f32,
        near,
    );
    let mut app = headless_app(bytes);
    app.world_mut()
        .resource_mut::<EditorState>()
        .request_open(doc.clone())?;
    let started = Instant::now();
    loop {
        app.update();
        let editor = app.world().resource::<EditorState>();
        if let Some(error) = &editor.open_error {
            return Err(error.clone());
        }
        let status = app.world().resource::<RuntimeStatus>();
        if let Some(error) = &status.error {
            return Err(error.clone());
        }
        if status.ready && editor.pending_open.is_none() && published_cpu_frame(app.world()).is_ok()
        {
            break;
        }
        if started.elapsed() >= Duration::from_secs(30) {
            return Err(format!(
                "CPU frame preparation timed out; phase={}",
                status.phase
            ));
        }
        std::thread::sleep(Duration::from_millis(2));
    }
    let frame = published_cpu_frame_with_body_topology(app.world(), body_reference || level1)?;
    if frame.doc != doc || frame.sample.position != 0.0 || !frame.sample.clip_id.is_empty() {
        return Err("Published CPU frame differs from requested Work/static pose".into());
    }
    let mut raster = Raster::new(width, height);
    let mut geometry_bytes = Vec::new();
    let mut parts = Vec::new();
    for part in frame.parts {
        if body_reference && part.name != "body" {
            continue;
        }
        let original_indices: &[usize] = if body_reference {
            part.full_body_indices
                .as_deref()
                .ok_or("complete fitted body topology absent")?
        } else {
            &part.indices
        };
        let transform = Mat4::from_cols_array(&part.transform);
        let matrix = projection * view * transform;
        let refined = if level1 && part.name == "body" {
            Some(level1_body(&part, body_reference)?)
        } else {
            None
        };
        let indices: &[usize] = refined
            .as_ref()
            .map_or(original_indices, |(_, indices)| indices);
        let positions: &[[f32; 3]] = refined
            .as_ref()
            .map_or(&part.frame.positions, |(positions, _)| positions);
        if indices.len() % 3 != 0 || positions.is_empty() {
            return Err("Published CPU mesh has invalid triangle topology".into());
        }
        geometry_bytes.extend_from_slice(part.name.as_bytes());
        geometry_bytes.push(0);
        geometry_bytes.extend_from_slice(&(positions.len() as u64).to_le_bytes());
        for point in positions {
            for v in point {
                if !v.is_finite() {
                    return Err("Nonfinite published position".into());
                }
                geometry_bytes.extend_from_slice(&v.to_le_bytes());
            }
        }
        for v in part.transform {
            geometry_bytes.extend_from_slice(&v.to_le_bytes());
        }
        geometry_bytes.extend_from_slice(&(indices.len() as u64).to_le_bytes());
        for index in indices {
            geometry_bytes.extend_from_slice(&(*index as u64).to_le_bytes());
        }
        for triangle in indices.chunks_exact(3) {
            let mut vertices = [Vec4::ZERO; 3];
            let mut world_points = [Vec3::ZERO; 3];
            for (i, index) in triangle.iter().enumerate() {
                let p = positions
                    .get(*index)
                    .ok_or("Published triangle index outside mesh")?;
                vertices[i] = matrix * Vec3::from_array(*p).extend(1.0);
                if body_reference {
                    world_points[i] = transform.transform_point3(Vec3::from_array(*p));
                }
                if !vertices[i].is_finite() {
                    return Err("Nonfinite projected position".into());
                }
            }
            if body_reference {
                raster.triangle_colored(vertices, far, body_reference_color(world_points));
            } else {
                raster.triangle(vertices, far);
            }
        }
        parts.push((part.name.into(), positions.len(), indices.len() / 3));
    }
    let covered_pixels = raster.depth.iter().filter(|z| z.is_finite()).count();
    if covered_pixels == 0 {
        return Err("Saved camera contains no visible character pixels".into());
    }
    let mut pixels = vec![255; (width * height * 3) as usize];
    for (i, z) in raster.depth.iter().enumerate() {
        if z.is_finite() {
            pixels[i * 3..i * 3 + 3].copy_from_slice(&raster.color[i]);
        }
    }
    Ok(CpuImage {
        pixels,
        geometry_bytes,
        parts,
        covered_pixels,
        view: view.to_cols_array(),
        projection: projection.to_cols_array(),
        near,
        far,
        body_reference,
    })
}

fn body_reference_color(world_points: [Vec3; 3]) -> [u8; 3] {
    let normal = (world_points[1] - world_points[0])
        .cross(world_points[2] - world_points[0])
        .normalize_or_zero();
    let light = Vec3::new(0.3, 0.45, 0.84).normalize();
    let shade = 0.42 + 0.58 * normal.dot(light).abs();
    [166_u8, 166, 170].map(|v| (f32::from(v) * shade).round() as u8)
}

struct Raster {
    width: u32,
    height: u32,
    depth: Vec<f64>,
    color: Vec<[u8; 3]>,
}
impl Raster {
    fn new(width: u32, height: u32) -> Self {
        Self {
            width,
            height,
            depth: vec![f64::NEG_INFINITY; (width * height) as usize],
            color: vec![[255, 255, 255]; (width * height) as usize],
        }
    }
    fn triangle(&mut self, vertices: [Vec4; 3], far: f32) {
        self.triangle_colored(vertices, far, [65, 72, 80]);
    }
    fn triangle_colored(&mut self, vertices: [Vec4; 3], far: f32, color: [u8; 3]) {
        // Homogeneous clipping: sides, reverse-Z near/far, plus the saved
        // stage's finite far distance. Clip before division to handle crossings.
        let planes: [fn(Vec4, f32) -> f32; 7] = [
            |p, _| p.x + p.w,
            |p, _| p.w - p.x,
            |p, _| p.y + p.w,
            |p, _| p.w - p.y,
            |p, _| p.z,
            |p, _| p.w - p.z,
            |p, f| f - p.w,
        ];
        let mut polygon = vertices.to_vec();
        for plane in planes {
            let input = std::mem::take(&mut polygon);
            if input.is_empty() {
                return;
            }
            let mut previous = *input.last().unwrap();
            let mut pd = plane(previous, far);
            for current in input {
                let cd = plane(current, far);
                if (pd >= 0.0) != (cd >= 0.0) {
                    polygon.push(previous.lerp(current, pd / (pd - cd)));
                }
                if cd >= 0.0 {
                    polygon.push(current);
                }
                previous = current;
                pd = cd;
            }
        }
        for i in 1..polygon.len().saturating_sub(1) {
            self.clipped([polygon[0], polygon[i], polygon[i + 1]], color);
        }
    }
    fn clipped(&mut self, points: [Vec4; 3], color: [u8; 3]) {
        let p = points.map(|v| {
            let x = f64::from(v.x) / f64::from(v.w);
            let y = f64::from(v.y) / f64::from(v.w);
            [
                (x + 1.0) * 0.5 * f64::from(self.width),
                (1.0 - y) * 0.5 * f64::from(self.height),
                f64::from(v.z) / f64::from(v.w),
            ]
        });
        if p.iter().flatten().any(|v| !v.is_finite()) {
            return;
        }
        fn edge(a: [f64; 3], b: [f64; 3], x: f64, y: f64) -> f64 {
            (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])
        }
        let area = edge(p[0], p[1], p[2][0], p[2][1]);
        if area.abs() < 1e-12 {
            return;
        }
        let min_x = p
            .iter()
            .map(|p| p[0])
            .fold(f64::INFINITY, f64::min)
            .floor()
            .max(0.0) as u32;
        let max_x = p
            .iter()
            .map(|p| p[0])
            .fold(f64::NEG_INFINITY, f64::max)
            .ceil()
            .min(f64::from(self.width)) as u32;
        let min_y = p
            .iter()
            .map(|p| p[1])
            .fold(f64::INFINITY, f64::min)
            .floor()
            .max(0.0) as u32;
        let max_y = p
            .iter()
            .map(|p| p[1])
            .fold(f64::NEG_INFINITY, f64::max)
            .ceil()
            .min(f64::from(self.height)) as u32;
        for y in min_y..max_y {
            for x in min_x..max_x {
                let px = f64::from(x) + 0.5;
                let py = f64::from(y) + 0.5;
                let a = edge(p[1], p[2], px, py) / area;
                let b = edge(p[2], p[0], px, py) / area;
                let c = 1.0 - a - b;
                if a >= 0.0 && b >= 0.0 && c >= 0.0 {
                    let z = a * p[0][2] + b * p[1][2] + c * p[2][2];
                    let index = (y * self.width + x) as usize;
                    if z > self.depth[index] {
                        self.depth[index] = z;
                        self.color[index] = color;
                    }
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn clips_near_crossings_rejects_behind_and_depth_is_order_independent() {
        let tri = [
            Vec4::new(-0.8, -0.8, 0.5, 1.0),
            Vec4::new(0.8, -0.8, 0.5, 1.0),
            Vec4::new(0.0, 0.8, 0.5, 1.0),
        ];
        let mut a = Raster::new(64, 64);
        a.triangle(tri, 10.0);
        assert!(a.depth.iter().any(|z| z.is_finite()));
        let behind = tri.map(|v| Vec4::new(v.x, v.y, 0.5, -1.0));
        let before = a.depth.clone();
        a.triangle(behind, 10.0);
        assert_eq!(a.depth, before);
        let mut crossing = tri;
        crossing[2].z = 2.0;
        let mut b = Raster::new(64, 64);
        b.triangle(crossing, 10.0);
        assert!(b.depth.iter().any(|z| z.is_finite()));
        let closer = tri.map(|mut v| {
            v.z = 0.8;
            v
        });
        let mut c = Raster::new(64, 64);
        c.triangle(closer, 10.0);
        c.triangle(tri, 10.0);
        a.triangle(closer, 10.0);
        assert_eq!(a.depth, c.depth);
    }
    #[test]
    fn camera_projection_matches_bevy() {
        use bevy::camera::CameraProjection;
        let p = PerspectiveProjection {
            fov: 36.0_f32.to_radians(),
            aspect_ratio: 1280.0 / 720.0,
            near: 0.05,
            far: 250.0,
            ..default()
        };
        assert_eq!(
            p.get_clip_from_view(),
            Mat4::perspective_infinite_reverse_rh(p.fov, p.aspect_ratio, p.near)
        );
    }
}

//! Bounded, windowless export of the actual published B1 body and garment.
//! No RenderPlugin, WindowPlugin, GPU adapter, experimental oracle or alternate
//! morph/rig/garment implementation is installed here.
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
}

pub fn validate_export_work(doc: &SceneDocument) -> Result<(), String> {
    doc.validate().map_err(|e| e.to_string())?;
    if doc.profile != nvwa_core::CharacterProfile::b1_character()
        || !doc.timeline.is_empty()
        || doc.character.appearance != nvwa_core::CharacterAppearance::None
    {
        return Err("CPU silhouette requires the eight-parameter new-character profile, an empty timeline and appearance none; use set_diagnostic_pose to select a saved static pose".into());
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
    let frame = published_cpu_frame(app.world())?;
    if frame.doc != doc || frame.sample.position != 0.0 || !frame.sample.clip_id.is_empty() {
        return Err("Published CPU frame differs from requested Work/static pose".into());
    }
    let mut raster = Raster::new(width, height);
    let mut geometry_bytes = Vec::new();
    let mut parts = Vec::new();
    for part in frame.parts {
        let transform = Mat4::from_cols_array(&part.transform);
        let matrix = projection * view * transform;
        let positions = &part.frame.positions;
        if part.indices.len() % 3 != 0 || positions.is_empty() {
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
        geometry_bytes.extend_from_slice(&(part.indices.len() as u64).to_le_bytes());
        for index in &part.indices {
            geometry_bytes.extend_from_slice(&(*index as u64).to_le_bytes());
        }
        for triangle in part.indices.chunks_exact(3) {
            let mut vertices = [Vec4::ZERO; 3];
            for (i, index) in triangle.iter().enumerate() {
                let p = positions
                    .get(*index)
                    .ok_or("Published triangle index outside mesh")?;
                vertices[i] = matrix * Vec3::from_array(*p).extend(1.0);
                if !vertices[i].is_finite() {
                    return Err("Nonfinite projected position".into());
                }
            }
            raster.triangle(vertices, far);
        }
        parts.push((part.name.into(), positions.len(), part.indices.len() / 3));
    }
    let covered_pixels = raster.depth.iter().filter(|z| z.is_finite()).count();
    if covered_pixels == 0 {
        return Err("Saved camera contains no visible character pixels".into());
    }
    let mut pixels = vec![255; (width * height * 3) as usize];
    for (i, z) in raster.depth.iter().enumerate() {
        if z.is_finite() {
            pixels[i * 3..i * 3 + 3].copy_from_slice(&[65, 72, 80]);
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
    })
}

struct Raster {
    width: u32,
    height: u32,
    depth: Vec<f64>,
}
impl Raster {
    fn new(width: u32, height: u32) -> Self {
        Self {
            width,
            height,
            depth: vec![f64::NEG_INFINITY; (width * height) as usize],
        }
    }
    fn triangle(&mut self, vertices: [Vec4; 3], far: f32) {
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
            self.clipped([polygon[0], polygon[i], polygon[i + 1]]);
        }
    }
    fn clipped(&mut self, points: [Vec4; 3]) {
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

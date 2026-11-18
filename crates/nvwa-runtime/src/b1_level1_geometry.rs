use bevy::prelude::Vec3;
use std::collections::{BTreeMap, BTreeSet};

/// One-time Catmull–Clark connectivity for a closed four-sided source cage.
/// Updates use current Nvwa-skinned source positions; no topology is rebuilt per frame.
pub struct Level1Plan {
    faces: Vec<[usize; 4]>,
    edges: Vec<Edge>,
    vertex_edges: Vec<Vec<usize>>,
    vertex_faces: Vec<Vec<usize>>,
    limit_neighbors: Vec<Vec<usize>>,
    limit_opposites: Vec<Vec<usize>>,
    pub triangles: Vec<u32>,
    source_count: usize,
}
struct Edge {
    a: usize,
    b: usize,
    faces: [usize; 2],
}
pub struct Level1Workspace {
    face_points: Vec<Vec3>,
    standard: Vec<Vec3>,
    pub positions: Vec<Vec3>,
    pub normals: Vec<Vec3>,
}
impl Level1Plan {
    pub fn new(source_count: usize, faces: Vec<[usize; 4]>) -> Result<Self, String> {
        let mut edge_map: BTreeMap<(usize, usize), Vec<usize>> = BTreeMap::new();
        let mut vertex_edges = vec![Vec::new(); source_count];
        let mut vertex_faces = vec![Vec::new(); source_count];
        for (fi, f) in faces.iter().enumerate() {
            if f.iter().any(|&v| v >= source_count) {
                return Err("source ID out of range".into());
            }
            for k in 0..4 {
                let a = f[k];
                let b = f[(k + 1) % 4];
                if a == b {
                    return Err("collapsed source edge".into());
                }
                edge_map.entry((a.min(b), a.max(b))).or_default().push(fi);
                vertex_faces[a].push(fi);
            }
        }
        let mut edges = Vec::with_capacity(edge_map.len());
        let mut edge_ids = BTreeMap::new();
        for ((a, b), adjacent) in edge_map {
            if adjacent.len() != 2 {
                return Err(format!("source edge {a}-{b} has {} faces", adjacent.len()));
            }
            let id = edges.len();
            edge_ids.insert((a, b), id);
            edges.push(Edge {
                a,
                b,
                faces: [adjacent[0], adjacent[1]],
            });
            vertex_edges[a].push(id);
            vertex_edges[b].push(id);
        }
        for (v, fs) in vertex_faces.iter().enumerate() {
            if fs.len() < 3 || fs.len() != vertex_edges[v].len() {
                return Err(format!("invalid closed fan at source ID {v}"));
            }
        }
        let face_offset = source_count + edges.len();
        let mut triangles = Vec::with_capacity(faces.len() * 8 * 3);
        let mut quads = Vec::with_capacity(faces.len() * 4);
        for (fi, f) in faces.iter().enumerate() {
            for k in 0..4 {
                let a = f[k];
                let b = f[(k + 1) % 4];
                let prev = f[(k + 3) % 4];
                let e_next = source_count + edge_ids[&(a.min(b), a.max(b))];
                let e_prev = source_count + edge_ids[&(a.min(prev), a.max(prev))];
                let fp = face_offset + fi;
                let quad = [a, e_next, fp, e_prev];
                triangles.extend([
                    a as u32,
                    e_next as u32,
                    fp as u32,
                    a as u32,
                    fp as u32,
                    e_prev as u32,
                ]);
                quads.push(quad);
            }
        }
        let count = source_count + edges.len() + faces.len();
        let mut neighbor_sets = vec![BTreeSet::new(); count];
        let mut limit_opposites = vec![Vec::new(); count];
        for f in &quads {
            for k in 0..4 {
                neighbor_sets[f[k]].insert(f[(k + 1) % 4]);
                neighbor_sets[f[k]].insert(f[(k + 3) % 4]);
                limit_opposites[f[k]].push(f[(k + 2) % 4]);
            }
        }
        let limit_neighbors: Vec<Vec<usize>> = neighbor_sets
            .into_iter()
            .map(|s| s.into_iter().collect())
            .collect();
        for i in 0..count {
            if limit_neighbors[i].len() != limit_opposites[i].len() || limit_neighbors[i].len() < 3
            {
                return Err(format!("invalid Level 1 limit fan at vertex {i}"));
            }
        }
        Ok(Self {
            faces,
            edges,
            vertex_edges,
            vertex_faces,
            limit_neighbors,
            limit_opposites,
            triangles,
            source_count,
        })
    }
    pub fn vertex_count(&self) -> usize {
        self.source_count + self.edges.len() + self.faces.len()
    }
    pub fn workspace(&self) -> Level1Workspace {
        Level1Workspace {
            face_points: vec![Vec3::ZERO; self.faces.len()],
            standard: vec![Vec3::ZERO; self.vertex_count()],
            positions: vec![Vec3::ZERO; self.vertex_count()],
            normals: vec![Vec3::ZERO; self.vertex_count()],
        }
    }
    pub fn update(&self, cage: &[Vec3], work: &mut Level1Workspace) -> Result<(), String> {
        if cage.len() != self.source_count {
            return Err("source position count changed".into());
        }
        for (fi, f) in self.faces.iter().enumerate() {
            work.face_points[fi] = (cage[f[0]] + cage[f[1]] + cage[f[2]] + cage[f[3]]) * 0.25;
        }
        for (i, e) in self.edges.iter().enumerate() {
            work.standard[self.source_count + i] = (cage[e.a]
                + cage[e.b]
                + work.face_points[e.faces[0]]
                + work.face_points[e.faces[1]])
                * 0.25;
        }
        for (i, fs) in self.vertex_faces.iter().enumerate() {
            let n = fs.len() as f32;
            let f_avg = fs.iter().map(|&fi| work.face_points[fi]).sum::<Vec3>() / n;
            let e_avg = self.vertex_edges[i]
                .iter()
                .map(|&ei| {
                    let e = &self.edges[ei];
                    (cage[e.a] + cage[e.b]) * 0.5
                })
                .sum::<Vec3>()
                / n;
            work.standard[i] = (f_avg + e_avg * 2.0 + cage[i] * (n - 3.0)) / n;
        }
        let face_offset = self.source_count + self.edges.len();
        work.standard[face_offset..].copy_from_slice(&work.face_points);
        // Blender's default use_limit_surface=True evaluates the bicubic
        // Catmull–Clark limit point at each Level 1 vertex. For a closed quad
        // fan this stencil has n² center, 4 per edge neighbor, 1 per opposite.
        for i in 0..self.vertex_count() {
            let n = self.limit_neighbors[i].len() as f32;
            let around = self.limit_neighbors[i]
                .iter()
                .map(|&v| work.standard[v])
                .sum::<Vec3>();
            let opposite = self.limit_opposites[i]
                .iter()
                .map(|&v| work.standard[v])
                .sum::<Vec3>();
            work.positions[i] =
                (work.standard[i] * (n * n) + around * 4.0 + opposite) / (n * (n + 5.0));
        }
        work.normals.fill(Vec3::ZERO);
        for t in self.triangles.chunks_exact(3) {
            let (a, b, c) = (t[0] as usize, t[1] as usize, t[2] as usize);
            let n = (work.positions[b] - work.positions[a])
                .cross(work.positions[c] - work.positions[a]);
            work.normals[a] += n;
            work.normals[b] += n;
            work.normals[c] += n;
        }
        for n in &mut work.normals {
            *n = n.normalize_or_zero();
        }
        if work
            .positions
            .iter()
            .chain(&work.normals)
            .any(|v| !v.is_finite())
        {
            return Err("nonfinite subdiv output".into());
        }
        Ok(())
    }
}

//! File boundary for the opt-in CPU exporter. Rendering consumes the exact
//! bounded bytes read here, not a second filesystem read after validation.
use super::*;
use sha2::{Digest, Sha256};
use std::{collections::BTreeMap, io::Write};

pub(super) const USAGE: &str = "  render <work.json> --assets <root> --output <new-directory> [--width 1280 --height 720] [--mode silhouette]\nCPU export: eight-parameter character or static waist profile, saved static diagnostic pose, appearance none; body + garment, saved perspective camera. No floor, lighting, textures, hair, motion or PBR.";
fn sha(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
fn error(code: &str, e: impl std::fmt::Display) -> CoreError {
    CoreError::new(code, e.to_string())
}

pub(super) fn capabilities(doc: &SceneDocument) -> serde_json::Value {
    serde_json::json!({"schema_version":1,"compiled":true,"mode":"silhouette","current_work_supported":nvwa_runtime::validate_export_work(doc).is_ok(),"profile":"nvwa-mpfb-b1-motion-v2","profiles":["nvwa-mpfb-b1-motion-v2","nvwa-mpfb-b1-waist-v1"],"timeline":"empty_only","pose":"saved_diagnostic_pose","appearance":"none_only","camera":"saved_perspective","parts":["body","garment"],"dimensions_each":[64,2048],"output":"new_directory_work_png_receipt","not_rendered":["floor","lighting","materials","textures","hair","eyes","motion"],"usage":USAGE})
}

fn assets(doc: &SceneDocument, root: &Path) -> Result<BTreeMap<String, Vec<u8>>, CoreError> {
    // Use the exact same bounded reader and canonical core validators as validate.
    let version = doc
        .profile
        .backend
        .b1_asset_version()
        .ok_or_else(|| error("unsupported_render", "B1 required"))?;
    let manifest_path = Path::new(&doc.profile.asset_path);
    let manifest_bytes = read_asset(root, manifest_path, B1_MAX_MANIFEST_BYTES)?;
    doc.profile.validate_asset_bytes(&manifest_bytes)?;
    let manifest = B1AssetManifest::from_bytes_for(version, &manifest_bytes)?;
    let parent = manifest_path
        .parent()
        .ok_or_else(|| error("unsafe_asset_path", "Manifest parent absent"))?;
    let mut bytes = BTreeMap::new();
    let mut total = 0usize;
    for entry in &manifest.files {
        let path = parent.join(&entry.path);
        let payload = read_asset(root, &path, B1_MAX_ASSET_BYTES)?;
        total = total
            .checked_add(payload.len())
            .ok_or_else(|| error("invalid_asset", "Size overflow"))?;
        if total > B1_MAX_TOTAL_ASSET_BYTES {
            return Err(error("invalid_asset", "B1 assets exceed 8 MiB"));
        }
        manifest.validate_file_bytes(&entry.path, &payload)?;
        // Runtime authenticates this same immutable snapshot before fitting.
        bytes.insert(
            path.to_str()
                .ok_or_else(|| error("unsafe_asset_path", "Non-UTF8 asset path"))?
                .to_owned(),
            payload,
        );
    }
    bytes.insert(doc.profile.asset_path.clone(), manifest_bytes);
    Ok(bytes)
}

struct Options {
    work: PathBuf,
    assets: PathBuf,
    output: PathBuf,
    width: u32,
    height: u32,
}
fn options(args: &[String]) -> Result<Options, CoreError> {
    let usage = || error("usage", USAGE);
    let work = args.get(1).ok_or_else(usage)?.into();
    let mut opts = BTreeMap::new();
    for pair in args[2..].chunks(2) {
        if pair.len() != 2
            || !["--assets", "--output", "--width", "--height", "--mode"]
                .contains(&pair[0].as_str())
            || opts.insert(pair[0].as_str(), pair[1].as_str()).is_some()
        {
            return Err(usage());
        }
    }
    if opts.get("--mode").is_some_and(|m| *m != "silhouette") {
        return Err(error(
            "unsupported_render",
            "Only silhouette mode is supported",
        ));
    }
    let dimensions = |key, default| -> Result<u32, CoreError> {
        let n = opts
            .get(key)
            .map_or(Ok(default), |s| s.parse::<u32>().map_err(|_| usage()))?;
        if !(64..=2048).contains(&n) {
            return Err(error(
                "out_of_range",
                "Width and height must each be 64..=2048",
            ));
        }
        Ok(n)
    };
    Ok(Options {
        work,
        assets: (*opts.get("--assets").ok_or_else(usage)?).into(),
        output: (*opts.get("--output").ok_or_else(usage)?).into(),
        width: dimensions("--width", 1280)?,
        height: dimensions("--height", 720)?,
    })
}
fn write_new(path: &Path, bytes: &[u8]) -> Result<(), CoreError> {
    let mut file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .map_err(|e| error("file_create", e))?;
    file.write_all(bytes)
        .and_then(|()| file.sync_all())
        .map_err(|e| error("file_write", e))
}
pub(super) fn run(args: &[String]) -> Result<(), CoreError> {
    let opts = options(args)?;
    match std::fs::symlink_metadata(&opts.output) {
        Ok(_) => return Err(error("output_exists", "CPU output must be a new directory")),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
        Err(e) => return Err(error("file_metadata", e)),
    }
    let raw = read(&opts.work)?;
    let doc = SceneDocument::from_json(&raw)?;
    let requested: serde_json::Value = serde_json::from_str(&raw).map_err(|e| error("parse", e))?;
    nvwa_runtime::validate_export_work(&doc).map_err(|e| error("unsupported_render", e))?;
    let bytes = assets(&doc, &opts.assets)?;
    let asset_hashes: BTreeMap<_, _> = bytes
        .iter()
        .map(|(path, bytes)| (path.clone(), sha(bytes)))
        .collect();
    let started = std::time::Instant::now();
    let image = nvwa_runtime::render_silhouette(&doc, bytes, opts.width, opts.height)
        .map_err(|e| error("render_failed", e))?;
    let render_seconds = started.elapsed().as_secs_f64();
    let mut png = Vec::new();
    {
        let mut encoder = png::Encoder::new(&mut png, opts.width, opts.height);
        encoder.set_color(png::ColorType::Rgb);
        encoder.set_depth(png::BitDepth::Eight);
        let mut writer = encoder.write_header().map_err(|e| error("png_encode", e))?;
        writer
            .write_image_data(&image.pixels)
            .map_err(|e| error("png_encode", e))?;
        writer.finish().map_err(|e| error("png_encode", e))?;
    }
    let executable = std::env::current_exe().map_err(|e| error("executable_identity", e))?;
    let executable_sha =
        sha(&std::fs::read(executable).map_err(|e| error("executable_identity", e))?);
    let receipt = serde_json::json!({
        "schema_version":1,"status":"rendered","renderer":"nvwa-cpu-silhouette-v1","mode":"silhouette",
        "work_sha256":sha(raw.as_bytes()),"document_revision":doc.revision,"profile":doc.profile.id,"backend":doc.profile.backend,
        "asset_sha256":asset_hashes,"executable_sha256":executable_sha,"package_version":env!("CARGO_PKG_VERSION"),
        "parameters":doc.character.parameters,"diagnostic_pose":doc.character.diagnostic_pose,"seconds":0,"playing":false,
        "camera":requested["stage"]["camera"],"effective_camera":doc.stage.camera,"projection":"perspective_reverse_z","view_matrix":image.view,"projection_matrix":image.projection,"near":image.near,"far":image.far,
        "width":opts.width,"height":opts.height,"covered_pixels":image.covered_pixels,"parts":image.parts,
        "geometry_sha256":sha(&image.geometry_bytes),"png_sha256":sha(&png),"pixels_sha256":sha(&image.pixels),
        "render_seconds":render_seconds,"timing_scope":"runtime preparation and CPU rasterization; excludes filesystem snapshot, PNG encoding and executable hashing",
        "foreground_rgb":[65,72,80],"background_rgb":[255,255,255],"antialiasing":"none_pixel_centers",
        "not_rendered":["floor","lighting","materials","textures","hair","eyes","motion"],
        "scope":"Actual production body and garment CPU geometry; silhouette only, not Web/PBR parity or clothing quality acceptance"
    });
    let receipt_bytes = serde_json::to_vec_pretty(&receipt).map_err(|e| error("serialize", e))?;
    // Everything is prepared before claiming a new directory. A persistence
    // failure can leave partial files but never a successful receipt; no retry
    // overwrites an existing directory. The receipt is the completion marker.
    std::fs::create_dir(&opts.output).map_err(|e| error("file_create", e))?;
    write_new(&opts.output.join("work.nvwa.json"), raw.as_bytes())?;
    write_new(&opts.output.join("actual.png"), &png)?;
    write_new(&opts.output.join("receipt.json"), &receipt_bytes)?;
    respond(serde_json::json!({"status":"rendered","output":opts.output,"receipt":receipt}))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn bounded_options_reject_duplicates_unknown_modes_and_bad_dimensions() {
        fn args(s: &str) -> Vec<String> {
            s.split_whitespace().map(str::to_owned).collect()
        }
        assert!(options(&args("render a --assets b --output c")).is_ok());
        for s in [
            "render a --assets b --output c --width 0",
            "render a --assets b --output c --height 2049",
            "render a --assets b --output c --mode depth",
            "render a --assets b --output c --width 100 --width 100",
            "render a --assets b --output c --unknown x",
        ] {
            assert!(options(&args(s)).is_err());
        }
    }
}

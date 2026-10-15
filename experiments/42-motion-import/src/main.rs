use std::path::Path;
fn main() {
    let args: Vec<_> = std::env::args().skip(1).collect();
    let result = if args.first().is_some_and(|s| s == "adapt-f32") && args.len() == 5 {
        nvwa_motion_import_experiment::adapt_f32_to(
            Path::new(&args[1]),
            Path::new(&args[2]),
            Path::new(&args[3]),
            Path::new(&args[4]),
        )
    } else if (4..=5).contains(&args.len()) {
        nvwa_motion_import_experiment::import_to(
            Path::new(&args[0]),
            Path::new(&args[1]),
            Path::new(&args[2]),
            Path::new(&args[3]),
            args.get(4).map(Path::new),
        )
    } else {
        eprintln!(
            "usage: nvwa-motion-import-experiment NORMALIZED.json RAW.json BASE.glb NEW_OUTPUT_DIR [RUN_RECEIPT.json]\n       nvwa-motion-import-experiment adapt-f32 SIDECAR.json ROOT.f32 ROT.f32 NEW_OUTPUT_DIR"
        );
        std::process::exit(2)
    };
    match result {
        Ok(v) => println!("{}", serde_json::to_string_pretty(&v).unwrap()),
        Err(e) => {
            eprintln!("import rejected: {e}");
            std::process::exit(1)
        }
    }
}

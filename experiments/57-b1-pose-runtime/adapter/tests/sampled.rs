//! Actual source execution in CI; the pinned portable seed is an explicit input.
#[test]
fn actual_source_sampled_regression() {
    let Some(seed) = std::env::var_os("B1_CI_INPUTS") else {
        assert!(
            !matches!(std::env::var("CI").as_deref(), Ok("true" | "1")),
            "B1_CI_INPUTS is required in CI; refusing a green NOT-RUN"
        );
        eprintln!(
            "NOT-RUN: set B1_CI_INPUTS to the authenticated portable seed for actual sampled regression"
        );
        return;
    };
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap();
    let output = std::env::temp_dir().join(format!("nvwa-b1-sampled-{}", std::process::id()));
    let status = std::process::Command::new("python3")
        .arg(root.join("sampled_regression.py"))
        .arg("--ci-inputs")
        .arg(seed)
        .arg("--binary")
        .arg(env!("CARGO_BIN_EXE_b1-pose-adapter"))
        .arg("--out")
        .arg(&output)
        .status()
        .expect("launch actual sampled source regression");
    assert!(
        status.success(),
        "actual sampled regression failed; retained {}",
        output.display()
    );
    eprintln!("sampled regression retained {}", output.display());
}

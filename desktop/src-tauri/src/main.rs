// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

fn crash_log_path() -> PathBuf {
    let mut p = if cfg!(target_os = "windows") {
        std::env::var("LOCALAPPDATA")
            .map(PathBuf::from)
            .unwrap_or_else(|_| PathBuf::from("."))
    } else {
        PathBuf::from("/tmp")
    };
    p.push("Nermes");
    let _ = fs::create_dir_all(&p);
    p.push("desktop.log");
    p
}

fn crash_log(msg: &str) {
    if let Ok(mut f) = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(crash_log_path())
    {
        let ts = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);
        let _ = writeln!(f, "[{}] {}", ts, msg);
    }
}

fn main() {
    crash_log("=== Nermes Desktop starting ===");

    // catch panics
    let orig_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        crash_log(&format!("PANIC: {}", info));
        orig_hook(info);
    }));

    crash_log(&format!(
        "exe={:?}, cwd={:?}",
        std::env::current_exe(),
        std::env::current_dir()
    ));

    app_lib::run();
    crash_log("=== Nermes Desktop exited normally ===");
}

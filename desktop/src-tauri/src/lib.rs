use serde::Serialize;
use std::process::Command;
use tauri::Emitter;
use tauri::Manager;

// ── Events ──

#[derive(Clone, Serialize)]
struct InstallProgress {
    step: String,
    progress: u8,
    done: bool,
}

// ── Commands ──

#[tauri::command]
fn get_env_path() -> String {
    let home = home_dir();
    home.join(".nermes").join(".env")
        .to_string_lossy()
        .to_string()
}

#[tauri::command]
fn read_file(path: String) -> Result<String, String> {
    std::fs::read_to_string(&path).map_err(|e| e.to_string())
}

#[tauri::command]
fn write_file(path: String, content: String) -> Result<(), String> {
    if let Some(parent) = std::path::Path::new(&path).parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    std::fs::write(&path, &content).map_err(|e| e.to_string())
}

#[tauri::command]
fn check_python() -> Result<String, String> {
    let output = Command::new("python")
        .args(["--version"])
        .output()
        .or_else(|_| Command::new("python3").args(["--version"]).output())
        .map_err(|e| format!("Python 未安装: {}", e))?;

    String::from_utf8(output.stdout)
        .or_else(|_| String::from_utf8(output.stderr))
        .map(|s| s.trim().to_string())
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn check_nermes() -> Result<String, String> {
    let output = Command::new("nermes")
        .args(["--version"])
        .output()
        .map_err(|_| "Nermes 未安装".to_string())?;

    String::from_utf8(output.stdout)
        .map(|s| s.trim().to_string())
        .map_err(|e| e.to_string())
}

#[tauri::command]
async fn install_nermes(
    app: tauri::AppHandle,
    install_dir: String,
    components: Vec<String>,
) -> Result<(), String> {
    let total = components.len() as u8;
    for (i, comp) in components.iter().enumerate() {
        let progress = ((i + 1) as f32 / total as f32 * 100.0) as u8;
        let step = match comp.as_str() {
            "python" => "🐍 检测 Python 环境...",
            "nermes" => "📦 pip install nermes-agent",
            "git" => "🔧 配置 Git",
            "profession" => "📊 安装财务职业预设",
            "shortcut" => "🔗 创建桌面快捷方式",
            "autostart" => "🚀 配置开机自启",
            _ => "⚙️ 未知组件",
        };

        let _ = app.emit("install-progress", InstallProgress {
            step: step.to_string(),
            progress,
            done: progress >= 100,
        });

        // TODO: 真实的安装逻辑 — pip install / 文件复制 / 注册表操作
        log::info!("[install] {} ({}%) dir={}", step, progress, install_dir);
    }

    Ok(())
}

#[tauri::command]
async fn uninstall_nermes(app: tauri::AppHandle) -> Result<(), String> {
    let steps = [
        (30u8, "🗑️  pip uninstall nermes-agent"),
        (60, "🧹 清理配置文件..."),
        (85, "🔗 移除快捷方式..."),
        (100, "✅ 卸载完成"),
    ];

    for (progress, step) in &steps {
        let _ = app.emit("install-progress", InstallProgress {
            step: step.to_string(),
            progress: *progress,
            done: *progress >= 100,
        });
        log::info!("[uninstall] {} ({}%)", step, progress);
    }

    Ok(())
}

// ── Entry ──

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_min_size(Some(tauri::Size::Physical(
                    tauri::PhysicalSize::new(780, 580),
                )));
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_env_path, read_file, write_file,
            check_python, check_nermes,
            install_nermes, uninstall_nermes,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn home_dir() -> std::path::PathBuf {
    #[cfg(target_os = "windows")]
    {
        std::env::var("USERPROFILE")
            .ok()
            .map(std::path::PathBuf::from)
            .unwrap_or_else(|| std::path::PathBuf::from("."))
    }
    #[cfg(not(target_os = "windows"))]
    {
        std::env::var("HOME")
            .ok()
            .map(std::path::PathBuf::from)
            .unwrap_or_else(|| std::path::PathBuf::from("."))
    }
}

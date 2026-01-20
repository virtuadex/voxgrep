use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use tauri::{AppHandle, Manager, Runtime};

struct AppState {
    python_process: Arc<Mutex<Option<Child>>>,
}

fn start_backend<R: Runtime>(_app: &AppHandle<R>) -> Result<Child, String> {
    let current_dir = std::env::current_dir().unwrap_or_default();
    let project_root = if current_dir.ends_with("src-tauri") {
        current_dir.parent().and_then(|p| p.parent()).unwrap_or(&current_dir).to_path_buf()
    } else if current_dir.ends_with("desktop") {
        current_dir.parent().unwrap_or(&current_dir).to_path_buf()
    } else {
        current_dir.clone()
    };

    // Check if poetry exists
    let has_poetry = std::process::Command::new("poetry")
        .arg("--version")
        .output()
        .is_ok();

    let (python_cmd, final_args) = if has_poetry {
        ("poetry", vec!["run".to_string(), "python".to_string(), "-m".to_string(), "voxgrep.server.app".to_string()])
    } else {
        let cmd = if cfg!(windows) { "python" } else { "python3" };
        (cmd, vec!["-m".to_string(), "voxgrep.server.app".to_string()])
    };

    println!("Starting Backend: {} {:?}", python_cmd, final_args);
    println!("Project Root: {:?}", project_root);

    let child = Command::new(python_cmd)
        .args(&final_args)
        .current_dir(&project_root)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to spawn python backend: {}", e))?;

    Ok(child)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(AppState {
            python_process: Arc::new(Mutex::new(None)),
        })
        .setup(|app| {
            let handle = app.handle().clone();
            let state = app.state::<AppState>();
            
            match start_backend(&handle) {
                Ok(child) => {
                    *state.python_process.lock().unwrap() = Some(child);
                    println!("Backend started successfully.");
                }
                Err(e) => eprintln!("Failed to start backend: {}", e),
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if let Ok(mut lock) = window.state::<AppState>().python_process.lock() {
                    if let Some(mut child) = lock.take() {
                        println!("Killing backend process...");
                        let _ = child.kill();
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

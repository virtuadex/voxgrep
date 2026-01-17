use serde::{Deserialize, Serialize};
use std::process::{Command, Stdio};
use std::io::{BufRead, BufReader};
use tauri::{AppHandle, Emitter, Runtime};

#[derive(Serialize, Deserialize, Clone)]
struct PythonEvent {
    event: String,
    data: serde_json::Value,
}

#[tauri::command]
async fn run_python_command<R: Runtime>(
    app: AppHandle<R>,
    args: Vec<String>,
) -> Result<(), String> {
    // Hardcoded for the prototype based on user's environment
    let python_path = "/Users/dex/Library/Caches/pypoetry/virtualenvs/videogrep-rHnP7eG6-py3.12/bin/python";
    let script_path = "desktop/desktop_api.py";

    let mut cmd_args = vec![script_path.to_string()];
    cmd_args.extend(args);

    let mut child = Command::new(python_path)
        .args(&cmd_args)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .current_dir("..") // The desktop directory's parent is the project root containing desktop_api.py
        .spawn()
        .map_err(|e| format!("Failed to spawn python: {}", e))?;

    let stdout = child.stdout.take().unwrap();
    let reader = BufReader::new(stdout);

    // Read stdout line by line and emit events
    for line in reader.lines() {
        if let Ok(line_content) = line {
            if let Ok(event) = serde_json::from_str::<PythonEvent>(&line_content) {
                app.emit("python-event", event).unwrap();
            } else {
                // Non-JSON output - maybe standard logging
                app.emit("python-log", line_content).unwrap();
            }
        }
    }

    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![run_python_command])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

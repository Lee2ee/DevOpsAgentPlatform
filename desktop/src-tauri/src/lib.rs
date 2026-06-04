use std::sync::Mutex;
use tauri::{AppHandle, Manager, State};

pub struct CoreEngineState {
    pub pid: Mutex<Option<u32>>,
}

/// Core Engine sidecar를 시작한다.
/// 이미 실행 중이면 skip.
#[tauri::command]
async fn start_core_engine(
    _app: AppHandle,
    state: State<'_, CoreEngineState>,
) -> Result<String, String> {
    let current_pid = state.pid.lock().unwrap().clone();
    if current_pid.is_some() {
        return Ok("already_running".into());
    }

    // sidecar 대신 직접 실행 (MVP: 별도 설치된 aidevops-server 사용)
    let child = std::process::Command::new("aidevops-server")
        .spawn()
        .map_err(|e| format!("Core Engine 시작 실패: {e}"))?;

    let pid = child.id();
    *state.pid.lock().unwrap() = Some(pid);
    Ok(format!("started:{pid}"))
}

/// Core Engine 프로세스를 종료한다.
#[tauri::command]
async fn stop_core_engine(state: State<'_, CoreEngineState>) -> Result<(), String> {
    if let Some(pid) = state.pid.lock().unwrap().take() {
        #[cfg(unix)]
        unsafe {
            libc::kill(pid as i32, libc::SIGTERM);
        }
        #[cfg(windows)]
        {
            let _ = std::process::Command::new("taskkill")
                .args(["/F", "/PID", &pid.to_string()])
                .output();
        }
    }
    Ok(())
}

/// Core Engine 포트를 반환한다.
#[tauri::command]
fn get_core_engine_port() -> u16 {
    8765
}

/// Core Engine HTTP health check
#[tauri::command]
async fn check_engine_health() -> bool {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(3))
        .build()
        .unwrap_or_default();

    client
        .get("http://127.0.0.1:8765/api/v1/health")
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .manage(CoreEngineState {
            pid: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            start_core_engine,
            stop_core_engine,
            get_core_engine_port,
            check_engine_health,
        ])
        .setup(|app| {
            // 앱 시작 시 Core Engine health check 후 실패하면 자동 시작 시도
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                if !check_engine_health().await {
                    let state = app_handle.state::<CoreEngineState>();
                    let _ = start_core_engine(app_handle.clone(), state).await;
                }
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

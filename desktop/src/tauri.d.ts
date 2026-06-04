// Tauri invoke 타입 선언 (Rust commands)
declare module "@tauri-apps/api/core" {
  function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T>;
}

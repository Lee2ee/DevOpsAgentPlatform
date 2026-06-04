import { apiClient } from "./client";

// ── Health ────────────────────────────────────
export const checkHealth = () => apiClient.get("/health").then((r) => r.data);

// ── Projects ──────────────────────────────────
export const scanProject = (path: string, useAi = true) =>
  apiClient.post("/projects/scan", { path, use_ai: useAi }).then((r) => r.data);

export const getProjects = () =>
  apiClient.get("/projects").then((r) => r.data);

export const getProject = (id: string) =>
  apiClient.get(`/projects/${id}`).then((r) => r.data);

export const deleteProject = (id: string) =>
  apiClient.delete(`/projects/${id}`).then((r) => r.data);

export const scanWorkspace = (path: string) =>
  apiClient.post("/projects/scan-workspace", { path }).then((r) => r.data);

// ── Docker ────────────────────────────────────
export const generateDocker = (projectId: string) =>
  apiClient.post("/docker/generate", { project_id: projectId }).then((r) => r.data);

export const saveDocker = (generationId: string, projectPath: string, overwrite = true) =>
  apiClient.post("/docker/save", { generation_id: generationId, project_path: projectPath, overwrite }).then((r) => r.data);

// ── CI/CD ─────────────────────────────────────
export const generateCicd = (projectId: string, platform: string) =>
  apiClient.post("/cicd/generate", { project_id: projectId, platform }).then((r) => r.data);

export const saveCicd = (generationId: string, projectPath: string, overwrite = true) =>
  apiClient.post("/cicd/save", { generation_id: generationId, project_path: projectPath, overwrite }).then((r) => r.data);

// ── Deploy ────────────────────────────────────
export interface DeployOptions {
  health_check_url?: string;
  health_check_timeout?: number;
  auto_rollback?: boolean;
  remote_app_dir?: string;
}

export const startDeploy = (
  projectId: string,
  serverId: string,
  strategy = "local_build",
  options: DeployOptions = {}
) =>
  apiClient
    .post("/deploy", { project_id: projectId, server_id: serverId, strategy, options })
    .then((r) => r.data);

export const getDeployment = (id: string) =>
  apiClient.get(`/deploy/${id}`).then((r) => r.data);

// ── Analyze ───────────────────────────────────
export const analyzeDeployment = (deploymentId: string, useAi = true) =>
  apiClient.post("/analyze", { deployment_id: deploymentId, use_ai: useAi }).then((r) => r.data);

export const analyzeLog = (logText: string, useAi = true) =>
  apiClient.post("/analyze", { log_text: logText, use_ai: useAi }).then((r) => r.data);

export const getAnalysis = (id: string) =>
  apiClient.get(`/analyze/${id}`).then((r) => r.data);

export const generatePatches = (analysisId: string, useAi = true) =>
  apiClient.post(`/analyze/${analysisId}/patch`, { use_ai: useAi }).then((r) => r.data);

export const applyPatch = (analysisId: string, patchId: string) =>
  apiClient.post(`/analyze/${analysisId}/apply`, { patch_id: patchId }).then((r) => r.data);

// ── Config ────────────────────────────────────
export const getAiConfig = () => apiClient.get("/config/ai").then((r) => r.data);
export const updateAiConfig = (cfg: object) =>
  apiClient.put("/config/ai", cfg).then((r) => r.data);

export const getServers = () => apiClient.get("/config/servers").then((r) => r.data);
export const addServer = (server: object) =>
  apiClient.post("/config/servers", server).then((r) => r.data);
export const updateServer = (id: string, server: object) =>
  apiClient.put(`/config/servers/${id}`, server).then((r) => r.data);

export const deleteServer = (id: string) =>
  apiClient.delete(`/config/servers/${id}`).then((r) => r.data);

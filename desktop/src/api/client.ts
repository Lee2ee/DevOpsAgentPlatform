import axios from "axios";

const PORT = 8765;

export const apiClient = axios.create({
  baseURL: `http://127.0.0.1:${PORT}/api/v1`,
  timeout: 30_000,
});

export const createDeploySocket = (deploymentId: string): WebSocket =>
  new WebSocket(`ws://127.0.0.1:${PORT}/api/v1/ws/deploy/${deploymentId}`);

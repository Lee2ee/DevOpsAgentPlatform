import { create } from "zustand";
import { createDeploySocket } from "../api/client";
import { getDeployment, startDeploy, type DeployOptions } from "../api";
import { useActivityStore } from "./activityStore";

export interface DeployStep {
  name: string;
  status: "pending" | "running" | "done" | "failed";
  duration_sec: number | null;
  log_output: string;
  error?: string;
}

export interface Deployment {
  deployment_id: string;
  project_id: string;
  server_id: string;
  status: string;
  strategy: string;
  steps: DeployStep[];
  started_at: string;
  finished_at: string | null;
  service_url: string | null;
  error_message: string | null;
}

interface DeployStore {
  activeDeployment: Deployment | null;
  logs: string[];
  isDeploying: boolean;
  startDeploy: (
    projectId: string,
    serverId: string,
    strategy: string,
    options: DeployOptions
  ) => Promise<void>;
  appendLog: (line: string) => void;
  clearLogs: () => void;
}

export const useDeployStore = create<DeployStore>((set, get) => ({
  activeDeployment: null,
  logs: [],
  isDeploying: false,

  startDeploy: async (projectId, serverId, strategy, options) => {
    set({ isDeploying: true, logs: [], activeDeployment: null });

    try {
      const data = await startDeploy(projectId, serverId, strategy, options);
      const deploymentId: string = data.deployment_id;

      useActivityStore.getState().addActivity({
        type: "deploy_start",
        title: `배포 시작`,
        detail: `project=${projectId} server=${serverId} strategy=${strategy}`,
        status: "info",
      });

      // 초기 deployment 상태 설정
      set({
        activeDeployment: {
          deployment_id: deploymentId,
          project_id: projectId,
          server_id: serverId,
          status: "running",
          strategy,
          steps: [],
          started_at: new Date().toISOString(),
          finished_at: null,
          service_url: null,
          error_message: null,
        },
      });

      // WebSocket으로 실시간 스트리밍
      const ws = createDeploySocket(deploymentId);

      ws.onmessage = (evt) => {
        const msg = JSON.parse(evt.data as string) as {
          event: string;
          data: Record<string, unknown>;
        };

        if (msg.event === "log") {
          get().appendLog(msg.data.line as string);
        } else if (msg.event === "step_start") {
          const stepName = msg.data.step as string;
          set((s) => {
            if (!s.activeDeployment) return s;
            const newStep: DeployStep = { name: stepName, status: "running", duration_sec: null, log_output: "" };
            const idx = s.activeDeployment.steps.findIndex((st) => st.name === stepName);
            const steps = idx >= 0
              ? s.activeDeployment.steps.map((st, i) => (i === idx ? newStep : st))
              : [...s.activeDeployment.steps, newStep];
            return { activeDeployment: { ...s.activeDeployment, steps } };
          });
        } else if (msg.event === "step_done") {
          const stepName = msg.data.step as string;
          const duration = msg.data.duration_sec as number;
          set((s) => {
            if (!s.activeDeployment) return s;
            const steps = s.activeDeployment.steps.map((st) =>
              st.name === stepName ? { ...st, status: "done" as const, duration_sec: Math.round(duration) } : st
            );
            return { activeDeployment: { ...s.activeDeployment, steps } };
          });
        } else if (msg.event === "step_fail") {
          const stepName = msg.data.step as string;
          const stepError = (msg.data.error as string | undefined) ?? undefined;
          set((s) => {
            if (!s.activeDeployment) return s;
            const steps = s.activeDeployment.steps.map((st) =>
              st.name === stepName ? { ...st, status: "failed" as const, error: stepError } : st
            );
            return { activeDeployment: { ...s.activeDeployment, steps } };
          });
        } else if (msg.event === "deploy_done") {
          const serviceUrl = msg.data.service_url as string;
          useActivityStore.getState().addActivity({
            type: "deploy_done",
            title: `배포 성공`,
            detail: serviceUrl ? `URL: ${serviceUrl}` : `deployment=${deploymentId}`,
            status: "success",
          });
          set((s) => ({
            isDeploying: false,
            activeDeployment: s.activeDeployment
              ? {
                  ...s.activeDeployment,
                  status: "success",
                  service_url: serviceUrl,
                  finished_at: msg.data.finished_at as string,
                }
              : null,
          }));
          ws.close();
        } else if (msg.event === "deploy_failed") {
          const errorMsg = msg.data.error as string;
          useActivityStore.getState().addActivity({
            type: "deploy_failed",
            title: `배포 실패`,
            detail: errorMsg,
            status: "failed",
          });
          set((s) => ({
            isDeploying: false,
            activeDeployment: s.activeDeployment
              ? {
                  ...s.activeDeployment,
                  status: "failed",
                  error_message: errorMsg,
                }
              : null,
          }));
          ws.close();
        }
      };

      ws.onerror = () => {
        get().appendLog("[WS] WebSocket 연결 실패 - 폴링으로 전환합니다.");
        // WS 오류 시 폴링으로 상태 조회
        const poll = setInterval(async () => {
          try {
            const dep = await getDeployment(deploymentId);
            set({ activeDeployment: dep });
            if (dep.status !== "running") {
              clearInterval(poll);
              set({ isDeploying: false });
            }
          } catch {
            clearInterval(poll);
          }
        }, 3000);
      };

      ws.onclose = (evt) => {
        // 비정상 종료 시 폴링으로 최종 상태 확인
        const current = get().activeDeployment;
        if (current && current.status === "running") {
          get().appendLog(`[WS] 연결 종료 (code=${evt.code}) - 폴링으로 상태 확인 중...`);
          const poll = setInterval(async () => {
            try {
              const dep = await getDeployment(deploymentId);
              set({ activeDeployment: dep });
              if (dep.status !== "running") {
                clearInterval(poll);
                set({ isDeploying: false });
              }
            } catch {
              clearInterval(poll);
            }
          }, 3000);
        }
      };
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ isDeploying: false });
      get().appendLog(`[ERR] ${msg}`);
    }
  },

  appendLog: (line) =>
    set((s) => ({ logs: [...s.logs.slice(-999), line] })),

  clearLogs: () => set({ logs: [] }),
}));

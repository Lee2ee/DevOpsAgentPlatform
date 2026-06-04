import { create } from "zustand";
import {
  addServer,
  updateServer,
  deleteServer,
  getAiConfig,
  getServers,
  updateAiConfig,
} from "../api";

export interface AIConfig {
  provider: string;
  model: string;
  base_url: string;
  api_key?: string;
  has_api_key?: boolean;
}

export interface Server {
  id: string;
  name: string;
  host: string;
  port: number;
  username: string;
  credential_id: string | null;
  has_credential: boolean;
}

interface SettingsStore {
  aiConfig: AIConfig;
  servers: Server[];
  loadSettings: () => Promise<void>;
  updateAiConfig: (cfg: AIConfig) => Promise<void>;
  addServer: (server: Omit<Server, "id">) => Promise<void>;
  updateServer: (id: string, server: Omit<Server, "id">) => Promise<void>;
  deleteServer: (id: string) => Promise<void>;
}

const DEFAULT_AI: AIConfig = {
  provider: "ollama",
  model: "qwen2.5-coder:7b",
  base_url: "http://localhost:11434",
};

export const useSettingsStore = create<SettingsStore>((set) => ({
  aiConfig: DEFAULT_AI,
  servers: [],

  loadSettings: async () => {
    try {
      const [ai, servers] = await Promise.all([getAiConfig(), getServers()]);
      set({
        aiConfig: ai ?? DEFAULT_AI,
        servers: servers ?? [],
      });
    } catch {
      // 서버 미실행 상태에서도 앱은 정상 표시
    }
  },

  updateAiConfig: async (cfg) => {
    await updateAiConfig(cfg);
    set({ aiConfig: cfg });
  },

  addServer: async (server) => {
    const data = await addServer(server);
    set((s) => ({ servers: [...s.servers, data] }));
  },

  updateServer: async (id, server) => {
    const data = await updateServer(id, server);
    set((s) => ({ servers: s.servers.map((sv) => (sv.id === id ? { ...sv, ...data } : sv)) }));
  },

  deleteServer: async (id) => {
    await deleteServer(id);
    set((s) => ({ servers: s.servers.filter((sv) => sv.id !== id) }));
  },
}));

import { create } from "zustand";
import { checkHealth } from "../api";

interface EngineStore {
  isRunning: boolean;
  version: string;
  checkStatus: () => Promise<void>;
}

export const useEngineStore = create<EngineStore>((set) => ({
  isRunning: false,
  version: "",
  checkStatus: async () => {
    try {
      const data = await checkHealth();
      set({ isRunning: true, version: data.version ?? "" });
    } catch {
      set({ isRunning: false });
    }
  },
}));

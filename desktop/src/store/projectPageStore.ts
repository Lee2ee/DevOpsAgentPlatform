import { create } from "zustand";

export interface DockerResult {
  generation_id: string;
  dockerfile: string;
  docker_compose: string | null;
  dockerignore: string;
  warnings: string[];
}

export interface CicdResult {
  generation_id: string;
  platform: string;
  file_path: string;
  content: string;
}

export type ProjectTab = "scan" | "docker" | "cicd";

interface ProjectPageStore {
  tab: ProjectTab;
  setTab: (tab: ProjectTab) => void;
  dockerResults: Record<string, DockerResult>;
  setDockerResult: (projectId: string, result: DockerResult | null) => void;
  cicdResults: Record<string, CicdResult>;
  setCicdResult: (projectId: string, result: CicdResult | null) => void;
  savedDocker: Record<string, boolean>;
  setSavedDocker: (projectId: string, saved: boolean) => void;
  savedCicd: Record<string, boolean>;
  setSavedCicd: (projectId: string, saved: boolean) => void;
}

export const useProjectPageStore = create<ProjectPageStore>((set) => ({
  tab: "scan",
  setTab: (tab) => set({ tab }),

  dockerResults: {},
  setDockerResult: (projectId, result) =>
    set((s) => {
      const next = { ...s.dockerResults };
      if (result) next[projectId] = result;
      else delete next[projectId];
      return { dockerResults: next };
    }),

  cicdResults: {},
  setCicdResult: (projectId, result) =>
    set((s) => {
      const next = { ...s.cicdResults };
      if (result) next[projectId] = result;
      else delete next[projectId];
      return { cicdResults: next };
    }),

  savedDocker: {},
  setSavedDocker: (projectId, saved) =>
    set((s) => ({ savedDocker: { ...s.savedDocker, [projectId]: saved } })),

  savedCicd: {},
  setSavedCicd: (projectId, saved) =>
    set((s) => ({ savedCicd: { ...s.savedCicd, [projectId]: saved } })),
}));

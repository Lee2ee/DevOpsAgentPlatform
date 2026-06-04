import { create } from "zustand";
import { getProjects, scanProject as apiScanProject, deleteProject as apiDeleteProject } from "../api";

export interface ScanResult {
  language: string | null;
  framework: string | null;
  language_version: string | null;
  build_tool: string | null;
  database: string[];
  message_queue: string[];
  cache: string[];
  existing_docker: boolean;
  existing_cicd: string;
  scan_confidence: number;
  scanned_at: string;
}

export interface Project {
  id: string;
  name: string;
  path: string;
  scan_result: ScanResult | null;
  created_at: string;
}

// 백엔드 ScanResult 응답 → 프론트 Project 변환
function mapScanResponse(data: Record<string, unknown>, path?: string): Project {
  return {
    id: data.project_id as string,
    name: (data.name as string) || ((path ?? "").split(/[\\/]/).pop() ?? path ?? ""),
    path: (data.path as string) || path || "",
    scan_result: {
      language: (data.language as string | null) ?? null,
      framework: (data.framework as string | null) ?? null,
      language_version: (data.language_version as string | null) ?? null,
      build_tool: (data.build_tool as string | null) ?? null,
      database: (data.database as string[]) ?? [],
      message_queue: (data.message_queue as string[]) ?? [],
      cache: (data.cache as string[]) ?? [],
      existing_docker: (data.existing_docker as boolean) ?? false,
      existing_cicd: (data.existing_cicd as string) ?? "none",
      scan_confidence: (data.scan_confidence as number) ?? 0,
      scanned_at: (data.scanned_at as string) ?? "",
    },
    created_at: (data.scanned_at as string) || new Date().toISOString(),
  };
}

// 백엔드 ProjectSummary 응답 → 프론트 Project 변환
function mapSummaryResponse(data: Record<string, unknown>): Project {
  return {
    id: data.project_id as string,
    name: data.name as string,
    path: data.path as string,
    scan_result: data.language
      ? {
          language: (data.language as string | null) ?? null,
          framework: (data.framework as string | null) ?? null,
          language_version: null,
          build_tool: null,
          database: [],
          message_queue: [],
          cache: [],
          existing_docker: false,
          existing_cicd: "none",
          scan_confidence: 0,
          scanned_at: (data.scanned_at as string) ?? "",
        }
      : null,
    created_at: (data.scanned_at as string) || "",
  };
}

interface ProjectStore {
  projects: Project[];
  currentProject: Project | null;
  isScanning: boolean;
  scanError: string | null;
  loadProjects: () => Promise<void>;
  scanProject: (path: string) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  setCurrentProject: (project: Project | null) => void;
}

export const useProjectStore = create<ProjectStore>((set) => ({
  projects: [],
  currentProject: null,
  isScanning: false,
  scanError: null,

  loadProjects: async () => {
    try {
      const data = await getProjects();
      const projects = (data as Record<string, unknown>[]).map(mapSummaryResponse);
      set({ projects });
    } catch {
      set({ projects: [] });
    }
  },

  scanProject: async (path: string) => {
    set({ isScanning: true, scanError: null });
    try {
      const data = await apiScanProject(path);
      const project = mapScanResponse(data as Record<string, unknown>, path);
      set((s) => ({
        projects: [project, ...s.projects.filter((p) => p.id !== project.id)],
        currentProject: project,
        isScanning: false,
      }));
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ isScanning: false, scanError: msg });
    }
  },

  deleteProject: async (id: string) => {
    try {
      await apiDeleteProject(id);
      set((s) => ({
        projects: s.projects.filter((p) => p.id !== id),
        currentProject: s.currentProject?.id === id ? null : s.currentProject,
      }));
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ scanError: `삭제 실패: ${msg}` });
    }
  },

  setCurrentProject: (project) => set({ currentProject: project }),
}));

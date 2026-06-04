import { useState, useEffect } from "react";
import { FolderOpen, Loader, AlertCircle, Trash2, Copy, Save, RefreshCw, FolderTree, Zap, CheckCircle2 } from "lucide-react";
import { useProjectStore } from "../store/projectStore";
import type { Project } from "../store/projectStore";
import { useProjectPageStore } from "../store/projectPageStore";
import { useActivityStore } from "../store/activityStore";
import { generateDocker, saveDocker, generateCicd, saveCicd, scanWorkspace, getRecommendation, scanProject as apiScanProject } from "../api";

interface DeployCombo {
  id: string;
  deploy_name: string;
  cicd_name: string;
  cicd_id: string;
  platform: string;
  description: string;
  synergy: string;
  pros: string[];
  cons: string[];
  estimated_cost: string;
  complexity: string;
  score: number;
  recommended: boolean;
  traffic_capacity: string;
}

interface Recommendation {
  project_id: string;
  scale: string;
  scale_label: string;
  scale_reason: string;
  infra_count: number;
  dep_count: number;
  infra_services: string[];
  combos: DeployCombo[];
}

interface SubProjectInfo {
  path: string;
  rel_path: string;
  name: string;
  build_file: string;
}

interface WorkspaceResult {
  root: string;
  root_name: string;
  subprojects: SubProjectInfo[];
}

interface WorkspaceProjectState {
  path: string;
  name: string;
  id: string;
  language: string | null;
  framework: string | null;
  recommendation: Recommendation | null;
  scanError: string | null;
  isLoading: boolean;
  quickStartStep: string | null;
  quickStartDone: boolean;
}


async function pickFolder(): Promise<string | null> {
  try {
    const { open } = await import("@tauri-apps/plugin-dialog");
    return await open({ directory: true }) as string | null;
  } catch {
    return null;
  }
}

const CICD_PLATFORMS = [
  { value: "github_actions", label: "GitHub Actions" },
  { value: "gitlab_ci",      label: "GitLab CI" },
  { value: "jenkins",        label: "Jenkins" },
  { value: "azure_devops",   label: "Azure DevOps" },
  { value: "bitbucket",      label: "Bitbucket Pipelines" },
];

export function ProjectPage() {
  const {
    currentProject, isScanning, scanError,
    scanProject, deleteProject, projects, setCurrentProject, loadProjects,
  } = useProjectStore();

  const {
    tab, setTab,
    dockerResults, setDockerResult,
    cicdResults, setCicdResult,
    savedDocker, setSavedDocker,
    savedCicd, setSavedCicd,
  } = useProjectPageStore();

  const { addActivity } = useActivityStore();

  const [manualPath, setManualPath] = useState(currentProject?.path ?? "");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [cicdPlatform, setCicdPlatform] = useState("github_actions");
  const [workspace, setWorkspace] = useState<WorkspaceResult | null>(null);
  const [workspaceProjects, setWorkspaceProjects] = useState<WorkspaceProjectState[]>([]);
  const [isWorkspaceView, setIsWorkspaceView] = useState(false);
  const [isWorkspaceScanning, setIsWorkspaceScanning] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [isLoadingRec, setIsLoadingRec] = useState(false);
  const [selectedComboId, setSelectedComboId] = useState<string | null>(null);
  const [quickStartStep, setQuickStartStep] = useState<string | null>(null);
  const [quickStartDone, setQuickStartDone] = useState(false);

  // 로딩/에러는 일시적 UI 상태라 로컬 유지
  const [isGeneratingDocker, setIsGeneratingDocker] = useState(false);
  const [dockerError, setDockerError] = useState<string | null>(null);
  const [isSavingDocker, setIsSavingDocker] = useState(false);
  const [isGeneratingCicd, setIsGeneratingCicd] = useState(false);
  const [cicdError, setCicdError] = useState<string | null>(null);
  const [isSavingCicd, setIsSavingCicd] = useState(false);

  const pid = currentProject?.id ?? "";
  const dockerResult = dockerResults[pid] ?? null;
  const cicdResult = cicdResults[pid] ?? null;
  const dockerSaved = savedDocker[pid] ?? false;
  const cicdSaved = savedCicd[pid] ?? false;

  const handleScan = async (path: string) => {
    if (!path.trim()) return;
    setWorkspace(null);
    setIsWorkspaceView(false);
    setWorkspaceProjects([]);
    setRecommendation(null);
    setQuickStartDone(false);
    await scanProject(path.trim());
    setTab("recommend");
    addActivity({ type: "scan", title: `프로젝트 스캔`, detail: path.trim(), status: "info" });
  };

  const doAllInOneWorkspace = async (rootName: string, subprojects: SubProjectInfo[]) => {
    if (subprojects.length === 0) return;
    setIsWorkspaceView(true);
    setWorkspaceProjects(
      subprojects.map((sp) => ({
        path: sp.path, name: sp.name, id: "", language: null, framework: null,
        recommendation: null, scanError: null, isLoading: true, quickStartStep: null, quickStartDone: false,
      }))
    );
    await Promise.all(
      subprojects.map(async (sp) => {
        try {
          const proj = await apiScanProject(sp.path) as any;
          const projectId = proj.project_id ?? proj.id;
          const rec = await getRecommendation(projectId) as Recommendation;
          setWorkspaceProjects((prev) =>
            prev.map((wp) =>
              wp.path === sp.path
                ? { ...wp, id: projectId, language: proj.language ?? null, framework: proj.framework ?? null, recommendation: rec, isLoading: false }
                : wp
            )
          );
        } catch (e) {
          setWorkspaceProjects((prev) =>
            prev.map((wp) =>
              wp.path === sp.path
                ? { ...wp, scanError: e instanceof Error ? e.message : String(e), isLoading: false }
                : wp
            )
          );
        }
      })
    );
    // store 프로젝트 목록 갱신 (apiScanProject는 store를 업데이트하지 않으므로)
    await loadProjects();
    addActivity({ type: "scan", title: `워크스페이스 스캔: ${rootName}`, detail: `${subprojects.length}개 프로젝트 분석 완료`, status: "info" });
  };

  const handleWorkspaceRootClick = async () => {
    if (!workspace) return;
    await doAllInOneWorkspace(workspace.root_name, workspace.subprojects);
  };

  const handleScanSubproject = async (path: string) => {
    setIsWorkspaceView(false);
    setManualPath(path);
    await scanProject(path);
    setTab("recommend");
    addActivity({ type: "scan", title: `프로젝트 스캔`, detail: path, status: "info" });
  };

  const handleWorkspaceProjectQuickStart = async (projectPath: string) => {
    const wp = workspaceProjects.find((p) => p.path === projectPath);
    if (!wp?.recommendation || !wp.id) return;
    const combo = wp.recommendation.combos.find((c) => c.recommended) ?? wp.recommendation.combos[0];
    if (!combo) return;

    const upd = (step: string | null) =>
      setWorkspaceProjects((prev) => prev.map((p) => p.path === projectPath ? { ...p, quickStartStep: step } : p));
    const done = () =>
      setWorkspaceProjects((prev) => prev.map((p) => p.path === projectPath ? { ...p, quickStartDone: true, quickStartStep: null } : p));

    upd("Docker 파일 생성 중...");
    try {
      const dockerData = await generateDocker(wp.id) as any;
      upd("Docker 파일 저장 중...");
      await saveDocker(dockerData.generation_id, projectPath);
      upd(`CI/CD (${combo.cicd_name}) 생성 중...`);
      const cicdData = await generateCicd(wp.id, combo.cicd_id) as any;
      upd("CI/CD 파일 저장 중...");
      await saveCicd(cicdData.generation_id, projectPath);
      done();
      addActivity({ type: "docker_gen", title: `빠른 시작 완료: ${wp.name}`, detail: `${combo.deploy_name} + ${combo.cicd_name}`, status: "success" });
    } catch (e) {
      upd(null);
      addActivity({ type: "docker_gen", title: `빠른 시작 실패: ${wp.name}`, detail: String(e), status: "failed" });
    }
  };

  // 페이지 진입 시 프로젝트 목록 로드
  useEffect(() => { loadProjects(); }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  // 프로젝트 변경 시 초기화 + 추천 즉시 로드
  useEffect(() => {
    setRecommendation(null);
    setSelectedComboId(null);
    setQuickStartDone(false);
    if (!currentProject) return;

    setIsLoadingRec(true);
    getRecommendation(currentProject.id)
      .then((data) => {
        const rec = data as Recommendation;
        setRecommendation(rec);
        const defaultCombo = rec.combos.find((c) => c.recommended) ?? rec.combos[0];
        if (defaultCombo) setSelectedComboId(defaultCombo.id);
      })
      .catch(() => setRecommendation(null))
      .finally(() => setIsLoadingRec(false));
  }, [currentProject?.id]);

  const handleQuickStart = async () => {
    if (!currentProject) return;
    const combo = recommendation?.combos.find((c) => c.id === selectedComboId);
    const cicdId = combo?.cicd_id ?? "github_actions";
    setQuickStartStep("Docker 파일 생성 중...");
    setQuickStartDone(false);
    try {
      const dockerData = await generateDocker(currentProject.id) as typeof dockerResult;
      setDockerResult(pid, dockerData);
      setQuickStartStep("Docker 파일 저장 중...");
      await saveDocker(dockerData!.generation_id, currentProject.path);
      setSavedDocker(pid, true);

      setQuickStartStep(`CI/CD (${combo?.cicd_name ?? cicdId}) 생성 중...`);
      const cicdData = await generateCicd(currentProject.id, cicdId) as typeof cicdResult;
      setCicdResult(pid, cicdData);
      setQuickStartStep("CI/CD 파일 저장 중...");
      await saveCicd(cicdData!.generation_id, currentProject.path);
      setSavedCicd(pid, true);

      setQuickStartDone(true);
      addActivity({
        type: "docker_gen",
        title: `빠른 시작 완료: ${currentProject.name}`,
        detail: combo ? `${combo.deploy_name} + ${combo.cicd_name}` : "",
        status: "success",
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      addActivity({ type: "docker_gen", title: `빠른 시작 실패: ${currentProject.name}`, detail: msg, status: "failed" });
    } finally {
      setQuickStartStep(null);
    }
  };

  const handleWorkspaceScan = async () => {
    if (!manualPath.trim()) return;
    setIsWorkspaceScanning(true);
    setWorkspaceError(null);
    try {
      const data = await scanWorkspace(manualPath.trim()) as WorkspaceResult;
      if (data.subprojects.length > 0) {
        setWorkspace(data);
        setIsWorkspaceView(false);
        setWorkspaceProjects([]);
      } else {
        await handleScan(manualPath.trim());
      }
    } catch (e: unknown) {
      setWorkspaceError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsWorkspaceScanning(false);
    }
  };

  const handleFolderPick = async () => {
    const folder = await pickFolder();
    if (folder) {
      setManualPath(folder);
      setIsWorkspaceScanning(true);
      setWorkspaceError(null);
      try {
        const data = await scanWorkspace(folder) as WorkspaceResult;
        if (data.subprojects.length > 0) {
          setWorkspace(data);
          setIsWorkspaceView(false);
          setWorkspaceProjects([]);
        } else {
          await handleScan(folder);
        }
      } catch {
        await handleScan(folder);
      } finally {
        setIsWorkspaceScanning(false);
      }
    }
  };

  const handleDelete = async (id: string) => {
    const name = projects.find((p) => p.id === id)?.name ?? id;
    setDeletingId(id);
    await deleteProject(id);
    setDeletingId(null);
    addActivity({ type: "delete", title: `프로젝트 삭제: ${name}`, detail: "", status: "info" });
  };

  const handleGenerateDocker = async () => {
    if (!currentProject) return;
    setIsGeneratingDocker(true);
    setDockerError(null);
    setSavedDocker(pid, false);
    try {
      const data = await generateDocker(currentProject.id);
      setDockerResult(pid, data as typeof dockerResult);
      addActivity({
        type: "docker_gen",
        title: `Dockerfile 생성: ${currentProject.name}`,
        detail: "",
        status: "success",
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setDockerError(msg);
      addActivity({
        type: "docker_gen",
        title: `Dockerfile 생성 실패: ${currentProject.name}`,
        detail: msg,
        status: "failed",
      });
    } finally {
      setIsGeneratingDocker(false);
    }
  };

  const handleSaveDocker = async () => {
    if (!dockerResult || !currentProject) return;
    setIsSavingDocker(true);
    try {
      await saveDocker(dockerResult.generation_id, currentProject.path);
      setSavedDocker(pid, true);
      addActivity({
        type: "docker_save",
        title: `Dockerfile 저장: ${currentProject.name}`,
        detail: currentProject.path,
        status: "success",
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setDockerError(msg);
      addActivity({
        type: "docker_save",
        title: `Dockerfile 저장 실패: ${currentProject.name}`,
        detail: msg,
        status: "failed",
      });
    } finally {
      setIsSavingDocker(false);
    }
  };

  const handleGenerateCicd = async () => {
    if (!currentProject) return;
    setIsGeneratingCicd(true);
    setCicdError(null);
    setSavedCicd(pid, false);
    try {
      const data = await generateCicd(currentProject.id, cicdPlatform);
      setCicdResult(pid, data as typeof cicdResult);
      addActivity({
        type: "cicd_gen",
        title: `CI/CD 생성 (${cicdPlatform}): ${currentProject.name}`,
        detail: "",
        status: "success",
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setCicdError(msg);
      addActivity({
        type: "cicd_gen",
        title: `CI/CD 생성 실패: ${currentProject.name}`,
        detail: msg,
        status: "failed",
      });
    } finally {
      setIsGeneratingCicd(false);
    }
  };

  const handleSaveCicd = async () => {
    if (!cicdResult || !currentProject) return;
    setIsSavingCicd(true);
    try {
      await saveCicd(cicdResult.generation_id, currentProject.path);
      setSavedCicd(pid, true);
      addActivity({
        type: "cicd_save",
        title: `CI/CD 저장 (${cicdPlatform}): ${currentProject.name}`,
        detail: currentProject.path,
        status: "success",
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setCicdError(msg);
      addActivity({
        type: "cicd_save",
        title: `CI/CD 저장 실패: ${currentProject.name}`,
        detail: msg,
        status: "failed",
      });
    } finally {
      setIsSavingCicd(false);
    }
  };

  const sr = currentProject?.scan_result;

  return (
    <div className="flex flex-col h-full gap-3">
      <h1 className="text-xl font-bold flex-shrink-0">Project Scanner</h1>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* ─── Left: 경로 입력 + 프로젝트 목록 ─── */}
        <div className="w-80 flex-shrink-0 flex flex-col gap-3 min-h-0">
          <div className="bg-gray-800 rounded-lg p-4 space-y-3 flex-shrink-0">
            <div className="flex gap-2">
              <input
                type="text"
                value={manualPath}
                onChange={(e) => setManualPath(e.target.value)}
                placeholder="/path/to/project"
                className="flex-1 bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-brand-500"
                onKeyDown={(e) => e.key === "Enter" && handleScan(manualPath)}
              />
              <button
                onClick={handleFolderPick}
                title="폴더 선택"
                className="flex items-center bg-gray-700 hover:bg-gray-600 px-2.5 py-2 rounded text-sm transition-colors flex-shrink-0"
              >
                <FolderOpen size={16} />
              </button>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleScan(manualPath)}
                disabled={isScanning || !manualPath.trim()}
                className="flex-1 flex items-center justify-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 rounded text-sm transition-colors"
              >
                {isScanning ? <Loader size={16} className="animate-spin" /> : null}
                {isScanning ? "스캔 중..." : "스캔"}
              </button>
              <button
                onClick={handleWorkspaceScan}
                disabled={isWorkspaceScanning || !manualPath.trim()}
                title="워크스페이스 스캔 (서브 프로젝트 트리)"
                className="flex items-center justify-center gap-1 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed px-3 py-2 rounded text-sm transition-colors"
              >
                {isWorkspaceScanning ? <Loader size={16} className="animate-spin" /> : <FolderTree size={16} />}
              </button>
            </div>
            {(scanError || workspaceError) && (
              <div className="flex items-center gap-2 text-red-400 text-xs">
                <AlertCircle size={13} />
                {scanError || workspaceError}
              </div>
            )}
          </div>

          {/* ─── 프로젝트 트리 목록 ─── */}
          {(workspace ? workspace.subprojects.length > 0 : projects.length > 0) && (
            <ProjectTree
              projects={projects}
              currentProject={currentProject}
              workspace={workspace}
              workspaceProjects={workspaceProjects}
              isWorkspaceView={isWorkspaceView}
              deletingId={deletingId}
              onSelect={(p) => { setCurrentProject(p); setManualPath(p.path); setIsWorkspaceView(false); setWorkspaceProjects([]); }}
              onDelete={handleDelete}
              onWorkspaceRootClick={workspace ? handleWorkspaceRootClick : undefined}
              onSubprojectClick={workspace ? handleScanSubproject : undefined}
              onWorkspaceClose={workspace ? () => { setWorkspace(null); setIsWorkspaceView(false); setWorkspaceProjects([]); } : undefined}
              onGroupRootClick={(rootName, items) => {
                const subs: SubProjectInfo[] = items.map((p) => ({ path: p.path, rel_path: p.name, name: p.name, build_file: "" }));
                doAllInOneWorkspace(rootName, subs);
              }}
            />
          )}
        </div>

        {/* ─── Right: 워크스페이스 트리 or 탭 패널 ─── */}
        <div className="flex-1 min-w-0 flex flex-col min-h-0">
          {isWorkspaceView ? (
            <WorkspaceAllInOnePanel
              projects={workspaceProjects}
              onClose={() => { setIsWorkspaceView(false); setWorkspaceProjects([]); }}
              onQuickStart={handleWorkspaceProjectQuickStart}
            />
          ) : currentProject ? (
            <>
              {/* 탭 헤더 */}
              <div className="flex gap-1 mb-3 flex-shrink-0">
                {(["scan", "recommend", "docker", "cicd"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                      tab === t
                        ? "bg-brand-600 text-white"
                        : "bg-gray-800 text-gray-400 hover:text-gray-200"
                    }`}
                  >
                    {t === "scan" ? "스캔 결과" : t === "recommend" ? "추천" : t === "docker" ? "Docker" : "CI/CD"}
                  </button>
                ))}
                <span className="ml-auto text-xs text-gray-600 self-center truncate max-w-xs">
                  {currentProject.name}
                </span>
              </div>

              {/* 탭 콘텐츠 */}
              <div className="flex-1 min-h-0 overflow-y-auto">
                {/* ── 추천 탭 ── */}
                {tab === "recommend" && (
                  <div className="space-y-4">
                    {isLoadingRec && (
                      <div className="flex items-center gap-2 text-gray-400 text-sm">
                        <Loader size={16} className="animate-spin" /> 분석 중...
                      </div>
                    )}
                    {recommendation && (
                      <>
                        {/* 규모 요약 */}
                        <div className="bg-gray-800 rounded-lg p-4">
                          <div className="flex items-center gap-3 mb-2">
                            <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                              recommendation.scale === "small"      ? "bg-green-900 text-green-300" :
                              recommendation.scale === "medium"     ? "bg-blue-900 text-blue-300" :
                              recommendation.scale === "large"      ? "bg-orange-900 text-orange-300" :
                                                                      "bg-red-900 text-red-300"
                            }`}>
                              {recommendation.scale_label}
                            </span>
                            <span className="text-xs text-gray-400">{recommendation.scale_reason}</span>
                          </div>
                          {recommendation.infra_services.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                              {recommendation.infra_services.map((s) => (
                                <span key={s} className="text-xs bg-brand-900/50 text-brand-300 rounded px-2 py-0.5">{s}</span>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* 조합 추천 카드 */}
                        <div className="space-y-2">
                          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">배포 환경 + CI/CD 추천 조합</h3>
                          {recommendation.combos.map((combo) => {
                            const isSelected = selectedComboId === combo.id;
                            return (
                              <div
                                key={combo.id}
                                onClick={() => setSelectedComboId(combo.id)}
                                className={`bg-gray-800 rounded-lg p-4 border cursor-pointer transition-colors ${
                                  isSelected ? "border-brand-400" : "border-gray-700 hover:border-gray-500"
                                }`}
                              >
                                {/* 헤더 */}
                                <div className="flex items-start justify-between mb-2">
                                  <div className="flex items-center gap-2 min-w-0">
                                    <span className={`w-3.5 h-3.5 rounded-full border-2 flex-shrink-0 ${
                                      isSelected ? "border-brand-400 bg-brand-400" : "border-gray-600"
                                    }`} />
                                    <div className="min-w-0">
                                      <span className="text-sm font-semibold text-gray-100">{combo.deploy_name}</span>
                                      <span className="text-gray-500 mx-1.5">+</span>
                                      <span className="text-sm font-semibold text-brand-300">{combo.cicd_name}</span>
                                    </div>
                                    {combo.recommended && (
                                      <span className="text-xs bg-brand-900 text-brand-300 px-2 py-0.5 rounded-full flex-shrink-0">추천</span>
                                    )}
                                  </div>
                                  <div className="flex gap-0.5 flex-shrink-0 ml-2">
                                    {Array.from({ length: 5 }).map((_, i) => (
                                      <span key={i} className={`text-xs ${i < combo.score ? "text-yellow-400" : "text-gray-700"}`}>★</span>
                                    ))}
                                  </div>
                                </div>

                                {/* 설명 */}
                                <p className="text-xs text-gray-400 ml-5 mb-1.5">{combo.description}</p>

                                {/* 시너지 */}
                                <p className="text-xs text-brand-400/80 ml-5 mb-2 italic">⚡ {combo.synergy}</p>

                                {/* 장단점 */}
                                <div className="grid grid-cols-2 gap-2 text-xs ml-5 mb-1.5">
                                  <div className="space-y-0.5">
                                    {combo.pros.map((p) => (
                                      <div key={p} className="text-green-400 flex items-start gap-1">
                                        <span className="flex-shrink-0">✓</span>{p}
                                      </div>
                                    ))}
                                  </div>
                                  <div className="space-y-0.5">
                                    {combo.cons.map((c) => (
                                      <div key={c} className="text-gray-500 flex items-start gap-1">
                                        <span className="flex-shrink-0">−</span>{c}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                                <div className="flex items-center gap-3 ml-5">
                                  <p className="text-xs text-gray-500">{combo.estimated_cost}</p>
                                  {combo.traffic_capacity && (
                                    <p className="text-xs text-cyan-400/80 flex items-center gap-1">
                                      <span>⇅</span>{combo.traffic_capacity}
                                    </p>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>

                        {/* 빠른 시작 */}
                        <div className="bg-gray-800 rounded-lg p-4">
                          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">빠른 시작</h3>
                          {quickStartDone ? (
                            <div className="flex items-center gap-2 text-green-400 text-sm">
                              <CheckCircle2 size={16} />
                              완료! Docker + CI/CD 파일이 프로젝트에 저장됐습니다.
                              <button onClick={() => setTab("docker")} className="ml-auto text-xs text-brand-400 hover:text-brand-300">
                                Docker 확인 →
                              </button>
                            </div>
                          ) : quickStartStep ? (
                            <div className="flex items-center gap-2 text-gray-300 text-sm">
                              <Loader size={14} className="animate-spin flex-shrink-0" />
                              {quickStartStep}
                            </div>
                          ) : (() => {
                            const combo = recommendation.combos.find((c) => c.id === selectedComboId);
                            return (
                              <div className="flex items-center gap-4">
                                <div className="text-xs text-gray-400 flex-1 min-w-0">
                                  {combo ? (
                                    <span>
                                      <span className="text-gray-200 font-medium">{combo.deploy_name}</span>
                                      <span className="text-gray-500 mx-1">+</span>
                                      <span className="text-brand-300 font-medium">{combo.cicd_name}</span>
                                      <span className="text-gray-500"> 조합으로 Docker·CI/CD 파일을 생성하고 저장합니다.</span>
                                    </span>
                                  ) : (
                                    <span className="text-gray-500">조합을 선택하세요.</span>
                                  )}
                                </div>
                                <button
                                  onClick={handleQuickStart}
                                  disabled={!selectedComboId}
                                  className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 rounded text-sm transition-colors flex-shrink-0"
                                >
                                  <Zap size={14} />
                                  빠른 시작
                                </button>
                              </div>
                            );
                          })()}
                        </div>
                      </>
                    )}
                  </div>
                )}

                {/* ── 스캔 결과 탭 ── */}
                {tab === "scan" && sr && (
                  <div className="bg-gray-800 rounded-lg p-4 space-y-4">
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div className="col-span-2">
                        <p className="text-xs text-gray-500">경로</p>
                        <p className="text-gray-200 text-xs font-mono break-all">{currentProject.path}</p>
                      </div>
                      <InfoRow label="언어" value={sr.language} />
                      <InfoRow label="프레임워크" value={sr.framework} />
                      <InfoRow label="빌드 도구" value={sr.build_tool} />
                      <InfoRow label="언어 버전" value={sr.language_version} />
                      <InfoRow label="데이터베이스" value={sr.database.join(", ") || null} />
                      <InfoRow label="캐시/MQ" value={[...sr.message_queue, ...sr.cache].join(", ") || null} />
                      <InfoRow label="기존 Docker" value={sr.existing_docker ? "있음" : "없음"} />
                      <InfoRow label="CI/CD" value={sr.existing_cicd !== "none" ? sr.existing_cicd : null} />
                    </div>
                    {sr.scan_confidence > 0 && (
                      <div className="text-xs text-gray-500">
                        스캔 정확도: {Math.round(sr.scan_confidence * 100)}%
                      </div>
                    )}
                  </div>
                )}

                {/* ── Docker 탭 ── */}
                {tab === "docker" && (
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleGenerateDocker}
                        disabled={isGeneratingDocker}
                        className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 px-4 py-2 rounded text-sm transition-colors"
                      >
                        {isGeneratingDocker
                          ? <Loader size={14} className="animate-spin" />
                          : <RefreshCw size={14} />}
                        {dockerResult ? "재생성" : "Dockerfile 생성"}
                      </button>
                      {dockerResult && (
                        <button
                          onClick={handleSaveDocker}
                          disabled={isSavingDocker || dockerSaved}
                          className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 px-4 py-2 rounded text-sm transition-colors"
                        >
                          <Save size={14} />
                          {dockerSaved ? "저장됨 ✓" : isSavingDocker ? "저장 중..." : "프로젝트에 저장"}
                        </button>
                      )}
                    </div>

                    {dockerError && (
                      <div className="flex items-center gap-2 text-red-400 text-xs">
                        <AlertCircle size={13} /> {dockerError}
                      </div>
                    )}

                    {dockerResult && (
                      <div className="space-y-3">
                        {dockerResult.warnings.length > 0 && (
                          <div className="text-yellow-400 text-xs space-y-1">
                            {dockerResult.warnings.map((w, i) => (
                              <div key={i} className="flex items-start gap-1">
                                <AlertCircle size={12} className="mt-0.5 flex-shrink-0" /> {w}
                              </div>
                            ))}
                          </div>
                        )}
                        <FilePreview title="Dockerfile" content={dockerResult.dockerfile} />
                        {dockerResult.docker_compose && (
                          <FilePreview title="docker-compose.yml" content={dockerResult.docker_compose} />
                        )}
                        <FilePreview title=".dockerignore" content={dockerResult.dockerignore} />
                      </div>
                    )}
                  </div>
                )}

                {/* ── CI/CD 탭 ── */}
                {tab === "cicd" && (
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <select
                        value={cicdPlatform}
                        onChange={(e) => { setCicdPlatform(e.target.value); setCicdResult(pid, null); setSavedCicd(pid, false); }}
                        className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-brand-500"
                      >
                        {CICD_PLATFORMS.map((p) => (
                          <option key={p.value} value={p.value}>{p.label}</option>
                        ))}
                      </select>
                      <button
                        onClick={handleGenerateCicd}
                        disabled={isGeneratingCicd}
                        className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 px-4 py-2 rounded text-sm transition-colors"
                      >
                        {isGeneratingCicd
                          ? <Loader size={14} className="animate-spin" />
                          : <RefreshCw size={14} />}
                        {cicdResult ? "재생성" : "CI/CD 생성"}
                      </button>
                      {cicdResult && (
                        <button
                          onClick={handleSaveCicd}
                          disabled={isSavingCicd || cicdSaved}
                          className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 px-4 py-2 rounded text-sm transition-colors"
                        >
                          <Save size={14} />
                          {cicdSaved ? "저장됨 ✓" : isSavingCicd ? "저장 중..." : "프로젝트에 저장"}
                        </button>
                      )}
                    </div>

                    {cicdError && (
                      <div className="flex items-center gap-2 text-red-400 text-xs">
                        <AlertCircle size={13} /> {cicdError}
                      </div>
                    )}

                    {cicdResult && (
                      <FilePreview title={cicdResult.file_path} content={cicdResult.content} />
                    )}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 bg-gray-800 rounded-lg flex items-center justify-center">
              <p className="text-gray-600 text-sm">프로젝트를 스캔하면 결과가 여기 표시됩니다.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── ProjectTree ────────────────────────────────────────────────
/** 여러 경로의 공통 조상 경로를 반환. 의미 없는 경우(드라이브만 등) null 반환. */
function getCommonRoot(paths: string[]): string | null {
  if (paths.length < 2) return null;
  const norm = paths.map((p) => p.replace(/\\/g, "/"));
  const parts = norm.map((p) => p.split("/"));
  const minLen = Math.min(...parts.map((p) => p.length));
  const common: string[] = [];
  for (let i = 0; i < minLen; i++) {
    if (parts.every((p) => p[i].toLowerCase() === parts[0][i].toLowerCase())) {
      common.push(parts[0][i]);
    } else break;
  }
  const joined = common.join("/");
  if (!joined || /^[A-Za-z]:$/.test(joined) || joined === "/") return null;
  return joined;
}

/** 프로젝트 배열을 공통 조상 경로로 클러스터링해 그룹으로 반환. */
function groupProjects(projects: Project[]): { rootName: string; rootPath: string; items: Project[] }[] {
  if (projects.length === 0) return [];

  const norm = (p: string) => p.replace(/\\/g, "/");
  const allPaths = projects.map((p) => norm(p.path));

  const makeGroup = (rootPath: string, items: Project[]) => ({
    rootName: rootPath.split("/").pop() ?? rootPath,
    rootPath,
    // 루트 경로 자체와 일치하는 프로젝트는 자식에서 제외 (중복 방지)
    items: items.filter((p) => norm(p.path) !== rootPath),
  });

  // 모든 프로젝트가 단일 공통 조상을 가지면 하나의 그룹
  const singleRoot = getCommonRoot(allPaths);
  if (singleRoot) {
    return [makeGroup(singleRoot, projects)];
  }

  // 드라이브/경로가 달라 공통 조상이 없으면 → 클러스터링
  const visited = new Set<number>();
  const groups: { rootName: string; rootPath: string; items: Project[] }[] = [];

  for (let i = 0; i < projects.length; i++) {
    if (visited.has(i)) continue;
    const cluster: number[] = [i];
    visited.add(i);

    for (let j = i + 1; j < projects.length; j++) {
      if (visited.has(j)) continue;
      const clusterPaths = cluster.map((k) => allPaths[k]);
      if (getCommonRoot([...clusterPaths, allPaths[j]])) {
        cluster.push(j);
        visited.add(j);
      }
    }

    const clusterProjects = cluster.map((k) => projects[k]);
    const clusterPaths = cluster.map((k) => allPaths[k]);
    const root = getCommonRoot(clusterPaths) ?? allPaths[cluster[0]].split("/").slice(0, -1).join("/");
    groups.push(makeGroup(root, clusterProjects));
  }

  return groups;
}

function ProjectTree({
  projects,
  currentProject,
  workspace,
  workspaceProjects,
  isWorkspaceView,
  deletingId,
  onSelect,
  onDelete,
  onWorkspaceRootClick,
  onSubprojectClick,
  onWorkspaceClose,
  onGroupRootClick,
}: {
  projects: Project[];
  currentProject: Project | null;
  workspace: WorkspaceResult | null;
  workspaceProjects: WorkspaceProjectState[];
  isWorkspaceView: boolean;
  deletingId: string | null;
  onSelect: (p: Project) => void;
  onDelete: (id: string) => void;
  onWorkspaceRootClick?: () => void;
  onSubprojectClick?: (path: string) => void;
  onWorkspaceClose?: () => void;
  onGroupRootClick?: (rootName: string, items: Project[]) => void;
}) {
  // ── 워크스페이스 모드: 폴더 선택 후 트리 표시 ──
  if (workspace) {
    const displayRoot = workspace.root_name || "워크스페이스";
    return (
      <div className="flex-1 overflow-y-auto min-h-0">
        {/* 워크스페이스 루트 — 클릭 시 전체 올인원 스캔 */}
        <div
          onClick={onWorkspaceRootClick}
          className={`flex items-center gap-1.5 px-2 py-1.5 mt-1 mb-0.5 rounded cursor-pointer transition-colors ${
            isWorkspaceView ? "bg-brand-700" : "hover:bg-gray-700"
          }`}
        >
          <FolderTree size={11} className="text-brand-400 flex-shrink-0" />
          <span className="text-xs font-semibold text-gray-300 truncate flex-1">{displayRoot}</span>
          {onWorkspaceClose && (
            <button
              onClick={(e) => { e.stopPropagation(); onWorkspaceClose!(); }}
              className="text-xs text-gray-600 hover:text-gray-400 flex-shrink-0 px-1"
              title="워크스페이스 닫기"
            >✕</button>
          )}
        </div>
        {/* 서브 프로젝트 목록 — 클릭 시 개별 스캔 */}
        {workspace.subprojects.map((sp, idx) => {
          const isLast = idx === workspace.subprojects.length - 1;
          const wp = workspaceProjects.find((p) => p.path === sp.path);
          const storeP = projects.find((p) => p.path === sp.path);
          const isActive = !isWorkspaceView && currentProject?.id === storeP?.id;
          return (
            <div
              key={sp.path}
              className={`flex items-center rounded text-sm transition-colors ${
                isActive ? "bg-brand-700" : "hover:bg-gray-700"
              }`}
            >
              <span className="pl-3 text-gray-700 font-mono text-xs flex-shrink-0 select-none">
                {isLast ? "└" : "├"}
              </span>
              <button
                onClick={() => onSubprojectClick?.(sp.path)}
                className="flex-1 text-left flex items-center gap-2 px-2 py-2 min-w-0"
              >
                <span className="font-medium truncate flex-1">{sp.name}</span>
                {wp?.language && <span className="text-gray-500 text-xs flex-shrink-0">{wp.language}</span>}
                {wp?.isLoading    && <Loader       size={11} className="animate-spin text-gray-500 flex-shrink-0" />}
                {wp?.quickStartDone && <CheckCircle2 size={11} className="text-green-400 flex-shrink-0" />}
                {wp?.scanError    && <AlertCircle  size={11} className="text-red-400 flex-shrink-0" />}
              </button>
            </div>
          );
        })}
      </div>
    );
  }

  // ── 일반 모드: 경로 클러스터별 트리, 단독 프로젝트는 그대로 ──
  const groups = groupProjects(projects);
  // 자식이 1개 이상인 그룹이 있으면 트리 표시
  const isGrouped = groups.some((g) => g.items.length > 0);

  return (
    <div className="flex-1 overflow-y-auto min-h-0">
      {isGrouped ? (
        groups.map((grp) => (
          <div key={grp.rootName} className="mb-1">
            <div
              onClick={() => onGroupRootClick?.(grp.rootName, grp.items)}
              className="flex items-center gap-1.5 px-2 py-1.5 mt-1 rounded cursor-pointer hover:bg-gray-700 transition-colors"
            >
              <FolderTree size={11} className="text-brand-400 flex-shrink-0" />
              <span className="text-xs font-semibold text-gray-300 truncate flex-1">{grp.rootName}</span>
              <span className="text-xs text-gray-600 flex-shrink-0">{grp.items.length}</span>
            </div>
            {grp.items.map((p, idx) => {
              const isLast = idx === grp.items.length - 1;
              return (
                <div
                  key={p.id}
                  className={`flex items-center rounded text-sm transition-colors ${
                    currentProject?.id === p.id ? "bg-brand-700" : "hover:bg-gray-700"
                  }`}
                >
                  <span className="pl-3 text-gray-700 font-mono text-xs flex-shrink-0 select-none">
                    {isLast ? "└" : "├"}
                  </span>
                  <button
                    onClick={() => onSelect(p)}
                    className="flex-1 text-left flex items-center gap-2 px-2 py-2 min-w-0"
                  >
                    <span className="font-medium truncate flex-1">{p.name}</span>
                    <span className="text-gray-500 text-xs flex-shrink-0">{p.scan_result?.language ?? "?"}</span>
                  </button>
                  <button
                    onClick={() => onDelete(p.id)}
                    disabled={deletingId === p.id}
                    title="삭제"
                    className="px-2 py-2 text-gray-600 hover:text-red-400 disabled:opacity-50 transition-colors flex-shrink-0"
                  >
                    {deletingId === p.id ? <Loader size={13} className="animate-spin" /> : <Trash2 size={13} />}
                  </button>
                </div>
              );
            })}
          </div>
        ))
      ) : (
        // 단독 프로젝트: 그대로 표시
        projects.map((p) => (
          <div
            key={p.id}
            className={`flex items-center rounded text-sm transition-colors ${
              currentProject?.id === p.id ? "bg-brand-700" : "hover:bg-gray-700"
            }`}
          >
            <button
              onClick={() => onSelect(p)}
              className="flex-1 text-left flex items-center gap-2 px-2 py-2 min-w-0"
            >
              <span className="font-medium truncate flex-1">{p.name}</span>
              <span className="text-gray-500 text-xs flex-shrink-0">{p.scan_result?.language ?? "?"}</span>
            </button>
            <button
              onClick={() => onDelete(p.id)}
              disabled={deletingId === p.id}
              title="삭제"
              className="px-2 py-2 text-gray-600 hover:text-red-400 disabled:opacity-50 transition-colors flex-shrink-0"
            >
              {deletingId === p.id ? <Loader size={13} className="animate-spin" /> : <Trash2 size={13} />}
            </button>
          </div>
        ))
      )}
    </div>
  );
}


// ── WorkspaceAllInOnePanel ──────────────────────────────────────
function WorkspaceAllInOnePanel({
  projects,
  onClose,
  onQuickStart,
}: {
  projects: WorkspaceProjectState[];
  onClose: () => void;
  onQuickStart: (path: string) => void;
}) {
  const doneCount = projects.filter((p) => p.quickStartDone).length;
  const loadingCount = projects.filter((p) => p.isLoading).length;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <span className="text-sm font-semibold text-gray-300 flex items-center gap-2">
          <FolderTree size={15} />
          워크스페이스
          <span className="text-xs text-gray-500 font-normal">
            ({projects.length}개 프로젝트
            {loadingCount > 0 ? ` · 분석 중 ${loadingCount}개` : ""}
            {doneCount > 0 ? ` · 완료 ${doneCount}개` : ""})
          </span>
        </span>
        <button onClick={onClose} className="text-xs text-gray-500 hover:text-gray-300 transition-colors">닫기</button>
      </div>
      <div className="flex-1 overflow-y-auto space-y-3">
        {projects.map((wp) => (
          <WorkspaceProjectCard key={wp.path} wp={wp} onQuickStart={onQuickStart} />
        ))}
      </div>
    </div>
  );
}

function WorkspaceProjectCard({
  wp,
  onQuickStart,
}: {
  wp: WorkspaceProjectState;
  onQuickStart: (path: string) => void;
}) {
  const { projects } = useProjectStore();
  const sr = projects.find((p) => p.path === wp.path)?.scan_result ?? null;
  const rec = wp.recommendation;
  const topCombo = rec?.combos.find((c) => c.recommended) ?? rec?.combos[0];
  const infra = [...(sr?.database ?? []), ...(sr?.cache ?? []), ...(sr?.message_queue ?? [])];

  return (
    <div id={`ws-card-${wp.path}`} className="bg-gray-800 rounded-lg p-4">
      {/* 헤더: 프로젝트명 + 규모 */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="font-semibold text-gray-100 truncate">{wp.name}</span>
          <div className="flex gap-1">
            {wp.language && <span className="text-xs bg-gray-700 text-gray-300 rounded px-1.5 py-0.5">{wp.language}</span>}
            {wp.framework && <span className="text-xs bg-brand-900/50 text-brand-400 rounded px-1.5 py-0.5">{wp.framework}</span>}
          </div>
        </div>
        {rec && (
          <span className={`px-2 py-0.5 rounded-full text-xs font-bold flex-shrink-0 ml-2 ${
            rec.scale === "small"  ? "bg-green-900 text-green-300" :
            rec.scale === "medium" ? "bg-blue-900 text-blue-300" :
            rec.scale === "large"  ? "bg-orange-900 text-orange-300" :
                                     "bg-red-900 text-red-300"
          }`}>{rec.scale_label}</span>
        )}
      </div>

      {/* 로딩 / 에러 */}
      {wp.isLoading && (
        <div className="flex items-center gap-2 text-gray-500 text-xs">
          <Loader size={12} className="animate-spin" /> 스캔 및 분석 중...
        </div>
      )}
      {wp.scanError && (
        <div className="text-red-400 text-xs flex items-center gap-1">
          <AlertCircle size={12} /> {wp.scanError}
        </div>
      )}

      {/* 스캔 상세 */}
      {sr && !wp.isLoading && (
        <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs mt-1.5 mb-2">
          {sr.build_tool && <span className="text-gray-500">빌드 <span className="text-gray-300">{sr.build_tool}</span></span>}
          {infra.length > 0 && <span className="text-gray-500">인프라 <span className="text-gray-300">{infra.join(", ")}</span></span>}
          <span className="text-gray-500">Docker <span className={sr.existing_docker ? "text-green-400" : "text-gray-600"}>{sr.existing_docker ? "있음" : "없음"}</span></span>
          {sr.existing_cicd !== "none" && <span className="text-gray-500">CI/CD <span className="text-brand-300">{sr.existing_cicd}</span></span>}
        </div>
      )}

      {/* 추천 조합 */}
      {topCombo && (
        <div className="mt-1 space-y-0.5 border-t border-gray-700 pt-2">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-medium text-gray-200">{topCombo.deploy_name}</span>
            <span className="text-gray-600 text-xs">+</span>
            <span className="text-sm font-medium text-brand-300">{topCombo.cicd_name}</span>
          </div>
          <div className="flex items-center gap-3 text-xs">
            {topCombo.traffic_capacity && <span className="text-cyan-400/80">⇅ {topCombo.traffic_capacity}</span>}
            <span className="text-gray-500">{topCombo.estimated_cost}</span>
          </div>
          <p className="text-xs text-gray-500 line-clamp-1">⚡ {topCombo.synergy}</p>
        </div>
      )}

      {/* 빠른 시작 */}
      <div className="mt-3">
        {wp.quickStartDone ? (
          <div className="flex items-center gap-1.5 text-green-400 text-xs">
            <CheckCircle2 size={13} /> Docker + CI/CD 파일 저장 완료
          </div>
        ) : wp.quickStartStep ? (
          <div className="flex items-center gap-1.5 text-gray-400 text-xs">
            <Loader size={12} className="animate-spin flex-shrink-0" /> {wp.quickStartStep}
          </div>
        ) : (
          <button
            onClick={() => onQuickStart(wp.path)}
            disabled={!topCombo || wp.isLoading || !wp.id}
            className="flex items-center gap-1.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed px-3 py-1.5 rounded text-xs transition-colors"
          >
            <Zap size={12} />
            빠른 시작
          </button>
        )}
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-gray-200">{value}</p>
    </div>
  );
}

function FilePreview({ title, content }: { title: string; content: string }) {
  const handleCopy = () => navigator.clipboard.writeText(content);
  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700">
        <span className="text-xs font-mono text-gray-400">{title}</span>
        <button
          onClick={handleCopy}
          title="복사"
          className="text-gray-600 hover:text-gray-300 transition-colors"
        >
          <Copy size={13} />
        </button>
      </div>
      <pre className="p-3 text-xs font-mono text-gray-300 overflow-x-auto whitespace-pre max-h-80 overflow-y-auto">
        {content}
      </pre>
    </div>
  );
}

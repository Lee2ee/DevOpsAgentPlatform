import { useState } from "react";
import { FolderOpen, Loader, AlertCircle, Trash2, Copy, Save, RefreshCw, FolderTree, ChevronRight, Package } from "lucide-react";
import { useProjectStore } from "../store/projectStore";
import { useProjectPageStore } from "../store/projectPageStore";
import { useActivityStore } from "../store/activityStore";
import { generateDocker, saveDocker, generateCicd, saveCicd, scanWorkspace } from "../api";

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

interface TreeNode {
  name: string;
  path: string;
  isProject: boolean;
  build_file?: string;
  children: TreeNode[];
}

function buildTree(rootName: string, rootPath: string, subprojects: SubProjectInfo[]): TreeNode {
  const root: TreeNode = { name: rootName, path: rootPath, isProject: false, children: [] };
  for (const sp of subprojects) {
    const parts = sp.rel_path ? sp.rel_path.split("/") : [sp.name];
    let node = root;
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLast = i === parts.length - 1;
      let child = node.children.find((c) => c.name === part);
      if (!child) {
        child = { name: part, path: sp.path, isProject: isLast, build_file: isLast ? sp.build_file : undefined, children: [] };
        node.children.push(child);
      } else if (isLast) {
        child.isProject = true;
        child.build_file = sp.build_file;
      }
      node = child;
    }
  }
  return root;
}

const BUILD_FILE_LABELS: Record<string, string> = {
  "pyproject.toml": "Python",
  "requirements.txt": "Python",
  "package.json": "Node.js",
  "pom.xml": "Java",
  "build.gradle": "Java",
  "build.gradle.kts": "Kotlin",
  "Cargo.toml": "Rust",
  "go.mod": "Go",
};

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
    scanProject, deleteProject, projects, setCurrentProject,
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
  const [workspaceResult, setWorkspaceResult] = useState<WorkspaceResult | null>(null);
  const [isWorkspaceScanning, setIsWorkspaceScanning] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);

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
    setWorkspaceResult(null);
    await scanProject(path.trim());
    setTab("scan");
    addActivity({ type: "scan", title: `프로젝트 스캔`, detail: path.trim(), status: "info" });
  };

  const handleWorkspaceScan = async () => {
    if (!manualPath.trim()) return;
    setIsWorkspaceScanning(true);
    setWorkspaceError(null);
    try {
      const data = await scanWorkspace(manualPath.trim()) as WorkspaceResult;
      setWorkspaceResult(data);
      addActivity({ type: "scan", title: `워크스페이스 스캔`, detail: manualPath.trim(), status: "info" });
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
      await handleScan(folder);
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

          {projects.length > 0 && (
            <div className="flex-1 overflow-y-auto min-h-0">
              <h2 className="text-xs font-semibold text-gray-400 mb-2">프로젝트 목록</h2>
              <div className="space-y-1">
                {projects.map((p) => (
                  <div
                    key={p.id}
                    className={`flex items-center rounded text-sm transition-colors ${
                      currentProject?.id === p.id ? "bg-brand-700" : "bg-gray-800 hover:bg-gray-700"
                    }`}
                  >
                    <button
                      onClick={() => { setCurrentProject(p); setManualPath(p.path); }}
                      className="flex-1 text-left flex items-center justify-between px-3 py-2 min-w-0"
                    >
                      <span className="font-medium truncate">{p.name}</span>
                      <span className="text-gray-500 text-xs ml-2 flex-shrink-0">
                        {p.scan_result?.language ?? "?"}
                      </span>
                    </button>
                    <button
                      onClick={() => handleDelete(p.id)}
                      disabled={deletingId === p.id}
                      title="삭제"
                      className="px-2 py-2 text-gray-600 hover:text-red-400 disabled:opacity-50 transition-colors flex-shrink-0"
                    >
                      {deletingId === p.id
                        ? <Loader size={13} className="animate-spin" />
                        : <Trash2 size={13} />}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ─── Right: 워크스페이스 트리 or 탭 패널 ─── */}
        <div className="flex-1 min-w-0 flex flex-col min-h-0">
          {workspaceResult ? (
            <WorkspaceTree
              result={workspaceResult}
              onClose={() => setWorkspaceResult(null)}
              onScan={(path) => { setWorkspaceResult(null); handleScan(path); setManualPath(path); }}
            />
          ) : currentProject ? (
            <>
              {/* 탭 헤더 */}
              <div className="flex gap-1 mb-3 flex-shrink-0">
                {(["scan", "docker", "cicd"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                      tab === t
                        ? "bg-brand-600 text-white"
                        : "bg-gray-800 text-gray-400 hover:text-gray-200"
                    }`}
                  >
                    {t === "scan" ? "스캔 결과" : t === "docker" ? "Docker" : "CI/CD"}
                  </button>
                ))}
                <span className="ml-auto text-xs text-gray-600 self-center truncate max-w-xs">
                  {currentProject.name}
                </span>
              </div>

              {/* 탭 콘텐츠 */}
              <div className="flex-1 min-h-0 overflow-y-auto">
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

// ── WorkspaceTree ──────────────────────────────────────────────
function WorkspaceTree({
  result,
  onClose,
  onScan,
}: {
  result: WorkspaceResult;
  onClose: () => void;
  onScan: (path: string) => void;
}) {
  const tree = buildTree(result.root_name, result.root, result.subprojects);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <span className="text-sm font-semibold text-gray-300 flex items-center gap-2">
          <FolderTree size={15} />
          워크스페이스 트리
          <span className="text-xs text-gray-500 font-normal">({result.subprojects.length}개 서브 프로젝트)</span>
        </span>
        <button onClick={onClose} className="text-xs text-gray-500 hover:text-gray-300 transition-colors">닫기</button>
      </div>
      <div className="flex-1 overflow-y-auto bg-gray-800 rounded-lg p-3">
        <TreeNodeView node={tree} depth={0} onScan={onScan} />
      </div>
    </div>
  );
}

function TreeNodeView({ node, depth, onScan }: { node: TreeNode; depth: number; onScan: (path: string) => void }) {
  const [open, setOpen] = useState(true);
  const hasChildren = node.children.length > 0;
  const indent = depth * 16;

  return (
    <div>
      <div
        className="flex items-center gap-1.5 py-1 px-2 rounded hover:bg-gray-700 group"
        style={{ paddingLeft: `${8 + indent}px` }}
      >
        {hasChildren ? (
          <button onClick={() => setOpen(!open)} className="text-gray-500 hover:text-gray-300 flex-shrink-0">
            <ChevronRight size={13} className={`transition-transform ${open ? "rotate-90" : ""}`} />
          </button>
        ) : (
          <span className="w-[13px] flex-shrink-0" />
        )}

        {node.isProject ? (
          <Package size={13} className="text-brand-400 flex-shrink-0" />
        ) : (
          <FolderOpen size={13} className="text-yellow-500 flex-shrink-0" />
        )}

        <span className={`text-sm ${node.isProject ? "text-gray-100" : "text-gray-400"}`}>
          {node.name}
        </span>

        {node.isProject && node.build_file && (
          <span className="text-xs text-gray-500 ml-1">
            {BUILD_FILE_LABELS[node.build_file] ?? node.build_file}
          </span>
        )}

        {node.isProject && (
          <button
            onClick={() => onScan(node.path)}
            className="ml-auto text-xs text-brand-400 hover:text-brand-300 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
          >
            스캔
          </button>
        )}
      </div>

      {hasChildren && open && (
        <div>
          {node.children.map((child) => (
            <TreeNodeView key={child.path} node={child} depth={depth + 1} onScan={onScan} />
          ))}
        </div>
      )}
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

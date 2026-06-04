import { useEffect, useState } from "react";
import { Rocket, AlertCircle, ChevronDown, ChevronUp, Info } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useProjectStore, type Project } from "../store/projectStore";
import { useSettingsStore, type Server } from "../store/settingsStore";
import { useDeployStore } from "../store/deployStore";
import { DeployProgress } from "../components/deploy/DeployProgress";

export function DeployPage() {
  const navigate = useNavigate();
  const { projects, loadProjects } = useProjectStore();
  const { servers, loadSettings } = useSettingsStore();
  const { isDeploying, startDeploy, clearLogs, activeDeployment } = useDeployStore();

  const [projectId, setProjectId] = useState("");
  const [serverId, setServerId] = useState("");
  const [strategy, setStrategy] = useState("local_build");
  const [healthUrl, setHealthUrl] = useState("");
  const [autoRollback, setAutoRollback] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    loadProjects();
    loadSettings();
  }, [loadProjects, loadSettings]);

  const selectedProject: Project | undefined = projects.find((p) => p.id === projectId);
  const selectedServer: Server | undefined = servers.find((s) => s.id === serverId);

  const handleServerChange = (id: string) => {
    setServerId(id);
    if (!healthUrl) {
      const server = servers.find((s) => s.id === id);
      const port = selectedProject?.scan_result?.app_port;
      if (server && port) {
        setHealthUrl(`http://${server.host}:${port}/health`);
      }
    }
  };

  const handleDeploy = async () => {
    if (!projectId || !serverId) return;
    clearLogs();
    await startDeploy(projectId, serverId, strategy, {
      auto_rollback: autoRollback,
      health_check_url: healthUrl || undefined,
    });
  };

  return (
    <div className="flex flex-col h-full gap-3">
      <h1 className="text-xl font-bold flex-shrink-0">Deploy</h1>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* ─── Left: 배포 설정 ─── */}
        <div className="w-96 flex-shrink-0 overflow-y-auto pr-1">
          <div className="bg-gray-800 rounded-lg p-4 space-y-4">

            {/* ① 프로젝트 선택 */}
            <div className="space-y-1">
              <label className="text-xs text-gray-400">① 배포할 프로젝트</label>
              {projects.length === 0 ? (
                <div className="flex items-center gap-2 text-sm text-yellow-400 bg-yellow-900/20 border border-yellow-800 rounded px-3 py-2">
                  <AlertCircle size={14} className="flex-shrink-0" />
                  <span>
                    스캔된 프로젝트가 없습니다.{" "}
                    <button onClick={() => navigate("/project")} className="underline hover:text-yellow-200">
                      Project 탭에서 먼저 스캔하세요.
                    </button>
                  </span>
                </div>
              ) : (
                <select
                  value={projectId}
                  onChange={(e) => { setProjectId(e.target.value); setServerId(""); setHealthUrl(""); }}
                  className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-brand-500"
                >
                  <option value="">프로젝트 선택...</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} · {p.scan_result?.language ?? "unknown"}{p.scan_result?.framework ? ` / ${p.scan_result.framework}` : ""}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* 프로젝트 정보 카드 */}
            {selectedProject?.scan_result && (
              <div className="bg-gray-900 rounded-lg px-3 py-2.5 grid grid-cols-2 gap-2 text-xs">
                <InfoChip label="언어" value={selectedProject.scan_result.language ?? "-"} />
                <InfoChip label="프레임워크" value={selectedProject.scan_result.framework ?? "-"} />
                <InfoChip label="빌드 도구" value={selectedProject.scan_result.build_tool ?? "-"} />
                <InfoChip label="DB" value={selectedProject.scan_result.database.join(", ") || "-"} />
              </div>
            )}

            {/* ② 서버 선택 */}
            {projectId && (
              <div className="space-y-1">
                <label className="text-xs text-gray-400">② 배포 대상 서버</label>
                {servers.length === 0 ? (
                  <div className="flex items-center gap-2 text-sm text-yellow-400 bg-yellow-900/20 border border-yellow-800 rounded px-3 py-2">
                    <AlertCircle size={14} className="flex-shrink-0" />
                    <span>
                      등록된 서버가 없습니다.{" "}
                      <button onClick={() => navigate("/settings")} className="underline hover:text-yellow-200">
                        Settings에서 추가하세요.
                      </button>
                    </span>
                  </div>
                ) : (
                  <select
                    value={serverId}
                    onChange={(e) => handleServerChange(e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-brand-500"
                  >
                    <option value="">서버 선택...</option>
                    {servers.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} — {s.username}@{s.host}:{s.port}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            )}

            {/* 배포 요약 */}
            {selectedProject && selectedServer && (
              <div className="flex items-start gap-2 bg-blue-900/20 border border-blue-800 rounded px-3 py-2 text-xs text-blue-300">
                <Info size={13} className="mt-0.5 flex-shrink-0" />
                <span>
                  <strong>{selectedProject.name}</strong>을(를){" "}
                  <strong>{selectedServer.username}@{selectedServer.host}</strong>에 배포합니다.
                  {selectedProject.scan_result?.language && (
                    <> ({selectedProject.scan_result.language})</>
                  )}
                </span>
              </div>
            )}

            {/* ③ 고급 옵션 */}
            {projectId && serverId && (
              <div>
                <button
                  onClick={() => setShowAdvanced((v) => !v)}
                  className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
                >
                  {showAdvanced ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                  고급 옵션
                </button>

                {showAdvanced && (
                  <div className="mt-3 space-y-3 pl-3 border-l border-gray-700">
                    <div className="space-y-1">
                      <label className="text-xs text-gray-400">배포 전략</label>
                      <div className="flex gap-4">
                        {[
                          { val: "local_build", label: "로컬 빌드", desc: "이 PC에서 빌드 후 전송" },
                          { val: "remote_build", label: "원격 빌드", desc: "서버에서 직접 빌드" },
                        ].map(({ val, label, desc }) => (
                          <label key={val} className="flex items-start gap-2 cursor-pointer text-sm">
                            <input
                              type="radio"
                              value={val}
                              checked={strategy === val}
                              onChange={() => setStrategy(val)}
                              className="accent-brand-500 mt-0.5"
                            />
                            <span>
                              {label}
                              <span className="block text-xs text-gray-500">{desc}</span>
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs text-gray-400">헬스체크 URL <span className="text-gray-600">(비워두면 스킵)</span></label>
                      <input
                        type="text"
                        value={healthUrl}
                        onChange={(e) => setHealthUrl(e.target.value)}
                        placeholder={`http://${selectedServer?.host ?? "서버IP"}:포트/health`}
                        className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-brand-500"
                      />
                    </div>

                    <label className="flex items-center gap-3 cursor-pointer text-sm">
                      <input
                        type="checkbox"
                        checked={autoRollback}
                        onChange={(e) => setAutoRollback(e.target.checked)}
                        className="accent-brand-500 w-4 h-4"
                      />
                      실패 시 자동 롤백
                    </label>
                  </div>
                )}
              </div>
            )}

            {/* 배포 버튼 */}
            <button
              onClick={handleDeploy}
              disabled={isDeploying || !projectId || !serverId}
              className="w-full flex items-center justify-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed rounded py-2 text-sm font-medium transition-colors"
            >
              <Rocket size={16} />
              {isDeploying ? "배포 중..." : "배포 시작"}
            </button>
          </div>
        </div>

        {/* ─── Right: 배포 진행 ─── */}
        <div className="flex-1 flex flex-col min-w-0 min-h-0">
          {activeDeployment ? (
            <DeployProgress />
          ) : (
            <div className="flex-1 bg-gray-800 rounded-lg flex items-center justify-center">
              <p className="text-gray-600 text-sm">배포를 시작하면 진행 상황이 여기 표시됩니다.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function InfoChip({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-gray-500 mb-0.5">{label}</p>
      <p className="text-gray-200 font-medium">{value}</p>
    </div>
  );
}

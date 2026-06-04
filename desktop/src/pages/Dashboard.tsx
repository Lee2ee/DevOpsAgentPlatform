import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Rocket, FolderSearch, Server, CheckCircle2, XCircle, Info, Loader,
  type LucideProps,
} from "lucide-react";
import type { ForwardRefExoticComponent, RefAttributes } from "react";
import { useProjectStore } from "../store/projectStore";
import { useEngineStore } from "../store/engineStore";
import { useSettingsStore } from "../store/settingsStore";
import { useActivityStore, type ActivityStatus } from "../store/activityStore";
import { useDeployStore } from "../store/deployStore";

function timeAgo(iso: string): string {
  const sec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (sec < 60) return `${sec}초 전`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}분 전`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}시간 전`;
  return `${Math.floor(hr / 24)}일 전`;
}

export function Dashboard() {
  const { isRunning } = useEngineStore();
  const { projects, loadProjects } = useProjectStore();
  const { servers, loadSettings } = useSettingsStore();
  const { activities } = useActivityStore();
  const { isDeploying, activeDeployment } = useDeployStore();
  const navigate = useNavigate();

  useEffect(() => {
    loadProjects();
    loadSettings();
  }, [loadProjects, loadSettings]);

  // 언어 분포 (언어 미확인 프로젝트 제외)
  const langCounts = projects.reduce<Record<string, number>>((acc, p) => {
    const lang = p.scan_result?.language;
    if (!lang) return acc;
    acc[lang] = (acc[lang] ?? 0) + 1;
    return acc;
  }, {});
  const langEntries = Object.entries(langCounts).sort((a, b) => b[1] - a[1]);

  // Docker / CI/CD 현황
  const dockerCount = projects.filter((p) => p.scan_result?.existing_docker).length;
  const cicdCount = projects.filter(
    (p) => p.scan_result?.existing_cicd && p.scan_result.existing_cicd !== "none"
  ).length;

  const recentActivities = activities.slice(0, 8);
  const showDeployBanner = isDeploying || activeDeployment?.status === "running";

  return (
    <div className="flex flex-col h-full gap-4">
      <h1 className="text-xl font-bold flex-shrink-0">Dashboard</h1>

      {/* 상태 카드 */}
      <div className="grid grid-cols-4 gap-3 flex-shrink-0">
        <StatusCard label="Core Engine" value={isRunning ? "실행 중" : "중지됨"} ok={isRunning} />
        <StatusCard label="스캔된 프로젝트" value={`${projects.length}개`} ok />
        <StatusCard label="등록된 서버" value={`${servers.length}개`} ok />
        <StatusCard
          label="마지막 활동"
          value={activities.length > 0 ? timeAgo(activities[0].timestamp) : "없음"}
          ok={activities.length > 0}
        />
      </div>

      {/* 배포 진행 배너 */}
      {showDeployBanner && (
        <div className="bg-blue-900/40 border border-blue-700 rounded-lg px-4 py-2.5 flex items-center gap-3 flex-shrink-0">
          <Loader size={14} className="animate-spin text-blue-400 flex-shrink-0" />
          <span className="text-sm text-blue-200">배포 진행 중...</span>
          <button
            onClick={() => navigate("/deploy")}
            className="ml-auto text-xs text-blue-400 hover:text-blue-200 transition-colors"
          >
            배포 보기 →
          </button>
        </div>
      )}

      <div className="flex gap-4 flex-1 min-h-0">
        {/* 왼쪽: 빠른 실행 + 프로젝트 현황 */}
        <div className="w-52 flex-shrink-0 flex flex-col gap-4">
          <div>
            <h2 className="text-xs font-semibold text-gray-400 mb-2">빠른 실행</h2>
            <div className="flex flex-col gap-2">
              <QuickBtn icon={FolderSearch} label="프로젝트 스캔" onClick={() => navigate("/project")} />
              <QuickBtn icon={Rocket} label="배포 시작" onClick={() => navigate("/deploy")} />
              <QuickBtn icon={Server} label="서버 관리" onClick={() => navigate("/settings")} />
            </div>
          </div>

          {projects.length > 0 && (
            <div className="bg-gray-800 rounded-lg p-3 flex-shrink-0">
              <h2 className="text-xs font-semibold text-gray-400 mb-2">프로젝트 현황</h2>
              <div className="space-y-1.5 text-xs mb-3">
                <div className="flex justify-between">
                  <span className="text-gray-500">Docker 설정됨</span>
                  <span className="text-green-400 font-medium">{dockerCount} / {projects.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">CI/CD 설정됨</span>
                  <span className="text-brand-300 font-medium">{cicdCount} / {projects.length}</span>
                </div>
              </div>
              {langEntries.length > 0 && (
                <>
                  <p className="text-xs text-gray-600 mb-1.5">언어 분포</p>
                  <div className="space-y-1.5">
                    {langEntries.slice(0, 5).map(([lang, count]) => (
                      <div key={lang} className="flex items-center gap-2 text-xs">
                        <div className="flex-1 bg-gray-900 rounded-full h-1.5 overflow-hidden">
                          <div
                            className="h-full bg-brand-500 rounded-full"
                            style={{ width: `${Math.round((count / projects.length) * 100)}%` }}
                          />
                        </div>
                        <span className="text-gray-400 w-14 truncate text-right">{lang}</span>
                        <span className="text-gray-600 w-3 text-right">{count}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* 가운데: 최근 프로젝트 */}
        <div className="flex-1 bg-gray-800 rounded-lg p-4 flex flex-col min-h-0 min-w-0">
          <h2 className="text-xs font-semibold text-gray-400 mb-3 flex-shrink-0">최근 프로젝트</h2>
          {projects.length > 0 ? (
            <div className="space-y-1.5 overflow-y-auto flex-1 min-h-0">
              {projects.slice(0, 10).map((p) => (
                <div
                  key={p.id}
                  onClick={() => navigate("/project")}
                  className="flex items-center gap-3 bg-gray-900 hover:bg-gray-700 rounded px-3 py-2 text-sm cursor-pointer transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-100 truncate">{p.name}</p>
                    <p className="text-gray-600 text-xs truncate">{p.path}</p>
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    {p.scan_result?.language && (
                      <span className="text-xs bg-gray-800 text-gray-400 rounded px-1.5 py-0.5">
                        {p.scan_result.language}
                      </span>
                    )}
                    {p.scan_result?.framework && (
                      <span className="text-xs bg-brand-900/50 text-brand-400 rounded px-1.5 py-0.5">
                        {p.scan_result.framework}
                      </span>
                    )}
                    {p.scan_result?.existing_docker && (
                      <span className="text-xs text-green-500" title="Docker 있음">🐳</span>
                    )}
                  </div>
                  {p.created_at && (
                    <span className="text-xs text-gray-600 flex-shrink-0 w-14 text-right">
                      {timeAgo(p.created_at)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-gray-600 text-sm">스캔된 프로젝트가 없습니다.</p>
            </div>
          )}
        </div>

        {/* 오른쪽: 최근 활동 */}
        <div className="w-60 flex-shrink-0 bg-gray-800 rounded-lg p-4 flex flex-col min-h-0">
          <h2 className="text-xs font-semibold text-gray-400 mb-3 flex-shrink-0">최근 활동</h2>
          {recentActivities.length > 0 ? (
            <div className="space-y-2.5 overflow-y-auto flex-1 min-h-0">
              {recentActivities.map((a) => (
                <div key={a.id} className="flex items-start gap-2 text-xs">
                  <ActivityIcon status={a.status} />
                  <div className="flex-1 min-w-0">
                    <p className="text-gray-200 truncate leading-4">{a.title}</p>
                    {a.detail && <p className="text-gray-600 truncate">{a.detail}</p>}
                    <p className="text-gray-700">{timeAgo(a.timestamp)}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-gray-600 text-sm text-center">활동 기록이 없습니다.</p>
            </div>
          )}
          {activities.length > 8 && (
            <button
              onClick={() => navigate("/activity")}
              className="mt-2 pt-2 border-t border-gray-700 text-xs text-gray-500 hover:text-gray-300 transition-colors flex-shrink-0"
            >
              전체 보기 ({activities.length}개) →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function ActivityIcon({ status }: { status: ActivityStatus }) {
  if (status === "success") return <CheckCircle2 size={13} className="text-green-400 flex-shrink-0 mt-0.5" />;
  if (status === "failed") return <XCircle size={13} className="text-red-400 flex-shrink-0 mt-0.5" />;
  return <Info size={13} className="text-blue-400 flex-shrink-0 mt-0.5" />;
}

function StatusCard({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className={`text-lg font-semibold ${ok ? "text-green-400" : "text-red-400"}`}>{value}</p>
    </div>
  );
}

function QuickBtn({
  icon: Icon,
  label,
  onClick,
}: {
  icon: ForwardRefExoticComponent<Omit<LucideProps, "ref"> & RefAttributes<SVGSVGElement>>;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 rounded-lg px-4 py-3 text-sm transition-colors w-full"
    >
      <Icon size={16} />
      {label}
    </button>
  );
}

import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Rocket, FolderSearch, Server, type LucideProps } from "lucide-react";
import type { ForwardRefExoticComponent, RefAttributes } from "react";
import { useProjectStore } from "../store/projectStore";
import { useEngineStore } from "../store/engineStore";
import { useSettingsStore } from "../store/settingsStore";

export function Dashboard() {
  const { isRunning } = useEngineStore();
  const { projects, loadProjects } = useProjectStore();
  const { servers, loadSettings } = useSettingsStore();
  const navigate = useNavigate();

  useEffect(() => {
    loadProjects();
    loadSettings();
  }, [loadProjects, loadSettings]);

  return (
    <div className="flex flex-col h-full gap-4">
      <h1 className="text-xl font-bold flex-shrink-0">Dashboard</h1>

      {/* 시스템 상태 */}
      <div className="grid grid-cols-3 gap-4 flex-shrink-0">
        <StatusCard
          label="Core Engine"
          value={isRunning ? "실행 중" : "중지됨"}
          ok={isRunning}
        />
        <StatusCard label="등록 프로젝트" value={`${projects.length}개`} ok />
        <StatusCard label="등록 서버" value={`${servers.length}개`} ok />
      </div>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* 빠른 실행 */}
        <div className="w-52 flex-shrink-0 flex flex-col gap-3">
          <h2 className="text-xs font-semibold text-gray-400">빠른 실행</h2>
          <div className="flex flex-col gap-2">
            <QuickBtn icon={FolderSearch} label="프로젝트 스캔" onClick={() => navigate("/project")} />
            <QuickBtn icon={Rocket} label="배포 시작" onClick={() => navigate("/deploy")} />
            <QuickBtn icon={Server} label="서버 관리" onClick={() => navigate("/settings")} />
          </div>
        </div>

        {/* 최근 프로젝트 */}
        <div className="flex-1 bg-gray-800 rounded-lg p-4 flex flex-col min-h-0 min-w-0">
          <h2 className="text-xs font-semibold text-gray-400 mb-3 flex-shrink-0">최근 프로젝트</h2>
          {projects.length > 0 ? (
            <div className="space-y-2 overflow-y-auto flex-1 min-h-0">
              {projects.slice(0, 10).map((p) => (
                <div
                  key={p.id}
                  className="flex items-center justify-between bg-gray-900 rounded px-4 py-2 text-sm"
                >
                  <span className="font-medium">{p.name}</span>
                  <span className="text-gray-500 text-xs truncate max-w-xs mx-4">{p.path}</span>
                  <span className="text-xs text-gray-400 flex-shrink-0">
                    {p.scan_result?.language ?? "unknown"}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-gray-600 text-sm">스캔된 프로젝트가 없습니다.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusCard({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className={`text-lg font-semibold ${ok ? "text-green-400" : "text-red-400"}`}>
        {value}
      </p>
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

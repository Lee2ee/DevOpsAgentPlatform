import { useEffect, useRef } from "react";
import { CheckCircle, XCircle, Loader, Circle } from "lucide-react";
import { useDeployStore, type DeployStep } from "../../store/deployStore";

const STEP_ORDER = ["precheck", "build", "transfer", "deploy", "healthcheck", "rollback"];

function StepIcon({ status }: { status: DeployStep["status"] }) {
  switch (status) {
    case "done":
      return <CheckCircle size={16} className="text-green-400" />;
    case "failed":
      return <XCircle size={16} className="text-red-400" />;
    case "running":
      return <Loader size={16} className="text-blue-400 animate-spin" />;
    default:
      return <Circle size={16} className="text-gray-600" />;
  }
}

export function DeployProgress() {
  const { activeDeployment, logs } = useDeployStore();
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  if (!activeDeployment) return null;

  const stepMap = new Map(
    (activeDeployment.steps ?? []).map((s) => [s.name, s])
  );

  return (
    <div className="h-full flex flex-col gap-3">
      {/* 단계 진행 표시 */}
      <div className="flex items-center gap-2 flex-wrap flex-shrink-0">
        {STEP_ORDER.map((name, idx) => {
          const step = stepMap.get(name);
          const status = step?.status ?? "pending";
          return (
            <div key={name} className="flex flex-col gap-1">
              <div className="flex items-center gap-1">
                {idx > 0 && <span className="text-gray-700 text-xs">→</span>}
                <div className="flex items-center gap-1 bg-gray-800 rounded px-2 py-1">
                  <StepIcon status={status as DeployStep["status"]} />
                  <span className="text-xs capitalize text-gray-300">{name}</span>
                  {step?.duration_sec != null && (
                    <span className="text-xs text-gray-500">{step.duration_sec}s</span>
                  )}
                </div>
              </div>
              {status === "failed" && step?.error && (
                <div className="text-xs text-red-400 bg-red-900/20 rounded px-2 py-1 max-w-xs whitespace-pre-wrap">
                  {step.error}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* 전체 상태 배너 */}
      {activeDeployment.status === "success" && (
        <div className="flex-shrink-0 bg-green-900/40 border border-green-700 rounded p-3 text-green-300 text-sm">
          배포 성공! 서비스 URL: {activeDeployment.service_url ?? "-"}
        </div>
      )}
      {activeDeployment.status === "failed" && (
        <div className="flex-shrink-0 bg-red-900/40 border border-red-700 rounded p-3 text-red-300 text-sm">
          배포 실패: {activeDeployment.error_message ?? "알 수 없는 오류"}
        </div>
      )}

      {/* 로그 콘솔 */}
      <div
        ref={logRef}
        className="flex-1 min-h-0 bg-black rounded p-3 overflow-y-auto font-mono text-xs text-gray-300 space-y-0.5"
      >
        {logs.length === 0 ? (
          <span className="text-gray-600">로그 대기 중...</span>
        ) : (
          logs.map((line, i) => (
            <div
              key={i}
              className={
              /\berror\b|\bError\b|\bERROR\b|\bfailed\b|\bFailed\b|\bFAILED\b/.test(line)
                ? "text-red-400"
                : line.startsWith("[stderr]")
                ? "text-yellow-400"
                : ""
            }
            >
              {line}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

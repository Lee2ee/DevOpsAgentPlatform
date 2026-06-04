import { CheckCircle, XCircle, Info, Trash2 } from "lucide-react";
import { useActivityStore, type Activity, type ActivityStatus } from "../store/activityStore";

function StatusIcon({ status }: { status: ActivityStatus }) {
  switch (status) {
    case "success":
      return <CheckCircle size={14} className="text-green-400 flex-shrink-0 mt-0.5" />;
    case "failed":
      return <XCircle size={14} className="text-red-400 flex-shrink-0 mt-0.5" />;
    default:
      return <Info size={14} className="text-blue-400 flex-shrink-0 mt-0.5" />;
  }
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function ActivityRow({ activity: a }: { activity: Activity }) {
  return (
    <div className="flex items-start gap-3 bg-gray-800 rounded px-3 py-2.5 text-sm">
      <StatusIcon status={a.status} />
      <div className="flex-1 min-w-0">
        <p className="text-gray-200 font-medium leading-snug">{a.title}</p>
        {a.detail && (
          <p className="text-gray-500 text-xs mt-0.5 break-all">{a.detail}</p>
        )}
      </div>
      <span className="text-gray-600 text-xs flex-shrink-0 whitespace-nowrap">
        {formatTime(a.timestamp)}
      </span>
    </div>
  );
}

export function ActivityPage() {
  const { activities, clearActivities } = useActivityStore();

  return (
    <div className="flex flex-col h-full gap-3">
      <div className="flex items-center justify-between flex-shrink-0">
        <h1 className="text-xl font-bold">Activity</h1>
        {activities.length > 0 && (
          <button
            onClick={clearActivities}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-red-400 transition-colors"
          >
            <Trash2 size={13} />
            전체 삭제
          </button>
        )}
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        {activities.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <p className="text-gray-600 text-sm">기록된 작업이 없습니다.</p>
          </div>
        ) : (
          <div className="space-y-1">
            {activities.map((a) => (
              <ActivityRow key={a.id} activity={a} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

import { useEffect } from "react";
import { useEngineStore } from "../../store/engineStore";

export function Header() {
  const { isRunning, version, checkStatus } = useEngineStore();

  useEffect(() => {
    checkStatus();
    const id = setInterval(checkStatus, 10_000);
    return () => clearInterval(id);
  }, [checkStatus]);

  return (
    <header className="h-10 flex items-center justify-between px-4 bg-gray-800 border-b border-gray-700 flex-shrink-0">
      <span className="text-gray-400 text-sm font-semibold tracking-wide">
        AI DevOps Agent Platform
      </span>
      <div className="flex items-center gap-3">
        <span className="text-xs text-gray-400">Core Engine</span>
        <span
          className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${
            isRunning
              ? "bg-green-900 text-green-300"
              : "bg-red-900 text-red-300"
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              isRunning ? "bg-green-400" : "bg-red-400"
            }`}
          />
          {isRunning ? `running v${version}` : "stopped"}
        </span>
      </div>
    </header>
  );
}

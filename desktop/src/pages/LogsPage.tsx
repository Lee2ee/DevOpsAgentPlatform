import { useState } from "react";
import { Search, Zap, Wrench } from "lucide-react";
import { analyzeLog, generatePatches } from "../api";

interface DetectedError {
  name: string;
  severity: string;
  category: string;
  suggestion: string;
  matched_lines: string[];
}

interface Patch {
  id: string;
  file_path: string;
  description: string;
  diff_content: string;
  confidence: number;
}

const SEV_COLOR: Record<string, string> = {
  critical: "text-red-400 bg-red-900/30",
  high: "text-orange-400 bg-orange-900/30",
  medium: "text-yellow-400 bg-yellow-900/30",
  low: "text-green-400 bg-green-900/30",
};

export function LogsPage() {
  const [logText, setLogText] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [errors, setErrors] = useState<DetectedError[]>([]);
  const [severity, setSeverity] = useState("");
  const [aiSummary, setAiSummary] = useState("");
  const [patches, setPatches] = useState<Patch[]>([]);
  const [isPatching, setIsPatching] = useState(false);

  const handleAnalyze = async () => {
    if (!logText.trim()) return;
    setIsAnalyzing(true);
    setPatches([]);
    try {
      const data = await analyzeLog(logText, false);
      setAnalysisId(data.analysis_id);
      setErrors(data.detected_errors ?? []);
      setSeverity(data.overall_severity ?? "");
      setAiSummary(data.ai_summary ?? "");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleGeneratePatch = async () => {
    if (!analysisId) return;
    setIsPatching(true);
    try {
      const data = await generatePatches(analysisId, false);
      setPatches(data ?? []);
    } finally {
      setIsPatching(false);
    }
  };

  const hasResults = errors.length > 0 || patches.length > 0;

  return (
    <div className="flex flex-col h-full gap-3">
      <h1 className="text-xl font-bold flex-shrink-0">Logs & Analysis</h1>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* ─── Left: 로그 입력 ─── */}
        <div className="w-96 flex-shrink-0 flex flex-col min-h-0">
          <div className="flex-1 bg-gray-800 rounded-lg p-4 flex flex-col gap-3 min-h-0">
            <label className="text-xs text-gray-400 flex-shrink-0">로그 붙여넣기</label>
            <textarea
              value={logText}
              onChange={(e) => setLogText(e.target.value)}
              placeholder="docker logs, journalctl 출력, 에러 메시지 등을 붙여넣으세요..."
              className="flex-1 min-h-0 w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-xs font-mono text-gray-300 focus:outline-none focus:border-brand-500 resize-none"
            />
            <button
              onClick={handleAnalyze}
              disabled={isAnalyzing || !logText.trim()}
              className="flex-shrink-0 flex items-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 rounded text-sm transition-colors"
            >
              <Search size={14} />
              {isAnalyzing ? "분석 중..." : "장애 분석"}
            </button>
          </div>
        </div>

        {/* ─── Right: 분석 결과 ─── */}
        <div className="flex-1 min-w-0 overflow-y-auto space-y-4">
          {!hasResults ? (
            <div className="h-full bg-gray-800 rounded-lg flex items-center justify-center">
              <p className="text-gray-600 text-sm">로그를 붙여넣고 분석하면 결과가 여기 표시됩니다.</p>
            </div>
          ) : (
            <>
              {/* 탐지된 에러 */}
              {errors.length > 0 && (
                <div className="bg-gray-800 rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h2 className="font-semibold">탐지된 에러</h2>
                    <span className={`text-xs px-2 py-0.5 rounded ${SEV_COLOR[severity] ?? "text-gray-400"}`}>
                      {severity.toUpperCase()}
                    </span>
                  </div>

                  <div className="space-y-2">
                    {errors.map((e, i) => (
                      <div key={i} className="bg-gray-900 rounded p-3 space-y-1">
                        <div className="flex items-center gap-2">
                          <span className={`text-xs px-1.5 py-0.5 rounded ${SEV_COLOR[e.severity] ?? ""}`}>
                            {e.severity}
                          </span>
                          <span className="font-medium text-sm">{e.name}</span>
                          <span className="text-xs text-gray-500">({e.category})</span>
                        </div>
                        <p className="text-xs text-gray-400">{e.suggestion}</p>
                        {e.matched_lines.length > 0 && (
                          <div className="bg-gray-950 rounded p-2 font-mono text-xs text-yellow-300 space-y-0.5">
                            {e.matched_lines.map((l, j) => <div key={j}>{l}</div>)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {aiSummary && (
                    <div className="bg-blue-900/20 border border-blue-800 rounded p-3 text-sm text-blue-300 whitespace-pre-wrap">
                      {aiSummary}
                    </div>
                  )}

                  <button
                    onClick={handleGeneratePatch}
                    disabled={isPatching}
                    className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 px-3 py-1.5 rounded text-sm transition-colors"
                  >
                    <Zap size={14} />
                    {isPatching ? "패치 생성 중..." : "패치 제안 생성"}
                  </button>
                </div>
              )}

              {/* 패치 뷰어 */}
              {patches.length > 0 && (
                <div className="space-y-3">
                  {patches.map((p, i) => (
                    <div key={p.id} className="bg-gray-800 rounded-lg p-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">
                          패치 {i + 1}: {p.file_path}
                        </span>
                        <span className="text-xs text-gray-400">
                          신뢰도 {Math.round(p.confidence * 100)}%
                        </span>
                      </div>
                      <p className="text-xs text-gray-400">{p.description}</p>
                      <pre className="bg-gray-900 rounded p-3 text-xs font-mono text-green-300 overflow-x-auto">
                        {p.diff_content}
                      </pre>
                      <button className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 px-3 py-1.5 rounded text-xs transition-colors">
                        <Wrench size={12} />
                        패치 적용
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

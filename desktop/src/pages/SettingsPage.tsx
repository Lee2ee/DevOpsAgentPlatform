import { useEffect, useState } from "react";
import { Plus, Trash2, CheckCircle, XCircle, HelpCircle, Pencil, X, Loader } from "lucide-react";
import { useSettingsStore, type AIConfig, type Server } from "../store/settingsStore";
import { checkHealth } from "../api";

// ── Provider 메타데이터 ────────────────────────────────────────
interface ProviderMeta {
  label: string;
  defaultModel: string;
  models: string[];
  needsApiKey: boolean;
  needsBaseUrl: boolean;
  help: string;
  apiKeyHint: string;
  apiKeyLink?: string;
}

const PROVIDERS: Record<string, ProviderMeta> = {
  ollama: {
    label: "Ollama (로컬)",
    defaultModel: "qwen2.5-coder:7b",
    models: ["qwen2.5-coder:7b", "qwen2.5-coder:14b", "codellama:7b", "llama3.2:3b", "llama3.1:8b", "gemma2:9b"],
    needsApiKey: false,
    needsBaseUrl: true,
    help: "로컬 PC에서 AI 모델을 실행합니다. API 비용이 없고 인터넷 연결이 불필요합니다. ollama.ai에서 Ollama를 설치한 뒤 원하는 모델을 pull 해야 합니다.\n예) ollama pull qwen2.5-coder:7b",
    apiKeyHint: "",
  },
  openai: {
    label: "OpenAI",
    defaultModel: "gpt-4o-mini",
    models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    needsApiKey: true,
    needsBaseUrl: false,
    help: "OpenAI API를 통해 GPT 모델을 사용합니다. 사용량에 따라 과금됩니다.",
    apiKeyHint: "sk-...으로 시작하는 키",
    apiKeyLink: "https://platform.openai.com/api-keys",
  },
  anthropic: {
    label: "Anthropic (Claude)",
    defaultModel: "claude-sonnet-4-6",
    models: ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
    needsApiKey: true,
    needsBaseUrl: false,
    help: "Anthropic의 Claude 모델을 사용합니다. 코드 이해와 분석에 강점이 있습니다.",
    apiKeyHint: "sk-ant-...으로 시작하는 키",
    apiKeyLink: "https://console.anthropic.com/settings/keys",
  },
  groq: {
    label: "Groq",
    defaultModel: "llama-3.3-70b-versatile",
    models: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
    needsApiKey: true,
    needsBaseUrl: false,
    help: "Groq의 고속 추론 클라우드를 사용합니다. 무료 티어를 제공하며 응답 속도가 매우 빠릅니다. LLaMA, Mixtral 등 오픈소스 모델을 사용합니다.",
    apiKeyHint: "gsk_...으로 시작하는 키",
    apiKeyLink: "https://console.groq.com/keys",
  },
};

export function SettingsPage() {
  const { aiConfig, servers, loadSettings, updateAiConfig, addServer, updateServer, deleteServer } =
    useSettingsStore();

  const [ai, setAi] = useState<AIConfig>(aiConfig);
  const [aiSaved, setAiSaved] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [customModel, setCustomModel] = useState(false);

  // 서버 추가 폼
  const [showAddServer, setShowAddServer] = useState(false);
  const [newServer, setNewServer] = useState({
    name: "", host: "", port: 22, username: "", password: "", credential_id: null as string | null,
  });

  // 서버 수정 상태
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ name: "", host: "", port: 22, username: "", password: "" });
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => { loadSettings(); }, [loadSettings]);
  useEffect(() => {
    setAi(aiConfig);
    setCustomModel(!Object.values(PROVIDERS).some((p) => p.models.includes(aiConfig.model)));
  }, [aiConfig]);

  const meta = PROVIDERS[ai.provider] ?? PROVIDERS.ollama;

  const handleProviderChange = (p: string) => {
    const next = PROVIDERS[p] ?? PROVIDERS.ollama;
    setAi((a) => ({ ...a, provider: p, model: next.defaultModel, base_url: a.base_url }));
    setCustomModel(false);
    setShowHelp(false);
  };

  const handleSaveAi = async () => {
    await updateAiConfig(ai);
    setAiSaved(true);
    setTimeout(() => setAiSaved(false), 2000);
  };

  const handleAddServer = async () => {
    if (!newServer.name || !newServer.host || !newServer.username) return;
    await addServer(newServer as Omit<Server, "id">);
    setNewServer({ name: "", host: "", port: 22, username: "", password: "", credential_id: null });
    setShowAddServer(false);
  };

  const handleStartEdit = (s: Server) => {
    setEditingId(s.id);
    setEditForm({ name: s.name, host: s.host, port: s.port, username: s.username, password: "" });
  };

  const handleSaveEdit = async () => {
    if (!editingId || !editForm.name || !editForm.host || !editForm.username) return;
    setIsSavingEdit(true);
    try {
      await updateServer(editingId, { ...editForm, credential_id: null });
      setEditingId(null);
    } finally {
      setIsSavingEdit(false);
    }
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await deleteServer(id);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="flex flex-col h-full gap-3">
      <h1 className="text-xl font-bold flex-shrink-0">Settings</h1>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* ─── Left: AI Provider ─── */}
        <div className="w-96 flex-shrink-0 overflow-y-auto pr-1">
          <section className="bg-gray-800 rounded-lg p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">AI Provider</h2>
              <button
                onClick={() => setShowHelp((v) => !v)}
                className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-200 transition-colors"
              >
                <HelpCircle size={14} />
                도움말
              </button>
            </div>

            {/* 도움말 패널 */}
            {showHelp && (
              <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 text-xs text-gray-300 space-y-2">
                <p className="font-semibold text-gray-200">{meta.label}</p>
                <p className="whitespace-pre-line leading-relaxed">{meta.help}</p>
                {meta.apiKeyLink && (
                  <p>
                    API Key 발급:{" "}
                    <span className="text-brand-500 font-mono">{meta.apiKeyLink}</span>
                  </p>
                )}
              </div>
            )}

            <div className="space-y-4 text-sm">
              {/* Provider 선택 */}
              <div className="space-y-2">
                <label className="text-xs text-gray-400">Provider</label>
                {Object.entries(PROVIDERS).map(([key, info]) => (
                  <label
                    key={key}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border cursor-pointer transition-colors ${
                      ai.provider === key
                        ? "border-brand-500 bg-brand-600/10 text-white"
                        : "border-gray-700 bg-gray-900 text-gray-300 hover:border-gray-500"
                    }`}
                  >
                    <input
                      type="radio"
                      name="provider"
                      value={key}
                      checked={ai.provider === key}
                      onChange={() => handleProviderChange(key)}
                      className="accent-brand-500"
                    />
                    <div>
                      <span className="font-medium">{info.label}</span>
                      <span className="ml-2 text-xs text-gray-500">
                        {info.needsApiKey ? "API Key 필요" : "로컬 실행"}
                      </span>
                    </div>
                  </label>
                ))}
              </div>

              {/* 모델 선택 드롭다운 */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-xs text-gray-400">Model</label>
                  <button
                    onClick={() => setCustomModel((v) => !v)}
                    className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
                  >
                    {customModel ? "▾ 목록에서 선택" : "✎ 직접 입력"}
                  </button>
                </div>
                {customModel ? (
                  <input
                    type="text"
                    value={ai.model}
                    onChange={(e) => setAi((a) => ({ ...a, model: e.target.value }))}
                    placeholder="모델명 직접 입력"
                    className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-brand-500"
                  />
                ) : (
                  <select
                    value={meta.models.includes(ai.model) ? ai.model : meta.defaultModel}
                    onChange={(e) => setAi((a) => ({ ...a, model: e.target.value }))}
                    className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-brand-500"
                  >
                    {meta.models.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                )}
              </div>

              {/* Ollama: Base URL */}
              {meta.needsBaseUrl && (
                <Field
                  label="Ollama Base URL"
                  value={ai.base_url}
                  onChange={(v) => setAi((a) => ({ ...a, base_url: v }))}
                  placeholder="http://localhost:11434"
                />
              )}

              {/* API Key */}
              {meta.needsApiKey && (
                <div className="space-y-1">
                  <label className="text-xs text-gray-400">
                    API Key
                    {meta.apiKeyHint && (
                      <span className="ml-2 text-gray-500">({meta.apiKeyHint})</span>
                    )}
                  </label>
                  <input
                    type="password"
                    value={ai.api_key ?? ""}
                    onChange={(e) => setAi((a) => ({ ...a, api_key: e.target.value }))}
                    placeholder={ai.has_api_key ? "••••••••  (변경하려면 새 키 입력)" : "입력 후 저장하면 암호화됩니다"}
                    className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-brand-500"
                  />
                  {ai.has_api_key && !ai.api_key && (
                    <p className="text-xs text-green-500">✓ API Key가 저장되어 있습니다</p>
                  )}
                </div>
              )}
            </div>

            <button
              onClick={handleSaveAi}
              className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 px-4 py-2 rounded text-sm transition-colors"
            >
              {aiSaved ? <CheckCircle size={14} /> : null}
              {aiSaved ? "저장됨" : "저장"}
            </button>
          </section>
        </div>

        {/* ─── Right: 서버 관리 + Engine 상태 ─── */}
        <div className="flex-1 flex flex-col gap-4 overflow-y-auto min-w-0">
          {/* 서버 관리 */}
          <section className="bg-gray-800 rounded-lg p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-semibold">배포 대상 서버</h2>
                <p className="text-xs text-gray-500 mt-0.5">SSH로 접근 가능한 Linux 서버 (AWS EC2, GCP, 온프레미스 등)</p>
              </div>
              <button
                onClick={() => setShowAddServer((v) => !v)}
                className="flex items-center gap-1 bg-gray-700 hover:bg-gray-600 px-3 py-1.5 rounded text-xs transition-colors flex-shrink-0"
              >
                <Plus size={12} />
                서버 추가
              </button>
            </div>

            {/* 서버 추가 폼 */}
            {showAddServer && (
              <div className="bg-gray-900 rounded-lg p-4 space-y-4 text-sm">
                {/* 안내 */}
                <div className="text-xs text-gray-400 bg-gray-800 rounded p-3 space-y-1 leading-relaxed">
                  <p className="font-semibold text-gray-300">필요한 것</p>
                  <p>· SSH 접속이 가능한 서버 IP 또는 도메인</p>
                  <p>· SSH 사용자 계정 (예: <span className="font-mono text-gray-300">ubuntu</span>, <span className="font-mono text-gray-300">ec2-user</span>, <span className="font-mono text-gray-300">root</span>)</p>
                  <p>· SSH 포트 (기본값 22, 변경했다면 해당 포트)</p>
                  <p className="text-gray-500 pt-1">SSH Key 인증은 Credentials 탭에서 등록 후 연결할 수 있습니다.</p>
                </div>

                <div className="space-y-3">
                  <Field
                    label="서버 이름 (구분용)"
                    value={newServer.name}
                    onChange={(v) => setNewServer((s) => ({ ...s, name: v }))}
                    placeholder="예) production-server, staging-aws"
                  />
                  <div className="grid grid-cols-3 gap-3">
                    <div className="col-span-2">
                      <Field
                        label="호스트 (IP 또는 도메인)"
                        value={newServer.host}
                        onChange={(v) => setNewServer((s) => ({ ...s, host: v }))}
                        placeholder="예) 192.168.1.10 또는 my.server.com"
                      />
                    </div>
                    <Field
                      label="SSH 포트"
                      type="number"
                      value={String(newServer.port)}
                      onChange={(v) => setNewServer((s) => ({ ...s, port: Number(v) }))}
                      placeholder="22"
                    />
                  </div>
                  <Field
                    label="SSH 사용자명"
                    value={newServer.username}
                    onChange={(v) => setNewServer((s) => ({ ...s, username: v }))}
                    placeholder="예) ubuntu, ec2-user, root"
                  />
                  <Field
                    label="SSH 비밀번호"
                    type="password"
                    value={newServer.password}
                    onChange={(v) => setNewServer((s) => ({ ...s, password: v }))}
                    placeholder="비밀번호 입력 (저장 시 암호화됨)"
                  />
                </div>

                <div className="flex gap-2 pt-1">
                  <button
                    onClick={handleAddServer}
                    disabled={!newServer.name || !newServer.host || !newServer.username}
                    className="bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-1.5 rounded text-xs transition-colors"
                  >
                    등록
                  </button>
                  <button
                    onClick={() => setShowAddServer(false)}
                    className="bg-gray-700 hover:bg-gray-600 px-3 py-1.5 rounded text-xs transition-colors"
                  >
                    취소
                  </button>
                </div>
              </div>
            )}

            {servers.length === 0 ? (
              <p className="text-sm text-gray-500">등록된 서버가 없습니다. 위 버튼으로 추가하세요.</p>
            ) : (
              <div className="space-y-2">
                {servers.map((s) => (
                  <div key={s.id} className="bg-gray-900 rounded text-sm">
                    {editingId === s.id ? (
                      /* ─ 수정 폼 ─ */
                      <div className="p-3 space-y-2">
                        <div className="grid grid-cols-3 gap-2">
                          <div className="col-span-2">
                            <Field label="서버 이름" value={editForm.name}
                              onChange={(v) => setEditForm((f) => ({ ...f, name: v }))} placeholder="이름" />
                          </div>
                          <Field label="SSH 포트" type="number" value={String(editForm.port)}
                            onChange={(v) => setEditForm((f) => ({ ...f, port: Number(v) }))} placeholder="22" />
                        </div>
                        <Field label="호스트" value={editForm.host}
                          onChange={(v) => setEditForm((f) => ({ ...f, host: v }))} placeholder="IP 또는 도메인" />
                        <Field label="사용자명" value={editForm.username}
                          onChange={(v) => setEditForm((f) => ({ ...f, username: v }))} placeholder="ubuntu" />
                        <Field label="SSH 비밀번호" type="password" value={editForm.password}
                          onChange={(v) => setEditForm((f) => ({ ...f, password: v }))}
                          placeholder="변경할 경우만 입력" />
                        <div className="flex gap-2 pt-1">
                          <button
                            onClick={handleSaveEdit}
                            disabled={isSavingEdit || !editForm.name || !editForm.host || !editForm.username}
                            className="flex items-center gap-1 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 px-3 py-1 rounded text-xs transition-colors"
                          >
                            {isSavingEdit ? <Loader size={12} className="animate-spin" /> : <CheckCircle size={12} />}
                            저장
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="flex items-center gap-1 bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded text-xs transition-colors"
                          >
                            <X size={12} /> 취소
                          </button>
                        </div>
                      </div>
                    ) : (
                      /* ─ 표시 행 ─ */
                      <div className="flex items-center justify-between px-3 py-2.5">
                        <div>
                          <span className="font-medium">{s.name}</span>
                          <span className="text-gray-500 text-xs ml-2 font-mono">
                            {s.username}@{s.host}:{s.port}
                          </span>
                          {s.has_credential
                            ? <span className="ml-2 text-xs text-green-500">● 인증 설정됨</span>
                            : <span className="ml-2 text-xs text-yellow-500">● 인증 없음</span>
                          }
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleStartEdit(s)}
                            title="수정"
                            className="p-1 text-gray-500 hover:text-gray-200 transition-colors"
                          >
                            <Pencil size={13} />
                          </button>
                          <button
                            onClick={() => handleDelete(s.id)}
                            disabled={deletingId === s.id}
                            title="삭제"
                            className="p-1 text-gray-500 hover:text-red-400 disabled:opacity-50 transition-colors"
                          >
                            {deletingId === s.id
                              ? <Loader size={13} className="animate-spin" />
                              : <Trash2 size={13} />}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Core Engine 상태 */}
          <EngineStatus />
        </div>
      </div>
    </div>
  );
}

function Field({
  label, value, onChange, type = "text", placeholder = "",
}: {
  label: string; value: string; onChange: (v: string) => void; type?: string; placeholder?: string;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs text-gray-400">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-100 focus:outline-none focus:border-brand-500"
      />
    </div>
  );
}

function EngineStatus() {
  const [status, setStatus] = useState<"checking" | "ok" | "error">("checking");

  useEffect(() => {
    checkHealth()
      .then(() => setStatus("ok"))
      .catch(() => setStatus("error"));
  }, []);

  return (
    <section className="bg-gray-800 rounded-lg p-5">
      <h2 className="font-semibold mb-3">Core Engine</h2>
      <div className="flex items-center gap-2 text-sm">
        {status === "ok" ? (
          <CheckCircle size={16} className="text-green-400" />
        ) : status === "error" ? (
          <XCircle size={16} className="text-red-400" />
        ) : (
          <span className="text-gray-400">확인 중...</span>
        )}
        <span>
          {status === "ok"
            ? "http://127.0.0.1:8765 연결 정상"
            : status === "error"
            ? "Core Engine에 연결할 수 없습니다"
            : ""}
        </span>
      </div>
    </section>
  );
}

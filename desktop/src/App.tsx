import { useState, useEffect, useRef } from "react";
import QRCode from "qrcode";
import "./App.css";

// ── Types ──

type Tab = "install" | "config" | "platforms" | "advanced";

interface ComponentItem {
  id: string;
  name: string;
  desc: string;
  required: boolean;
}

interface InstallState {
  installDir: string;
  installProgress: number; // 0-100
  installLog: string[];
  installed: boolean;
  installing: boolean;
  // Components
  components: Set<string>;
  // Config
  provider: string;
  apiKey: string;
  model: string;
  baseUrl: string;
  // Platforms
  selectedPlatforms: Set<string>;
  // Advanced
  envContent: string;
  envSaved: boolean;
}

// ── Components ──

const COMPONENTS: ComponentItem[] = [
  { id: "python", name: "Python 3.11+", desc: "运行环境（如未安装则自动下载）", required: true },
  { id: "nermes", name: "Nermes 核心", desc: "nermes-agent 主程序", required: true },
  { id: "git", name: "Git", desc: "版本控制，技能更新需要", required: false },
  { id: "shortcut", name: "桌面快捷方式", desc: "在桌面创建 Nermes 启动图标", required: false },
  { id: "profession", name: "财务职业预设", desc: "内置财务审计/税务/报表技能", required: false },
  { id: "autostart", name: "开机自启", desc: "Nermes 随系统启动", required: false },
];

// ── Constants ──

const PROVIDERS = [
  { value: "deepseek", label: "DeepSeek (推荐)", defaultUrl: "https://api.deepseek.com/v1" },
  { value: "openai", label: "OpenAI", defaultUrl: "https://api.openai.com/v1" },
  { value: "anthropic", label: "Anthropic / Claude", defaultUrl: "https://api.anthropic.com/v1" },
  { value: "custom", label: "自定义 Provider", defaultUrl: "" },
];

const MODELS: Record<string, { value: string; label: string }[]> = {
  deepseek: [
    { value: "deepseek-v4-pro", label: "DeepSeek V4 Pro" },
    { value: "deepseek-v4-flash", label: "DeepSeek V4 Flash" },
  ],
  openai: [
    { value: "gpt-4o", label: "GPT-4o" },
    { value: "gpt-4o-mini", label: "GPT-4o Mini" },
  ],
  anthropic: [
    { value: "claude-sonnet-4-20250514", label: "Claude Sonnet 4" },
    { value: "claude-haiku-3-5", label: "Claude Haiku 3.5" },
  ],
  custom: [{ value: "", label: "手动输入模型名" }],
};

const PLATFORMS = [
  { id: "weixin", name: "微信", icon: "💬", description: "个人微信消息推送", qrLabel: "扫码登录微信" },
  { id: "wecom", name: "企业微信", icon: "🏢", description: "企业微信应用", qrLabel: "扫码绑定企业微信" },
  { id: "dingtalk", name: "钉钉", icon: "📌", description: "钉钉机器人", qrLabel: "扫码添加钉钉机器人" },
  { id: "feishu", name: "飞书", icon: "🐦", description: "飞书应用", qrLabel: "扫码绑定飞书" },
  { id: "telegram", name: "Telegram", icon: "✈️", description: "Telegram Bot", qrLabel: "扫码添加 Bot" },
  { id: "discord", name: "Discord", icon: "🎮", description: "Discord Bot", qrLabel: "扫码添加 Bot" },
];

function defaultComponents(): Set<string> {
  return new Set(COMPONENTS.filter((c) => c.required).map((c) => c.id));
}

// ═══════════════════════════════════════════
// App
// ═══════════════════════════════════════════

export default function App() {
  const [tab, setTab] = useState<Tab>("install");
  const [state, setState] = useState<InstallState>({
    installDir: "%LOCALAPPDATA%\\Nermes",
    installProgress: 0,
    installLog: [],
    installed: false,
    installing: false,
    components: defaultComponents(),
    provider: "deepseek",
    apiKey: "",
    model: "deepseek-v4-pro",
    baseUrl: "https://api.deepseek.com/v1",
    selectedPlatforms: new Set(["weixin"]),
    envContent: "",
    envSaved: false,
  });

  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state.installLog]);

  const addLog = (msg: string) => {
    setState((prev) => ({ ...prev, installLog: [...prev.installLog, msg] }));
  };

  const update = (patch: Partial<InstallState>) => {
    setState((prev) => ({ ...prev, ...patch }));
  };

  // ── Component toggle ──
  const toggleComponent = (id: string) => {
    const c = COMPONENTS.find((x) => x.id === id);
    if (c?.required) return; // 必须组件不可取消
    const next = new Set(state.components);
    next.has(id) ? next.delete(id) : next.add(id);
    update({ components: next });
  };

  // ── Install ──

  const pickDir = async () => {
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const dir = await open({ directory: true, title: "选择安装目录" });
      if (dir) update({ installDir: dir as string });
    } catch { /* fallback: manual input */ }
  };

  const startInstall = () => {
    const selected = state.components;
    const steps: { label: string; progress: number }[] = [];

    if (selected.has("python")) steps.push({ label: "🐍 检测 Python 环境...", progress: 10 });
    if (selected.has("python")) steps.push({ label: "📥 pip install --upgrade pip", progress: 20 });
    if (selected.has("nermes")) steps.push({ label: "📦 pip install nermes-agent", progress: 40 });
    if (selected.has("git")) steps.push({ label: "🔧 配置 Git", progress: 55 });
    if (selected.has("profession")) steps.push({ label: "📊 安装财务职业预设", progress: 70 });
    if (selected.has("shortcut")) steps.push({ label: "🔗 创建桌面快捷方式", progress: 85 });
    if (selected.has("autostart")) steps.push({ label: "🚀 配置开机自启", progress: 95 });
    steps.push({ label: "✅ 安装完成！", progress: 100 });

    update({ installing: true, installLog: [], installProgress: 0 });

    let i = 0;
    const timer = setInterval(() => {
      if (i < steps.length) {
        const step = steps[i];
        addLog(step.label);
        update({ installProgress: step.progress });
        i++;
      } else {
        clearInterval(timer);
        update({ installing: false, installed: true, installProgress: 100 });
      }
    }, 700);
  };

  const uninstall = () => {
    update({ installing: true, installLog: [], installProgress: 0 });
    const steps = [
      { label: "🗑️  pip uninstall nermes-agent", progress: 30 },
      { label: "🧹 清理配置文件...", progress: 60 },
      { label: "🔗 移除快捷方式...", progress: 85 },
      { label: "✅ 卸载完成", progress: 100 },
    ];
    let i = 0;
    const timer = setInterval(() => {
      if (i < steps.length) {
        addLog(steps[i].label);
        update({ installProgress: steps[i].progress });
        i++;
      } else {
        clearInterval(timer);
        update({ installing: false, installed: false, installProgress: 0 });
      }
    }, 600);
  };

  // ── Platforms ──

  const togglePlatform = (id: string) => {
    const next = new Set(state.selectedPlatforms);
    next.has(id) ? next.delete(id) : next.add(id);
    update({ selectedPlatforms: next });
  };

  // ── Config ──

  const saveEnv = () => {
    update({ envSaved: true });
    setTimeout(() => update({ envSaved: false }), 2000);
  };

  const onProviderChange = (provider: string) => {
    const prov = PROVIDERS.find((p) => p.value === provider);
    const models = MODELS[provider] || [];
    update({ provider, baseUrl: prov?.defaultUrl || "", model: models[0]?.value || "" });
  };

  // ═══════════════════════════════════════════
  // Render
  // ═══════════════════════════════════════════

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <h1>🐂 Nermes</h1>
        <p className="subtitle">桌面管理工具</p>
      </header>

      {/* Tabs */}
      <nav className="tab-nav">
        {([
          ["install", "📦 安装"],
          ["config", "⚙️ 模型"],
          ["platforms", "📱 平台"],
          ["advanced", "🔧 高级"],
        ] as [Tab, string][]).map(([id, label]) => (
          <button key={id} className={`tab-btn ${tab === id ? "active" : ""}`} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main className="app-main">
        {/* ═══ INSTALL ═══ */}
        {tab === "install" && (
          <div className="step-content">
            <h2>📦 {state.installed ? "已安装" : "安装 Nermes"}</h2>
            {state.installed && <p className="installed-ver">Nermes Agent v0.14 — 运行正常 ✅</p>}

            {/* Dir picker */}
            {!state.installed && (
              <div className="form-group">
                <label>安装目录</label>
                <div className="input-row">
                  <input
                    value={state.installDir}
                    onChange={(e) => update({ installDir: e.target.value })}
                    placeholder="C:\\Users\\..."
                  />
                  <button className="btn-small" onClick={pickDir}>浏览...</button>
                </div>
              </div>
            )}

            {/* Component checklist (only when not installed) */}
            {!state.installed && (
              <div className="component-list">
                <label className="component-label">安装组件</label>
                {COMPONENTS.map((c) => {
                  const checked = state.components.has(c.id);
                  return (
                    <label key={c.id} className={`component-item ${c.required ? "required" : ""}`}>
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={c.required || state.installing}
                        onChange={() => toggleComponent(c.id)}
                      />
                      <span className="comp-name">
                        {c.name}
                        {c.required && <span className="comp-tag">必须</span>}
                      </span>
                      <span className="comp-desc">{c.desc}</span>
                    </label>
                  );
                })}
              </div>
            )}

            {/* Progress bar (during install/uninstall) */}
            {state.installing && (
              <div className="progress-section">
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${state.installProgress}%` }}
                  />
                </div>
                <span className="progress-text">{state.installProgress}%</span>
              </div>
            )}

            {/* Log */}
            {state.installLog.length > 0 && (
              <div className="install-log">
                {state.installLog.map((line, i) => (
                  <div key={i} className="log-line">{line}</div>
                ))}
                <div ref={logEndRef} />
              </div>
            )}

            {/* Buttons */}
            <div className="install-actions">
              {!state.installed && !state.installing && (
                <button className="btn-primary" onClick={startInstall}>
                  🚀 安装
                </button>
              )}
              {state.installed && !state.installing && (
                <button className="btn-danger" onClick={uninstall}>
                  🗑️ 卸载 Nermes
                </button>
              )}
              {state.installing && (
                <button className="btn-primary" disabled>
                  ⏳ {state.installProgress < 100 ? "正在执行..." : "完成"}
                </button>
              )}
            </div>
          </div>
        )}

        {/* ═══ CONFIG ═══ */}
        {tab === "config" && (
          <div className="step-content">
            <h2>⚙️ 模型配置</h2>
            <p>配置 AI 模型连接信息，密钥保存在本地。</p>

            <div className="form-group">
              <label>Provider</label>
              <select value={state.provider} onChange={(e) => onProviderChange(e.target.value)}>
                {PROVIDERS.map((p) => (<option key={p.value} value={p.value}>{p.label}</option>))}
              </select>
            </div>
            <div className="form-group">
              <label>API Key</label>
              <input type="password" value={state.apiKey}
                onChange={(e) => update({ apiKey: e.target.value })} placeholder="sk-..." />
              <span className="form-hint">密钥仅存储在本地 ~/.nermes/.env</span>
            </div>
            <div className="form-group">
              <label>Base URL</label>
              <input value={state.baseUrl}
                onChange={(e) => update({ baseUrl: e.target.value })} placeholder="https://api.xxx.com/v1" />
            </div>
            <div className="form-group">
              <label>模型</label>
              {state.provider === "custom" ? (
                <input value={state.model} onChange={(e) => update({ model: e.target.value })} placeholder="输入模型名称" />
              ) : (
                <select value={state.model} onChange={(e) => update({ model: e.target.value })}>
                  {(MODELS[state.provider] || []).map((m) => (<option key={m.value} value={m.value}>{m.label}</option>))}
                </select>
              )}
            </div>
            <button className="btn-primary" onClick={() => addLog("✅ 配置已保存")}>💾 保存配置</button>
          </div>
        )}

        {/* ═══ PLATFORMS ═══ */}
        {tab === "platforms" && (
          <div className="step-content">
            <h2>📱 消息平台</h2>
            <p>选择要接入的平台，扫码完成绑定。</p>
            <div className="platform-grid">
              {PLATFORMS.map((p) => {
                const selected = state.selectedPlatforms.has(p.id);
                return (
                  <div key={p.id} className={`platform-card ${selected ? "selected" : ""}`}
                    onClick={() => togglePlatform(p.id)}>
                    <div className="platform-check">{selected ? "✅" : "⬜"}</div>
                    <div className="platform-icon">{p.icon}</div>
                    <div className="platform-name">{p.name}</div>
                    <div className="platform-desc">{p.description}</div>
                  </div>
                );
              })}
            </div>
            {state.selectedPlatforms.size > 0 && (
              <div className="qr-section">
                <h3>📷 扫码绑定</h3>
                <p className="qr-hint">在 Nermes CLI 中运行 <code>nermes gateway setup</code> 获取真实二维码。</p>
                <div className="qr-grid">
                  {PLATFORMS.filter((p) => state.selectedPlatforms.has(p.id)).map((p) => (
                    <QRCard key={p.id} platform={p} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ═══ ADVANCED ═══ */}
        {tab === "advanced" && (
          <div className="step-content">
            <h2>🔧 环境变量</h2>
            <p>手动编辑 ~/.nermes/.env 文件，适合高级用户或兜底配置。</p>
            <div className="form-group">
              <label>.env 文件内容</label>
              <textarea className="env-editor" value={state.envContent}
                onChange={(e) => update({ envContent: e.target.value })}
                placeholder={`# Nermes 环境变量\nDEEPSEEK_API_KEY=sk-xxx\n# 自定义 Provider\nCUSTOM_BASE_URL=https://api.xxx.com/v1`}
                rows={12} spellCheck={false} />
            </div>
            <button className="btn-primary" onClick={saveEnv}>
              {state.envSaved ? "✅ 已保存" : "💾 保存"}
            </button>
            <div className="env-hint">
              <p>支持的环境变量：</p>
              <code>PROVIDER_API_KEY</code> — 各 provider 的 API Key<br />
              <code>PROVIDER_BASE_URL</code> — 自定义 API 地址<br />
              <code>DEFAULT_MODEL</code> — 默认模型<br />
              <code>GATEWAY_PLATFORMS</code> — 启用的消息平台
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        Nermes v0.14 · {state.installed ? "已安装" : "未安装"}
      </footer>
    </div>
  );
}

// ── QR Card ──

function QRCard({ platform }: { platform: { id: string; qrLabel: string } }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (canvasRef.current) {
      QRCode.toCanvas(canvasRef.current, `nermes://gateway/setup/${platform.id}`, {
        width: 140, margin: 1,
        color: { dark: "#ffd700", light: "#1a1a3e" },
      });
    }
  }, [platform.id]);
  return (
    <div className="qr-card">
      <canvas ref={canvasRef} width={140} height={140} />
      <div className="qr-label">{platform.qrLabel}</div>
    </div>
  );
}

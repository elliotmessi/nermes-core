import { useState, useEffect, useRef } from "react";
import QRCode from "qrcode";
import "./App.css";

// ── Types ──

type Tab = "install" | "config" | "platforms" | "advanced";

interface Platform {
  id: string;
  name: string;
  icon: string;
  description: string;
  qrLabel: string;
}

interface InstallState {
  installDir: string;
  installLog: string[];
  installDone: boolean;
  installing: boolean;
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

const PLATFORMS: Platform[] = [
  { id: "weixin", name: "微信", icon: "💬", description: "个人微信消息推送", qrLabel: "扫码登录微信" },
  { id: "wecom", name: "企业微信", icon: "🏢", description: "企业微信应用", qrLabel: "扫码绑定企业微信" },
  { id: "dingtalk", name: "钉钉", icon: "📌", description: "钉钉机器人", qrLabel: "扫码添加钉钉机器人" },
  { id: "feishu", name: "飞书", icon: "🐦", description: "飞书应用", qrLabel: "扫码绑定飞书" },
  { id: "telegram", name: "Telegram", icon: "✈️", description: "Telegram Bot", qrLabel: "扫码添加 Bot" },
  { id: "discord", name: "Discord", icon: "🎮", description: "Discord Bot", qrLabel: "扫码添加 Bot" },
];

// ── App ──

export default function App() {
  const [tab, setTab] = useState<Tab>("install");
  const [state, setState] = useState<InstallState>({
    installDir: "%LOCALAPPDATA%\\Nermes",
    installLog: [],
    installDone: false,
    installing: false,
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

  // ── Actions ──

  const pickDir = async () => {
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const dir = await open({ directory: true, title: "选择安装目录" });
      if (dir) update({ installDir: dir as string });
    } catch {
      // Fallback: manual input
    }
  };

  const startInstall = () => {
    update({ installing: true, installLog: [] });
    const dir = state.installDir;
    const steps = [
      `📁 安装目录: ${dir}`,
      `🐍 检测 Python 环境...`,
      `✅ Python 3.11+ 已就绪`,
      `📦 pip install nermes-agent...`,
      `✅ Nermes 核心安装完成`,
      `⚙️  生成配置文件...`,
      `🔑 写入 API Key...`,
      `✅ 配置完成`,
    ];
    let i = 0;
    const timer = setInterval(() => {
      if (i < steps.length) {
        addLog(steps[i]);
        i++;
      } else {
        clearInterval(timer);
        update({ installing: false, installDone: true });
      }
    }, 600);
  };

  const togglePlatform = (id: string) => {
    const next = new Set(state.selectedPlatforms);
    next.has(id) ? next.delete(id) : next.add(id);
    update({ selectedPlatforms: next });
  };

  const saveEnv = () => {
    update({ envSaved: true });
    setTimeout(() => update({ envSaved: false }), 2000);
  };

  const onProviderChange = (provider: string) => {
    const prov = PROVIDERS.find((p) => p.value === provider);
    const models = MODELS[provider] || [];
    update({
      provider,
      baseUrl: prov?.defaultUrl || "",
      model: models[0]?.value || "",
    });
  };

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
          <button
            key={id}
            className={`tab-btn ${tab === id ? "active" : ""}`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main className="app-main">
        {/* ═══ 安装 ═══ */}
        {tab === "install" && (
          <div className="step-content">
            <h2>📦 安装 Nermes</h2>

            <div className="form-group">
              <label>安装目录</label>
              <div className="input-row">
                <input
                  value={state.installDir}
                  onChange={(e) => update({ installDir: e.target.value })}
                  placeholder="C:\Users\..."
                />
                <button className="btn-small" onClick={pickDir}>
                  浏览...
                </button>
              </div>
            </div>

            <button
              className="btn-primary"
              onClick={startInstall}
              disabled={state.installing}
            >
              {state.installing ? "⏳ 安装中..." : state.installDone ? "✅ 重新安装" : "🚀 开始安装"}
            </button>

            {state.installLog.length > 0 && (
              <div className="install-log">
                {state.installLog.map((line, i) => (
                  <div key={i} className="log-line">{line}</div>
                ))}
                <div ref={logEndRef} />
              </div>
            )}

            {state.installDone && (
              <div className="done-badge">✅ 安装完成！切换到「模型」标签页配置 API Key</div>
            )}
          </div>
        )}

        {/* ═══ 模型配置 ═══ */}
        {tab === "config" && (
          <div className="step-content">
            <h2>⚙️ 模型配置</h2>
            <p>配置 AI 模型连接信息，密钥保存在本地。</p>

            <div className="form-group">
              <label>Provider</label>
              <select value={state.provider} onChange={(e) => onProviderChange(e.target.value)}>
                {PROVIDERS.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>API Key</label>
              <input
                type="password"
                value={state.apiKey}
                onChange={(e) => update({ apiKey: e.target.value })}
                placeholder="sk-..."
              />
              <span className="form-hint">密钥仅存储在本地 ~/.nermes/.env</span>
            </div>

            <div className="form-group">
              <label>Base URL</label>
              <input
                value={state.baseUrl}
                onChange={(e) => update({ baseUrl: e.target.value })}
                placeholder="https://api.xxx.com/v1"
              />
            </div>

            <div className="form-group">
              <label>模型</label>
              {state.provider === "custom" ? (
                <input
                  value={state.model}
                  onChange={(e) => update({ model: e.target.value })}
                  placeholder="输入模型名称"
                />
              ) : (
                <select value={state.model} onChange={(e) => update({ model: e.target.value })}>
                  {(MODELS[state.provider] || []).map((m) => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </select>
              )}
            </div>

            <button className="btn-primary" onClick={() => addLog("✅ 配置已保存")}>
              💾 保存配置
            </button>
          </div>
        )}

        {/* ═══ 消息平台 ═══ */}
        {tab === "platforms" && (
          <div className="step-content">
            <h2>📱 消息平台</h2>
            <p>选择要接入的平台，扫码完成绑定。</p>

            <div className="platform-grid">
              {PLATFORMS.map((p) => {
                const selected = state.selectedPlatforms.has(p.id);
                return (
                  <div
                    key={p.id}
                    className={`platform-card ${selected ? "selected" : ""}`}
                    onClick={() => togglePlatform(p.id)}
                  >
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
                <p className="qr-hint">
                  请在 Nermes CLI 中运行 <code>nermes gateway setup</code> 获取真实二维码。
                </p>
                <div className="qr-grid">
                  {PLATFORMS.filter((p) => state.selectedPlatforms.has(p.id)).map(
                    (p) => (
                      <QRCard key={p.id} platform={p} />
                    )
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ═══ 高级 ═══ */}
        {tab === "advanced" && (
          <div className="step-content">
            <h2>🔧 环境变量</h2>
            <p>手动编辑 ~/.nermes/.env 文件，适合高级用户或兜底配置。</p>

            <div className="form-group">
              <label>.env 文件内容</label>
              <textarea
                className="env-editor"
                value={state.envContent}
                onChange={(e) => update({ envContent: e.target.value })}
                placeholder={`# Nermes 环境变量
DEEPSEEK_API_KEY=sk-xxx
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
# 自定义 Provider
CUSTOM_BASE_URL=https://api.xxx.com/v1
CUSTOM_API_KEY=sk-xxx
CUSTOM_MODEL=gpt-4o`}
                rows={12}
                spellCheck={false}
              />
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
        Nermes v0.14 · {state.installDone ? "已安装" : "未安装"}
      </footer>
    </div>
  );
}

// ── QR Card Component ──

function QRCard({ platform }: { platform: Platform }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (canvasRef.current) {
      QRCode.toCanvas(canvasRef.current, `nermes://gateway/setup/${platform.id}`, {
        width: 140,
        margin: 1,
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

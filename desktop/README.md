# Nermes Desktop 🐂

Nermes (牛马) Windows 桌面管理工具 — 可视化安装与管理。

## 功能

| 标签页 | 功能 |
|--------|------|
| 📦 安装 | 选择目录 → 勾选组件 → 进度条安装 → 卸载 |
| ⚙️ 模型 | 选择服务商、填入 API Key、Base URL、模型名 |
| 📱 平台 | 微信 / 企业微信 / 钉钉 / 飞书 / Telegram / Discord 绑定 |
| 🔧 高级 | 手动编辑 `~/.nermes/.env` 环境变量（兜底方案） |

## 技术栈

- **前端**：React 19 + TypeScript + Vite + QRCode.js
- **桌面壳**：Tauri 2.x (Rust)
- **打包**：NSIS（`.exe` 安装包）
- **构建**：GitHub Actions（Windows 运行环境）

## 开发

```bash
cd desktop
pnpm install
pnpm tauri dev      # 完整模式（需要 Rust 环境）
pnpm dev            # 仅前端 UI 预览（浏览器）
```

## 构建

Windows 安装包由 CI 自动构建，无需本地环境：

- 推送 `main` 分支且 `desktop/**` 目录有变更时自动触发
- 产物下载：GitHub Actions → Artifacts

## 项目结构

```
desktop/
├── src/App.tsx           # 主界面（安装 / 模型 / 平台 / 高级 四个标签页）
├── src/App.css           # 深色主题（金 + 深蓝）
├── src-tauri/            # Rust 后端
│   ├── src/lib.rs        # 文件读写、环境检测、安装卸载命令
│   ├── Cargo.toml        # Rust 依赖配置
│   └── tauri.conf.json   # 窗口尺寸、打包参数、权限声明
└── ../.github/workflows/build-desktop.yml   # CI 构建流水线
```

## 许可证

MIT — 作为 nermes-core 的一部分

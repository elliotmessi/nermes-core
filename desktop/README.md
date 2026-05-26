# Nermes Desktop 🐂

Nermes (牛马) Windows 桌面管理工具 — 可视化安装与管理。

## 功能

| 标签页 | 功能 |
|--------|------|
| 📦 安装 | 选择目录 → 一键安装 Nermes |
| ⚙️ 模型 | Provider / API Key / Base URL / Model 配置 |
| 📱 平台 | 微信/企微/钉钉/飞书/Telegram/Discord 多平台绑定 |
| 🔧 高级 | 手动编辑 ~/.nermes/.env 环境变量（兜底） |

## 技术栈

- **前端**: React 19 + TypeScript + Vite + QRCode.js
- **桌面壳**: Tauri 2.x (Rust)
- **打包**: NSIS (.exe)
- **CI**: GitHub Actions (Windows runner)

## 开发

```bash
cd desktop
pnpm install
pnpm tauri dev      # 完整模式（需 Rust 环境）
pnpm dev            # 仅前端 UI 预览
```

## 构建

Windows 构建通过 CI 自动完成：
- Push `main` 且 `desktop/**` 变更 → 自动构建 NSIS 安装包
- 下载：GitHub Actions Artifacts

## 项目结构

```
desktop/
├── src/App.tsx           # 主界面（4 标签页）
├── src/App.css           # 深色主题样式
├── src-tauri/            # Rust 后端
│   ├── src/lib.rs        # 文件读写 / 环境检测命令
│   ├── Cargo.toml
│   └── tauri.conf.json   # 窗口 / 打包 / 权限
└── .github/../build-desktop.yml  # Windows 构建流水线
```

## License

MIT — 作为 nermes-core 的一部分

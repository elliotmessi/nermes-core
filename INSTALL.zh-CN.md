# Nermes 安装指南

## 前置要求

- Linux / macOS / Windows WSL2
- 网络连接（需要访问 GitHub 和 PyPI 镜像）
- DeepSeek API Key（[免费注册](https://platform.deepseek.com)）

## 一键安装

```bash
curl -fsSL https://raw.githubusercontent.com/nousresearch/nermes-core/main/scripts/install.sh | bash
```

## 安装过程

安装脚本会自动完成以下步骤：

1. **检测系统环境** — 确认操作系统和可用工具
2. **安装 uv 包管理器** — 快速的 Python 包管理工具
3. **安装 Python 3.11** — 通过 uv 自动管理，无需手动安装
4. **克隆 Nermes 仓库** — 从 GitHub 下载最新代码
5. **创建虚拟环境** — 隔离的 Python 运行环境
6. **安装依赖** — 自动安装所有必需的 Python 和 Node.js 包
7. **配置 PATH** — 将 `nermes` 命令添加到系统路径
8. **运行配置向导** — 设置 API Key 和默认模型
9. **（可选）安装职业预设** — 选择职业包（财务/律师/教师等）

## 安装后验证

```bash
# 检查安装是否成功
nermes --version

# 查看系统状态
nermes doctor

# 开始对话
nermes
```

## 手动安装（高级用户）

```bash
git clone https://github.com/nousresearch/nermes-core.git
cd nermes-core
./setup-hermes.sh
```

## 卸载

```bash
# 删除 Nermes 数据目录
rm -rf ~/.hermes

# 删除命令链接
rm -f ~/.local/bin/nermes

# 删除代码（如果使用默认安装路径）
rm -rf ~/.hermes/hermes-agent
```

## 常见问题

### Q: 安装时提示 "Permission denied"
A: 请确保 `~/.local/bin` 在你的 PATH 中，并且有写入权限。

### Q: 国内访问 GitHub 太慢
A: 安装脚本已配置清华 PyPI 镜像和 npmmirror npm 镜像，但 Git 克隆仍需访问 GitHub。可以使用代理或 Gitee 镜像。

### Q: 如何配置 DeepSeek？
A: 运行 `nermes setup`，在模型配置步骤选择 "deepseek" 作为提供商。

### Q: Windows 如何安装？
A: 推荐使用 WSL2。原生 Windows 支持正在开发中。

### Q: 如何安装财务版？
A: 安装过程中会询问是否安装职业预设，选择「财务」即可。也可稍后运行：
```bash
bash ~/.hermes/hermes-agent/professions/finance/apply.sh
```

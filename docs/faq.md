# 常见问题 FAQ

> 收集了 Nermes 使用过程中最常遇到的问题，涵盖安装、配置、使用、安全和费用等方面。

---

## 📦 安装与运行

### Q1：安装报错 `pip install` 失败怎么办？

**常见原因及解决方法：**

| 原因 | 解决方法 |
|------|---------|
| Python 版本过低 | 请确保 Python ≥ 3.10：`python --version` |
| pip 版本过旧 | 执行 `pip install --upgrade pip` 后重试 |
| 网络问题 | 使用国内镜像源：`pip install nermes-core -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| 依赖冲突 | 建议在虚拟环境中安装：`python -m venv venv && source venv/bin/activate && pip install nermes-core` |
| 权限不足 | 添加 `--user` 参数，或使用管理员终端 |

如果以上都无法解决，请到 [GitHub Issues](https://github.com/nermes/nermes-core/issues) 提交详细错误信息。

### Q2：启动时提示 "ModuleNotFoundError"

这通常是依赖安装不完整导致的。可以尝试：

```bash
pip install --upgrade nermes-core
# 或重新安装所有依赖
pip install --force-reinstall nermes-core
```

### Q3：能在 Windows 上使用吗？

可以。推荐在 **WSL2（Windows Subsystem for Linux）** 下运行，体验最佳。如果直接在 Windows 上运行，部分工具（如文件监视、系统命令）可能受限。

WSL2 安装步骤：
1. 在 PowerShell 中执行 `wsl --install`
2. 安装完成后启动 Ubuntu
3. 在 WSL 中运行 `pip install nermes-core`

### Q4：Nermes 支持 ARM 架构吗（如树莓派、Mac M系列）？

支持。Nermes 核心代码是纯 Python，兼容 ARM64 架构。在 Mac M1/M2/M3 和树莓派上均可正常运行。

### Q5：安装后 `nermes` 命令找不到？

```bash
# 检查是否安装成功
pip list | grep nermes

# 如果已安装但找不到命令，可能是 PATH 问题
python -m nermes --version

# 解决方式：将 Python 脚本目录加入 PATH
# Linux/macOS 用户
echo 'export PATH="$PATH:$HOME/.local/bin"' >> ~/.bashrc
source ~/.bashrc
```

---

## 🔑 API Key 与模型

### Q6：必须使用 OpenAI 吗？可以用其他模型吗？

不是必须的。Nermes 支持多种模型提供商：

- **OpenAI**（GPT-4o、GPT-4-turbo、GPT-3.5-turbo）
- **Anthropic**（Claude 3.5 Sonnet、Claude 3 Opus）
- **DeepSeek**（DeepSeek-V2、DeepSeek-Coder）
- **本地模型**：通过 Ollama 运行 Llama、Qwen、Mistral 等开源模型
- **兼容 OpenAI API 的任何服务**（如 Together AI、Groq、vLLM 等）

切换方式：运行 `nermes init` 重新选择提供商，或编辑 `~/.nermes/config.yaml`。

### Q7：API Key 安全吗？会不会泄露？

Nermes 采取多重保护措施：

1. **本地存储**：API Key 存储在本地文件中，不会上传到任何第三方服务器
2. **加密保存**：建议将 Key 放在 `~/.nermes/.env` 文件中，文件权限默认设置为 600（仅当前用户可读）
3. **传输加密**：所有 API 请求均通过 HTTPS 加密传输
4. **不记录密钥**：系统的日志文件会自动过滤 API Key 信息

> ⚠️ 请勿将包含 API Key 的配置文件分享给他人或上传到公开仓库。

### Q8：API Key 在哪里获取？

| 提供商 | 获取地址 | 价格参考 |
|--------|---------|---------|
| OpenAI | https://platform.openai.com/api-keys | GPT-4o 约 $2.50/百万输入 token |
| Anthropic | https://console.anthropic.com/ | Claude 3.5 Sonnet 约 $3.00/百万输入 token |
| DeepSeek | https://platform.deepseek.com/ | 约 ¥1.00/百万输入 token（性价比高） |
| Ollama（本地） | https://ollama.ai/ | 免费，需要本地 GPU |

### Q9：使用本地模型需要什么配置？

| 模型 | 最低内存 | 推荐显存 | 效果 |
|-----|---------|---------|------|
| Qwen2-7B | 8GB | 6GB | 良好 |
| Llama-3-8B | 8GB | 8GB | 良好 |
| Qwen2-14B | 16GB | 12GB | 优秀 |
| DeepSeek-V2-Lite | 8GB | 6GB | 良好 |

使用本地模型无需 API Key，配置方式：

```bash
# 安装 Ollama
curl -fsSL https://ollama.ai/install.sh | sh
# 拉取模型
ollama pull qwen2:7b
# 在 Nermes 中配置
nermes init  # 选择 Ollama 作为提供商
```

---

## 💬 微信绑定

### Q10：如何将 Nermes 绑定到微信？

需要配合 Nermes Gateway 使用：

1. 安装 Gateway：`pip install nermes-gateway`
2. 配置微信平台：`nermes gateway config weixin`
3. 按照提示填写你的微信信息
4. 启动 Gateway：`nermes gateway start`

详细教程请查看 [微信绑定文档](https://docs.nermes.dev/wechat-bind)。

### Q11：绑定微信后，别人能通过微信访问我的数据吗？

不能。微信绑定仅面向你自己——系统会验证消息发送者的身份，只有你授权的微信号才能与 Nermes 对话。群聊中，Nermes 只在被 @ 时才会响应。

### Q12：支持多个微信账号吗？

支持。你可以为每个微信账号创建独立的 Nermes 实例，或者通过配置多个平台接入点实现多账号管理。

---

## 📊 数据与隐私

### Q13：我的数据存在哪里？会上传到云端吗？

**所有数据默认存储在本地**，路径为 `~/.nermes/data/`。包括：
- 记账数据 → `~/.nermes/data/finance.db`
- 待办事项 → `~/.nermes/data/todos.json`
- 对话历史 → `~/.nermes/data/sessions/`

Nermes **不会主动上传任何数据**到云端。只有在调用 AI 模型 API 时，你当前对话的消息才会发送给模型提供商处理。

### Q14：如何备份和恢复数据？

备份：

```bash
# 备份整个数据目录
cp -r ~/.nermes ~/.nermes.backup.$(date +%Y%m%d)
```

恢复：

```bash
# 将备份覆盖回原位置
cp -r ~/.nermes.backup.20260523 ~/.nermes
```

你也可以将备份文件同步到自己的云盘或 NAS 中。

### Q15：如何清除我的所有数据？

```bash
# 清除所有数据（包括配置、账单、对话历史等）
nermes reset --all

# 仅清除对话历史，保留配置和账单
nermes reset --sessions

# 仅清除账单数据
nermes reset --finance
```

> ⚠️ `nermes reset --all` 不可逆，操作前请确认已备份重要数据。

---

## 💰 费用

### Q16：Nermes 本身收费吗？

**完全免费开源**。Nermes 采用 Apache 2.0 许可证，你可以免费使用、修改和分发，无需支付任何费用。

### Q17：使用 Nermes 会产生哪些费用？

只有当调用第三方 API 时才会产生费用：

| 项目 | 费用情况 |
|------|---------|
| Nermes 本体 | 免费 |
| OpenAI API | 按 token 计费（约 $0.01-0.03/次对话） |
| 其他模型 API | 各家定价不同 |
| 本地模型 | 仅需电费 |
| Docker 部署 | 需自行承担服务器费用 |

**估算**：普通用户日常使用（每天约 50 次对话），使用 GPT-4o 每月约 $3-10。

### Q18：如何查看 API 调用统计？

```bash
nermes stats
```

输出示例：

```
📊 API 调用统计（本月）
━━━━━━━━━━━━━━━━━━━━━━━
总调用次数  │  1,234 次
总 Token 数 │  2.5M
预估费用    │  $5.67
提供商      │  OpenAI
模型        │  GPT-4o
```

---

## 🔧 使用问题

### Q19：Nermes 连不上网络怎么办？

检查以下几点：

1. 确保网络正常：`ping 8.8.8.8`
2. 检查 API Key 是否正确：`nermes config`
3. 测试 API 连通性：`nermes test-connection`
4. 如果使用代理，需要在配置中设置：

```yaml
# ~/.nermes/config.yaml
proxy:
  http: http://127.0.0.1:7890
  https: http://127.0.0.1:7890
```

### Q20：如何更新 Nermes？

```bash
pip install --upgrade nermes-core
```

更新后建议查看 [更新日志](https://github.com/nermes/nermes-core/releases) 了解新功能和变更。

### Q21：Nermes 支持多语言吗？

支持。目前支持中文（简体/繁体）、英文、日文。可在配置中设置：

```bash
nermes config set language zh-CN
```

### Q22：如何卸载 Nermes？

```bash
pip uninstall nermes-core

# 可选：清除用户数据
rm -rf ~/.nermes
```

---

## 📝 反馈与贡献

### Q23：遇到了 Bug 怎么办？

1. 查看 [已知问题列表](https://github.com/nermes/nermes-core/issues)
2. 收集日志信息：`nermes logs > error.log`
3. 提交 Issue 时附上日志和重现步骤

### Q24：如何贡献代码或文档？

欢迎贡献！请阅读 [贡献指南](https://github.com/nermes/nermes-core/blob/main/CONTRIBUTING.md)：

- 提交 Pull Request
- 完善文档
- 开发插件
- 修复 Bug
- 翻译本地化

---

## 联系我们

- 📖 完整文档：[https://docs.nermes.dev](https://docs.nermes.dev)
- 💬 社区问答：[https://discord.gg/nermes](https://discord.gg/nermes)
- 🐛 提交 Issue：[https://github.com/nermes/nermes-core/issues](https://github.com/nermes/nermes-core/issues)
- 📧 邮件支持：support@nermes.dev

---

*没找到你要的答案？请提交 Issue 或加入社区提问，我们会尽快回复。*

"""Random tips shown at CLI session start to help users discover features."""

import random


# ---------------------------------------------------------------------------
# Tip corpus — one-liners covering slash commands, CLI flags, config,
# keybindings, tools, gateway, skills, profiles, and workflow tricks.
# ---------------------------------------------------------------------------

TIPS = [
    # --- Slash Commands ---
    "/background <prompt>（别名 /bg 或 /btw）在独立会话中运行任务，当前会话保持空闲。",
    "/branch 创建当前会话的分支，让你探索不同方向而不丢失进度。",
    "/compress 在对话过长时手动压缩上下文。",
    "/rollback 列出文件系统检查点——将 agent 修改过的文件恢复到任何先前状态。",
    "/rollback diff 2 预览自检查点 2 以来的变更，不执行任何恢复。",
    "/rollback 2 src/file.py 从特定检查点恢复单个文件。",
    "/title \"my project\" 为会话命名——之后可用 /resume 或 hermes -c 恢复。",
    "/resume 从之前命名的会话中断处继续。",
    "/queue <prompt> 将消息排队到下一轮，不中断当前轮次。",
    "/undo 移除对话中最后一轮用户/助手的交互。",
    "/retry 重新发送你上一条消息——当 agent 的回复不太准确时很有用。",
    "/verbose 循环切换工具进度显示：关闭 → 仅新 → 全部 → 详细。",
    "/reasoning high 增加模型的思考深度。/reasoning show 显示推理过程。",
    "/fast 切换优先处理模式以获得更快的 API 响应（取决于提供商）。",
    "/yolo 在会话余下部分跳过所有危险命令的审批提示。",
    "/model 让你在会话中切换模型——试试 /model sonnet 或 /model gpt-5。",
    "/model --global 永久更改默认模型。",
    "/personality pirate 设置趣味个性——内置 14 种选项，从可爱风到莎士比亚风。",
    "/skin 更换 CLI 主题——试试 ares、mono、slate、poseidon 或 charizard。",
    "/statusbar 切换显示持久状态栏，展示模型、Token、上下文填充百分比、成本和时长。",
    "/tools disable browser 临时移除当前会话的浏览器工具。",
    "/browser connect 通过 CDP 将浏览器工具附加到正在运行的 Chromium 系列浏览器。",
    "/plugins 列出已安装的插件及其状态。",
    "/cron 管理定时任务——设置周期性提示并投递到任意平台。",
    "/reload-mcp 热重载 MCP 服务器配置，无需重启。",
    "/usage 显示 Token 用量、费用明细和会话时长。",
    "/insights 显示最近 30 天的使用分析。",
    "/paste 检查剪贴板中的图片并将其附加到下一条消息。",
    "/profile 显示当前激活的 profile 及其主目录。",
    "/config 一目了然显示当前配置。",
    "/stop 终止 agent 生成的所有正在运行的背景进程。",

    # --- @ Context References ---
    "@file:path/to/file.py 将文件内容直接注入到你的消息中。",
    "@file:main.py:10-50 只注入文件的第 10-50 行。",
    "@folder:src/ 注入目录树列表。",
    "@diff 将未暂存的 Git 变更注入到消息中。",
    "@staged 注入已暂存的 Git 变更（git diff --staged）。",
    "@git:5 注入最近 5 次提交及其完整补丁。",
    "@url:https://example.com 获取并注入网页内容。",
    "输入 @ 触发文件系统路径补全——交互式导航到任意文件。",
    "组合多个引用：\"Review @file:main.py and @file:test.py for consistency.\"",

    # --- Keybindings ---
    "Alt+Enter 插入换行符用于多行输入。（Windows Terminal 会拦截 Alt+Enter——请改用 Ctrl+Enter。）",
    "Ctrl+C 中断 agent。2 秒内连按两次强制退出。",
    "Ctrl+Z 将 Hermes 挂起到后台——在 shell 中运行 fg 恢复。",
    "Tab 接受自动建议的虚影文本或自动补全斜杠命令。",
    "在 agent 工作时输入新消息可中断并重定向它。",
    "Alt+V 将剪贴板中的图片粘贴到对话中。",
    "粘贴 5 行以上时自动保存到文件并插入简洁引用。",

    # --- CLI Flags ---
    "hermes -c 恢复最近的 CLI 会话。hermes -c \"project name\" 按标题恢复。",
    "hermes -w 创建隔离的 Git worktree——非常适合并行 agent 工作流。",
    "hermes -w -q \"Fix issue #42\" 将 worktree 隔离与一次性查询相结合。",
    "hermes chat -t web,terminal 仅启用特定工具集，打造专注的会话。",
    "hermes chat -s github-pr-workflow 在启动时预加载技能。",
    "hermes chat -q \"query\" 运行单次非交互查询后退出。",
    "hermes chat --max-turns 200 覆盖每轮默认的 90 次迭代限制。",
    "hermes chat --checkpoints 在每次破坏性文件变更前启用文件系统快照。",
    "hermes --yolo 绕过整个会话中所有危险命令的审批提示。",
    "hermes chat --source telegram 为会话添加标签，便于在 hermes sessions 列表中过滤。",
    "hermes -p work chat 在指定 profile 下运行，不更改默认配置。",

    # --- CLI Subcommands ---
    "hermes doctor --fix 诊断并自动修复配置和依赖问题。",
    "hermes dump 输出简洁的安装摘要——非常适合 Bug 报告。",
    "hermes config set KEY VALUE 自动将密钥路由到 .env，其余所有内容路由到 config.yaml。",
    "hermes config edit 在默认编辑器中打开 config.yaml。",
    "hermes config check 扫描缺失或过期的配置选项。",
    "hermes sessions browse 打开带有搜索功能的交互式会话选择器。",
    "hermes sessions stats 按平台和数据库大小显示会话统计。",
    "hermes sessions prune --older-than 30 清理旧会话。",
    "hermes skills search react --source skills-sh 搜索 skills.sh 公共目录。",
    "hermes skills check 扫描已安装的 hub 技能是否有上游更新。",
    "hermes skills tap add myorg/skills-repo 添加自定义 GitHub 技能源。",
    "hermes skills snapshot export setup.json 导出技能配置用于备份或分享。",
    "hermes mcp add github --command npx 从命令行添加 MCP 服务器。",
    "hermes mcp serve 将 Hermes 自身作为 MCP 服务器运行，供其他 agent 使用。",
    "hermes auth add 让你添加多个 API 密钥用于凭据池轮换。",
    "hermes completion bash >> ~/.bashrc 为所有命令和 profile 启用 Tab 补全。",
    "hermes logs -f 实时追踪 agent.log。--level WARNING --since 1h 过滤输出。",
    "hermes backup 创建整个 Hermes 主目录的 zip 备份。",
    "hermes profile create coder 创建隔离的 profile，它自身将成为独立的命令。",
    "hermes profile create work --clone 将当前配置和密钥复制到新 profile。",
    "hermes update 自动将新的捆绑技能同步到所有 profile。",
    "hermes gateway install 将 Hermes 设置为系统服务（systemd/launchd）。",
    "hermes memory setup 让你配置外部记忆提供商（Honcho、Mem0 等）。",
    "hermes webhook subscribe 创建带有 HMAC 验证的事件驱动 Webhook 路由。",
    "省钱技巧：hermes tools 禁用未使用的工具，hermes skills config 精简技能。",
    "/reasoning low 或 /reasoning minimal 将思考深度降至默认（medium）以下——响应更快、更便宜。",
    "hermes models 将视觉、压缩和辅助任务路由到更便宜的模型——在不降低主聊天模型的情况下削减 85%+ 的背景 Token 成本。",

    # --- Configuration ---
    "在 config.yaml 中设置 display.bell_on_complete: true，长任务完成时会有铃响提示。",
    "设置 display.streaming: true 以实时看到模型生成 Token 的过程。",
    "设置 display.show_reasoning: true 以查看模型的思维链推理过程。",
    "设置 display.compact: true 以减少输出中的空白，呈现更密集的信息。",
    "设置 display.busy_input_mode: queue 将消息排队而非中断 agent；或设为 steer 通过 /steer 在运行中注入。",
    "设置 display.resume_display: minimal 以在恢复会话时跳过完整的对话回顾。",
    "设置 compression.threshold: 0.50 控制自动压缩触发时机（默认：上下文 50%）。",
    "设置 agent.max_turns: 200 以允许 agent 每轮执行更多工具调用步骤。",
    "设置 file_read_max_chars: 200000 以增加每次 read_file 调用的最大内容量。",
    "设置 approvals.mode: smart 让 LLM 自动批准安全命令并自动拒绝危险命令。",
    "在 config.yaml 中设置 fallback_model 以自动故障转移到备用提供商。",
    "设置 privacy.redact_pii: true 以在发送到 LLM 前对用户 ID 和电话号码进行哈希处理。",
    "设置 browser.record_sessions: true 以自动将浏览器会话录制为 WebM 视频。",
    "在 config.yaml 中设置 worktree: true 以始终创建 Git worktree（等同于 hermes -w）。",
    "设置 security.website_blocklist.enabled: true 以阻止特定域名被网页工具访问。",
    "设置 cron.wrap_response: false 以传递原始 agent 输出，不带 cron 页眉/页脚。",
    "HERMES_TIMEZONE 使用任何 IANA 时区字符串覆盖服务器时区。",
    "config.yaml 中支持环境变量替换：使用 ${VAR_NAME} 语法。",
    "config.yaml 中的快速命令立即运行 shell 命令，零 Token 消耗。",
    "可以在 config.yaml 的 agent.personalities 下定义自定义个性。",
    "provider_routing 控制 OpenRouter 提供商的排序、白名单和黑名单。",

    # --- Tools & Capabilities ---
    "execute_code 运行通过编程方式调用 Hermes 工具的 Python 脚本——结果不进入上下文。",
    "delegate_task 默认生成最多 3 个并发子 agent（delegation.max_concurrent_children），每个具有独立上下文以并行工作。",
    "web_extract 支持 PDF 链接——传入任意 PDF 链接即可转换为 Markdown。",
    "search_files 基于 ripgrep，比 grep 更快——用它替代终端 grep。",
    "patch 使用 9 种模糊匹配策略，细微的空格差异不会破坏编辑。",
    "patch 支持 V4A 格式，单次调用即可批量编辑多个文件。",
    "read_file 在找不到文件时会建议相似的文件名。",
    "read_file 自动去重——重复读取未更改的文件返回轻量存根。",
    "browser_vision 截取屏幕截图并用 AI 分析——适用于验证码和视觉内容。",
    "browser_console 可以在页面上下文中执行 JavaScript 表达式。",
    "image_generate 使用 FLUX 2 Pro 创建图像并自动进行 2 倍放大。",
    "text_to_speech 将文本转换为音频——在 Telegram 上以语音气泡形式播放。",
    "send_message 可以从会话内触达任何已连接的消息平台。",
    "todo 工具帮助 agent 在会话期间跟踪复杂的多步骤任务。",
    "session_search 对所有历史对话执行全文搜索。",
    "agent 自动将偏好、纠正和环境事实保存到记忆中。",
    "mixture_of_agents 将难题协同路由到 4 个前沿 LLM。",
    "终端命令支持后台模式，使用 notify_on_complete 处理长时间运行的任务。",
    "终端后台进程支持 watch_patterns，可在特定输出行出现时发出警报。",
    "终端工具支持 6 种后端：local、Docker、SSH、Modal、Daytona 和 Singularity。",

    # --- Profiles ---
    "每个 profile 拥有独立的配置、API 密钥、记忆、会话、技能和定时任务。",
    "Profile 名称会成为 shell 命令——'hermes profile create coder' 创建 'coder' 命令。",
    "hermes profile export coder -o backup.tar.gz 创建可移植的 profile 归档文件。",
    "如果两个 profile 意外共享了同一个机器人 Token，第二个网关将被阻止并显示明确的错误信息。",

    # --- Sessions ---
    "会话在首次交互后自动生成描述性标题——无需手动命名。",
    "会话标题支持谱系：\"my project\" → \"my project #2\" → \"my project #3\"。",
    "退出时 Hermes 会打印一条包含会话 ID 和统计信息的恢复命令。",
    "hermes sessions export backup.jsonl 导出所有会话用于备份或分析。",
    "hermes -r SESSION_ID 通过 ID 恢复任意之前的会话。",

    # --- Memory ---
    "记忆是冻结的快照——更改仅在下次会话启动时出现在系统提示中。",
    "记忆条目会自动扫描提示注入和数据外泄模式。",
    "agent 有两种记忆存储：个人笔记（约 2200 字）和用户画像（约 1375 字）。",
    "你对 agent 的纠正（\"不，应该这样做\"）通常会自动保存到记忆中。",

    # --- Skills ---
    "超过 80 个内置技能，涵盖 GitHub、创意、MLOps、生产力、研究等。",
    "每个已安装的技能自动成为斜杠命令——输入 / 即可查看所有。",
    "hermes skills install official/security/1password 从仓库安装可选技能。",
    "技能可以限制在特定操作系统——有些仅在 macOS 或 Linux 上加载。",
    "config.yaml 中的 skills.external_dirs 让你从自定义目录加载技能。",
    "agent 可以使用 skill_manage 创建自己的技能作为程序性记忆。",
    "plan 技能将 Markdown 计划保存到活动工作区的 .hermes/plans/ 下。",

    # --- Cron & Scheduling ---
    "定时任务可以附加技能：hermes cron add --skill blogwatcher \"Check for new posts\"。",
    "定时任务的投递目标包括 Telegram、Discord、Slack、电子邮件、短信等 12+ 个平台。",
    "如果定时任务响应以 [SILENT] 开头，则跳过投递——适用于仅监控的任务。",
    "定时任务支持相对延迟（30m）、间隔（every 2h）、Cron 表达式和 ISO 时间戳。",
    "定时任务在全新的 agent 会话中运行——提示必须自包含。",

    # --- Voice ---
    "如果安装了 faster-whisper（免费本地语音转文字），语音模式无需 API 密钥即可使用。",
    "五种 TTS 提供商可用：Edge TTS（免费）、ElevenLabs、OpenAI、NeuTTS（免费本地）、MiniMax。",
    "/voice on 在 CLI 中启用语音模式。Ctrl+B 切换按键通话录音。",
    "流式 TTS 在生成句子的同时播放——无需等待完整响应。",
    "Telegram、Discord、WhatsApp 和 Slack 上的语音消息会自动转写为文字。",

    # --- Gateway & Messaging ---
    "Hermes 运行在 21 个消息平台上：Telegram、Discord、Slack、WhatsApp、Signal、Matrix、IRC、Microsoft Teams、电子邮件等。",
    "hermes gateway install 将其设置为开机自启的系统服务。",
    "钉钉使用 Stream 模式——无需 Webhook 或公网 URL。",
    "BlueBubbles 通过本地 macOS 服务器为 Hermes 带来 iMessage 支持。",
    "Webhook 路由支持 HMAC 验证、速率限制和事件过滤。",
    "API 服务器开放与 OpenAI 兼容的端点，兼容 Open WebUI 和 LibreChat。",
    "Discord 语音频道模式：机器人加入语音频道，转写语音并回话。",
    "group_sessions_per_user: true 让群聊中的每个人拥有自己的会话。",
    "/sethome 将当前聊天标记为定时任务投递的主频道。",
    "网关支持基于不活跃的超时机制——活跃的 agent 可以无限期运行。",

    # --- Security ---
    "危险命令审批有 4 个层级：一次、会话、始终（永久白名单）、拒绝。",
    "智能审批模式使用 LLM 自动批准安全命令并标记危险命令。",
    "SSRF 保护阻止私有网络、回环地址、链路本地地址和云元数据地址。",
    "Tirith 执行前扫描检测同形 URL 欺骗和管道到解释器模式。",
    "MCP 子进程接收过滤后的环境——只有安全的系统变量通过。",
    "上下文文件（.hermes.md、AGENTS.md）在加载前会进行提示注入安全扫描。",
    "config.yaml 中的 command_allowlist 永久批准特定的 shell 命令模式。",

    # --- Context & Compression ---
    "上下文达到阈值时自动压缩——记忆被刷新，历史被总结。",
    "状态栏随上下文填充程度依次变为黄色、橙色和红色。",
    "~/.hermes/SOUL.md 中的 SOUL.md 是 agent 的主要身份——自定义它以塑造行为。",
    "Hermes 从 .hermes.md、AGENTS.md、CLAUDE.md 或 .cursorrules（首个匹配）加载项目上下文。",
    "子目录中的 AGENTS.md 文件会随着 agent 进入文件夹而逐步发现。",
    "上下文文件上限为 20,000 字符，并智能截取首尾。",

    # --- Browser ---
    "五种浏览器提供商：本地 Chromium、Browserbase、Browser Use、Camofox 和 Firecrawl。",
    "Camofox 是一款反检测浏览器——基于 Firefox 分支，具有 C++ 指纹欺骗能力。",
    "browser_navigate 自动返回页面快照——之后无需再调用 browser_snapshot。",
    "browser_vision 设置 annotate=true 时在交互元素上叠加编号标签。",

    # --- MCP ---
    "MCP 服务器在 config.yaml 中配置——支持 stdio 和 HTTP 两种传输方式。",
    "按服务器工具过滤：tools.include 白名单和 tools.exclude 黑名单指定特定工具。",
    "MCP 服务器在运行时自动生成工具集——hermes tools 可按平台切换它们。",
    "MCP OAuth 支持：auth: oauth 启用基于浏览器的 PKCE 授权。",

    # --- Checkpoints & Rollback ---
    "未修改文件时检查点零开销——默认启用。",
    "回滚前的快照会自动保存，以便你可以撤销回滚。",
    "/rollback 同时撤销对话轮次，因此 agent 不会记住被回滚的更改。",
    "检查点使用 ~/.hermes/checkpoints/ 中的影子仓库——永远不会触碰项目的 .git。",

    # --- Batch & Data ---
    "batch_runner.py 并行处理数百个提示以生成训练数据。",
    "hermes chat -Q 启用静默模式用于编程调用——隐藏横幅和旋转动画。",
    "轨迹保存（--save-trajectories）捕获完整的工具使用轨迹以用于模型训练。",

    # --- Plugins ---
    "三种插件类型：通用（工具/钩子）、记忆提供商和上下文引擎。",
    "hermes plugins install owner/repo 直接从 GitHub 安装插件。",
    "8 个外部记忆提供商可用：Honcho、OpenViking、Mem0、Hindsight 等。",
    "插件钩子包括 pre/post_tool_call、pre/post_llm_call 以及用于输出规范化的 transform_terminal_output。",

    # --- Miscellaneous ---
    "提示缓存（Anthropic）通过重用已缓存的系统提示前缀来降低成本。",
    "agent 在后台线程中自动生成会话标题——零延迟影响。",
    "智能模型路由可以将简单查询自动路由到更便宜的模型。",
    "斜杠命令支持前缀匹配：/h 解析为 /help，/mod 解析为 /model。",
    "将文件路径拖入终端会自动附加图片或以上下文形式发送。",
    "仓库根目录中的 .worktreeinclude 列出需要复制到 worktree 的 gitignore 文件。",
    "hermes acp 将 Hermes 作为 ACP 服务器运行，集成 VS Code、Zed 和 JetBrains。",
    "自定义提供商：在 config.yaml 的 custom_providers 下保存命名端点。",
    "HERMES_EPHEMERAL_SYSTEM_PROMPT 注入一个永不保存到历史的系统提示。",
    "credential_pool_strategies 支持 fill_first、round_robin、least_used 和 random 轮换策略。",
    "hermes login 支持 Nous 和 OpenAI Codex 提供商的基于 OAuth 的身份验证。",
    "API 服务器同时支持 Chat Completions 和 Responses API，并带有服务器端状态管理。",
    "config 中的 tool_preview_length: 0 在旋转动画活动流中显示完整文件路径。",
    "hermes status --deep 对所有组件运行更深入的诊断检查。",

    # --- Hidden Gems & Power-User Tricks ---
    "定时任务可以附加 Python 脚本（--script），其 stdout 会作为上下文注入到提示中。",
    "定时脚本存放在 ~/.hermes/scripts/ 中，在 agent 之前运行——非常适合数据采集管道。",
    "config.yaml 中的 prefill_messages_file 将少量示例注入每次 API 调用，从不保存到历史。",
    "SOUL.md 完全替换 agent 的默认身份——重写它以打造属于你自己的 Hermes。",
    "SOUL.md 在首次运行时自动填充默认个性。编辑 ~/.hermes/SOUL.md 进行自定义。",
    "/compress <focus topic> 将 60-70% 的摘要预算分配给指定主题，并积极裁剪其余部分。",
    "在第二次及以上压缩时，压缩器会更新先前的摘要而非从头开始。",
    "在网关会话重置前，Hermes 会自动将重要事实后台刷新到记忆中。",
    "config.yaml 中的 network.force_ipv4: true 修复 IPv6 故障服务器上的挂起问题——对 socket 进行猴子补丁。",
    "终端工具注释常见退出码：grep 返回 1 = '未找到匹配（非错误）'。",
    "失败的前台终端命令自动重试最多 3 次，使用指数退避（2 秒、4 秒、8 秒）。",
    "裸 sudo 命令自动重写为从 .env 中管道传入 SUDO_PASSWORD——无需交互式提示。",
    "execute_code 内置辅助函数：json_parse() 容错解析、shell_quote() 和带退避的 retry()。",
    "execute_code 的 7 个沙箱工具（web_search、terminal、read/write/search/patch）使用 RPC——从不进入上下文。",
    "同一文件区域读取 3 次以上触发警告。4 次以上则硬阻断以防止循环。",
    "write_file 和 patch 检测文件自上次读取后是否被外部修改，并发出陈旧警告。",
    "V4A 补丁格式支持添加文件、删除文件和移动文件指令——不只是更新。",
    "MCP 服务器可以通过采样请求 LLM 补全——agent 成为服务器的工具。",
    "MCP 服务器发送 notifications/tools/list_changed 以触发自动工具重新注册，无需重启。",
    "delegate_task 设置 acp_command: 'claude' 可从任意平台生成 Claude Code 作为子 agent。",
    "委托有心跳线程——子进程活动传播到父进程，防止网关超时。",
    "当提供商返回 HTTP 402（需要付款）时，辅助客户端自动回退到下一个提供商。",
    "agent.tool_use_enforcement 引导那些描述操作而非调用工具的模型——对 GPT/Codex 自动启用。",
    "agent.restart_drain_timeout（默认 60 秒）让正在运行的 agent 在网关重启生效前完成工作。",
    "agent.api_max_retries（默认 3）控制 agent 在暴露错误前重试失败 API 调用的次数——降低它以实现快速回退。",
    "网关按会话缓存 AIAgent 实例——销毁此缓存会破坏 Anthropic 提示缓存。",
    "任何网站都可以通过 /.well-known/skills/index.json 暴露技能——技能中心会自动发现它们。",
    "位于 ~/.hermes/skills/.hub/audit.log 的技能审计日志跟踪每次安装和移除操作。",
    "过时的 Git worktree 自动清理：存在 24-72 小时且无未推送提交的 worktree 在启动时被修剪。",
    "每个 profile 在 HERMES_HOME/home/ 拥有独立的子进程 HOME——隔离的 Git、SSH、npm、gh 配置。",
    "HERMES_HOME_MODE 环境变量（八进制，如 0701）为 Web 服务器遍历设置自定义目录权限。",
    "容器模式：在 HERMES_HOME 中放置 .container-mode 文件，主机 CLI 自动在容器中执行。",
    "Ctrl+C 有 5 个优先级层级：取消录音 → 取消提示 → 取消选择器 → 中断 agent → 退出。",
    "agent 运行期间的每次中断都会记录到 ~/.hermes/interrupt_debug.log，包含时间戳。",
    "BROWSER_CDP_URL 将浏览器工具连接到任何正在运行的 Chromium 系列浏览器——接受 WebSocket、HTTP 或 host:port。",
    "BROWSERBASE_ADVANCED_STEALTH=true 启用自定义 Chromium 的高级反检测功能（Scale 计划）。",
    "CLI 在宽度小于 80 列的终端中自动切换到紧凑模式。",
    "快速命令支持两种类型：exec（直接运行 shell 命令）和 alias（重定向到另一个命令）。",
    "按任务委托模型：config 中的 delegation.model 和 delegation.provider 将子 agent 路由到更便宜的模型。",
    "delegation.reasoning_effort 独立控制子 agent 的思考深度。",
    "config.yaml 中的 display.platforms 允许按平台覆盖显示设置：{telegram: {tool_progress: all}}。",
    "config 中的 human_delay.mode 模拟人类打字速度——可配置 min_ms/max_ms 范围。",
    "配置版本迁移在加载时自动运行——新配置键无需手动干预即可生效。",
    "GPT 和 Codex 模型会获得特殊的系统提示指导，以实现工具纪律和强制工具使用。",
    "Gemini 模型会获得针对绝对路径、并行工具调用和非交互式命令的定制指令。",
    "config.yaml 中的 context.engine 可以设置为插件名称，以选择替代的上下文管理策略。",
    "超过 8000 Token 的浏览器页面会在返回给 agent 前由辅助 LLM 自动总结。",
    "压缩器执行一次廉价预处理：超过 200 字符的工具输出在 LLM 运行前被替换为占位符。",
    "压缩失败时，后续尝试暂停 10 分钟以避免 API 过度调用。",
    "长的危险命令（>70 字符）在审批提示中提供 'view' 选项以先查看完整文本。",
    "音频电平可视化在录音期间根据麦克风 RMS 电平显示 ▁▂▃▄▅▆▇ 柱状条。",
    "Profile 名称不能与已有的 PATH 二进制文件冲突——'hermes profile create ls' 会被拒绝。",
    "hermes profile create backup --clone-all 复制所有内容（配置、密钥、SOUL.md、记忆、技能、会话）。",
    "语音录制键可通过 config.yaml 中的 voice.record_key 配置——不仅限于 Ctrl+B。",
    ".cursorrules 和 .cursor/rules/*.mdc 文件会自动检测并作为项目上下文加载。",
    "上下文文件支持 10+ 种提示注入模式——不可见 Unicode、'忽略指令'、数据窃取尝试。",
    "GPT-5 和 Codex 在消息格式中使用 'developer' 角色而非 'system'。",
    "按任务辅助覆盖：config.yaml 中的 auxiliary.vision.provider、auxiliary.compression.model 等。",
    "辅助客户端将 'main' 视为提供商别名——解析为实际的主提供商 + 模型。",
    "hermes claw migrate --dry-run 预览 OpenClaw 迁移，不写入任何内容。",
    "带引号或转义空格粘贴的文件路径会自动处理——无需手动清理。",
    "斜杠命令从不触发大粘贴折叠——带大参数的 /command 也能正常工作。",
    "在中断模式下，agent 执行期间输入的斜杠命令绕过中断逻辑并立即执行。",
    "HERMES_DEV=1 绕过容器模式检测以进行本地开发。",
    "每个 MCP 服务器拥有自己的工具集（mcp-servername），可通过 hermes tools 独立切换。",
    "配置中的 MCP ${ENV_VAR} 占位符在服务器生成时解析——包括来自 ~/.hermes/.env 的变量。",
    "来自信任仓库（NousResearch）的技能获得 'trusted' 安全级别；社区技能获得额外扫描。",
    "位于 ~/.hermes/skills/.hub/quarantine/ 的技能隔离区存放待安全审查的技能。",

    # --- Advanced Slash Commands ---
    '/steer <prompt> 在下一次工具调用后注入一条备注——在不中断的情况下中途调整方向。',
    '/goal <text> 设置一个持续运行的 Ralph-loop 目标——Hermes 自动一轮接一轮继续，直到评审判定完成。',
    '/snapshot create [label] 保存 Hermes 配置的完整状态快照；/snapshot restore <id> 之后恢复。',
    '/copy [N] 将最后一条助手回复复制到剪贴板，或使用数字指定倒数第 N 条。',
    '/redraw 强制完全重绘 UI，修复 tmux 调整大小或鼠标选择后的终端漂移问题。',
    '/agents（别名 /tasks）显示当前会话中的活跃 agent 和运行中的后台任务。',
    '/footer 切换最终回复上的网关页脚，显示模型、工具数量和轮次耗时。',
    '/busy queue|steer|interrupt 控制 Hermes 工作时按 Enter 键的行为。',
    '/topic 在 Telegram 私聊中启用用户管理的多会话主题模式——/topic <id> 内联恢复历史会话。',
    '/approve session|always 以你选择的信任范围执行待处理的危险命令；/deny 拒绝它。',
    '/restart 在排空活跃运行后优雅重启网关，重启完成后通知请求者。',
    '/kanban boards switch <slug> 在聊天内切换活跃的多项目看板。',
    '/reload 将 ~/.hermes/.env 重新加载到运行中的会话——无需重启即可获取新 API 密钥。',

    # --- Cron (no-agent & scripts) ---
    'cronjob 设置 no_agent=True 按计划运行脚本并直接发送 stdout——零 Token、零 LLM。',
    '空的定时脚本 stdout 表示静默触发——不投递任何内容，非常适合阈值监控。',
    "HERMES_CRON_MAX_PARALLEL（默认 4）限制每次触发同时运行的定时任务数量，防止突发流量耗尽可能的密钥。",

    # --- Gateway Hooks ---
    '网关钩子存放在 ~/.hermes/hooks/<name>/ 下，包含 HOOK.yaml + handler.py——处理器必须命名为 `handle`。',
    '钩子事件包括 gateway:startup、session:start、agent:step 和 command:* 通配符订阅。',
    '放置一个 ~/.hermes/BOOT.md 清单，gateway:startup 钩子会在每次启动时作为一次性 agent 运行它。',

    # --- Curator ---
    'hermes curator run --dry-run 预览 curator 将要归档或合并的内容，不进行任何变更。',
    "hermes curator pin <skill> 对技能设置硬围栏，防止自动归档和 agent 的 skill_manage 工具操作。",
    'hermes curator rollback 从运行前快照恢复技能——备份存放在 skills/.curator_backups/ 下。',

    # --- Credential Pools & Routing ---
    'hermes auth reset <provider> 清除凭据池上的所有冷却时间和耗尽标志。',
    'credential_pool_strategies.<provider>: round_robin 均匀循环使用密钥，而非默认的 fill_first。',
    'use_gateway: true 按工具将 web、image、tts 或 browser 路由到你的 Nous 订阅——无需额外密钥。',
    'provider_routing.data_collection: deny 排除 OpenRouter 上存储数据的提供商。',
    'provider_routing.require_parameters: true 仅路由到支持你请求中所有参数的提供商。',

    # --- TUI & Dashboard ---
    'HERMES_TUI_RESUME=1 在启动时自动重新附加到最近的 TUI 会话——SSH 断开后很方便。',
    "HERMES_TUI_THEME=light|dark|<hex> 在未设置 COLORFGBG 的终端上强制 TUI 主题。",
    'TUI 中的 Ctrl+G 或 Ctrl+X Ctrl+E 在 $EDITOR 中打开输入缓冲区，用于长多行提示。',
    'TUI 内联渲染 LaTeX——$E=mc^2$ 显示为 Unicode 数学符号而非原始 TeX。',
    'hermes dashboard 在 127.0.0.1:9119 启动本地 Web 界面——零数据离开 localhost。',
    'hermes dashboard --tui 通过 xterm.js 和 WebSocket PTY 在浏览器中嵌入完整的 Hermes TUI。',
    '在 ~/.hermes/dashboard-themes/ 中放入一个包含两种调色板颜色的 YAML 文件，即可更换整个仪表盘皮肤。',
    '仪表盘插件即插即用：manifest.json + JS 包放在 ~/.hermes/dashboard-plugins/ 中——无需 npm 构建。',
    '仪表盘主题中的 layoutVariant: cockpit 添加一个 260px 的左侧边栏，插件可通过 sidebar 插槽填充内容。',

    # --- Env Vars & Config Gates ---
    "display.tool_progress_command: true 在消息平台上暴露 /verbose 命令；默认仅在 CLI 中可用。",
    'HERMES_BACKGROUND_NOTIFICATIONS=result 仅在后台任务完成时通知（可选值：all/error/off）。',
    'HERMES_WRITE_SAFE_ROOT 将 write_file 和 patch 限制在指定目录前缀内；外部写入需要审批。',
    'HERMES_IGNORE_RULES 跳过 AGENTS.md、SOUL.md、.cursorrules、记忆和预加载技能的自动注入。',
    'HERMES_ACCEPT_HOOKS 自动批准 config.yaml 中声明的未见过的 shell 钩子，无需 TTY 提示。',
    'auxiliary.goal_judge.model 将 /goal 评审路由到廉价快速的模型，使循环成本接近零。',
    '检查点跳过多于 50,000 个文件的目录，避免在大型单体仓库上执行缓慢的 Git 操作。',

    # --- TTS ---
    'tts.provider: piper 在 CPU 上运行 44 种语言的本地 TTS——语音自动下载到 ~/.hermes/cache/piper-voices/。',
    'tts.providers.<name>.type: command 使用 {input_path} 和 {output_path} 占位符连接任意 CLI TTS 引擎。',

    # --- API Server & Proxy ---
    'API_SERVER_ENABLED=true 在网关旁运行一个 OpenAI 兼容的端点，供 Open WebUI 和 LibreChat 使用。',
    'GATEWAY_PROXY_URL 运行拆分模式：平台 I/O 在本地，agent 工作委托给远程 API 服务器。',

    # --- Platform-specific ---
    'MATRIX_DEVICE_ID 为端到端加密固定稳定的设备 ID——否则每次启动密钥轮换，历史消息解密失败。',
    '设置 TELEGRAM_WEBHOOK_URL 时必须同时设置 TELEGRAM_WEBHOOK_SECRET——使用 openssl rand -hex 32 生成。',

    # --- Batch ---
    "batch_runner.py --resume 通过文本内容匹配已完成的提示，因此数据集重新排序不会重复执行已完成的工作。",

    # --- Less-Known Slash Commands ---
    '/new 原地启动全新会话（别名 /reset）——新会话 ID、清空历史，CLI 保持打开。',
    '/clear 清除终端屏幕并启动新会话——一个快捷键完成视觉重置。',
    '/history 在 CLI 内联打印当前对话——方便快速回顾。',
    '/save 将当前对话写入磁盘而不结束会话。',
    '/status 一目了然显示会话信息：ID、标题、模型、Token 用量和已用时间。',
    '/image <path> 为下一条提示附加本地图片文件，无需粘贴或拖放。',
    '/platforms 在聊天内直接显示网关和消息平台的连接状态。',
    '/commands 分页显示完整的斜杠命令 + 已安装技能列表——在缺少 Tab 补全的平台上很有用。',
    '/toolsets 列出所有可用的工具集，让你知道 -t/--toolsets 接受哪些参数。',
    '/gquota 在 Google Gemini Code Assist 提供商激活时以进度条显示配额使用情况。',
    '/voice tts 切换仅 TTS 模式——agent 语音回复，但你仍通过打字输入提示。',
    '/reload-skills 重新扫描 ~/.hermes/skills/，使即插技能无需重启会话即可生效。',
    '/indicator kaomoji|emoji|unicode|ascii 选择 agent 运行期间显示的 TUI 忙碌指示器样式。',
    '/debug 上传支持包（系统信息 + 日志）并返回可分享的链接——在聊天中也能使用。',

    # --- CLI Subcommands & Flags ---
    'hermes -z "<prompt>" 是最纯粹的一次性查询：仅 stdout 输出最终答案——非常适合在脚本中通过管道使用。',
    'hermes chat --pass-session-id 将会话 ID 注入到系统提示中，使 agent 可以自我引用。',
    'hermes chat --image path/to/pic.png 将本地图片附加到单次 -q 查询中，无需单独的上传步骤。',
    'hermes chat --ignore-user-config 跳过 ~/.hermes/config.yaml——适用于可复现的 Bug 报告和 CI 运行。',
    "hermes chat --source tool 标记编程会话，使其不干扰 hermes sessions 列表。",
    'hermes dump --show-keys 包含脱敏的 API 密钥指纹，用于更深入的支持调试。',
    'hermes sessions rename <ID> "new title" 重命名任意历史会话；hermes sessions delete <ID> 删除会话。',
    'hermes import 恢复由 sessions export 或 profile export 生成的会话导出或 profile 归档。',
    'hermes fallback 交互式管理 fallback_model 链——无需手动编辑 config.yaml。',
    'hermes pairing 轮换私聊配对 Token——轮换后第一个发消息的人获得机器人访问权限。',
    'hermes setup 通过一次交互式流程引导首次用户完成提供商、密钥和平台配置。',
    'hermes status --deep 对所有组件运行全面健康检查；普通 hermes status 是快速视图。',

    # --- Agent Behavior Env Vars ---
    'HERMES_AGENT_TIMEOUT=0 禁用网关对运行中 agent 的不活跃杀死机制——适用于长时间研究任务。',
    'HERMES_ENABLE_PROJECT_PLUGINS=1 从 ./.hermes/plugins/ 自动加载仓库本地插件——设计上受信任门控保护。',
    "HERMES_DISABLE_FILE_STATE_GUARD=1 关闭 patch 和 write_file 上的'文件自你读取后已更改'保护。",
    'HERMES_ALLOW_PRIVATE_URLS=true 允许网页工具访问 localhost 和私有网络——网关模式下默认关闭。',
    'HERMES_OPTIONAL_SKILLS=name1,name2 在每个 profile 首次运行时自动安装额外的可选目录技能。',
    'HERMES_BUNDLED_SKILLS 指向一个自定义的捆绑技能树——被 Homebrew 和 Nix 打包使用。',
    'HERMES_DUMP_REQUEST_STDOUT=1 将每次 API 请求的负载输出到 stdout 而非日志文件。',
    'HERMES_OAUTH_TRACE=1 记录脱敏的 OAuth Token 交换和刷新尝试，用于调试提供商身份验证。',
    'HERMES_STREAM_RETRIES（默认 3）控制临时网络错误时的流中重连尝试次数。',

    # --- Gateway Behavior Env Vars ---
    'HERMES_GATEWAY_BUSY_ACK_ENABLED=false 在用户向忙碌的 agent 发消息时静默 ⚡/⏳/⏩ 确认消息。',
    'HERMES_AGENT_NOTIFY_INTERVAL（默认 180 秒）设置网关在长轮次中发送进度通知的频率。',
    'HERMES_RESTART_DRAIN_TIMEOUT（默认 900 秒）限制 /restart 在强制前等待运行中任务完成的最长时间。',
    'HERMES_CHECKPOINT_TIMEOUT（默认 30 秒）限制文件系统检查点创建时间——在大型单体仓库上可调高。',

    # --- Auxiliary Tasks & Image Generation ---
    'config.yaml 中的 image_gen.model 选择 FAL 模型：flux-2/klein、gpt-image-2、nano-banana-pro 等。',
    'image_gen.provider 通过插件（OpenAI Images、Codex、FAL）路由图像生成，而非使用默认方式。',
    'AUXILIARY_VISION_BASE_URL + AUXILIARY_VISION_API_KEY 将视觉分析指向任意 OpenAI 兼容端点。',

    # --- Security ---
    'security.tirith_fail_open: false 使 Hermes 在 tirith 扫描器本身出错时阻止命令执行。',
    'TIRITH_FAIL_OPEN 环境变量覆盖 tirith_fail_open 配置——无需编辑 config.yaml 即可快速切换。',

    # --- Sessions & Source Tags ---
    '--source tool 的聊天默认从 hermes sessions 列表中排除——明确设置 --source 即可查看它们。',
    '会话 ID 以时间戳为前缀（20250305_091523_abcd），因此在 ls 和 jq 中自然排序。',

    # --- Misc ---
    'API_SERVER_MODEL_NAME 自定义 /v1/models 上的模型名称——多 profile Open WebUI 设置中至关重要。',
    '仪表盘插件从 /dashboard-plugins/<name>/ 提供——将文件放入 ~/.hermes/dashboard-plugins/ 即可。',
]


def get_random_tip(exclude_recent: int = 0) -> str:
    """Return a random tip string.

    Args:
        exclude_recent: not used currently; reserved for future
            deduplication across sessions.
    """
    return random.choice(TIPS)



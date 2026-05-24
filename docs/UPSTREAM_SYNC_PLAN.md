# Hermes → Nermes 上游同步计划

**目的：** 每周五从 Hermes Agent 上游同步最新代码，合并后重新汉化新增文案。

## 当前差距

| 指标 | 数值 |
|------|------|
| Fork 基点 | `1e71b7180` |
| 上游新增 commit | **130** |
| Nermes 独有 commit | **41** |
| 双向修改的冲突文件 | **30** |

## 合并原则（优先级从高到低）

1. **Nermes 品牌优先** — 所有 `hermes` → `nermes` 的替换、路径隔离（`~/.nermes`）以我们的改动为准
2. **汉化文案优先** — `locales/zh.yaml`、`setup.py` 中文提示等以我们为准；上游新增的英文文案需要补译
3. **行业功能叠加** — `professions/`、`tools/finance_*` 是我们独有的，不冲突
4. **上游功能保留** — 新的 feature、bugfix、API 变更全部接纳，仅对用户可见文案做汉化处理
5. **本地化资源** — `nermes_catalog.json`、`nermes_platforms.json` 我们独有，不冲突
6. **README/LICENSE** — 我们的品牌版本不动

## 冲突文件分类（30 个）

### A 类：纯品牌替换冲突（低风险，约 15 个）

这些文件我们只改了 `hermes` → `nermes` / `~/.hermes` → `~/.nermes` 等字符串替换。合并策略：**全部取我们版本**，然后逐文件检查上游是否新增了需要汉化的文案。

```
cli.py
run_agent.py
hermes_state.py
agent/auxiliary_client.py
gateway/config.py
gateway/pairing.py
gateway/run.py
gateway/platforms/base.py
gateway/platforms/telegram.py
gateway/platforms/wecom.py
gateway/platforms/dingtalk.py
gateway/platforms/qqbot/adapter.py
cron/scheduler.py
tools/terminal_tool.py
tools/skills_hub.py
tui_gateway/server.py
```

### B 类：品牌 + 功能双重修改（中风险，约 8 个）

这些文件我们除了品牌替换，还改了行为逻辑（如 `env_loader.py` 的 `NERMES_HOME`、`setup.py` 的平台列表）。合并策略：**手动 diff，逐处判断**。

```
hermes_cli/config.py       — 我们改了默认值、DeepSeek 镜像
hermes_cli/setup.py        — 我们加了中文平台列表、汉化了所有文案
hermes_cli/env_loader.py   — 我们加了 NERMES_HOME 优先
hermes_cli/main.py          — 我们改了 --help 文案
hermes_cli/gateway.py       — 我们改了 setup gateway 文案
hermes_cli/commands.py      — 我们改了 slash command 描述
hermes_cli/_parser.py       — 我们改了 CLI 参数名
hermes_cli/auth.py          — 品牌文案
```

### C 类：上游纯新增（无风险，约 7 个）

上游新增或改动、我们没碰过的文件——直接自动合并。

```
hermes_cli/fallback_config.py
hermes_cli/kanban.py
hermes_cli/plugins_cmd.py
hermes_cli/secrets_cli.py
hermes_cli/skills_hub.py
hermes_cli/tools_config.py
```

## 同步流程（每周五执行）

### Step 0: 准备工作

```bash
cd ~/projects/nermes-core
git checkout main
git pull origin main          # 确保本地最新
git fetch upstream main       # 拉取上游最新
```

### Step 1: 创建同步分支

```bash
git checkout -b sync/upstream-$(date +%Y%m%d)
```

### Step 2: 合并上游

```bash
git merge upstream/main
```

预计有 30+ 冲突，按以下策略解决：

- **A 类文件**：`git checkout --ours <file>` 然后人工扫描上游 diff 找新增英文文案
- **B 类文件**：手动 `vimdiff` 逐冲突解决——我们的文案/配置优先，上游的功能逻辑保留
- **C 类文件**：自动合并
- `README.md` / `LICENSE`：永远取 our 版本

### Step 3: 汉化扫描（合并后）

```bash
# 找出上游新增/修改的 Python 文件中，包含用户可见英文文案的行
git diff main...HEAD -- '*.py' | grep '^+.*["'"'"'].*[a-z]' | grep -v '^+++'

# 特别检查 locales/en.yaml 新增的 key
git diff main...HEAD -- locales/en.yaml | grep '^+  [a-z]'
```

对新增英文文案：
1. 如果 `locales/zh.yaml` 中已有对应 key → 检查翻译质量
2. 如果没有 → 在 `locales/zh.yaml` 中新增中文翻译
3. 如果是 Python 文件中的 f-string / print → 直接汉化

### Step 4: 品牌复查

```bash
# 扫描合并后是否有上游引入的 hermes 品牌残留
git diff main...HEAD -- '*.py' '*.yaml' '*.md' | grep '^+.*Hermes' | grep -v 'HERMES_LANGUAGE' | grep -v 'hermes-agent' | grep -v 'hermes_state' | grep -v 'import.*hermes'
```

### Step 5: 测试

```bash
python -m py_compile $(git diff --name-only main...HEAD -- '*.py')
nermes doctor
```

### Step 6: 提交 & 合并

```bash
git add -A
git commit -m "sync: 合并 Hermes Agent 上游 $(date +%Y-%m-%d)

- 上游 130 commits (截止 $(git rev-parse --short upstream/main))
- 冲突文件: X 个
- 新增汉化: Y 处
- 功能变更: [简述]"

git checkout main
git merge sync/upstream-$(date +%Y%m%d)
git push origin main
```

## 自动化建议

### 汉化检测脚本

可以在合并后自动运行，检测需要汉化的新增文案：

```bash
# scripts/check-localization.sh
# 对比合并前后，找出新增的英文用户可见文案
git diff $MERGE_BASE..HEAD -- '*.py' \
  | grep -E '^\+.*(print_|\.info\(|\.header\(|t\(")' \
  | grep -v '^+++' \
  | grep '[a-zA-Z]{3,}' \
  > /tmp/new_strings_to_localize.txt
```

### Cron 任务（未来）

可以设置每周五自动执行同步脚本（但不自动 push，只生成 PR 或报告）。

## 风险点

1. **上游大幅重构** — 如果上游重命名核心模块、修改 API 签名，需要更多手工适配
2. **我们的 41 个 commit 历史** — 如果上游也改了相同位置，冲突可能比预期多
3. **新功能兼容** — 上游新增的工具/平台可能依赖新的依赖包，需要更新 `pyproject.toml`

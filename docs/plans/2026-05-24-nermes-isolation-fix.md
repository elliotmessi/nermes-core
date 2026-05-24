# Nermes-Hermes 配置隔离修复计划

> 目标：消除 Nermes 所有用户可见的 Hermes 品牌/路径引用，确保 `nermes setup` 全程显示 Nermes 且配置写入 `~/.nermes/`。

**审计时间**: 2026-05-24  
**修复范围**: 用户可见文字 + 硬编码路径 → 动态路径，不改注释/内部变量/模块名

---

## 审计结果

| 类别 | 数量 | 影响 |
|------|------|------|
| 用户可见 Hermes 文字 | ~30 处 | Gateway 启动、平台连接、微信设置等 |
| 硬编码 `~/.hermes/` 路径 | ~8 处 | 日志/环境变量路径提示 |
| 服务标识符 | ~3 处 | systemd unit 名 |
| 代码注释/文档 | ~400+ | 不影响功能，**本轮不修** |

---

## 批次 1: 硬编码 `~/.hermes/` 路径 → 动态

**原则**: 所有路径必须用 `get_hermes_home()` 动态解析，不硬编码任何路径。

### 1.1 `hermes_cli/gateway.py` - 日志路径提示

**文件**: `hermes_cli/gateway.py:5109, 5180, 5442, 5445`

```
旧: nohup hermes gateway run > ~/.hermes/logs/gateway.log 2>&1 &
新: 动态拼接 {home}/logs/gateway.log
```

### 1.2 `hermes_cli/gateway.py` - .env 路径提示

**文件**: `hermes_cli/gateway.py:4799`

```
旧: Set these env vars in ~/.hermes/.env: ...
新: Set these env vars in {home}/.env: ...
```

### 1.3 `hermes_cli/gateway.py` - 微信设置（✅ 已修复）

```
已修复: "~/.hermes/.env" → {env_path}  动态路径
已修复: "Hermes will open/store" → "Nermes will open/store"
```

---

## 批次 2: 用户可见 Hermes 品牌文字

### 2.1 `gateway/run.py`

| 行号 | 原文 | 修改 |
|------|------|------|
| 3553 | `"Starting Hermes Gateway..."` | `"Starting Nermes Gateway..."` |
| 13522 | `"update Hermes Agent"` | `"update Nermes Agent"` |
| 13549 | `"update Hermes Agent"` | `"update Nermes Agent"` |
| 18159 | `"Hermes Gateway - Multi-platform messaging"` | `"Nermes Gateway - 多平台消息集成"` |

### 2.2 `gateway/platforms/whatsapp.py:245`

```
旧: DEFAULT_REPLY_PREFIX = "⚕ *Hermes Agent*\n────────────\n"
新: DEFAULT_REPLY_PREFIX = "⚕ *Nermes Agent*\n────────────\n"
```

### 2.3 `gateway/platforms/discord.py:3035`

```
旧: description="Update Hermes Agent to the latest version"
新: description="Update Nermes Agent to the latest version"
```

### 2.4 `hermes_cli/gateway.py:1258`

```
旧: SERVICE_DESCRIPTION = "Hermes Agent Gateway - Messaging Platform Integration"
新: SERVICE_DESCRIPTION = "Nermes Agent Gateway - 消息平台集成"
```

### 2.5 `hermes_cli/gateway.py:3209`

```
旧: "│           ⚕ Hermes Gateway Starting...                 │"
新: "│           ⚕ Nermes Gateway 启动中...                  │"
```

### 2.6 `hermes_cli/gateway.py` - 其他 Hermes 提示

搜索并替换 `grep -n "Hermes " hermes_cli/gateway.py | grep -v "^#" | grep -v "def \|class \|import "` 中所有用户可见的 Hermes → Nermes。

### 2.7 `acp_adapter/entry.py:114`

```
旧: description="Run Hermes Agent as an ACP stdio server."
新: description="Run Nermes Agent as an ACP stdio server."
```

### 2.8 `acp_adapter/server.py:1,1874`

```
旧: """ACP agent server — exposes Hermes Agent..."""
新: """ACP agent server — exposes Nermes Agent..."""

旧: return f"Hermes Agent v{HERMES_VERSION}"
新: return f"Nermes Agent v{HERMES_VERSION}"
```

### 2.9 `mcp_serve.py:461`

```
旧: "Hermes Agent messaging bridge..."
新: "Nermes Agent messaging bridge..."
```

---

## 批次 3: 服务标识符

### 3.1 `hermes_cli/gateway.py:1257`

```
旧: _SERVICE_BASE = "hermes-gateway"
新: _SERVICE_BASE = "nermes-gateway"
```

> ⚠️ 此项会影响 systemd 服务名、plist 标签。如果用户已有 Hermes gateway 服务运行，不会冲突（Nermes 用自己的 service 名）。

### 3.2 `hermes_cli/gateway.py:1319-1320`

```
旧: Default ``~/.hermes`` returns ``hermes-gateway``
    Profile ``~/.hermes/profiles/coder`` returns ``hermes-gateway-coder``.
新: Default ``~/.nermes`` returns ``nermes-gateway``
    Profile ``~/.nermes/profiles/coder`` returns ``nermes-gateway-coder``.
```

### 3.3 `hermes_cli/gateway.py:1949-1950` (macOS plist)

```
旧: Default ``~/.hermes`` → ``ai.hermes.gateway.plist``
    Profile ``~/.hermes/profiles/coder`` → ``ai.hermes.gateway-coder.plist``
新: Default ``~/.nermes`` → ``ai.nermes.gateway.plist``
    Profile ``~/.nermes/profiles/coder`` → ``ai.nermes.gateway-coder.plist``
```

---

## 批次 4: 修复 `_setup_weixin` 中 `get_env_value` 路径确认

**文件**: `hermes_cli/gateway.py:4225-4226`

验证 `get_env_value("WEIXIN_ACCOUNT_ID")` 和 `get_env_value("WEIXIN_TOKEN")` 实际上是从 `~/.nermes/.env` 读取（因为 `get_hermes_home()` 已修），但需确认 `get_env_value` 的实现路径。

---

## 验收标准

### 必须通过

1. ✅ `nermes setup` 全程不出现 "Hermes" 文字（除技术说明外）
2. ✅ `nermes setup` 微信连接向导显示 `~/.nermes/.env`
3. ✅ `nermes gateway run` 日志路径指向 `~/.nermes/logs/`
4. ✅ WhatsApp/Discord 等平台的 Agent 名称显示为 "Nermes"
5. ✅ systemd 服务名使用 `nermes-gateway`
6. ✅ Gateway 启动 banner 显示 "Nermes Gateway"

### 验证命令

```bash
# 1. 搜索残留
grep -rn "Hermes " gateway/run.py gateway/platforms/ hermes_cli/gateway.py acp_adapter/ mcp_serve.py \
  | grep -v "^#" | grep -v "def \|class \|import " | grep -v "hermes_"

# 2. 搜索残留路径
grep -rn "~/.hermes" gateway/ hermes_cli/gateway.py \
  | grep -v "^#" | grep -v "legacy" | grep -v "old"

# 3. 运行 setup
NERMES_HOME=~/.nermes nermes setup
# → 选择微信 → 确认文案都是 Nermes + ~/.nermes/.env

# 4. 运行 gateway
NERMES_HOME=~/.nermes nermes gateway run
# → 确认启动 banner 是 Nermes
```

---

## 不改的范围

- ❌ 代码注释中的 "Hermes"（如 `"""Hermes profile are returned."""`)
- ❌ 模块名（`hermes_cli`, `hermes_constants`, `hermes_state` 等）
- ❌ 内部变量名（`hermes_home`, `HERMES_VERSION` 等）
- ❌ 旧版迁移代码（`legacy Hermes` 注释）
- ❌ Docker/Nix 部署脚本（`docker/`, `nix/`）
- ❌ 测试文件（`tests/`）

"""
Status command for hermes CLI.

Shows the status of all Hermes Agent components.
"""

import os
import sys
import subprocess  # noqa: F401 — re-exported for tests that monkeypatch status.subprocess to guard against regressions
import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

from hermes_cli.auth import AuthError, resolve_provider
from hermes_cli.colors import Colors, color
from hermes_cli.config import get_env_path, get_env_value, get_hermes_home, load_config
from hermes_cli.models import provider_label
from hermes_cli.nous_subscription import get_nous_subscription_features
from hermes_cli.runtime_provider import resolve_requested_provider
from hermes_cli.vercel_auth import describe_vercel_auth
from hermes_constants import OPENROUTER_MODELS_URL
from tools.tool_backend_helpers import managed_nous_tools_enabled

def check_mark(ok: bool) -> str:
    if ok:
        return color("✓", Colors.GREEN)
    return color("✗", Colors.RED)

def redact_key(key: str) -> str:
    """Redact an API key for display.

    Thin wrapper over :func:`agent.redact.mask_secret`. Preserves the
    "(not set)" placeholder in dim color to match ``hermes config``'s
    output (previously this variant was missing the DIM color —
    consolidated via PR that also introduced ``mask_secret``).
    """
    from agent.redact import mask_secret
    return mask_secret(key, empty=color("(未设置)", Colors.DIM))


def _format_iso_timestamp(value) -> str:
    """Format ISO timestamps for status output, converting to local timezone."""
    if not value or not isinstance(value, str):
        return "(未知)"
    from datetime import datetime, timezone
    text = value.strip()
    if not text:
        return "(未知)"
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return value
    return parsed.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _configured_model_label(config: dict) -> str:
    """Return the configured default model from config.yaml."""
    model_cfg = config.get("model")
    if isinstance(model_cfg, dict):
        model = (model_cfg.get("default") or model_cfg.get("name") or "").strip()
    elif isinstance(model_cfg, str):
        model = model_cfg.strip()
    else:
        model = ""
    return model or "(未设置)"


def _effective_provider_label() -> str:
    """Return the provider label matching current CLI runtime resolution."""
    requested = resolve_requested_provider()
    try:
        effective = resolve_provider(requested)
    except AuthError:
        effective = requested or "auto"

    if effective == "openrouter" and get_env_value("OPENAI_BASE_URL"):
        effective = "custom"

    return provider_label(effective)


from hermes_constants import is_termux as _is_termux


def show_status(args):
    """Show status of all Hermes Agent components."""
    show_all = getattr(args, 'all', False)
    deep = getattr(args, 'deep', False)

    print()
    print(color("┌─────────────────────────────────────────────────────────┐", Colors.CYAN))
    print(color("│                 ⚕ Nermes Agent 状态                │", Colors.CYAN))
    print(color("└─────────────────────────────────────────────────────────┘", Colors.CYAN))

    # =========================================================================
    # Environment
    # =========================================================================
    print()
    print(color("◆ 环境", Colors.CYAN, Colors.BOLD))
    print(f"  项目路径:  {PROJECT_ROOT}")
    print(f"  Python:       {sys.version.split()[0]}")

    env_path = get_env_path()
    print(f"  .env 文件:    {check_mark(env_path.exists())} {'已存在' if env_path.exists() else '未找到'}")

    try:
        config = load_config()
    except Exception:
        config = {}

    print(f"  模型:        {_configured_model_label(config)}")
    print(f"  提供商:     {_effective_provider_label()}")

    # =========================================================================
    # API Keys
    # =========================================================================
    print()
    print(color("◆ API 密钥", Colors.CYAN, Colors.BOLD))

    # Values may be a single env var name (str) or a tuple of alternates (first found wins).
    keys: dict[str, str | tuple[str, ...]] = {
        "OpenRouter": "OPENROUTER_API_KEY",
        "OpenAI": "OPENAI_API_KEY",
        "Anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_TOKEN"),
        "Google / Gemini": ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
        "DeepSeek": "DEEPSEEK_API_KEY",
        "xAI / Grok": "XAI_API_KEY",
        "NVIDIA NIM": "NVIDIA_API_KEY",
        "Z.AI / GLM": "GLM_API_KEY",
        "Kimi": "KIMI_API_KEY",
        "StepFun Step Plan": "STEPFUN_API_KEY",
        "MiniMax": "MINIMAX_API_KEY",
        "MiniMax-CN": "MINIMAX_CN_API_KEY",
        "Firecrawl": "FIRECRAWL_API_KEY",
        "Tavily": "TAVILY_API_KEY",
        "Browser Use": "BROWSER_USE_API_KEY",  # Optional — local browser works without this
        "Browserbase": "BROWSERBASE_API_KEY",  # Optional — direct credentials only
        "FAL": "FAL_KEY",
        "ElevenLabs": "ELEVENLABS_API_KEY",
        "GitHub": "GITHUB_TOKEN",
    }

    def _resolve_env(env_ref) -> str:
        """Return first non-empty env var value from a str or tuple of names."""
        if isinstance(env_ref, tuple):
            for candidate in env_ref:
                v = get_env_value(candidate) or ""
                if v:
                    return v
            return ""
        return get_env_value(env_ref) or ""

    for name, env_ref in keys.items():
        # Anthropic already has a dedicated lookup below; keep that as the
        # single source of truth (it also resolves OAuth tokens), skip here
        # so we don't print two "Anthropic" rows.
        if name == "Anthropic":
            continue
        value = _resolve_env(env_ref)
        has_key = bool(value)
        display = redact_key(value) if not show_all else value
        print(f"  {name:<12}  {check_mark(has_key)} {display}")

    from hermes_cli.auth import get_anthropic_key
    anthropic_value = get_anthropic_key()
    anthropic_display = redact_key(anthropic_value) if not show_all else anthropic_value
    print(f"  {'Anthropic':<12}  {check_mark(bool(anthropic_value))} {anthropic_display}")

    # =========================================================================
    # Auth Providers (OAuth)
    # =========================================================================
    print()
    print(color("◆ 认证提供商", Colors.CYAN, Colors.BOLD))

    try:
        from hermes_cli.auth import (
            get_nous_auth_status,
            get_codex_auth_status,
            get_qwen_auth_status,
            get_minimax_oauth_auth_status,
        )
        nous_status = get_nous_auth_status()
        codex_status = get_codex_auth_status()
        qwen_status = get_qwen_auth_status()
        minimax_status = get_minimax_oauth_auth_status()
    except Exception:
        nous_status = {}
        codex_status = {}
        qwen_status = {}
        minimax_status = {}

    nous_logged_in = bool(nous_status.get("logged_in"))
    nous_error = nous_status.get("error")
    nous_label = "已登录" if nous_logged_in else "未登录（运行: hermes auth add nous --type oauth）"
    print(
        f"  {'Nous Portal':<12}  {check_mark(nous_logged_in)} "
        f"{nous_label}"
    )
    portal_url = nous_status.get("portal_base_url") or "(未知)"
    access_exp = _format_iso_timestamp(nous_status.get("access_expires_at"))
    key_exp = _format_iso_timestamp(nous_status.get("agent_key_expires_at"))
    refresh_label = "是" if nous_status.get("has_refresh_token") else "否"
    if nous_logged_in or portal_url != "(未知)" or nous_error:
        print(f"    门户地址: {portal_url}")
    if nous_logged_in or nous_status.get("access_expires_at"):
        print(f"    访问过期: {access_exp}")
    if nous_logged_in or nous_status.get("agent_key_expires_at"):
        print(f"    密钥过期: {key_exp}")
    if nous_logged_in or nous_status.get("has_refresh_token"):
        print(f"    刷新令牌: {refresh_label}")
    if nous_error and not nous_logged_in:
        print(f"    错误:      {nous_error}")

    codex_logged_in = bool(codex_status.get("logged_in"))
    print(
        f"  {'OpenAI Codex':<12}  {check_mark(codex_logged_in)} "
        f"{'已登录' if codex_logged_in else '未登录（运行: hermes model）'}"
    )
    codex_auth_file = codex_status.get("auth_store")
    if codex_auth_file:
        print(f"    认证文件:  {codex_auth_file}")
    codex_last_refresh = _format_iso_timestamp(codex_status.get("last_refresh"))
    if codex_status.get("last_refresh"):
        print(f"    刷新时间:  {codex_last_refresh}")
    if codex_status.get("error") and not codex_logged_in:
        print(f"    错误:      {codex_status.get('error')}")

    qwen_logged_in = bool(qwen_status.get("logged_in"))
    print(
        f"  {'Qwen OAuth':<12}  {check_mark(qwen_logged_in)} "
        f"{'已登录' if qwen_logged_in else '未登录（运行: qwen auth qwen-oauth）'}"
    )
    qwen_auth_file = qwen_status.get("auth_file")
    if qwen_auth_file:
        print(f"    认证文件:  {qwen_auth_file}")
    qwen_exp = qwen_status.get("expires_at_ms")
    if qwen_exp:
        from datetime import datetime, timezone
        print(f"    访问过期: {datetime.fromtimestamp(int(qwen_exp) / 1000, tz=timezone.utc).isoformat()}")
    if qwen_status.get("error") and not qwen_logged_in:
        print(f"    错误:      {qwen_status.get('error')}")

    minimax_logged_in = bool(minimax_status.get("logged_in"))
    print(
        f"  {'MiniMax OAuth':<12}  {check_mark(minimax_logged_in)} "
        f"{'已登录' if minimax_logged_in else '未登录（运行: hermes auth add minimax-oauth）'}"
    )
    minimax_region = minimax_status.get("region")
    if minimax_logged_in and minimax_region:
        print(f"    区域:     {minimax_region}")
    minimax_exp = minimax_status.get("expires_at")
    if minimax_exp:
        print(f"    访问过期: {minimax_exp}")
    if minimax_status.get("error") and not minimax_logged_in:
        print(f"    错误:      {minimax_status.get('error')}")

    # xAI OAuth — separate try/except so an import failure here cannot
    # disrupt the already-printed Nous/Codex/Qwen/MiniMax rows above.
    try:
        from hermes_cli.auth import get_xai_oauth_auth_status
        xai_oauth_status = get_xai_oauth_auth_status() or {}
    except Exception:
        xai_oauth_status = {}

    xai_oauth_logged_in = bool(xai_oauth_status.get("logged_in"))
    print(
        f"  {'xAI OAuth':<12}  {check_mark(xai_oauth_logged_in)} "
        f"{'已登录' if xai_oauth_logged_in else '未登录（运行: hermes auth add xai-oauth）'}"
    )
    xai_auth_file = xai_oauth_status.get("auth_store")
    if xai_auth_file:
        print(f"    认证文件:  {xai_auth_file}")
    if xai_oauth_status.get("last_refresh"):
        print(f"    刷新时间:  {_format_iso_timestamp(xai_oauth_status.get('last_refresh'))}")
    if xai_oauth_status.get("error") and not xai_oauth_logged_in:
        print(f"    错误:      {xai_oauth_status.get('error')}")

    # =========================================================================
    # Nous Subscription Features
    # =========================================================================
    if managed_nous_tools_enabled():
        features = get_nous_subscription_features(config)
        print()
        print(color("◆ Nous 工具网关", Colors.CYAN, Colors.BOLD))
        if not features.nous_auth_present:
            print("  Nous Portal   ✗ 未登录")
        else:
            print("  Nous Portal   ✓ 托管工具可用")
        for feature in features.items():
            if feature.managed_by_nous:
                state = "通过 Nous 订阅激活"
            elif feature.active:
                current = feature.current_provider or "已配置提供商"
                state = f"通过 {current} 激活"
            elif feature.included_by_default and features.nous_auth_present:
                state = "已包含在订阅中，当前未选择"
            elif feature.key == "modal" and features.nous_auth_present:
                state = "可通过订阅获取（可选）"
            else:
                state = "未配置"
            print(f"  {feature.label:<15} {check_mark(feature.available or feature.active or feature.managed_by_nous)} {state}")
    elif nous_logged_in:
        # Logged into Nous but on the free tier — show upgrade nudge
        print()
        print(color("◆ Nous 工具网关", Colors.CYAN, Colors.BOLD))
        print("  您的免费版 Nous 账户不包含工具网关访问权限。")
        print("  升级订阅以解锁托管的网络、图像、TTS 和浏览器工具。")
        try:
            portal_url = nous_status.get("portal_base_url", "").rstrip("/")
            if portal_url:
                print(f"  升级: {portal_url}")
        except Exception:
            pass

    # =========================================================================
    # API-Key Providers
    # =========================================================================
    print()
    print(color("◆ API 密钥提供商", Colors.CYAN, Colors.BOLD))

    apikey_providers = {
        "Z.AI / GLM":       ("GLM_API_KEY", "ZAI_API_KEY", "Z_AI_API_KEY"),
        "Kimi / Moonshot":  ("KIMI_API_KEY",),
        "StepFun Step Plan": ("STEPFUN_API_KEY",),
        "MiniMax":          ("MINIMAX_API_KEY",),
        "MiniMax (China)":  ("MINIMAX_CN_API_KEY",),
    }
    for pname, env_vars in apikey_providers.items():
        key_val = ""
        for ev in env_vars:
            key_val = get_env_value(ev) or ""
            if key_val:
                break
        configured = bool(key_val)
        label = "已配置" if configured else "未配置（运行: hermes model）"
        print(f"  {pname:<16} {check_mark(configured)} {label}")

    # LM Studio reachability — only probe when it's the active provider so
    # users with foreign configs don't see noise. Auth rejection vs. silent
    # empty list is the most common LM Studio support case.
    if _effective_provider_label() == "LM Studio":
        from hermes_cli.models import probe_lmstudio_models
        model_cfg = config.get("model")
        base = (model_cfg.get("base_url") if isinstance(model_cfg, dict) else None) or get_env_value("LM_BASE_URL") or "http://127.0.0.1:1234/v1"
        try:
            models = probe_lmstudio_models(api_key=get_env_value("LM_API_KEY") or "", base_url=base, timeout=1.5)
            if models is None:
                ok, msg = False, f"无法访问 {base}"
            else:
                ok, msg = True, f"可访问（{len(models)} 个模型）{base}"
        except AuthError:
            ok, msg = False, "认证被拒绝 — 设置 LM_API_KEY"
        print(f"  {'LM Studio':<16} {check_mark(ok)} {msg}")

    # =========================================================================
    # Terminal Configuration
    # =========================================================================
    print()
    print(color("◆ 终端后端", Colors.CYAN, Colors.BOLD))

    terminal_cfg = config.get("terminal", {}) if isinstance(config.get("terminal"), dict) else {}
    terminal_env = os.getenv("TERMINAL_ENV", "")
    if not terminal_env:
        terminal_env = terminal_cfg.get("backend", "local")
    print(f"  后端:      {terminal_env}")

    if terminal_env == "ssh":
        ssh_host = os.getenv("TERMINAL_SSH_HOST", "")
        ssh_user = os.getenv("TERMINAL_SSH_USER", "")
        print(f"  SSH 主机:     {ssh_host or '(未设置)'}")
        print(f"  SSH 用户:     {ssh_user or '(未设置)'}")
    elif terminal_env == "docker":
        docker_image = os.getenv("TERMINAL_DOCKER_IMAGE", "python:3.11-slim")
        print(f"  Docker 镜像: {docker_image}")
    elif terminal_env == "daytona":
        daytona_image = os.getenv("TERMINAL_DAYTONA_IMAGE", "nikolaik/python-nodejs:python3.11-nodejs20")
        print(f"  Daytona 镜像: {daytona_image}")
    elif terminal_env == "vercel_sandbox":
        runtime = os.getenv("TERMINAL_VERCEL_RUNTIME") or terminal_cfg.get("vercel_runtime") or "node24"
        persist = os.getenv("TERMINAL_CONTAINER_PERSISTENT")
        if persist is None:
            persist_enabled = bool(terminal_cfg.get("container_persistent", True))
        else:
            persist_enabled = persist.lower() in {"1", "true", "yes", "on"}
        auth_status = describe_vercel_auth()
        sdk_ok = importlib.util.find_spec("vercel") is not None
        sdk_label = "已安装" if sdk_ok else "未安装（安装: pip install 'hermes-agent[vercel]'）"
        print(f"  运行时:      {runtime}")
        print(f"  SDK:          {check_mark(sdk_ok)} {sdk_label}")
        print(f"  认证:         {check_mark(auth_status.ok)} {auth_status.label}")
        for line in auth_status.detail_lines:
            print(f"  认证详情:  {line}")
        print(f"  持久化:  {'快照文件系统' if persist_enabled else '临时文件系统'}")
        print("  进程:    活动进程在清理、快照或沙盒重建后无法存活")

    sudo_password = os.getenv("SUDO_PASSWORD", "")
    print(f"  Sudo:         {check_mark(bool(sudo_password))} {'已启用' if sudo_password else '已禁用'}")

    # =========================================================================
    # Messaging Platforms
    # =========================================================================
    print()
    print(color("◆ 消息平台", Colors.CYAN, Colors.BOLD))

    platforms = {
        "Telegram": ("TELEGRAM_BOT_TOKEN", "TELEGRAM_HOME_CHANNEL"),
        "Discord": ("DISCORD_BOT_TOKEN", "DISCORD_HOME_CHANNEL"),
        "WhatsApp": ("WHATSAPP_ENABLED", None),
        "Signal": ("SIGNAL_HTTP_URL", "SIGNAL_HOME_CHANNEL"),
        "Slack": ("SLACK_BOT_TOKEN", None),
        "Email": ("EMAIL_ADDRESS", "EMAIL_HOME_ADDRESS"),
        "SMS": ("TWILIO_ACCOUNT_SID", "SMS_HOME_CHANNEL"),
        "DingTalk": ("DINGTALK_CLIENT_ID", None),
        "Feishu": ("FEISHU_APP_ID", "FEISHU_HOME_CHANNEL"),
        "WeCom": ("WECOM_BOT_ID", "WECOM_HOME_CHANNEL"),
        "WeCom Callback": ("WECOM_CALLBACK_CORP_ID", None),
        "Weixin": ("WEIXIN_ACCOUNT_ID", "WEIXIN_HOME_CHANNEL"),
        "BlueBubbles": ("BLUEBUBBLES_SERVER_URL", "BLUEBUBBLES_HOME_CHANNEL"),
        "QQBot": ("QQ_APP_ID", "QQ_HOME_CHANNEL"),
        "Yuanbao": ("YUANBAO_APP_ID", "YUANBAO_HOME_CHANNEL"),
    }

    for name, (token_var, home_var) in platforms.items():
        token = os.getenv(token_var, "")
        has_token = bool(token)
        
        home_channel = ""
        if home_var:
            home_channel = os.getenv(home_var, "")
        # Back-compat: QQBot home channel was renamed from QQ_HOME_CHANNEL to QQBOT_HOME_CHANNEL
        if not home_channel and home_var == "QQBOT_HOME_CHANNEL":
            home_channel = os.getenv("QQ_HOME_CHANNEL", "")
        
        status = "已配置" if has_token else "未配置"
        if home_channel:
            status += f"（主页: {home_channel}）"
        
        print(f"  {name:<12}  {check_mark(has_token)} {status}")

    # Plugin-registered platforms
    try:
        from gateway.platform_registry import platform_registry
        for entry in platform_registry.plugin_entries():
            configured = entry.check_fn()
            status_str = "已配置" if configured else "未配置"
            label = entry.label
            print(f"  {label:<12}  {check_mark(configured)} {status_str}（插件）")
    except Exception:
        pass

    # =========================================================================
    # Gateway Status
    # =========================================================================
    print()
    print(color("◆ 网关服务", Colors.CYAN, Colors.BOLD))

    try:
        from hermes_cli.gateway import get_gateway_runtime_snapshot, _format_gateway_pids

        snapshot = get_gateway_runtime_snapshot()
        is_running = snapshot.running
        print(f"  状态:       {check_mark(is_running)} {'运行中' if is_running else '已停止'}")
        print(f"  管理器:      {snapshot.manager}")
        if snapshot.gateway_pids:
            print(f"  PID:       {_format_gateway_pids(snapshot.gateway_pids)}")
        if snapshot.has_process_service_mismatch:
            print("  服务:      已安装但未管理当前运行的网关")
        elif _is_termux() and not snapshot.gateway_pids:
            print("  启动命令:   hermes gateway")
            print("  注意:      Android 可能在 Termux 挂起时停止后台任务")
        elif snapshot.service_installed and not snapshot.service_running:
            print("  服务:      已安装但已停止")
    except Exception:
        if _is_termux():
            print(f"  状态:       {color('unknown', Colors.DIM)}")
            print("  管理器:      Termux / 手动进程")
        elif sys.platform.startswith('linux'):
            print(f"  状态:       {color('unknown', Colors.DIM)}")
            print("  管理器:      systemd/手动")
        elif sys.platform == 'darwin':
            print(f"  状态:       {color('unknown', Colors.DIM)}")
            print("  管理器:      launchd")
        else:
            print(f"  状态:       {color('N/A', Colors.DIM)}")
            print("  管理器:      （此平台不支持）")

    # =========================================================================
    # Cron Jobs
    # =========================================================================
    print()
    print(color("◆ 定时任务", Colors.CYAN, Colors.BOLD))

    jobs_file = get_hermes_home() / "cron" / "jobs.json"
    if jobs_file.exists():
        import json
        try:
            with open(jobs_file, encoding="utf-8") as f:
                data = json.load(f)
                jobs = data.get("jobs", [])
                enabled_jobs = [j for j in jobs if j.get("enabled", True)]
                print(f"  任务:         {len(enabled_jobs)} 活跃，共 {len(jobs)} 个")
        except Exception:
            print("  任务:         （读取任务文件出错）")
    else:
        print("  任务:         0")

    # =========================================================================
    # Sessions
    # =========================================================================
    print()
    print(color("◆ 会话", Colors.CYAN, Colors.BOLD))

    sessions_file = get_hermes_home() / "sessions" / "sessions.json"
    if sessions_file.exists():
        import json
        try:
            with open(sessions_file, encoding="utf-8") as f:
                data = json.load(f)
                print(f"  活跃:       {len(data)} 个会话")
        except Exception:
            print("  活跃:       （读取会话文件出错）")
    else:
        print("  活跃:       0")

    # =========================================================================
    # Deep checks
    # =========================================================================
    if deep:
        print()
        print(color("◆ 深度检查", Colors.CYAN, Colors.BOLD))
        
        # Check OpenRouter connectivity
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        if openrouter_key:
            try:
                import httpx
                response = httpx.get(
                    OPENROUTER_MODELS_URL,
                    headers={"Authorization": f"Bearer {openrouter_key}"},
                    timeout=10
                )
                ok = response.status_code == 200
                print(f"  OpenRouter:   {check_mark(ok)} {'可达' if ok else f'错误（{response.status_code}）'}")
            except Exception as e:
                print(f"  OpenRouter:   {check_mark(False)} 错误: {e}")
        
        # Check gateway port
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', 18789))
            sock.close()
            # Port in use = gateway likely running
            port_in_use = result == 0
            # This is informational, not necessarily bad
            print(f"  端口 18789:   {'使用中' if port_in_use else '可用'}")
        except OSError:
            pass

    print()
    print(color("─" * 60, Colors.DIM))
    print(color(" 运行 'hermes doctor' 获取详细诊断", Colors.DIM))
    print(color(" 运行 'hermes setup' 进行配置", Colors.DIM))
    print()

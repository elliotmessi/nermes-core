"""Hermes Agent 交互式安装向导。

模块化向导，各章节可独立运行：
  1. 模型与提供商 — 选择你的 AI 提供商和模型
  2. 终端后端 — 代理执行命令的环境
  3. 代理设置 — 迭代次数、压缩、会话重置
  4. 消息平台 — 连接 Telegram、Discord 等
  5. 工具 — 配置 TTS、网页搜索、图像生成等

配置文件存储在 ~/.hermes/ 中，方便随时查看。
"""

import importlib.util
import json
import logging
import os
import re
import shutil
import sys
import copy
from pathlib import Path
from typing import Optional, Dict, Any

from hermes_cli.nous_subscription import get_nous_subscription_features
from tools.tool_backend_helpers import managed_nous_tools_enabled
from utils import base_url_hostname
from hermes_constants import get_optional_skills_dir

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

_DOCS_BASE = "https://hermes-agent.nousresearch.com/docs"


def _model_config_dict(config: Dict[str, Any]) -> Dict[str, Any]:
    current_model = config.get("model")
    if isinstance(current_model, dict):
        return dict(current_model)
    if isinstance(current_model, str) and current_model.strip():
        return {"default": current_model.strip()}
    return {}


def _get_credential_pool_strategies(config: Dict[str, Any]) -> Dict[str, str]:
    strategies = config.get("credential_pool_strategies")
    return dict(strategies) if isinstance(strategies, dict) else {}


def _set_credential_pool_strategy(config: Dict[str, Any], provider: str, strategy: str) -> None:
    if not provider:
        return
    strategies = _get_credential_pool_strategies(config)
    strategies[provider] = strategy
    config["credential_pool_strategies"] = strategies


def _supports_same_provider_pool_setup(provider: str) -> bool:
    if not provider or provider == "custom":
        return False
    if provider == "openrouter":
        return True
    from hermes_cli.auth import PROVIDER_REGISTRY

    pconfig = PROVIDER_REGISTRY.get(provider)
    if not pconfig:
        return False
    return pconfig.auth_type in {"api_key", "oauth_device_code"}


# Default model lists per provider — used as fallback when the live
# /models endpoint can't be reached.
_DEFAULT_PROVIDER_MODELS = {
    "copilot-acp": [
        "copilot-acp",
    ],
    "copilot": [
        "gpt-5.4",
        "gpt-5.4-mini",
        "gpt-5-mini",
        "gpt-5.3-codex",
        "gpt-5.2-codex",
        "gpt-4.1",
        "gpt-4o",
        "gpt-4o-mini",
        "claude-opus-4.6",
        "claude-sonnet-4.6",
        "claude-sonnet-4.5",
        "claude-haiku-4.5",
        "gemini-2.5-pro",
    ],
    "gemini": [
        "gemini-3.1-pro-preview", "gemini-3-pro-preview",
        "gemini-3-flash-preview", "gemini-3.1-flash-lite-preview",
    ],
    "zai": ["glm-5.1", "glm-5", "glm-4.7", "glm-4.5", "glm-4.5-flash"],
    "kimi-coding": ["kimi-k2.6", "kimi-k2.5", "kimi-k2-thinking", "kimi-k2-turbo-preview"],
    "kimi-coding-cn": ["kimi-k2.6", "kimi-k2.5", "kimi-k2-thinking", "kimi-k2-turbo-preview"],
    "stepfun": ["step-3.5-flash", "step-3.5-flash-2603"],
    "arcee": ["trinity-large-thinking", "trinity-large-preview", "trinity-mini"],
    "minimax": ["MiniMax-M2.7", "MiniMax-M2.5", "MiniMax-M2.1", "MiniMax-M2"],
    "minimax-cn": ["MiniMax-M2.7", "MiniMax-M2.5", "MiniMax-M2.1", "MiniMax-M2"],
    "ai-gateway": ["anthropic/claude-opus-4.6", "anthropic/claude-sonnet-4.6", "openai/gpt-5", "google/gemini-3-flash"],
    "kilocode": ["anthropic/claude-opus-4.6", "anthropic/claude-sonnet-4.6", "openai/gpt-5.4", "google/gemini-3-pro-preview", "google/gemini-3-flash-preview"],
    "opencode-zen": ["gpt-5.4", "gpt-5.3-codex", "claude-sonnet-4-6", "gemini-3-flash", "glm-5", "kimi-k2.5", "minimax-m2.7"],
    "opencode-go": ["kimi-k2.6", "kimi-k2.5", "glm-5.1", "glm-5", "mimo-v2.5-pro", "mimo-v2.5", "mimo-v2-pro", "mimo-v2-omni", "minimax-m2.7", "minimax-m2.5", "qwen3.6-plus", "qwen3.5-plus"],
    "huggingface": [
        "Qwen/Qwen3.5-397B-A17B", "Qwen/Qwen3-235B-A22B-Thinking-2507",
        "Qwen/Qwen3-Coder-480B-A35B-Instruct", "deepseek-ai/DeepSeek-R1-0528",
        "deepseek-ai/DeepSeek-V3.2", "moonshotai/Kimi-K2.5",
    ],
}


def _current_reasoning_effort(config: Dict[str, Any]) -> str:
    agent_cfg = config.get("agent")
    if isinstance(agent_cfg, dict):
        return str(agent_cfg.get("reasoning_effort") or "").strip().lower()
    return ""


def _set_reasoning_effort(config: Dict[str, Any], effort: str) -> None:
    agent_cfg = config.get("agent")
    if not isinstance(agent_cfg, dict):
        agent_cfg = {}
        config["agent"] = agent_cfg
    agent_cfg["reasoning_effort"] = effort




# Import config helpers
from hermes_cli.config import (
    cfg_get,
    DEFAULT_CONFIG,
    get_hermes_home,
    get_config_path,
    get_env_path,
    load_config,
    save_config,
    save_env_value,
    remove_env_value,
    get_env_value,
    ensure_hermes_home,
)
# display_hermes_home imported lazily at call sites (stale-module safety during hermes update)

from hermes_cli.colors import Colors, color


def print_header(title: str):
    """Print a section header."""
    print()
    print(color(f"◆ {title}", Colors.CYAN, Colors.BOLD))


from hermes_cli.cli_output import (  # noqa: E402
    print_error,
    print_info,
    print_success,
    print_warning,
)


def is_interactive_stdin() -> bool:
    """Return True when stdin looks like a usable interactive TTY."""
    stdin = getattr(sys, "stdin", None)
    if stdin is None:
        return False
    try:
        return bool(stdin.isatty())
    except Exception:
        return False


def print_noninteractive_setup_guidance(reason: str | None = None) -> None:
    """Print guidance for headless/non-interactive setup flows."""
    print()
    print(color("⚕ Hermes 安装 — 非交互模式", Colors.CYAN, Colors.BOLD))
    print()
    if reason:
        print_info(reason)
    print_info("此处无法使用交互式安装向导。")
    print()
    print_info("请使用环境变量或配置命令来设置 Hermes：")
    print_info("  hermes config set model.provider custom")
    print_info("  hermes config set model.base_url http://localhost:8080/v1")
    print_info("  hermes config set model.default your-model-name")
    print()
    print_info("或者在环境中设置 OPENROUTER_API_KEY / OPENAI_API_KEY。")
    print_info("在交互式终端中运行 'hermes setup' 以使用完整的安装向导。")
    print()


def prompt(question: str, default: str = None, password: bool = False) -> str:
    """提示输入，可设置默认值和密码模式。"""
    if default:
        display = f"{question} [{default}]: "
    else:
        display = f"{question}: "

    try:
        if password:
            import getpass

            value = getpass.getpass(color(display, Colors.YELLOW))
        else:
            value = input(color(display, Colors.YELLOW))

        cleaned = _sanitize_pasted_input(value)
        return cleaned.strip() or default or ""
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(1)


_BRACKETED_PASTE_PATTERN = re.compile(r"\x1b\[\s*200~|\x1b\[\s*201~")


def _sanitize_pasted_input(value: str) -> str:
    """Strip terminal bracketed-paste control markers from pasted text."""
    if not isinstance(value, str) or not value:
        return value
    return _BRACKETED_PASTE_PATTERN.sub("", value)


def _curses_prompt_choice(question: str, choices: list, default: int = 0, description: str | None = None) -> int:
    """Single-select menu using curses. Delegates to curses_radiolist."""
    from hermes_cli.curses_ui import curses_radiolist
    return curses_radiolist(question, choices, selected=default, cancel_returns=-1, description=description)



def prompt_choice(question: str, choices: list, default: int = 0, description: str | None = None) -> int:
    """Prompt for a choice from a list with arrow key navigation.

    Escape keeps the current default (skips the question).
    Ctrl+C exits the wizard.
    """
    idx = _curses_prompt_choice(question, choices, default, description=description)
    if idx >= 0:
        if idx == default:
            print_info("  跳过（保留当前值）")
            print()
            return default
        print()
        return idx

    print(color(question, Colors.YELLOW))
    for i, choice in enumerate(choices):
        marker = "●" if i == default else "○"
        if i == default:
            print(color(f"  {marker} {choice}", Colors.GREEN))
        else:
            print(f"  {marker} {choice}")

    print_info(f"  回车使用默认值 ({default + 1})  Ctrl+C 退出")

    while True:
        try:
            value = input(
                color(f"  Select [1-{len(choices)}] ({default + 1}): ", Colors.DIM)
            )
            if not value:
                return default
            idx = int(value) - 1
            if 0 <= idx < len(choices):
                return idx
            print_error(f"请输入 1 到 {len(choices)} 之间的数字")
        except ValueError:
            print_error("请输入数字")
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(1)


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """Prompt for yes/no. Ctrl+C exits, empty input returns default."""
    default_str = "Y/n" if default else "y/N"

    while True:
        try:
            value = (
                input(color(f"{question} [{default_str}]: ", Colors.YELLOW))
                .strip()
                .lower()
            )
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(1)

        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print_error("请输入 'y' 或 'n'")


def prompt_checklist(title: str, items: list, pre_selected: list = None) -> list:
    """
    Display a multi-select checklist and return the indices of selected items.

    Each item in `items` is a display string. `pre_selected` is a list of
    indices that should be checked by default. A "Continue →" option is
    appended at the end — the user toggles items with Space and confirms
    with Enter on "Continue →".

    Falls back to a numbered toggle interface when simple_term_menu is
    unavailable.

    Returns:
        List of selected indices (not including the Continue option).
    """
    if pre_selected is None:
        pre_selected = []

    from hermes_cli.curses_ui import curses_checklist

    chosen = curses_checklist(
        title,
        items,
        set(pre_selected),
        cancel_returns=set(pre_selected),
    )
    return sorted(chosen)


def _prompt_api_key(var: dict):
    """Display a nicely formatted API key input screen for a single env var."""
    tools = var.get("tools", [])
    tools_str = ", ".join(tools[:3])
    if len(tools) > 3:
        tools_str += f", +{len(tools) - 3} more"

    print()
    print(color(f"  ─── {var.get('description', var['name'])} ───", Colors.CYAN))
    print()
    if tools_str:
        print_info(f"  启用：{tools_str}")
    if var.get("url"):
        print_info(f"  获取密钥：{var['url']}")
    print()

    if var.get("password"):
        value = prompt(f"  {var.get('prompt', var['name'])}", password=True)
    else:
        value = prompt(f"  {var.get('prompt', var['name'])}")

    if value:
        save_env_value(var["name"], value)
        print_success("  ✓ 已保存")
    else:
        print_warning("  已跳过（稍后可通过 'hermes setup' 配置）")


def _print_setup_summary(config: dict, hermes_home):
    """Print the setup completion summary."""
    # Tool availability summary
    print()
    print_header("工具可用性概览")

    tool_status = []
    subscription_features = get_nous_subscription_features(config)

    # Vision — use the same runtime resolver as the actual vision tools
    try:
        from agent.auxiliary_client import get_available_vision_backends

        _vision_backends = get_available_vision_backends()
    except Exception:
        _vision_backends = []

    if _vision_backends:
        tool_status.append(("视觉（图像分析）", True, None))
    else:
        tool_status.append(("视觉（图像分析）", False, "运行 'hermes setup' 进行配置"))

    # Mixture of Agents — requires OpenRouter specifically (calls multiple models)
    if get_env_value("OPENROUTER_API_KEY"):
        tool_status.append(("多模型混合（Mixture of Agents）", True, None))
    else:
        tool_status.append(("多模型混合（Mixture of Agents）", False, "OPENROUTER_API_KEY"))

    # Web tools (Exa, Parallel, Firecrawl, or Tavily)
    if subscription_features.web.managed_by_nous:
        tool_status.append(("网页搜索与提取（Nous 订阅）", True, None))
    elif subscription_features.web.available:
        label = "网页搜索与提取"
        if subscription_features.web.current_provider:
            label = f"网页搜索与提取（{subscription_features.web.current_provider}）"
        tool_status.append((label, True, None))
    else:
        tool_status.append(("网页搜索与提取", False, "EXA_API_KEY、PARALLEL_API_KEY、FIRECRAWL_API_KEY/FIRECRAWL_API_URL、TAVILY_API_KEY 或 SEARXNG_URL"))

    # Browser tools (local Chromium, Camofox, Browserbase, Browser Use, or Firecrawl)
    browser_provider = subscription_features.browser.current_provider
    if subscription_features.browser.managed_by_nous:
        tool_status.append(("浏览器自动化（Nous Browser Use）", True, None))
    elif subscription_features.browser.available:
        label = "浏览器自动化"
        if browser_provider:
            label = f"浏览器自动化（{browser_provider}）"
        tool_status.append((label, True, None))
    else:
        missing_browser_hint = "npm install -g agent-browser，设置 CAMOFOX_URL，或配置 Browser Use 或 Browserbase"
        if browser_provider == "Browserbase":
            missing_browser_hint = (
                "npm install -g agent-browser 并设置 "
                "BROWSERBASE_API_KEY/BROWSERBASE_PROJECT_ID"
            )
        elif browser_provider == "Browser Use":
            missing_browser_hint = (
                "npm install -g agent-browser 并设置 BROWSER_USE_API_KEY"
            )
        elif browser_provider == "Camofox":
            missing_browser_hint = "CAMOFOX_URL"
        elif browser_provider == "Local browser":
            missing_browser_hint = "npm install -g agent-browser"
        tool_status.append(
            ("Browser Automation", False, missing_browser_hint)
        )

    # Image generation — FAL (direct or via Nous), or any plugin-registered
    # provider (OpenAI, etc.)
    if subscription_features.image_gen.managed_by_nous:
        tool_status.append(("图像生成（Nous 订阅）", True, None))
    elif subscription_features.image_gen.available:
        tool_status.append(("图像生成", True, None))
    else:
        # Fall back to probing plugin-registered providers so OpenAI-only
        # setups don't show as "missing FAL_KEY".
        _img_backend = None
        try:
            from agent.image_gen_registry import list_providers
            from hermes_cli.plugins import _ensure_plugins_discovered

            _ensure_plugins_discovered()
            for _p in list_providers():
                if _p.name == "fal":
                    continue
                try:
                    if _p.is_available():
                        _img_backend = _p.display_name
                        break
                except Exception:
                    continue
        except Exception:
            pass
        if _img_backend:
            tool_status.append((f"图像生成（{_img_backend}）", True, None))
        else:
            tool_status.append(("图像生成", False, "FAL_KEY 或 OPENAI_API_KEY"))

    # Video generation — opt-in via `hermes tools` → Video Generation.
    # Only show the row when a plugin reports available so we don't badger
    # users who don't care about video gen with a "missing" status line.
    try:
        from agent.video_gen_registry import list_providers as _list_video_providers
        from hermes_cli.plugins import _ensure_plugins_discovered as _ensure_plugins
        _ensure_plugins()
        _video_backend = None
        for _vp in _list_video_providers():
            try:
                if _vp.is_available():
                    _video_backend = _vp.display_name
                    break
            except Exception:
                continue
    except Exception:
        _video_backend = None
    if _video_backend:
        tool_status.append((f"视频生成（{_video_backend}）", True, None))

    # TTS — show configured provider
    tts_provider = cfg_get(config, "tts", "provider", default="edge")
    if subscription_features.tts.managed_by_nous:
        tool_status.append(("语音合成（通过 Nous 订阅的 OpenAI）", True, None))
    elif tts_provider == "elevenlabs" and get_env_value("ELEVENLABS_API_KEY"):
        tool_status.append(("语音合成（ElevenLabs）", True, None))
    elif tts_provider == "openai" and (
        get_env_value("VOICE_TOOLS_OPENAI_KEY") or get_env_value("OPENAI_API_KEY")
    ):
        tool_status.append(("语音合成（OpenAI）", True, None))
    elif tts_provider == "minimax" and get_env_value("MINIMAX_API_KEY"):
        tool_status.append(("语音合成（MiniMax）", True, None))
    elif tts_provider == "mistral" and get_env_value("MISTRAL_API_KEY"):
        tool_status.append(("语音合成（Mistral Voxtral）", True, None))
    elif tts_provider == "gemini" and (get_env_value("GEMINI_API_KEY") or get_env_value("GOOGLE_API_KEY")):
        tool_status.append(("语音合成（Google Gemini）", True, None))
    elif tts_provider == "neutts":
        try:
            neutts_ok = importlib.util.find_spec("neutts") is not None
        except Exception:
            neutts_ok = False
        if neutts_ok:
            tool_status.append(("语音合成（NeuTTS 本地）", True, None))
        else:
            tool_status.append(("语音合成（NeuTTS — 未安装）", False, "运行 'hermes setup tts'"))
    elif tts_provider == "kittentts":
        try:
            import importlib.util
            kittentts_ok = importlib.util.find_spec("kittentts") is not None
        except Exception:
            kittentts_ok = False
        if kittentts_ok:
            tool_status.append(("语音合成（KittenTTS 本地）", True, None))
        else:
            tool_status.append(("语音合成（KittenTTS — 未安装）", False, "运行 'hermes setup tts'"))
    else:
        tool_status.append(("语音合成（Edge TTS）", True, None))

    if subscription_features.modal.managed_by_nous:
        tool_status.append(("Modal 执行（Nous 订阅）", True, None))
    elif cfg_get(config, "terminal", "backend") == "modal":
        if subscription_features.modal.direct_override:
            tool_status.append(("Modal 执行（直接 Modal）", True, None))
        else:
            tool_status.append(("Modal 执行", False, "运行 'hermes setup terminal'"))
    elif managed_nous_tools_enabled() and subscription_features.nous_auth_present:
        tool_status.append(("Modal 执行（可选，通过 Nous 订阅）", True, None))

    # Home Assistant
    if get_env_value("HASS_TOKEN"):
        tool_status.append(("智能家居（Home Assistant）", True, None))

    # Spotify (OAuth via hermes auth spotify — check auth.json, not env vars)
    try:
        from hermes_cli.auth import get_provider_auth_state
        _spotify_state = get_provider_auth_state("spotify") or {}
        if _spotify_state.get("access_token") or _spotify_state.get("refresh_token"):
            tool_status.append(("Spotify（PKCE OAuth）", True, None))
    except Exception:
        pass

    # Skills Hub
    if get_env_value("GITHUB_TOKEN"):
        tool_status.append(("技能中心（GitHub）", True, None))
    else:
        tool_status.append(("技能中心（GitHub）", False, "GITHUB_TOKEN"))

    # Terminal (always available if system deps met)
    tool_status.append(("终端/命令", True, None))

    # Task planning (always available, in-memory)
    tool_status.append(("任务规划（待办事项）", True, None))

    # Skills (always available -- bundled skills + user-created skills)
    tool_status.append(("Skills (view, create, edit)", True, None))

    # Print status
    available_count = sum(1 for _, avail, _ in tool_status if avail)
    total_count = len(tool_status)

    print_info(f"可用：{available_count}/{total_count} 个工具类别")
    print()

    for name, available, missing_var in tool_status:
        if available:
            print(f"   {color('✓', Colors.GREEN)} {name}")
        else:
            print(
                f"   {color('✗', Colors.RED)} {name} {color(f'(missing {missing_var})', Colors.DIM)}"
            )

    print()

    disabled_tools = [(name, var) for name, avail, var in tool_status if not avail]
    if disabled_tools:
        print_warning(
            "部分工具尚未启用。运行 'hermes setup tools' 进行配置，"
        )
        from hermes_constants import display_hermes_home as _dhh
        print_warning(f"或直接编辑 {_dhh()}/.env 添加缺失的 API 密钥。")
        print()

    # Done banner
    print()
    print(
        color(
            "┌─────────────────────────────────────────────────────────┐", Colors.GREEN
        )
    )
    print(
        color(
            "│              ✓ 安装完成！                              │", Colors.GREEN
        )
    )
    print(
        color(
            "└─────────────────────────────────────────────────────────┘", Colors.GREEN
        )
    )
    print()

    # Show file locations prominently
    from hermes_constants import display_hermes_home as _dhh
    print(color(f"📁 所有文件都在 {_dhh()}/ 中：", Colors.CYAN, Colors.BOLD))
    print()
    print(f"   {color('设置文件：', Colors.YELLOW)}  {get_config_path()}")
    print(f"   {color('API 密钥：', Colors.YELLOW)}  {get_env_path()}")
    print(
        f"   {color('Data:', Colors.YELLOW)}      {hermes_home}/cron/, sessions/, logs/"
    )
    print()

    print(color("─" * 60, Colors.DIM))
    print()
    print(color("📝 编辑配置：", Colors.CYAN, Colors.BOLD))
    print()
    print(f"   {color('hermes setup', Colors.GREEN)}          重新运行完整向导")
    print(f"   {color('hermes setup model', Colors.GREEN)}    更改模型/提供商")
    print(f"   {color('hermes setup terminal', Colors.GREEN)} 更改终端后端")
    print(f"   {color('hermes setup gateway', Colors.GREEN)}  配置消息平台")
    print(f"   {color('hermes setup tools', Colors.GREEN)}    配置工具提供商")
    print()
    print(f"   {color('hermes config', Colors.GREEN)}         查看当前设置")
    print(
        f"   {color('hermes config edit', Colors.GREEN)}    在编辑器中打开配置文件"
    )
    print(f"   {color('hermes config set <key> <value>', Colors.GREEN)}")
    print("                          设置特定值")
    print()
    print("   或直接编辑文件：")
    print(f"   {color(f'nano {get_config_path()}', Colors.DIM)}")
    print(f"   {color(f'nano {get_env_path()}', Colors.DIM)}")
    print()

    print(color("─" * 60, Colors.DIM))
    print()
    print(color("🚀 准备就绪！", Colors.CYAN, Colors.BOLD))
    print()
    print(f"   {color('hermes', Colors.GREEN)}              开始聊天")
    print(f"   {color('hermes gateway', Colors.GREEN)}      启动消息网关")
    print(f"   {color('hermes doctor', Colors.GREEN)}       检查问题")
    print()


def _prompt_container_resources(config: dict):
    """Prompt for container resource settings (Docker, Singularity, Modal, Daytona)."""
    terminal = config.setdefault("terminal", {})

    print()
    print_info("容器资源设置：")

    # Persistence
    current_persist = terminal.get("container_persistent", True)
    persist_label = "是" if current_persist else "否"
    print_info("  持久化文件系统可在会话间保留文件。")
    print_info("  设置为 '否' 则每次重置的临时沙箱。")
    persist_str = prompt(
        "  会话间持久化文件系统？（是/否）", persist_label
    )
    terminal["container_persistent"] = persist_str.lower() in {"yes", "true", "y", "1"}

    # CPU
    current_cpu = terminal.get("container_cpu", 1)
    cpu_str = prompt("  CPU 核心数", str(current_cpu))
    try:
        terminal["container_cpu"] = float(cpu_str)
    except ValueError:
        pass

    # Memory
    current_mem = terminal.get("container_memory", 5120)
    mem_str = prompt("  内存（MB，5120 = 5GB）", str(current_mem))
    try:
        terminal["container_memory"] = int(mem_str)
    except ValueError:
        pass

    # Disk
    current_disk = terminal.get("container_disk", 51200)
    disk_str = prompt("  磁盘（MB，51200 = 50GB）", str(current_disk))
    try:
        terminal["container_disk"] = int(disk_str)
    except ValueError:
        pass


def _prompt_vercel_sandbox_settings(config: dict):
    """Prompt for Vercel Sandbox settings without exposing unsupported disk sizing."""
    terminal = config.setdefault("terminal", {})

    print()
    print_info("Vercel Sandbox 设置：")
    print_info("  文件系统持久化使用 Vercel 快照。")
    print_info("  快照仅恢复文件；沙箱重建后运行中的进程不会继续。")

    from tools.terminal_tool import _SUPPORTED_VERCEL_RUNTIMES

    current_runtime = terminal.get("vercel_runtime") or "node24"
    supported_label = ", ".join(_SUPPORTED_VERCEL_RUNTIMES)
    runtime = prompt(f"  Runtime ({supported_label})", current_runtime).strip() or current_runtime
    if runtime not in _SUPPORTED_VERCEL_RUNTIMES:
        print_warning(f"不支持的 Vercel 运行环境 '{runtime}'，保留 {current_runtime}。")
        runtime = current_runtime if current_runtime in _SUPPORTED_VERCEL_RUNTIMES else "node24"
    terminal["vercel_runtime"] = runtime
    save_env_value("TERMINAL_VERCEL_RUNTIME", runtime)

    current_persist = terminal.get("container_persistent", True)
    persist_label = "是" if current_persist else "否"
    terminal["container_persistent"] = prompt(
        "  使用快照持久化文件系统？（是/否）", persist_label
    ).lower() in {"yes", "true", "y", "1", "是"}

    current_cpu = terminal.get("container_cpu", 1)
    cpu_str = prompt("  CPU 核心数", str(current_cpu))
    try:
        terminal["container_cpu"] = float(cpu_str)
    except ValueError:
        pass

    current_mem = terminal.get("container_memory", 5120)
    mem_str = prompt("  内存（MB，5120 = 5GB）", str(current_mem))
    try:
        terminal["container_memory"] = int(mem_str)
    except ValueError:
        pass

    if terminal.get("container_disk", 51200) not in {0, 51200}:
        print_warning("Vercel Sandbox 不支持自定义磁盘大小；container_disk 已重置为 51200。")
    terminal["container_disk"] = 51200

    print()
    print_info("Vercel 认证：")
    print_info("  使用长期有效的 Vercel 访问令牌以及项目/团队 ID。")
    linked_project = _read_nearest_vercel_project()
    if linked_project:
        print_info("  在最近的 .vercel/project.json 中找到了默认值。")

    remove_env_value("VERCEL_OIDC_TOKEN")
    token = prompt("    Vercel 访问令牌", get_env_value("VERCEL_TOKEN") or "", password=True)
    project = prompt(
        "    Vercel 项目 ID",
        get_env_value("VERCEL_PROJECT_ID") or linked_project.get("projectId", ""),
    )
    team = prompt(
        "    Vercel 团队 ID",
        get_env_value("VERCEL_TEAM_ID") or linked_project.get("orgId", ""),
    )
    if token:
        save_env_value("VERCEL_TOKEN", token)
    if project:
        save_env_value("VERCEL_PROJECT_ID", project)
    if team:
        save_env_value("VERCEL_TEAM_ID", team)


def _read_nearest_vercel_project(start: Path | None = None) -> dict[str, str]:
    """Read project/team defaults from the nearest Vercel link file."""
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for directory in (current, *current.parents):
        project_file = directory / ".vercel" / "project.json"
        if not project_file.exists():
            continue
        try:
            data = json.loads(project_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {
            key: value
            for key, value in {
                "projectId": data.get("projectId"),
                "orgId": data.get("orgId"),
            }.items()
            if isinstance(value, str) and value.strip()
        }
    return {}


# Tool categories and provider config are now in tools_config.py (shared
# between `hermes tools` and `hermes setup tools`).


# =============================================================================
# Section 1: Model & Provider Configuration
# =============================================================================



def setup_model_provider(config: dict, *, quick: bool = False):
    """Configure the inference provider and default model.

    Delegates to ``cmd_model()`` (the same flow used by ``hermes model``)
    for provider selection, credential prompting, and model picking.
    This ensures a single code path for all provider setup — any new
    provider added to ``hermes model`` is automatically available here.

    When *quick* is True, skips credential rotation, vision, and TTS
    configuration — used by the streamlined first-time quick setup.
    """
    from hermes_cli.config import load_config, save_config

    print_header("推理提供商")
    print_info("选择如何连接到你的主要聊天模型。")
    print_info(f"   指南：{_DOCS_BASE}/integrations/providers")
    print()

    # Delegate to the shared hermes model flow — handles provider picker,
    # credential prompting, model selection, and config persistence.
    from hermes_cli.main import select_provider_and_model
    try:
        select_provider_and_model()
    except (SystemExit, KeyboardInterrupt):
        print()
        print_info("提供商设置已跳过。")
    except Exception as exc:
        logger.debug("select_provider_and_model error during setup: %s", exc)
        print_warning(f"提供商设置遇到错误：{exc}")
        print_info("稍后可重试：hermes model")

    # Re-sync the wizard's config dict from what cmd_model saved to disk.
    # This is critical: cmd_model writes to disk via its own load/save cycle,
    # and the wizard's final save_config(config) must not overwrite those
    # changes with stale values (#4172). Refresh the dict in place so callers
    # that keep the same object see every section the shared model picker may
    # have changed (model, custom_providers, auxiliary, provider metadata, etc.).
    _refreshed = load_config()
    config.clear()
    config.update(_refreshed)

    # Derive the selected provider for downstream steps (vision setup).
    selected_provider = None
    _m = config.get("model")
    if isinstance(_m, dict):
        selected_provider = _m.get("provider")

    # ── Same-provider fallback & rotation setup (full setup only) ──
    if not quick and _supports_same_provider_pool_setup(selected_provider):
        try:
            from types import SimpleNamespace
            from agent.credential_pool import load_pool
            from hermes_cli.auth_commands import auth_add_command

            pool = load_pool(selected_provider)
            entries = pool.entries()
            entry_count = len(entries)
            manual_count = sum(1 for entry in entries if str(getattr(entry, "source", "")).startswith("manual"))
            auto_count = entry_count - manual_count
            print()
            print_header("同提供商备用与轮换")
            print_info(
                "Hermes 可以为同一提供商保存多个凭据，并在凭据用尽或限流时轮换使用。"
            )
            print_info(
                "这样可以保持你的主要提供商，同时减少配额问题带来的中断。"
            )
            
            print()
            if auto_count > 0:
                print_info(
                    f"{selected_provider} 当前的池化凭据：{entry_count} "
                    f"（{manual_count} 个手动，{auto_count} 个从环境/共享认证自动检测）"
                )
            else:
                print_info(f"{selected_provider} 当前的池化凭据：{entry_count}")

            while prompt_yes_no("是否为同提供商备用添加另一个凭据？", False):
                auth_add_command(
                    SimpleNamespace(
                        provider=selected_provider,
                        auth_type="",
                        label=None,
                        api_key=None,
                        portal_url=None,
                        inference_url=None,
                        client_id=None,
                        scope=None,
                        no_browser=False,
                        timeout=15.0,
                        insecure=False,
                        ca_bundle=None,
                        min_key_ttl_seconds=5 * 60,
                    )
                )
                pool = load_pool(selected_provider)
                entry_count = len(pool.entries())
                print_info(f"提供商池现有 {entry_count} 个凭据。")

            if entry_count > 1:
                strategy_labels = [
                    "优先使用——持续使用第一个健康凭据直到用尽",
                    "轮询——每次轮换到下一个健康凭据",
                    "随机——每次随机选择一个健康凭据",
                ]
                current_strategy = _get_credential_pool_strategies(config).get(selected_provider, "fill_first")
                default_strategy_idx = {
                    "fill_first": 0,
                    "round_robin": 1,
                    "random": 2,
                }.get(current_strategy, 0)
                strategy_idx = prompt_choice(
                    "选择同提供商轮换策略：",
                    strategy_labels,
                    default_strategy_idx,
                )
                strategy_value = ["fill_first", "round_robin", "random"][strategy_idx]
                _set_credential_pool_strategy(config, selected_provider, strategy_value)
                print_success(f"已保存 {selected_provider} 轮换策略：{strategy_value}")
        except Exception as exc:
            logger.debug("Could not configure same-provider fallback in setup: %s", exc)

    # ── Vision & Image Analysis Setup (full setup only) ──
    if quick:
        _vision_needs_setup = False
    else:
        try:
            from agent.auxiliary_client import get_available_vision_backends
            _vision_backends = set(get_available_vision_backends())
        except Exception:
            _vision_backends = set()

        _vision_needs_setup = not bool(_vision_backends)

        if selected_provider in _vision_backends:
            _vision_needs_setup = False

    if _vision_needs_setup:
        _prov_names = {
            "nous-api": "Nous Portal API key",
            "copilot": "GitHub Copilot",
            "copilot-acp": "GitHub Copilot ACP",
            "zai": "Z.AI / GLM",
            "kimi-coding": "Kimi / Moonshot",
            "kimi-coding-cn": "Kimi / Moonshot (China)",
            "stepfun": "StepFun Step Plan",
            "minimax": "MiniMax",
            "minimax-cn": "MiniMax CN",
            "anthropic": "Anthropic",
            "ai-gateway": "Vercel AI Gateway",
            "custom": "your custom endpoint",
        }
        _prov_display = _prov_names.get(selected_provider, selected_provider or "your provider")

        print()
        print_header("视觉与图像分析（可选）")
        print_info(f"视觉使用独立的多模态后端。{_prov_display}")
        print_info("目前未提供 Hermes 可自动用于视觉的后端，")
        print()

        _vision_choices = [
            "OpenRouter — 使用 Gemini（免费套餐 openrouter.ai/keys）",
            "OpenAI 兼容端点 — 基础 URL、API 密钥和视觉模型",
            "暂时跳过",
        ]
        _vision_idx = prompt_choice("配置视觉：", _vision_choices, 2)

        if _vision_idx == 0:  # OpenRouter
            _or_key = prompt("  OpenRouter API 密钥", password=True).strip()
            if _or_key:
                save_env_value("OPENROUTER_API_KEY", _or_key)
                print_success("OpenRouter 密钥已保存 — 视觉将使用 Gemini")
            else:
                print_info("已跳过 — 视觉将不可用")
        elif _vision_idx == 1:  # OpenAI-compatible endpoint
            _base_url = prompt("  Base URL (blank for OpenAI)").strip() or "https://api.openai.com/v1"
            _api_key_label = "  API 密钥"
            _is_native_openai = base_url_hostname(_base_url) == "api.openai.com"
            if _is_native_openai:
                _api_key_label = "  OpenAI API 密钥"
            _oai_key = prompt(_api_key_label, password=True).strip()
            if _oai_key:
                save_env_value("OPENAI_API_KEY", _oai_key)
                # Save vision base URL to config (not .env — only secrets go there)
                _vaux = config.setdefault("auxiliary", {}).setdefault("vision", {})
                _vaux["base_url"] = _base_url
                if _is_native_openai:
                    _oai_vision_models = ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"]
                    _vm_choices = _oai_vision_models + ["使用默认（gpt-4o-mini）"]
                    _vm_idx = prompt_choice("选择视觉模型：", _vm_choices, 0)
                    _selected_vision_model = (
                        _oai_vision_models[_vm_idx]
                        if _vm_idx < len(_oai_vision_models)
                        else "gpt-4o-mini"
                    )
                else:
                    _selected_vision_model = prompt("  视觉模型（留空则使用主要/自定义默认值）").strip()
                if _selected_vision_model:
                    save_env_value("AUXILIARY_VISION_MODEL", _selected_vision_model)
                print_success(
                    f"视觉已配置：{_base_url}"
                    + (f"（{_selected_vision_model}）" if _selected_vision_model else "")
                )
            else:
                print_info("已跳过 — 视觉将不可用")
        else:
            print_info("已跳过 — 稍后可通过 'hermes setup' 或配置 AUXILIARY_VISION_* 设置添加")


    # Tool Gateway prompt is already shown by _model_flow_nous() above.
    save_config(config)

    if not quick and selected_provider != "nous":
        _setup_tts_provider(config)


# =============================================================================
# Section 1b: TTS Provider Configuration
# =============================================================================


def _check_espeak_ng() -> bool:
    """Check if espeak-ng is installed."""
    return shutil.which("espeak-ng") is not None or shutil.which("espeak") is not None


def _install_neutts_deps() -> bool:
    """Install NeuTTS dependencies with user approval. Returns True on success."""
    import subprocess
    import sys

    # Check espeak-ng
    if not _check_espeak_ng():
        print()
        print_warning("NeuTTS 需要 espeak-ng 进行音素化。")
        if sys.platform == "darwin":
            print_info("安装命令：brew install espeak-ng")
        elif sys.platform == "win32":
            print_info("安装命令：choco install espeak-ng")
        else:
            print_info("安装命令：sudo apt install espeak-ng")
        print()
        if prompt_yes_no("立即安装 espeak-ng？", True):
            try:
                if sys.platform == "darwin":
                    subprocess.run(["brew", "install", "espeak-ng"], check=True)
                elif sys.platform == "win32":
                    subprocess.run(["choco", "install", "espeak-ng", "-y"], check=True)
                else:
                    subprocess.run(["sudo", "apt", "install", "-y", "espeak-ng"], check=True)
                print_success("espeak-ng 已安装")
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print_warning(f"无法自动安装 espeak-ng：{e}")
                print_info("请手动安装后重新运行安装向导。")
                return False
        else:
            print_warning("NeuTTS 需要 espeak-ng。请先手动安装后再使用 NeuTTS。")

    # Install neutts Python package
    print()
    print_info("正在安装 neutts Python 包...")
    print_info("首次使用时会下载 TTS 模型（约 300MB）。")
    print()
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "neutts[all]", "--quiet"],
            check=True, timeout=300,
        )
        print_success("neutts 安装成功")
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print_error(f"neutts 安装失败：{e}")
        print_info("手动安装：python -m pip install -U neutts[all]")
        return False


def _install_kittentts_deps() -> bool:
    """Install KittenTTS dependencies with user approval. Returns True on success."""
    import subprocess
    import sys

    wheel_url = (
        "https://github.com/KittenML/KittenTTS/releases/download/"
        "0.8.1/kittentts-0.8.1-py3-none-any.whl"
    )
    print()
    print_info("正在安装 kittentts Python 包（首次使用下载约 25-80MB 模型）...")
    print()
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", wheel_url, "soundfile", "--quiet"],
            check=True, timeout=300,
        )
        print_success("kittentts 安装成功")
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print_error(f"kittentts 安装失败：{e}")
        print_info(f"手动安装：python -m pip install -U '{wheel_url}' soundfile")
        return False


def _xai_oauth_logged_in_for_setup() -> bool:
    """True iff xAI Grok OAuth credentials are already stored locally.

    Lets TTS / STT setup skip the API-key prompt for users who logged in
    through ``hermes model`` -> xAI Grok OAuth (SuperGrok Subscription).
    """
    try:
        from hermes_cli.auth import get_xai_oauth_auth_status

        return bool(get_xai_oauth_auth_status().get("logged_in"))
    except Exception:
        return False


def _run_xai_oauth_login_from_setup() -> bool:
    """Run the xAI Grok OAuth loopback login from inside the setup wizard.

    Returns True on success, False on any failure (the caller falls back
    to whatever the user picked next, e.g. Edge TTS).
    """
    try:
        from hermes_cli.auth import (
            DEFAULT_XAI_OAUTH_BASE_URL,
            _is_remote_session,
            _save_xai_oauth_tokens,
            _update_config_for_provider,
            _xai_oauth_loopback_login,
        )
    except Exception as exc:
        print_warning(f"xAI Grok OAuth 辅助函数不可用：{exc}")
        return False

    open_browser = not _is_remote_session()
    print()
    print_info("正在登录 xAI Grok OAuth（SuperGrok 订阅）...")
    try:
        creds = _xai_oauth_loopback_login(open_browser=open_browser)
        _save_xai_oauth_tokens(
            creds["tokens"],
            discovery=creds.get("discovery"),
            redirect_uri=creds.get("redirect_uri", ""),
            last_refresh=creds.get("last_refresh"),
        )
        _update_config_for_provider(
            "xai-oauth", creds.get("base_url", DEFAULT_XAI_OAUTH_BASE_URL)
        )
        return True
    except Exception as exc:
        print_warning(f"xAI Grok OAuth 登录失败：{exc}")
        return False


def _setup_tts_provider(config: dict):
    """Interactive TTS provider selection with install flow for NeuTTS."""
    tts_config = config.get("tts", {})
    current_provider = tts_config.get("provider", "edge")
    subscription_features = get_nous_subscription_features(config)

    provider_labels = {
        "edge": "Edge TTS",
        "elevenlabs": "ElevenLabs",
        "openai": "OpenAI TTS",
        "xai": "xAI TTS",
        "minimax": "MiniMax TTS",
        "mistral": "Mistral Voxtral TTS",
        "gemini": "Google Gemini TTS",
        "neutts": "NeuTTS",
        "kittentts": "KittenTTS",
    }
    current_label = provider_labels.get(current_provider, current_provider)

    print()
    print_header("语音合成提供商（可选）")
    print_info(f"当前：{current_label}")
    print()

    choices = []
    providers = []
    if managed_nous_tools_enabled() and subscription_features.nous_auth_present:
        choices.append("Nous 订阅（托管的 OpenAI TTS，计入订阅费用）")
        providers.append("nous-openai")
    choices.extend(
        [
            "Edge TTS（免费，云端，无需配置）",
            "ElevenLabs（高质量，需要 API 密钥）",
            "OpenAI TTS（高品质，需要 API 密钥）",
            "xAI TTS（Grok 语音 — OAuth 登录或 API 密钥）",
            "MiniMax TTS（高质量，支持语音克隆，需要 API 密钥）",
            "Mistral Voxtral TTS（多语言，原生 Opus，需要 API 密钥）",
            "Google Gemini TTS（30 种预制语音，提示词可控，需要 API 密钥）",
            "NeuTTS（本地设备端，免费，下载约 300MB 模型）",
            "KittenTTS（本地设备端，免费，轻量约 25-80MB ONNX）",
        ]
    )
    providers.extend(["edge", "elevenlabs", "openai", "xai", "minimax", "mistral", "gemini", "neutts", "kittentts"])
    choices.append(f"保留当前（{current_label}）")
    keep_current_idx = len(choices) - 1
    idx = prompt_choice("选择 TTS 提供商：", choices, keep_current_idx)

    if idx == keep_current_idx:
        return

    selected = providers[idx]
    selected_via_nous = selected == "nous-openai"
    if selected == "nous-openai":
        selected = "openai"
        print_info("OpenAI TTS 将使用托管的 Nous 网关，费用计入你的订阅。")
        if get_env_value("VOICE_TOOLS_OPENAI_KEY") or get_env_value("OPENAI_API_KEY"):
            print_warning(
                "直接 OpenAI 凭据仍处于配置状态，在从 ~/.hermes/.env 中移除前可能优先使用。"
            )

    if selected == "neutts":
        # Check if already installed
        try:
            already_installed = importlib.util.find_spec("neutts") is not None
        except Exception:
            already_installed = False

        if already_installed:
            print_success("NeuTTS 已安装")
        else:
            print()
            print_info("NeuTTS 需要：")
            print_info("  • Python 包：neutts（安装约 50MB + 首次使用下载约 300MB 模型）")
            print_info("  • 系统包：espeak-ng（音素化器）")
            print()
            if prompt_yes_no("立即安装 NeuTTS 依赖？", True):
                if not _install_neutts_deps():
                    print_warning("NeuTTS 安装未完成。回退到 Edge TTS。")
                    selected = "edge"
            else:
                print_info("跳过安装。手动安装后设置 tts.provider 为 'neutts'。")
                selected = "edge"

    elif selected == "elevenlabs":
        existing = get_env_value("ELEVENLABS_API_KEY")
        if not existing:
            print()
            api_key = prompt("ElevenLabs API 密钥", password=True)
            if api_key:
                save_env_value("ELEVENLABS_API_KEY", api_key)
                print_success("ElevenLabs API 密钥已保存")
            else:
                print_warning("未提供 API 密钥。回退到 Edge TTS。")
                selected = "edge"

    elif selected == "openai" and not selected_via_nous:
        existing = get_env_value("VOICE_TOOLS_OPENAI_KEY") or get_env_value("OPENAI_API_KEY")
        if not existing:
            print()
            api_key = prompt("OpenAI TTS API 密钥", password=True)
            if api_key:
                save_env_value("VOICE_TOOLS_OPENAI_KEY", api_key)
                print_success("OpenAI TTS API 密钥已保存")
            else:
                print_warning("未提供 API 密钥。回退到 Edge TTS。")
                selected = "edge"

    elif selected == "xai":
        # Resolution order: existing OAuth tokens (free for SuperGrok subscribers
        # via the Hermes auth store) > existing XAI_API_KEY > prompt the user.
        # When neither is configured, offer both options instead of forcing the
        # API-key path — xAI TTS works fine with OAuth bearer tokens too.
        oauth_logged_in = _xai_oauth_logged_in_for_setup()
        existing_api_key = get_env_value("XAI_API_KEY")

        if oauth_logged_in:
            print_success(
                "xAI TTS 将使用你的 xAI Grok OAuth（SuperGrok 订阅）"
                "凭据"
            )
        elif existing_api_key:
            print_success("xAI TTS 将使用你现有的 XAI_API_KEY")
        else:
            print()
            choice_idx = prompt_choice(
                "xAI TTS 如何认证？",
                choices=[
                    "使用 xAI Grok OAuth（SuperGrok 订阅）登录 — 浏览器登录",
                    "粘贴 xAI API 密钥（console.x.ai）",
                    "跳过 → 回退到 Edge TTS",
                ],
                default=0,
            )
            if choice_idx == 0:
                if _run_xai_oauth_login_from_setup():
                    print_success(
                        "已登录 — xAI TTS 将使用这些 OAuth 凭据"
                    )
                else:
                    print_warning(
                        "xAI Grok OAuth 登录未完成。回退到 Edge TTS。"
                    )
                    selected = "edge"
            elif choice_idx == 1:
                api_key = prompt("xAI API key for TTS", password=True)
                if api_key:
                    save_env_value("XAI_API_KEY", api_key)
                    print_success("xAI TTS API 密钥已保存")
                else:
                    from hermes_constants import display_hermes_home as _dhh
                    print_warning(
                        "未提供 xAI TTS API 密钥。通过 hermes setup model 或 "
                        f"{_dhh()}/.env 配置 XAI_API_KEY 以使用 xAI TTS。"
                        "回退到 Edge TTS。"
                    )
                    selected = "edge"
            else:
                print_warning("xAI TTS 已跳过。回退到 Edge TTS。")
                selected = "edge"

        if selected == "xai":
            print()
            voice_id = prompt("xAI voice_id（回车使用 'eve'，或粘贴自定义语音 ID）")
            if voice_id and voice_id.strip():
                config.setdefault("tts", {}).setdefault("xai", {})["voice_id"] = voice_id.strip()
                print_success(f"xAI voice_id 已设置为：{voice_id.strip()}")


    elif selected == "minimax":
        existing = get_env_value("MINIMAX_API_KEY")
        if not existing:
            print()
            api_key = prompt("MiniMax TTS API 密钥", password=True)
            if api_key:
                save_env_value("MINIMAX_API_KEY", api_key)
                print_success("MiniMax TTS API 密钥已保存")
            else:
                print_warning("未提供 API 密钥。回退到 Edge TTS。")
                selected = "edge"

    elif selected == "mistral":
        existing = get_env_value("MISTRAL_API_KEY")
        if not existing:
            print()
            api_key = prompt("Mistral TTS API 密钥", password=True)
            if api_key:
                save_env_value("MISTRAL_API_KEY", api_key)
                print_success("Mistral TTS API 密钥已保存")
            else:
                print_warning("未提供 API 密钥。回退到 Edge TTS。")
                selected = "edge"

    elif selected == "gemini":
        existing = get_env_value("GEMINI_API_KEY") or get_env_value("GOOGLE_API_KEY")
        if not existing:
            print()
            print_info("在 https://aistudio.google.com/app/apikey 获取免费 API 密钥")
            api_key = prompt("Gemini TTS API 密钥", password=True)
            if api_key:
                save_env_value("GEMINI_API_KEY", api_key)
                print_success("Gemini TTS API 密钥已保存")
            else:
                print_warning("未提供 API 密钥。回退到 Edge TTS。")
                selected = "edge"

    elif selected == "kittentts":
        # Check if already installed
        try:
            import importlib.util
            already_installed = importlib.util.find_spec("kittentts") is not None
        except Exception:
            already_installed = False

        if already_installed:
            print_success("KittenTTS 已安装")
        else:
            print()
            print_info("KittenTTS 很轻量（约 25-80MB，仅 CPU，无需 API 密钥）。")
            print_info("语音：Jasper、Bella、Luna、Bruno、Rosie、Hugo、Kiki、Leo")
            print()
            if prompt_yes_no("立即安装 KittenTTS？", True):
                if not _install_kittentts_deps():
                    print_warning("KittenTTS 安装未完成。回退到 Edge TTS。")
                    selected = "edge"
            else:
                print_info("跳过安装。手动安装后设置 tts.provider 为 'kittentts'。")
                selected = "edge"

    # Save the selection
    if "tts" not in config:
        config["tts"] = {}
    config["tts"]["provider"] = selected
    save_config(config)
    print_success(f"TTS 提供商已设置为：{provider_labels.get(selected, selected)}")


def setup_tts(config: dict):
    """Standalone TTS setup (for 'hermes setup tts')."""
    _setup_tts_provider(config)


# =============================================================================
# Section 2: Terminal Backend Configuration
# =============================================================================


def setup_terminal_backend(config: dict):
    """Configure the terminal execution backend."""
    import platform as _platform
    print_header("终端后端")
    print_info("选择 Hermes 运行 Shell 命令和代码的位置。")
    print_info("这影响工具执行、文件访问和隔离性。")
    print_info(f"   指南：{_DOCS_BASE}/developer-guide/environments")
    print()

    current_backend = cfg_get(config, "terminal", "backend", default="local")
    is_linux = _platform.system() == "Linux"

    # Build backend choices with descriptions
    terminal_choices = [
        "本地 —— 在本机直接运行（默认）",
        "Docker —— 隔离容器，可配置资源",
        "Modal —— 无服务器云端沙箱",
        "SSH —— 在远程机器上运行",
        "Daytona —— 持久化云端开发环境",
        "Vercel Sandbox —— 云端微虚拟机，支持快照文件系统持久化",
    ]
    idx_to_backend = {0: "local", 1: "docker", 2: "modal", 3: "ssh", 4: "daytona", 5: "vercel_sandbox"}
    backend_to_idx = {"local": 0, "docker": 1, "modal": 2, "ssh": 3, "daytona": 4, "vercel_sandbox": 5}

    next_idx = 6
    if is_linux:
        terminal_choices.append("Singularity/Apptainer —— 适用于 HPC 的容器")
        idx_to_backend[next_idx] = "singularity"
        backend_to_idx["singularity"] = next_idx
        next_idx += 1

    # Add keep current option
    keep_current_idx = next_idx
    terminal_choices.append(f"保留当前设置（{current_backend}）")
    idx_to_backend[keep_current_idx] = current_backend

    terminal_idx = prompt_choice(
        "选择终端后端：", terminal_choices, keep_current_idx
    )

    selected_backend = idx_to_backend.get(terminal_idx)

    if terminal_idx == keep_current_idx:
        print_info(f"保留当前后端：{current_backend}")
        return

    config.setdefault("terminal", {})["backend"] = selected_backend

    if selected_backend == "local":
        print_success("终端后端：本地")
        print_info("命令直接在本机运行。")

        # Gateway/cron working directory
        print()
        print_info("网关工作目录：")
        print_info("  用于 Telegram/Discord/cron 会话。")
        print_info("  CLI/TUI 始终使用启动目录。")
        current_cwd = cfg_get(config, "terminal", "cwd", default="")
        cwd = prompt("  网关工作目录", current_cwd or str(Path.home()))
        if cwd:
            config["terminal"]["cwd"] = cwd

        # Sudo support
        print()
        existing_sudo = get_env_value("SUDO_PASSWORD")
        if existing_sudo:
            print_info("Sudo 密码：已配置")
        elif prompt_yes_no(
            "启用 sudo 支持？（存储密码用于 apt install 等操作）", False
        ):
            sudo_pass = prompt("  Sudo 密码", password=True)
            if sudo_pass:
                save_env_value("SUDO_PASSWORD", sudo_pass)
                print_success("Sudo 密码已保存")

    elif selected_backend == "docker":
        print_success("终端后端：Docker")

        # Check if Docker is available
        docker_bin = shutil.which("docker")
        if not docker_bin:
            print_warning("未在 PATH 中找到 Docker！")
            print_info("安装 Docker：https://docs.docker.com/get-docker/")
        else:
            print_info(f"已找到 Docker：{docker_bin}")

        # Docker image
        current_image = cfg_get(config, "terminal", "docker_image", default="nikolaik/python-nodejs:python3.11-nodejs20")
        image = prompt("  Docker 镜像", current_image)
        config["terminal"]["docker_image"] = image
        save_env_value("TERMINAL_DOCKER_IMAGE", image)

        _prompt_container_resources(config)

    elif selected_backend == "singularity":
        print_success("终端后端：Singularity/Apptainer")

        # Check if singularity/apptainer is available
        sing_bin = shutil.which("apptainer") or shutil.which("singularity")
        if not sing_bin:
            print_warning("未在 PATH 中找到 Singularity/Apptainer！")
            print_info(
                "安装：https://apptainer.org/docs/admin/main/installation.html"
            )
        else:
            print_info(f"已找到：{sing_bin}")

        current_image = cfg_get(config, "terminal", "singularity_image", default="docker://nikolaik/python-nodejs:python3.11-nodejs20")
        image = prompt("  容器镜像", current_image)
        config["terminal"]["singularity_image"] = image
        save_env_value("TERMINAL_SINGULARITY_IMAGE", image)

        _prompt_container_resources(config)

    elif selected_backend == "modal":
        print_success("终端后端：Modal")
        print_info("无服务器云端沙箱。每个会话拥有独立的容器。")
        from tools.managed_tool_gateway import is_managed_tool_gateway_ready
        from tools.tool_backend_helpers import normalize_modal_mode

        managed_modal_available = bool(
            managed_nous_tools_enabled()
            and
            get_nous_subscription_features(config).nous_auth_present
            and is_managed_tool_gateway_ready("modal")
        )
        modal_mode = normalize_modal_mode(cfg_get(config, "terminal", "modal_mode"))
        use_managed_modal = False
        if managed_modal_available:
            modal_choices = [
                "使用我的 Nous 订阅",
                "使用我自己的 Modal 账户",
            ]
            if modal_mode == "managed":
                default_modal_idx = 0
            elif modal_mode == "direct":
                default_modal_idx = 1
            else:
                default_modal_idx = 1 if get_env_value("MODAL_TOKEN_ID") else 0
            modal_mode_idx = prompt_choice(
                "选择 Modal 执行的计费方式：",
                modal_choices,
                default_modal_idx,
            )
            use_managed_modal = modal_mode_idx == 0

        if use_managed_modal:
            config["terminal"]["modal_mode"] = "managed"
            print_info("Modal 执行将使用托管的 Nous 网关，费用计入你的订阅。")
            if get_env_value("MODAL_TOKEN_ID") or get_env_value("MODAL_TOKEN_SECRET"):
                print_info(
                    "直接 Modal 凭据仍处于配置状态，但此后端已固定为托管模式。"
                )
        else:
            config["terminal"]["modal_mode"] = "direct"
            print_info("需要 Modal 账户：https://modal.com")

            # Check if modal SDK is installed
            try:
                __import__("modal")
            except ImportError:
                print_info("正在安装 modal SDK...")
                import subprocess

                uv_bin = shutil.which("uv")
                if uv_bin:
                    result = subprocess.run(
                        [
                            uv_bin,
                            "pip",
                            "install",
                            "--python",
                            sys.executable,
                            "modal",
                        ],
                        capture_output=True,
                        text=True,
                    )
                else:
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "modal"],
                        capture_output=True,
                        text=True,
                    )
                if result.returncode == 0:
                    print_success("modal SDK 已安装")
                else:
                    print_warning("安装失败 — 手动运行：pip install modal")

            # Modal token
            print()
            print_info("Modal 认证：")
            print_info("  在此获取令牌：https://modal.com/settings")
            existing_token = get_env_value("MODAL_TOKEN_ID")
            if existing_token:
                print_info("  Modal 令牌：已配置")
                if prompt_yes_no("  更新 Modal 凭据？", False):
                    token_id = prompt("    Modal 令牌 ID", password=True)
                    token_secret = prompt("    Modal 令牌密钥", password=True)
                    if token_id:
                        save_env_value("MODAL_TOKEN_ID", token_id)
                    if token_secret:
                        save_env_value("MODAL_TOKEN_SECRET", token_secret)
            else:
                token_id = prompt("    Modal 令牌 ID", password=True)
                token_secret = prompt("    Modal 令牌密钥", password=True)
                if token_id:
                    save_env_value("MODAL_TOKEN_ID", token_id)
                if token_secret:
                    save_env_value("MODAL_TOKEN_SECRET", token_secret)

        _prompt_container_resources(config)

    elif selected_backend == "daytona":
        print_success("终端后端：Daytona")
        print_info("持久化云端开发环境。")
        print_info("每个会话获得专用的沙箱，具有文件系统持久化功能。")
        print_info("注册地址：https://daytona.io")

        # Check if daytona SDK is installed
        try:
            __import__("daytona")
        except ImportError:
            print_info("正在安装 daytona SDK...")
            import subprocess

            uv_bin = shutil.which("uv")
            if uv_bin:
                result = subprocess.run(
                    [uv_bin, "pip", "install", "--python", sys.executable, "daytona"],
                    capture_output=True,
                    text=True,
                )
            else:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "daytona"],
                    capture_output=True,
                    text=True,
                )
            if result.returncode == 0:
                print_success("daytona SDK 已安装")
            else:
                print_warning("安装失败 — 手动运行：pip install daytona")
                if result.stderr:
                    print_info(f"  错误：{result.stderr.strip().splitlines()[-1]}")

        # Daytona API key
        print()
        existing_key = get_env_value("DAYTONA_API_KEY")
        if existing_key:
            print_info("  Daytona API 密钥：已配置")
            if prompt_yes_no("  更新 API 密钥？", False):
                api_key = prompt("    Daytona API 密钥", password=True)
                if api_key:
                    save_env_value("DAYTONA_API_KEY", api_key)
                    print_success("    已更新")
        else:
            api_key = prompt("    Daytona API 密钥", password=True)
            if api_key:
                save_env_value("DAYTONA_API_KEY", api_key)
                print_success("    已配置")

        # Daytona image
        current_image = cfg_get(config, "terminal", "daytona_image", default="nikolaik/python-nodejs:python3.11-nodejs20")
        image = prompt("  沙箱镜像", current_image)
        config["terminal"]["daytona_image"] = image
        save_env_value("TERMINAL_DAYTONA_IMAGE", image)

        _prompt_container_resources(config)

    elif selected_backend == "vercel_sandbox":
        print_success("终端后端：Vercel Sandbox")
        print_info("云端微虚拟机沙箱，支持基于快照的文件系统持久化。")
        print_info("需要可选 SDK：pip install 'hermes-agent[vercel]'")

        try:
            __import__("vercel")
        except ImportError:
            print_info("正在安装 vercel SDK...")
            import subprocess

            uv_bin = shutil.which("uv")
            if uv_bin:
                result = subprocess.run(
                    [uv_bin, "pip", "install", "--python", sys.executable, "vercel"],
                    capture_output=True,
                    text=True,
                )
            else:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "vercel"],
                    capture_output=True,
                    text=True,
                )
            if result.returncode == 0:
                print_success("vercel SDK 已安装")
            else:
                print_warning("安装失败 — 手动运行：pip install 'hermes-agent[vercel]'")
                if result.stderr:
                    print_info(f"  错误：{result.stderr.strip().splitlines()[-1]}")

        _prompt_vercel_sandbox_settings(config)

    elif selected_backend == "ssh":
        print_success("终端后端：SSH")
        print_info("通过 SSH 在远程机器上运行命令。")

        # SSH host
        current_host = get_env_value("TERMINAL_SSH_HOST") or ""
        host = prompt("  SSH 主机（主机名或 IP）", current_host)
        if host:
            save_env_value("TERMINAL_SSH_HOST", host)

        # SSH user
        current_user = get_env_value("TERMINAL_SSH_USER") or ""
        user = prompt("  SSH 用户", current_user or os.getenv("USER", ""))
        if user:
            save_env_value("TERMINAL_SSH_USER", user)

        # SSH port
        current_port = get_env_value("TERMINAL_SSH_PORT") or "22"
        port = prompt("  SSH 端口", current_port)
        if port and port != "22":
            save_env_value("TERMINAL_SSH_PORT", port)

        # SSH key
        current_key = get_env_value("TERMINAL_SSH_KEY") or ""
        default_key = str(Path.home() / ".ssh" / "id_rsa")
        ssh_key = prompt("  SSH 私钥路径", current_key or default_key)
        if ssh_key:
            save_env_value("TERMINAL_SSH_KEY", ssh_key)

        # Test connection
        if host and prompt_yes_no("  测试 SSH 连接？", True):
            print_info("  正在测试连接...")
            import subprocess

            ssh_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5"]
            if ssh_key:
                ssh_cmd.extend(["-i", ssh_key])
            if port and port != "22":
                ssh_cmd.extend(["-p", port])
            ssh_cmd.append(f"{user}@{host}" if user else host)
            ssh_cmd.append("echo ok")
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print_success("  SSH 连接成功！")
            else:
                print_warning(f"  SSH 连接失败：{result.stderr.strip()}")
                print_info("  请检查你的 SSH 密钥和主机设置。")

    # Sync terminal backend to .env so terminal_tool picks it up directly.
    # config.yaml is the source of truth, but terminal_tool reads TERMINAL_ENV.
    save_env_value("TERMINAL_ENV", selected_backend)
    if selected_backend == "modal":
        save_env_value("TERMINAL_MODAL_MODE", config["terminal"].get("modal_mode", "auto"))
    if selected_backend == "vercel_sandbox":
        save_env_value("TERMINAL_VERCEL_RUNTIME", config["terminal"].get("vercel_runtime", "node24"))
    save_config(config)
    print()
    print_success(f"终端后端已设置为：{selected_backend}")


# =============================================================================
# Section 3: Agent Settings
# =============================================================================


def _apply_default_agent_settings(config: dict):
    """Apply recommended defaults for all agent settings without prompting."""
    config.setdefault("agent", {})["max_turns"] = 90
    # config.yaml is the authoritative source for max_turns; the gateway
    # bridges it into HERMES_MAX_ITERATIONS at startup. We no longer write
    # to .env to avoid the dual-source inconsistency that caused the
    # 60-vs-500 bug (stale .env entry silently shadowing config.yaml).
    remove_env_value("HERMES_MAX_ITERATIONS")

    config.setdefault("display", {})["tool_progress"] = "all"

    config.setdefault("compression", {})["enabled"] = True
    config["compression"]["threshold"] = 0.50

    config.setdefault("session_reset", {}).update({
        "mode": "both",
        "idle_minutes": 1440,
        "at_hour": 4,
    })

    save_config(config)
    print_success("已应用推荐默认值：")
    print_info("  最大迭代次数：90")
    print_info("  工具进度显示：全部")
    print_info("  压缩阈值：0.50")
    print_info("  会话重置：无活动（1440 分钟）+ 每日（4:00）")
    print_info("  稍后可运行 `hermes setup agent` 进行自定义。")


def setup_agent_settings(config: dict):
    """Configure agent behavior: iterations, progress display, compression, session reset."""

    print_header("代理设置")
    print_info(f"   指南：{_DOCS_BASE}/user-guide/configuration")
    print()

    # ── Max Iterations ──
    # config.yaml is authoritative; read from there. If a legacy .env
    # entry is still around (from pre-PR#18413 setups), prefer the
    # config value so we don't surface a stale number to the user.
    current_max = str(cfg_get(config, "agent", "max_turns", default=90))
    print_info("每次对话的最大工具调用迭代次数。")
    print_info("数值越高 = 可处理更复杂的任务，但消耗更多令牌。")
    print_info(
        f"回车保留 {current_max}。大多数任务使用 90，开放式探索使用 150+。"
    )

    max_iter_str = prompt("最大迭代次数", current_max)
    try:
        max_iter = int(max_iter_str)
        if max_iter > 0:
            # Write to config.yaml (authoritative) only. Also clean up any
            # stale .env entry from earlier setup runs — the gateway's
            # bridge in gateway/run.py now unconditionally derives
            # HERMES_MAX_ITERATIONS from agent.max_turns at startup.
            config.setdefault("agent", {})["max_turns"] = max_iter
            config.pop("max_turns", None)
            remove_env_value("HERMES_MAX_ITERATIONS")
            print_success(f"最大迭代次数已设置为 {max_iter}")
    except ValueError:
        print_warning("无效数字，保留当前值")

    # ── Tool Progress Display ──
    print_info("")
    print_info("工具进度显示")
    print_info("控制工具活动的显示详细程度（CLI 和消息平台）。")
    print_info("  关闭    — 静默，仅显示最终响应")
    print_info("  新      — 仅在工具改变时显示名称（较少噪音）")
    print_info("  全部    — 显示每次工具调用及简短预览")
    print_info("  详细    — 完整参数、结果和调试日志")

    current_mode = cfg_get(config, "display", "tool_progress", default="all")
    mode = prompt("工具进度模式", current_mode)
    if mode.lower() in {"off", "new", "all", "verbose"}:
        if "display" not in config:
            config["display"] = {}
        config["display"]["tool_progress"] = mode.lower()
        save_config(config)
        print_success(f"工具进度已设置为：{mode.lower()}")
    else:
        print_warning(f"未知模式 '{mode}'，保留 '{current_mode}'")

    # ── Context Compression ──
    print_header("上下文压缩")
    print_info("当上下文过长时自动总结旧消息。")
    print_info(
        "阈值越高 = 越晚压缩（使用更多上下文）。阈值越低 = 越早压缩。"
    )

    config.setdefault("compression", {})["enabled"] = True

    current_threshold = cfg_get(config, "compression", "threshold", default=0.50)
    threshold_str = prompt("压缩阈值（0.5-0.95）", str(current_threshold))
    try:
        threshold = float(threshold_str)
        if 0.5 <= threshold <= 0.95:
            config["compression"]["threshold"] = threshold
    except ValueError:
        pass

    print_success(
        f"上下文压缩阈值已设置为 {config['compression'].get('threshold', 0.50)}"
    )

    # ── Session Reset Policy ──
    print_header("会话重置策略")
    print_info(
        "消息会话（Telegram、Discord 等）会随时间积累上下文。"
    )
    print_info(
        "每条消息都会添加到对话历史中，这意味着 API 成本不断增长。"
    )
    print_info("")
    print_info(
        "为管理这个问题，会话可以在一定时间不活动后自动重置，"
    )
    print_info(
        "或者在每天固定时间重置。重置时，代理会将重要信息保存到持久记忆，"
    )
    print_info(
        "但对话上下文会被清除。"
    )
    print_info("")
    print_info("你也可以随时在聊天中输入 /reset 手动重置。")
    print_info("")

    reset_choices = [
        "无活动 + 每日重置（推荐 — 哪个先到触发哪个）",
        "仅无活动（N 分钟无消息后重置）",
        "仅每日（每天固定时间重置）",
        "从不自动重置（上下文持续到 /reset 或上下文压缩）",
        "保留当前设置",
    ]

    current_policy = config.get("session_reset", {})
    current_mode = current_policy.get("mode", "both")
    current_idle = current_policy.get("idle_minutes", 1440)
    current_hour = current_policy.get("at_hour", 4)

    default_reset = {"both": 0, "idle": 1, "daily": 2, "none": 3}.get(current_mode, 0)

    reset_idx = prompt_choice("会话重置模式：", reset_choices, default_reset)

    config.setdefault("session_reset", {})

    if reset_idx == 0:  # Both
        config["session_reset"]["mode"] = "both"
        idle_str = prompt("  无活动超时（分钟）", str(current_idle))
        try:
            idle_val = int(idle_str)
            if idle_val > 0:
                config["session_reset"]["idle_minutes"] = idle_val
        except ValueError:
            pass
        hour_str = prompt("  每日重置小时（0-23，本地时间）", str(current_hour))
        try:
            hour_val = int(hour_str)
            if 0 <= hour_val <= 23:
                config["session_reset"]["at_hour"] = hour_val
        except ValueError:
            pass
        print_success(
            f"会话将在无活动 {config['session_reset'].get('idle_minutes', 1440)} 分钟后或每天 {config['session_reset'].get('at_hour', 4)}:00 重置"
        )
    elif reset_idx == 1:  # Idle only
        config["session_reset"]["mode"] = "idle"
        idle_str = prompt("  无活动超时（分钟）", str(current_idle))
        try:
            idle_val = int(idle_str)
            if idle_val > 0:
                config["session_reset"]["idle_minutes"] = idle_val
        except ValueError:
            pass
        print_success(
            f"会话将在无活动 {config['session_reset'].get('idle_minutes', 1440)} 分钟后重置"
        )
    elif reset_idx == 2:  # Daily only
        config["session_reset"]["mode"] = "daily"
        hour_str = prompt("  每日重置小时（0-23，本地时间）", str(current_hour))
        try:
            hour_val = int(hour_str)
            if 0 <= hour_val <= 23:
                config["session_reset"]["at_hour"] = hour_val
        except ValueError:
            pass
        print_success(
            f"会话将在每天 {config['session_reset'].get('at_hour', 4)}:00 重置"
        )
    elif reset_idx == 3:  # None
        config["session_reset"]["mode"] = "none"
        print_info(
            "会话永远不会自动重置。上下文仅通过压缩管理。"
        )
        print_warning(
            "长对话将增加成本。需要时请手动使用 /reset 重置。"
        )
    # else: keep current (idx == 4)

    save_config(config)


# =============================================================================
# Section 4: Messaging Platforms (Gateway)
# =============================================================================


def _setup_telegram():
    """Configure Telegram bot credentials and allowlist."""
    print_header("Telegram")
    existing = get_env_value("TELEGRAM_BOT_TOKEN")
    if existing:
        print_info("Telegram：已配置")
        if not prompt_yes_no("重新配置 Telegram？", False):
            # Check missing allowlist on existing config
            if not get_env_value("TELEGRAM_ALLOWED_USERS"):
                print_info("⚠️  Telegram 没有用户白名单 — 任何人都可以使用你的机器人！")
                if prompt_yes_no("立即添加允许用户？", True):
                    print_info("   查找 Telegram 用户 ID：给 @userinfobot 发消息")
                    allowed_users = prompt("允许的用户 ID（逗号分隔）")
                    if allowed_users:
                        save_env_value("TELEGRAM_ALLOWED_USERS", allowed_users.replace(" ", ""))
                        print_success("Telegram 白名单已配置")
            return

    print_info("通过 Telegram 上的 @BotFather 创建机器人")
    import re

    while True:
        token = prompt("Telegram 机器人令牌", password=True)
        if not token:
            return
        if not re.match(r"^\d+:[A-Za-z0-9_-]{30,}$", token):
            print_error(
                "令牌格式无效。格式：<数字ID>:<字母数字哈希> "
                "（例如：123456789:ABCdefGHI-jklMNOpqrSTUvwxYZ）"
            )
            continue
        break
    save_env_value("TELEGRAM_BOT_TOKEN", token)
    print_success("Telegram 令牌已保存")

    print()
    print_info("🔒 安全：限制谁可以使用你的机器人")
    print_info("   查找你的 Telegram 用户 ID：")
    print_info("   1. 在 Telegram 中给 @userinfobot 发消息")
    print_info("   2. 它会回复你的数字 ID（例如：123456789）")
    print()
    allowed_users = prompt(
        "允许的用户 ID（逗号分隔，留空则开放访问）"
    )
    if allowed_users:
        save_env_value("TELEGRAM_ALLOWED_USERS", allowed_users.replace(" ", ""))
        print_success("Telegram 白名单已配置 — 仅列出用户可使用机器人")
    else:
        print_info("⚠️ 未设置白名单 — 任何找到你机器人都可以使用！")

    print()
    print_info("📬 主频道：Hermes 发送定时任务结果、")
    print_info("   跨平台消息和通知的地方。")
    print_info("   对于 Telegram 私聊，这是你的用户 ID（同上）。")

    first_user_id = allowed_users.split(",")[0].strip() if allowed_users else ""
    if first_user_id:
        if prompt_yes_no(f"使用你的用户 ID（{first_user_id}）作为主频道？", True):
            save_env_value("TELEGRAM_HOME_CHANNEL", first_user_id)
            print_success(f"Telegram 主频道已设置为 {first_user_id}")
        else:
            home_channel = prompt("主频道 ID（留空则稍后在 Telegram 中使用 /set-home 设置）")
            if home_channel:
                save_env_value("TELEGRAM_HOME_CHANNEL", home_channel)
    else:
        print_info("   你也可以稍后在 Telegram 聊天中输入 /set-home 设置。")
        home_channel = prompt("主频道 ID（留空则稍后设置）")
        if home_channel:
            save_env_value("TELEGRAM_HOME_CHANNEL", home_channel)


def _setup_discord():
    """Configure Discord bot credentials and allowlist."""
    print_header("Discord")
    existing = get_env_value("DISCORD_BOT_TOKEN")
    if existing:
        print_info("Discord：已配置")
        if not prompt_yes_no("重新配置 Discord？", False):
            if not get_env_value("DISCORD_ALLOWED_USERS"):
                print_info("⚠️  Discord 没有用户白名单 — 任何人都可以使用你的机器人！")
                if prompt_yes_no("立即添加允许用户？", True):
                    print_info("   查找 Discord ID：启用开发者模式，右键点击名称 → 复制 ID")
                    allowed_users = prompt("允许的用户 ID（逗号分隔）")
                    if allowed_users:
                        cleaned_ids = _clean_discord_user_ids(allowed_users)
                        save_env_value("DISCORD_ALLOWED_USERS", ",".join(cleaned_ids))
                        print_success("Discord 白名单已配置")
            return

    print_info("在 https://discord.com/developers/applications 创建机器人")
    token = prompt("Discord 机器人令牌", password=True)
    if not token:
        return
    save_env_value("DISCORD_BOT_TOKEN", token)
    print_success("Discord 令牌已保存")

    print()
    print_info("🔒 安全：限制谁可以使用你的机器人")
    print_info("   查找你的 Discord 用户 ID：")
    print_info("   1. 在 Discord 设置中启用开发者模式")
    print_info("   2. 右键点击你的名字 → 复制 ID")
    print()
    print_info("   你也可以使用 Discord 用户名（网关启动时解析）。")
    print()
    allowed_users = prompt(
        "允许的用户 ID 或用户名（逗号分隔，留空则开放访问）"
    )
    if allowed_users:
        cleaned_ids = _clean_discord_user_ids(allowed_users)
        save_env_value("DISCORD_ALLOWED_USERS", ",".join(cleaned_ids))
        print_success("Discord 白名单已配置")
    else:
        print_info("⚠️ 未设置白名单 — 任何有你机器人的服务器上的人都可以使用！")

    print()
    print_info("📬 主频道：Hermes 发送定时任务结果、")
    print_info("   跨平台消息和通知的地方。")
    print_info("   获取频道 ID：右键点击频道 → 复制频道 ID")
    print_info("   （需要在 Discord 设置中启用开发者模式）")
    print_info("   你也可以稍后在 Discord 频道中输入 /set-home 设置。")
    home_channel = prompt("主频道 ID（留空则稍后使用 /set-home 设置）")
    if home_channel:
        save_env_value("DISCORD_HOME_CHANNEL", home_channel)


def _clean_discord_user_ids(raw: str) -> list:
    """Strip common Discord mention prefixes from a comma-separated ID string."""
    cleaned = []
    for uid in raw.replace(" ", "").split(","):
        uid = uid.strip()
        if uid.startswith("<@") and uid.endswith(">"):
            uid = uid.lstrip("<@!").rstrip(">")
        if uid.lower().startswith("user:"):
            uid = uid[5:]
        if uid:
            cleaned.append(uid)
    return cleaned


def _setup_slack():
    """Configure Slack bot credentials."""
    print_header("Slack")
    existing = get_env_value("SLACK_BOT_TOKEN")
    if existing:
        print_info("Slack：已配置")
        if not prompt_yes_no("重新配置 Slack？", False):
            # Even without reconfiguring, offer to refresh the manifest so
            # new commands (e.g. /btw, /stop, ...) get registered in Slack.
            if prompt_yes_no(
                "使用最新命令列表重新生成 Slack 应用清单？"
                "（推荐在 `hermes update` 后执行）",
                True,
            ):
                _write_slack_manifest_and_instruct()
            return

    print_info("创建 Slack 应用的步骤：")
    print_info("   1. 前往 https://api.slack.com/apps → 创建新应用")
    print_info("      选择 '从应用清单' — 我们将在下面为你生成一个。")
    print_info("   2. 启用 Socket 模式：设置 → Socket 模式 → 启用")
    print_info("      • 创建应用级令牌，作用域为 'connections:write'")
    print_info("   3. 安装到工作区：设置 → 安装应用")
    print_info("   4. 安装后，邀请机器人到频道：/invite @YourBot")
    print()
    print_info("   完整指南：https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack/")
    print()

    # Generate and write manifest up-front so the user can paste it into
    # the "Create from manifest" flow instead of clicking through scopes /
    # events / slash commands one at a time.
    _write_slack_manifest_and_instruct()

    print()
    bot_token = prompt("Slack 机器人令牌（xoxb-...）", password=True)
    if not bot_token:
        return
    save_env_value("SLACK_BOT_TOKEN", bot_token)
    app_token = prompt("Slack 应用令牌（xapp-...）", password=True)
    if app_token:
        save_env_value("SLACK_APP_TOKEN", app_token)
    print_success("Slack 令牌已保存")

    print()
    print_info("🔒 安全：限制谁可以使用你的机器人")
    print_info("   查找成员 ID：点击用户名 → 查看完整资料 → ⋮ → 复制成员 ID")
    print()
    allowed_users = prompt(
        "允许的用户 ID（逗号分隔，留空则拒绝除已配对用户外的所有人）"
    )
    if allowed_users:
        save_env_value("SLACK_ALLOWED_USERS", allowed_users.replace(" ", ""))
        print_success("Slack 白名单已配置")
    else:
        print_warning("⚠️ 未设置 Slack 白名单 — 未配对用户默认被拒绝。")
        print_info("   只有在你故意开放工作区访问时才设置 SLACK_ALLOW_ALL_USERS=true 或 GATEWAY_ALLOW_ALL_USERS=true。")

    print()
    print_info("📬 主频道：Hermes 发送定时任务结果、")
    print_info("   跨平台消息和通知的地方。")
    print_info("   获取频道 ID：在 Slack 中打开频道，右键点击")
    print_info("   频道名称 → 复制链接 — ID 以 C 开头（例如 C01ABC2DE3F）。")
    print_info("   你也可以稍后在 Slack 频道中输入 /set-home 设置。")
    home_channel = prompt("主频道 ID（留空则稍后使用 /set-home 设置）")
    if home_channel:
        save_env_value("SLACK_HOME_CHANNEL", home_channel.strip())


def _write_slack_manifest_and_instruct():
    """Generate the Slack manifest, write it under HERMES_HOME, and print
    paste-into-Slack instructions.

    Exposed as its own helper so both the initial setup flow and the
    "reconfigure? → no" branch can refresh the manifest without the user
    re-entering tokens. Failures are non-fatal — if the manifest write
    fails for any reason, we print a warning and skip rather than abort
    the whole Slack setup.
    """
    try:
        from hermes_cli.slack_cli import _build_full_manifest
        from hermes_constants import get_hermes_home

        manifest = _build_full_manifest(
            bot_name="Hermes",
            bot_description="你的 Hermes 代理在 Slack 上",
        )
        target = Path(get_hermes_home()) / "slack-manifest.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        import json as _json
        target.write_text(
            _json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print_success(f"Slack 应用清单已写入：{target}")
        print_info(
            "   将其粘贴到 https://api.slack.com/apps → 你的应用 → 功能 "
            "→ 应用清单 → 编辑，然后保存。如果范围或斜杠命令更改，"
            "Slack 会提示重新安装。"
        )
        print_info(
            "   在 Hermes 添加新命令后，随时重新运行 `hermes slack manifest --write` 刷新。"
        )
    except Exception as exc:  # pragma: no cover - best-effort UX helper
        print_warning(f"无法写入 Slack 清单：{exc}")
        print_info(
            "   稍后可手动生成：hermes slack manifest --write"
        )


def _setup_matrix():
    """Configure Matrix credentials."""
    print_header("Matrix")
    existing = get_env_value("MATRIX_ACCESS_TOKEN") or get_env_value("MATRIX_PASSWORD")
    if existing:
        print_info("Matrix：已配置")
        if not prompt_yes_no("重新配置 Matrix？", False):
            return

    print_info("兼容任何 Matrix 家庭服务器（Synapse、Conduit、Dendrite 或 matrix.org）。")
    print_info("   1. 在家庭服务器上创建机器人用户，或使用你自己的账户")
    print_info("   2. 从 Element 获取访问令牌，或提供用户 ID + 密码")
    print()
    homeserver = prompt("家庭服务器 URL（例如 https://matrix.example.org）")
    if homeserver:
        save_env_value("MATRIX_HOMESERVER", homeserver.rstrip("/"))

    print()
    print_info("认证：提供访问令牌（推荐），或用户 ID + 密码。")
    token = prompt("访问令牌（留空则使用密码登录）", password=True)
    if token:
        save_env_value("MATRIX_ACCESS_TOKEN", token)
        user_id = prompt("用户 ID（@bot:server — 可选，会自动检测）")
        if user_id:
            save_env_value("MATRIX_USER_ID", user_id)
        print_success("Matrix 访问令牌已保存")
    else:
        user_id = prompt("用户 ID（@bot:server）")
        if user_id:
            save_env_value("MATRIX_USER_ID", user_id)
        password = prompt("密码", password=True)
        if password:
            save_env_value("MATRIX_PASSWORD", password)
            print_success("Matrix 凭据已保存")

    if token or get_env_value("MATRIX_PASSWORD"):
        print()
        want_e2ee = prompt_yes_no("启用端到端加密（E2EE）？", False)
        if want_e2ee:
            save_env_value("MATRIX_ENCRYPTION", "true")
            print_success("E2EE 已启用")

        matrix_pkg = "mautrix[encryption]" if want_e2ee else "mautrix"
        try:
            __import__("mautrix")
        except ImportError:
            print_info(f"正在安装 {matrix_pkg}...")
            import subprocess
            uv_bin = shutil.which("uv")
            if uv_bin:
                result = subprocess.run(
                    [uv_bin, "pip", "install", "--python", sys.executable, matrix_pkg],
                    capture_output=True, text=True,
                )
            else:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", matrix_pkg],
                    capture_output=True, text=True,
                )
            if result.returncode == 0:
                print_success(f"{matrix_pkg} 已安装")
            else:
                print_warning(f"安装失败 — 手动运行：pip install '{matrix_pkg}'")
                if result.stderr:
                    print_info(f"  错误：{result.stderr.strip().splitlines()[-1]}")

        print()
        print_info("🔒 安全：限制谁可以使用你的机器人")
        print_info("   Matrix 用户 ID 格式为 @username:server")
        print()
        allowed_users = prompt("允许的用户 ID（逗号分隔，留空则开放访问）")
        if allowed_users:
            save_env_value("MATRIX_ALLOWED_USERS", allowed_users.replace(" ", ""))
            print_success("Matrix 白名单已配置")
        else:
            print_info("⚠️ 未设置白名单 — 任何能给机器人发消息的人都可以使用！")

        print()
        print_info("📬 主房间：Hermes 发送定时任务结果和通知的地方。")
        print_info("   房间 ID 格式为 !abc123:server（在 Element 房间设置中显示）")
        print_info("   你也可以稍后在 Matrix 房间中输入 /set-home 设置。")
        home_room = prompt("主房间 ID（留空则稍后使用 /set-home 设置）")
        if home_room:
            save_env_value("MATRIX_HOME_ROOM", home_room)


def _setup_mattermost():
    """Configure Mattermost bot credentials."""
    print_header("Mattermost")
    existing = get_env_value("MATTERMOST_TOKEN")
    if existing:
        print_info("Mattermost：已配置")
        if not prompt_yes_no("重新配置 Mattermost？", False):
            return

    print_info("兼容任何自托管的 Mattermost 实例。")
    print_info("   1. 在 Mattermost 中：集成 → 机器人账户 → 添加机器人账户")
    print_info("   2. 复制机器人令牌")
    print()
    mm_url = prompt("Mattermost 服务器 URL（例如 https://mm.example.com）")
    if mm_url:
        save_env_value("MATTERMOST_URL", mm_url.rstrip("/"))
    token = prompt("机器人令牌", password=True)
    if not token:
        return
    save_env_value("MATTERMOST_TOKEN", token)
    print_success("Mattermost 令牌已保存")

    print()
    print_info("🔒 安全：限制谁可以使用你的机器人")
    print_info("   查找用户 ID：点击头像 → 个人资料")
    print_info("   或使用 API：GET /api/v4/users/me")
    print()
    allowed_users = prompt("允许的用户 ID（逗号分隔，留空则开放访问）")
    if allowed_users:
        save_env_value("MATTERMOST_ALLOWED_USERS", allowed_users.replace(" ", ""))
        print_success("Mattermost 白名单已配置")
    else:
        print_info("⚠️ 未设置白名单 — 任何能给机器人发消息的人都可以使用！")

    print()
    print_info("📬 主频道：Hermes 发送定时任务结果和通知的地方。")
    print_info("   获取频道 ID：点击频道名称 → 查看信息 → 复制 ID")
    print_info("   你也可以稍后在 Mattermost 频道中输入 /set-home 设置。")
    home_channel = prompt("主频道 ID（留空则稍后使用 /set-home 设置）")
    if home_channel:
        save_env_value("MATTERMOST_HOME_CHANNEL", home_channel)
    print_info("   在编辑器中打开配置：hermes config edit")


def _setup_bluebubbles():
    """Configure BlueBubbles iMessage gateway."""
    print_header("BlueBubbles (iMessage)")
    existing = get_env_value("BLUEBUBBLES_SERVER_URL")
    if existing:
        print_info("BlueBubbles：已配置")
        if not prompt_yes_no("重新配置 BlueBubbles？", False):
            return

    print_info("通过 BlueBubbles 将 Hermes 连接到 iMessage — 一个免费的开源 macOS 服务器，")
    print_info("将 iMessage 桥接到任何设备。")
    print_info("   需要运行 BlueBubbles Server v1.0.0+ 的 Mac")
    print_info("   下载：https://bluebubbles.app/")
    print()
    print_info("在 BlueBubbles 服务器 → 设置 → API 中，记下你的服务器 URL 和密码。")
    print()

    server_url = prompt("BlueBubbles 服务器 URL（例如 http://192.168.1.10:1234）")
    if not server_url:
        print_warning("需要服务器 URL — 跳过 BlueBubbles 设置")
        return
    save_env_value("BLUEBUBBLES_SERVER_URL", server_url.rstrip("/"))

    password = prompt("BlueBubbles 服务器密码", password=True)
    if not password:
        print_warning("需要密码 — 跳过 BlueBubbles 设置")
        return
    save_env_value("BLUEBUBBLES_PASSWORD", password)
    print_success("BlueBubbles 凭据已保存")

    print()
    print_info("🔒 安全：限制谁可以给你的机器人发消息")
    print_info("   Use iMessage addresses: email (user@icloud.com) or phone (+15551234567)")
    print()
    allowed_users = prompt("允许的 iMessage 地址（逗号分隔，留空则开放访问）")
    if allowed_users:
        save_env_value("BLUEBUBBLES_ALLOWED_USERS", allowed_users.replace(" ", ""))
        print_success("BlueBubbles 白名单已配置")
    else:
        print_info("⚠️ 未设置白名单 — 任何能给你发 iMessage 的人都可以使用机器人！")

    print()
    print_info("📬 主频道：用于接收定时任务结果和通知的电话或电子邮件。")
    print_info("   你也可以稍后在 iMessage 聊天中使用 /set-home 设置。")
    home_channel = prompt("主频道地址（留空则稍后设置）")
    if home_channel:
        save_env_value("BLUEBUBBLES_HOME_CHANNEL", home_channel)

    print()
    print_info("高级设置（默认值适用于大多数情况）：")
    if prompt_yes_no("配置 Webhook 监听器设置？", False):
        webhook_port = prompt("Webhook 监听端口（默认：8645）")
        if webhook_port:
            try:
                save_env_value("BLUEBUBBLES_WEBHOOK_PORT", str(int(webhook_port)))
                print_success(f"Webhook 端口已设置为 {webhook_port}")
            except ValueError:
                print_warning("端口号无效，使用默认 8645")

    print()
    print_info("需要 BlueBubbles Private API 助手来实现输入状态指示、")
    print_info("已读回执和 Tapback 反应。基本消息功能无需它也能工作。")
    print_info("   安装：https://docs.bluebubbles.app/helper-bundle/installation")


def _setup_qqbot():
    """Configure QQ Bot (Official API v2) via gateway setup."""
    from hermes_cli.gateway import _setup_qqbot as _gateway_setup_qqbot
    _gateway_setup_qqbot()


def _setup_webhooks():
    """Configure webhook integration."""
    print_header("Webhook")
    existing = get_env_value("WEBHOOK_ENABLED")
    if existing:
        print_info("Webhook：已配置")
        if not prompt_yes_no("重新配置 Webhook？", False):
            return

    print()
    print_warning("⚠  Webhook 和 SMS 平台需要将网关端口暴露到互联网。")
    print_warning("   为安全起见，请在沙箱环境（Docker、VM 等）中运行网关，")
    print_warning("   以限制提示注入的攻击范围。")
    print()
    print_info("   完整指南：https://hermes-agent.nousresearch.com/docs/user-guide/messaging/webhooks/")
    print()

    port = prompt("Webhook 端口（默认 8644）")
    if port:
        try:
            save_env_value("WEBHOOK_PORT", str(int(port)))
            print_success(f"Webhook 端口已设置为 {port}")
        except ValueError:
            print_warning("端口号无效，使用默认 8644")

    secret = prompt("全局 HMAC 密钥（所有路由共用）", password=True)
    if secret:
        save_env_value("WEBHOOK_SECRET", secret)
        print_success("Webhook 密钥已保存")
    else:
        print_warning("未设置密钥 — 你必须在 config.yaml 中为每个路由配置密钥")

    save_env_value("WEBHOOK_ENABLED", "true")
    print()
    print_success("Webhook 已启用！下一步：")
    from hermes_constants import display_hermes_home as _dhh
    print_info(f"   1. 在 {_dhh()}/config.yaml 中定义 Webhook 路由")
    print_info("   2. 将你的服务（GitHub、GitLab 等）指向：")
    print_info("      http://your-server:8644/webhooks/<路由名称>")
    print()
    print_info("   路由配置指南：")
    print_info("   https://hermes-agent.nousresearch.com/docs/user-guide/messaging/webhooks/#configuring-routes")
    print()
    print_info("   在编辑器中打开配置：hermes config edit")
    print_info("   在编辑器中打开配置：hermes config edit")


def setup_gateway(config: dict):
    """Configure messaging platform integrations."""
    from hermes_cli.gateway import _all_platforms, _platform_status, _configure_platform

    print_header("消息平台")
    print_info("连接消息平台，随时随地与 Hermes 聊天。")
    print_info("空格键切换，回车确认。")
    print()

    platforms = _all_platforms()

    # Build checklist, pre-selecting already-configured platforms.
    items = []
    pre_selected = []
    for i, plat in enumerate(platforms):
        status = _platform_status(plat)
        items.append(f"{plat['emoji']} {plat['label']}  ({status})")
        if status == "configured":
            pre_selected.append(i)

    selected = prompt_checklist("选择要配置的平台：", items, pre_selected)

    if not selected:
        print_info("未选择任何平台。稍后运行 'hermes setup gateway' 进行配置。")
        return

    for idx in selected:
        _configure_platform(platforms[idx])

    # ── Gateway Service Setup ──
    # Count any platform (built-in or plugin) the user configured during this
    # setup pass — reuses ``_platform_status`` so plugin platforms like IRC
    # are picked up without another hard-coded env-var list.
    def _is_progress(status: str) -> bool:
        s = status.lower()
        return not (
            s == "not configured"
            or s.startswith("partially")
            or s.startswith("plugin disabled")
        )

    any_messaging = any(
        _is_progress(_platform_status(p)) for p in _all_platforms()
    )
    if any_messaging:
        print()
        print_info("━" * 50)
        print_success("消息平台已配置！")

        # Check if any home channels are missing
        missing_home = []
        if get_env_value("TELEGRAM_BOT_TOKEN") and not get_env_value(
            "TELEGRAM_HOME_CHANNEL"
        ):
            missing_home.append("Telegram")
        if get_env_value("DISCORD_BOT_TOKEN") and not get_env_value(
            "DISCORD_HOME_CHANNEL"
        ):
            missing_home.append("Discord")
        if get_env_value("SLACK_BOT_TOKEN") and not get_env_value("SLACK_HOME_CHANNEL"):
            missing_home.append("Slack")
        if get_env_value("BLUEBUBBLES_SERVER_URL") and not get_env_value("BLUEBUBBLES_HOME_CHANNEL"):
            missing_home.append("BlueBubbles")
        if get_env_value("QQ_APP_ID") and not (
            get_env_value("QQBOT_HOME_CHANNEL") or get_env_value("QQ_HOME_CHANNEL")
        ):
            missing_home.append("QQBot")

        if missing_home:
            print()
            print_warning(f"以下平台未设置主频道：{', '.join(missing_home)}")
            print_info("   没有主频道，定时任务和跨平台消息")
            print_info("   无法发送到这些平台。")
            print_info("   稍后在聊天中使用 /set-home 设置，或：")
            for plat in missing_home:
                print_info(
                    f"     hermes config set {plat.upper()}_HOME_CHANNEL <频道ID>"
                )

        # Offer to install the gateway as a system service
        import platform as _platform

        _is_linux = _platform.system() == "Linux"
        _is_macos = _platform.system() == "Darwin"
        _is_windows = _platform.system() == "Windows"

        from hermes_cli.gateway import (
            _is_service_installed,
            _is_service_running,
            supports_systemd_services,
            has_conflicting_systemd_units,
            has_legacy_hermes_units,
            install_linux_gateway_from_setup,
            print_systemd_scope_conflict_warning,
            print_legacy_unit_warning,
            systemd_start,
            systemd_restart,
            launchd_install,
            launchd_start,
            launchd_restart,
            UserSystemdUnavailableError,
            SystemScopeRequiresRootError,
            _system_scope_wizard_would_need_root,
            _print_system_scope_remediation,
        )

        service_installed = _is_service_installed()
        service_running = _is_service_running()
        supports_systemd = supports_systemd_services()
        supports_service_manager = supports_systemd or _is_macos or _is_windows

        print()
        if supports_systemd and has_conflicting_systemd_units():
            print_systemd_scope_conflict_warning()
            print()

        if supports_systemd and has_legacy_hermes_units():
            print_legacy_unit_warning()
            print()

        if service_running:
            if supports_systemd and _system_scope_wizard_would_need_root():
                _print_system_scope_remediation("restart")
            elif prompt_yes_no("  重启网关以应用更改？", True):
                try:
                    if supports_systemd:
                        systemd_restart()
                    elif _is_macos:
                        launchd_restart()
                    elif _is_windows:
                        from hermes_cli import gateway_windows
                        gateway_windows.restart()
                except UserSystemdUnavailableError as e:
                    print_error("  重启失败 — 用户 systemd 不可达：")
                    for line in str(e).splitlines():
                        print(f"  {line}")
                except SystemScopeRequiresRootError as e:
                    # Defense in depth: the pre-check above should have
                    # caught this, but a race (unit file appearing mid-run)
                    # could still land here. Previously this exited the
                    # whole wizard via sys.exit(1).
                    print_error(f"  重启失败：{e}")
                    _print_system_scope_remediation("restart")
                except Exception as e:
                    print_error(f"  重启失败：{e}")
        elif service_installed:
            if supports_systemd and _system_scope_wizard_would_need_root():
                _print_system_scope_remediation("start")
            elif prompt_yes_no("  启动网关服务？", True):
                try:
                    if supports_systemd:
                        systemd_start()
                    elif _is_macos:
                        launchd_start()
                    elif _is_windows:
                        from hermes_cli import gateway_windows
                        gateway_windows.start()
                except UserSystemdUnavailableError as e:
                    print_error("  启动失败 — 用户 systemd 不可达：")
                    for line in str(e).splitlines():
                        print(f"  {line}")
                except SystemScopeRequiresRootError as e:
                    print_error(f"  启动失败：{e}")
                    _print_system_scope_remediation("start")
                except Exception as e:
                    print_error(f"  启动失败：{e}")
        elif supports_service_manager:
            if supports_systemd:
                svc_name = "systemd"
            elif _is_macos:
                svc_name = "launchd"
            else:
                svc_name = "Scheduled Task"
            if prompt_yes_no(
                f"  将网关安装为 {svc_name} 服务？（后台运行，开机自启）",
                True,
            ):
                try:
                    installed_scope = None
                    did_install = False
                    started_inline = False
                    if supports_systemd:
                        installed_scope, did_install = install_linux_gateway_from_setup(force=False)
                    elif _is_macos:
                        launchd_install(force=False)
                        did_install = True
                    else:
                        # gateway_windows.install() registers the Scheduled
                        # Task AND starts it immediately (via schtasks /Run
                        # or a direct spawn fallback), so no separate start
                        # prompt is needed here.
                        from hermes_cli import gateway_windows
                        gateway_windows.install(force=False)
                        did_install = True
                        started_inline = True
                    print()
                    if did_install and not started_inline and prompt_yes_no("  现在启动服务？", True):
                        try:
                            if supports_systemd:
                                systemd_start(system=installed_scope == "system")
                            elif _is_macos:
                                launchd_start()
                        except UserSystemdUnavailableError as e:
                            print_error("  启动失败 — 用户 systemd 不可达：")
                            for line in str(e).splitlines():
                                print(f"  {line}")
                        except SystemScopeRequiresRootError as e:
                            print_error(f"  启动失败：{e}")
                            _print_system_scope_remediation("start")
                        except Exception as e:
                            print_error(f"  启动失败：{e}")
                except Exception as e:
                    print_error(f"  安装失败：{e}")
                    print_info("  你可以手动重试：hermes gateway install")
            else:
                print_info("  稍后可安装：hermes gateway install")
                if supports_systemd:
                    print_info("  或作为开机服务：sudo hermes gateway install --system")
                print_info("  或在前台运行：hermes gateway")
        else:
            from hermes_constants import is_container
            if is_container():
                print_info("启动网关以让你的机器人上线：")
                print_info("   hermes gateway run          # 作为容器主进程运行")
                print_info("")
                print_info("如需自动重启，可使用 Docker 重启策略：")
                print_info("   docker run --restart unless-stopped ...")
                print_info("   docker restart <容器>  # 手动重启")
            else:
                print_info("启动网关以让你的机器人上线：")
                print_info("   hermes gateway              # 在前台运行")

        print_info("━" * 50)


# =============================================================================
# Section 5: Tool Configuration (delegates to unified tools_config.py)
# =============================================================================


def setup_tools(config: dict, first_install: bool = False):
    """Configure tools — delegates to the unified tools_command() in tools_config.py.

    Both `hermes setup tools` and `hermes tools` use the same flow:
    platform selection → toolset toggles → provider/API key configuration.

    Args:
        first_install: When True, uses the simplified first-install flow
            (no platform menu, prompts for all unconfigured API keys).
    """
    from hermes_cli.tools_config import tools_command

    tools_command(first_install=first_install, config=config)


# =============================================================================
# Post-Migration Section Skip Logic
# =============================================================================


def _model_section_has_credentials(config: dict) -> bool:
    """Return True when any known inference provider has usable credentials.

    Sources of truth:
      * ``PROVIDER_REGISTRY`` in ``hermes_cli.auth`` — lists every supported
        provider along with its ``api_key_env_vars``.
      * ``active_provider`` in the auth store — covers OAuth device-code /
        external-OAuth providers (Nous, Codex, Qwen, Gemini CLI, ...).
      * The legacy OpenRouter aggregator env vars, which route generic
        ``OPENAI_API_KEY`` / ``OPENROUTER_API_KEY`` values through OpenRouter.
    """
    try:
        from hermes_cli.auth import get_active_provider
        if get_active_provider():
            return True
    except Exception:
        pass

    try:
        from hermes_cli.auth import PROVIDER_REGISTRY
    except Exception:
        PROVIDER_REGISTRY = {}  # type: ignore[assignment]

    def _has_key(pconfig) -> bool:
        for env_var in pconfig.api_key_env_vars:
            # CLAUDE_CODE_OAUTH_TOKEN is set by Claude Code itself, not by
            # the user — mirrors is_provider_explicitly_configured in auth.py.
            if env_var == "CLAUDE_CODE_OAUTH_TOKEN":
                continue
            if get_env_value(env_var):
                return True
        return False

    # Prefer the provider declared in config.yaml, avoids false positives
    # from stray env vars (GH_TOKEN, etc.) when the user has already picked
    # a different provider.
    model_cfg = config.get("model") if isinstance(config, dict) else None
    if isinstance(model_cfg, dict):
        provider_id = (model_cfg.get("provider") or "").strip().lower()
        if provider_id in PROVIDER_REGISTRY:
            if _has_key(PROVIDER_REGISTRY[provider_id]):
                return True
        if provider_id == "openrouter":
            for env_var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
                if get_env_value(env_var):
                    return True

    # OpenRouter aggregator fallback (no provider declared in config).
    for env_var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        if get_env_value(env_var):
            return True

    for pid, pconfig in PROVIDER_REGISTRY.items():
        # Skip copilot in auto-detect: GH_TOKEN / GITHUB_TOKEN are
        # commonly set for git tooling.  Mirrors resolve_provider in auth.py.
        if pid == "copilot":
            continue
        if _has_key(pconfig):
            return True
    return False


def _gateway_platform_short_label(label: str) -> str:
    """Strip trailing parenthetical qualifiers from a gateway platform label."""
    base = label.split("(", 1)[0].strip()
    return base or label


def _get_section_config_summary(config: dict, section_key: str) -> Optional[str]:
    """Return a short summary if a setup section is already configured, else None.

    Used after OpenClaw migration to detect which sections can be skipped.
    ``get_env_value`` is the module-level import from hermes_cli.config
    so that test patches on ``setup_mod.get_env_value`` take effect.
    """
    if section_key == "model":
        if not _model_section_has_credentials(config):
            return None
        model = config.get("model")
        if isinstance(model, str) and model.strip():
            return model.strip()
        if isinstance(model, dict):
            return str(model.get("default") or model.get("model") or "configured")
        return "configured"

    elif section_key == "terminal":
        backend = cfg_get(config, "terminal", "backend", default="local")
        return f"backend: {backend}"

    elif section_key == "agent":
        max_turns = cfg_get(config, "agent", "max_turns", default=90)
        return f"max turns: {max_turns}"

    elif section_key == "gateway":
        from hermes_cli.gateway import _all_platforms, _platform_status
        # Count any non-empty status other than the "not configured" sentinel —
        # platforms like WhatsApp ("enabled, not paired"), Matrix ("configured
        # + E2EE"), and Signal ("partially configured") all indicate the user
        # has already started setup and we shouldn't force the section to rerun.
        configured = [
            _gateway_platform_short_label(plat["label"])
            for plat in _all_platforms()
            if _platform_status(plat) and _platform_status(plat) != "not configured"
        ]
        if configured:
            return ", ".join(configured)
        return None  # No platforms configured — section must run

    elif section_key == "tools":
        tools = []
        if get_env_value("ELEVENLABS_API_KEY"):
            tools.append("TTS/ElevenLabs")
        if get_env_value("BROWSERBASE_API_KEY"):
            tools.append("Browser")
        if get_env_value("FIRECRAWL_API_KEY"):
            tools.append("Firecrawl")
        if tools:
            return ", ".join(tools)
        return None

    return None


def _skip_configured_section(
    config: dict, section_key: str, label: str
) -> bool:
    """Show an already-configured section summary and offer to skip.

    Returns True if the user chose to skip, False if the section should run.
    """
    summary = _get_section_config_summary(config, section_key)
    if not summary:
        return False
    print()
    print_success(f"  {label}: {summary}")
    return not prompt_yes_no(f"  Reconfigure {label.lower()}?", default=False)


# =============================================================================
# OpenClaw Migration
# =============================================================================


_OPENCLAW_SCRIPT = (
    get_optional_skills_dir(PROJECT_ROOT / "optional-skills")
    / "migration"
    / "openclaw-migration"
    / "scripts"
    / "openclaw_to_hermes.py"
)


def _load_openclaw_migration_module():
    """Load the openclaw_to_hermes migration script as a module.

    Returns the loaded module, or None if the script can't be loaded.
    """
    if not _OPENCLAW_SCRIPT.exists():
        return None

    spec = importlib.util.spec_from_file_location(
        "openclaw_to_hermes", _OPENCLAW_SCRIPT
    )
    if spec is None or spec.loader is None:
        return None

    mod = importlib.util.module_from_spec(spec)
    # Register in sys.modules so @dataclass can resolve the module
    # (Python 3.11+ requires this for dynamically loaded modules)
    import sys as _sys
    _sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        _sys.modules.pop(spec.name, None)
        raise
    return mod


# Item kinds that represent high-impact changes warranting explicit warnings.
# Gateway tokens/channels can hijack messaging platforms from the old agent.
# Config values may have different semantics between OpenClaw and Hermes.
# Instruction/context files (.md) can contain incompatible setup procedures.
_HIGH_IMPACT_KIND_KEYWORDS = {
    "gateway": "⚠ Gateway/messaging — this will configure Hermes to use your OpenClaw messaging channels",
    "telegram": "⚠ Telegram — this will point Hermes at your OpenClaw Telegram bot",
    "slack": "⚠ Slack — this will point Hermes at your OpenClaw Slack workspace",
    "discord": "⚠ Discord — this will point Hermes at your OpenClaw Discord bot",
    "whatsapp": "⚠ WhatsApp — this will point Hermes at your OpenClaw WhatsApp connection",
    "config": "⚠ Config values — OpenClaw settings may not map 1:1 to Hermes equivalents",
    "soul": "⚠ Instruction file — may contain OpenClaw-specific setup/restart procedures",
    "memory": "⚠ Memory/context file — may reference OpenClaw-specific infrastructure",
    "context": "⚠ Context file — may contain OpenClaw-specific instructions",
}


def _print_migration_preview(report: dict):
    """Print a detailed dry-run preview of what migration would do.

    Groups items by category and adds explicit warnings for high-impact
    changes like gateway token takeover and config value differences.
    """
    items = report.get("items", [])
    if not items:
        print_info("无需迁移。")
        return

    migrated_items = [i for i in items if i.get("status") == "migrated"]
    conflict_items = [i for i in items if i.get("status") == "conflict"]
    skipped_items = [i for i in items if i.get("status") == "skipped"]

    warnings_shown = set()

    if migrated_items:
        print(color("  将导入：", Colors.GREEN))
        for item in migrated_items:
            kind = item.get("kind", "unknown")
            dest = item.get("destination", "")
            if dest:
                dest_short = str(dest).replace(str(Path.home()), "~")
                print(f"      {kind:<22s} → {dest_short}")
            else:
                print(f"      {kind}")

            # Check for high-impact items and collect warnings
            kind_lower = kind.lower()
            dest_lower = str(dest).lower()
            for keyword, warning in _HIGH_IMPACT_KIND_KEYWORDS.items():
                if keyword in kind_lower or keyword in dest_lower:
                    warnings_shown.add(warning)
        print()

    if conflict_items:
        print(color("  将覆盖（与现有 Hermes 配置冲突）：", Colors.YELLOW))
        for item in conflict_items:
            kind = item.get("kind", "unknown")
            reason = item.get("reason", "已存在")
            print(f"      {kind:<22s}  {reason}")
        print()

    if skipped_items:
        print(color("  将跳过：", Colors.DIM))
        for item in skipped_items:
            kind = item.get("kind", "unknown")
            reason = item.get("reason", "")
            print(f"      {kind:<22s}  {reason}")
        print()

    # Print collected warnings
    if warnings_shown:
        print(color("  ── 警告 ──", Colors.YELLOW))
        for warning in sorted(warnings_shown):
            print(color(f"    {warning}", Colors.YELLOW))
        print()
        print(color("  注意：OpenClaw 配置值在 Hermes 中可能有不同语义。", Colors.YELLOW))
        print(color("  例如，OpenClaw 的 tool_call_execution: "auto" ≠ Hermes 的 yolo 模式。", Colors.YELLOW))
        print(color("  OpenClaw 的指令文件（.md）可能包含不兼容的操作步骤。", Colors.YELLOW))
        print()


def _offer_openclaw_migration(hermes_home: Path) -> bool:
    """Detect ~/.openclaw and offer to migrate during first-time setup.

    Runs a dry-run first to show the user exactly what would be imported,
    overwritten, or taken over. Only executes after explicit confirmation.

    Returns True if migration ran successfully, False otherwise.
    """
    openclaw_dir = Path.home() / ".openclaw"
    if not openclaw_dir.is_dir():
        return False

    if not _OPENCLAW_SCRIPT.exists():
        return False

    print()
    print_header("检测到 OpenClaw 安装")
    print_info(f"在 {openclaw_dir} 找到 OpenClaw 数据")
    print_info("Hermes 可以在进行任何更改之前预览将导入的内容。")
    print()

    if not prompt_yes_no("是否要查看可以导入的内容？", default=True):
        print_info(
            "跳过迁移。稍后可运行：hermes claw migrate --dry-run"
        )
        return False

    # Ensure config.yaml exists before migration tries to read it
    config_path = get_config_path()
    if not config_path.exists():
        save_config(load_config())

    # Load the migration module
    try:
        mod = _load_openclaw_migration_module()
        if mod is None:
            print_warning("无法加载迁移脚本。")
            return False
    except Exception as e:
        print_warning(f"无法加载迁移脚本：{e}")
        logger.debug("OpenClaw migration module load error", exc_info=True)
        return False

    # ── Phase 1: Dry-run preview ──
    try:
        selected = mod.resolve_selected_options(None, None, preset="full")
        dry_migrator = mod.Migrator(
            source_root=openclaw_dir.resolve(),
            target_root=hermes_home.resolve(),
            execute=False,  # dry-run — no files modified
            workspace_target=None,
            overwrite=True,  # show everything including conflicts
            migrate_secrets=True,
            output_dir=None,
            selected_options=selected,
            preset_name="full",
        )
        preview_report = dry_migrator.migrate()
    except Exception as e:
        print_warning(f"迁移预览失败：{e}")
        logger.debug("OpenClaw migration preview error", exc_info=True)
        return False

    # Display the full preview
    preview_summary = preview_report.get("summary", {})
    preview_count = preview_summary.get("migrated", 0)

    if preview_count == 0:
        print()
        print_info("无需从 OpenClaw 导入。")
        return False

    print()
    print_header(f"迁移预览 — 将导入 {preview_count} 项")
    print_info("尚未进行任何更改。请查看以下列表：")
    print()
    _print_migration_preview(preview_report)

    # ── Phase 2: Confirm and execute ──
    if not prompt_yes_no("继续执行迁移？", default=False):
        print_info(
            "迁移已取消。稍后可运行：hermes claw migrate"
        )
        print_info(
            "使用 --dry-run 再次预览，或使用 --preset minimal 进行轻量导入。"
        )
        return False

    # Execute the migration — overwrite=False so existing Hermes configs are
    # preserved. The user saw the preview; conflicts are skipped by default.
    try:
        migrator = mod.Migrator(
            source_root=openclaw_dir.resolve(),
            target_root=hermes_home.resolve(),
            execute=True,
            workspace_target=None,
            overwrite=False,  # preserve existing Hermes config
            migrate_secrets=True,
            output_dir=None,
            selected_options=selected,
            preset_name="full",
        )
        report = migrator.migrate()
    except Exception as e:
        print_warning(f"迁移失败：{e}")
        logger.debug("OpenClaw migration error", exc_info=True)
        return False

    # Print final summary
    summary = report.get("summary", {})
    migrated = summary.get("migrated", 0)
    skipped = summary.get("skipped", 0)
    conflicts = summary.get("conflict", 0)
    errors = summary.get("error", 0)

    print()
    if migrated:
        print_success(f"已从 OpenClaw 导入 {migrated} 项。")
    if conflicts:
        print_info(f"跳过了在 Hermes 中已存在的 {conflicts} 项（使用 hermes claw migrate --overwrite 强制覆盖）。")
    if skipped:
        print_info(f"跳过 {skipped} 项（未找到或未更改）。")
    if errors:
        print_warning(f"{errors} 项有错误 — 请检查迁移报告。")

    output_dir = report.get("output_dir")
    if output_dir:
        print_info(f"完整报告已保存至：{output_dir}")

    print_success("迁移完成！继续安装...")
    return True


# =============================================================================
# Main Wizard Orchestrator
# =============================================================================

SETUP_SECTIONS = [
    ("model", "模型与提供商", setup_model_provider),
    ("tts", "语音合成", setup_tts),
    ("terminal", "终端后端", setup_terminal_backend),
    ("gateway", "消息平台（网关）", setup_gateway),
    ("tools", "工具", setup_tools),
    ("agent", "代理设置", setup_agent_settings),
]


def run_setup_wizard(args):
    """Run the interactive setup wizard.

    Supports full, quick, and section-specific setup:
      hermes setup           — full or quick (auto-detected)
      hermes setup model     — just model/provider
      hermes setup tts       — just text-to-speech
      hermes setup terminal  — just terminal backend
      hermes setup gateway   — just messaging platforms
      hermes setup tools     — just tool configuration
      hermes setup agent     — just agent settings
    """
    from hermes_cli.config import is_managed, managed_error
    if is_managed():
        managed_error("run setup wizard")
        return
    ensure_hermes_home()

    reset_requested = bool(getattr(args, "reset", False))
    if reset_requested:
        save_config(copy.deepcopy(DEFAULT_CONFIG))
        print_success("配置已重置为默认值。")

    reconfigure_requested = bool(getattr(args, "reconfigure", False))
    quick_requested = bool(getattr(args, "quick", False))

    config = load_config()
    hermes_home = get_hermes_home()

    # Back up existing config before setup modifies it (#3522)
    config_path = get_config_path()
    if config_path.exists():
        from datetime import datetime as _dt
        _backup_path = config_path.with_suffix(
            f".yaml.bak.{_dt.now().strftime('%Y%m%d_%H%M%S')}"
        )
        try:
            import shutil
            shutil.copy2(config_path, _backup_path)
        except Exception:
            _backup_path = None
    else:
        _backup_path = None

    # Detect non-interactive environments (headless SSH, Docker, CI/CD)
    non_interactive = getattr(args, 'non_interactive', False)
    if not non_interactive and not is_interactive_stdin():
        non_interactive = True

    if non_interactive:
        print_noninteractive_setup_guidance(
            "Running in a non-interactive environment (no TTY detected)."
        )
        return

    # Check if a specific section was requested
    section = getattr(args, "section", None)
    if section:
        for key, label, func in SETUP_SECTIONS:
            if key == section:
                print()
                print(
                    color(
                        "┌─────────────────────────────────────────────────────────┐",
                        Colors.MAGENTA,
                    )
                )
                print(color(f"│     ⚕ Hermes Setup — {label:<34s} │", Colors.MAGENTA))
                print(
                    color(
                        "└─────────────────────────────────────────────────────────┘",
                        Colors.MAGENTA,
                    )
                )
                func(config)
                save_config(config)
                print()
                print_success(f"{label} configuration complete!")
                return

        print_error(f"未知的安装章节：{section}")
        print_info(f"可用章节：{', '.join(k for k, _, _ in SETUP_SECTIONS)}")
        return

    # Check if this is an existing installation with a provider configured
    from hermes_cli.auth import get_active_provider

    active_provider = get_active_provider()
    is_existing = (
        bool(get_env_value("OPENROUTER_API_KEY"))
        or bool(get_env_value("OPENAI_BASE_URL"))
        or active_provider is not None
    )

    print()
    print(
        color(
            "┌─────────────────────────────────────────────────────────┐",
            Colors.MAGENTA,
        )
    )
    print(
        color(
            "│             ⚕ Hermes 代理安装向导                   │", Colors.MAGENTA
        )
    )
    print(
        color(
            "├─────────────────────────────────────────────────────────┤",
            Colors.MAGENTA,
        )
    )
    print(
        color(
            "│  让我们配置你的 Hermes 代理安装。                    │", Colors.MAGENTA
        )
    )
    print(
        color(
            "│  随时按 Ctrl+C 退出。                               │", Colors.MAGENTA
        )
    )
    print(
        color(
            "└─────────────────────────────────────────────────────────┘",
            Colors.MAGENTA,
        )
    )

    migration_ran = False

    if is_existing:
        # Existing install — default is the full-wizard reconfigure flow.
        # Every prompt shows the current value as its default, so pressing
        # Enter keeps it.  Opt into `--quick` for the narrow "just fill in
        # missing items" flow (useful after a partial OpenClaw migration
        # or when a required API key got cleared).
        if quick_requested:
            _run_quick_setup(config, hermes_home)
            return

        print()
        print_header("重新配置")
        print_success("你已经配置了 Hermes。")
        print_info("运行完整向导 — 每个提示都会显示你当前的值。")
        print_info("回车保留，或输入新值进行更改。")
        print_info("")
        print_info("提示：使用 'hermes setup model|terminal|")
        print_info("     gateway|tools' 直接跳转到对应章节，或使用 --quick 仅补充缺失项。")
        # Fall through to the "Full Setup — run all sections" block below.
        # --reconfigure is now the default on existing installs; the flag
        # is preserved for backwards compatibility but is a no-op here.
    else:
        # ── First-Time Setup ──
        print()

        # --reconfigure / --quick on a fresh install are meaningless — fall
        # through to the normal first-time flow.
        if reconfigure_requested or quick_requested:
            print_info("未找到现有配置 — 运行首次安装。")
            print()

        # Offer OpenClaw migration before configuration begins
        migration_ran = _offer_openclaw_migration(hermes_home)
        if migration_ran:
            config = load_config()

        setup_mode = prompt_choice("你希望如何设置 Hermes？", [
            "快速安装 — 提供商、模型和消息（推荐）",
            "完整安装 — 配置所有内容",
        ], 0)

        if setup_mode == 0:
            _run_first_time_quick_setup(config, hermes_home, is_existing)
            return

    # ── Full Setup — run all sections ──
    print_header("配置位置")
    print_info(f"配置文件：{get_config_path()}")
    print_info(f"密钥文件：{get_env_path()}")
    print_info(f"数据文件夹：{hermes_home}")
    print_info(f"安装目录：{PROJECT_ROOT}")
    print()
    print_info("你可以直接编辑这些文件或使用 'hermes config edit'")

    if migration_ran:
        print()
        print_info("设置已从 OpenClaw 导入。")
        print_info("以下各章节将显示导入的内容 — 回车保留，")
        print_info("或在需要时选择重新配置。")

    # Section 1: Model & Provider
    if not (migration_ran and _skip_configured_section(config, "model", "模型与提供商")):
        setup_model_provider(config)

    # Section 2: Terminal Backend
    if not (migration_ran and _skip_configured_section(config, "terminal", "终端后端")):
        setup_terminal_backend(config)

    # Section 3: Agent Settings
    if not (migration_ran and _skip_configured_section(config, "agent", "代理设置")):
        setup_agent_settings(config)

    # Section 4: Messaging Platforms
    if not (migration_ran and _skip_configured_section(config, "gateway", "消息平台")):
        setup_gateway(config)

    # Section 5: Tools
    if not (migration_ran and _skip_configured_section(config, "tools", "工具")):
        setup_tools(config, first_install=not is_existing)

    # Save and show summary
    save_config(config)
    if _backup_path and _backup_path.exists():
        print_info(f"之前的配置已备份至：{_backup_path}")
        print_info("如果安装更改了你自定义的值，可通过以下方式恢复：")
        print_info(f"  cp {_backup_path} {config_path}")
    _print_setup_summary(config, hermes_home)


def _run_first_time_quick_setup(config: dict, hermes_home, is_existing: bool):
    """Streamlined first-time setup: provider, model, terminal & messaging.

    Applies sensible defaults for TTS (Edge), agent settings, and tools —
    the user can customize later via ``hermes setup <section>``.
    """
    # Step 1: Model & Provider (essential — skips rotation/vision/TTS)
    setup_model_provider(config, quick=True)

    # Step 2: Terminal Backend — where commands run is a core decision
    setup_terminal_backend(config)

    # Step 3: Apply defaults for everything else
    _apply_default_agent_settings(config)

    save_config(config)

    # Step 4: Offer messaging gateway setup
    print()
    gateway_choice = prompt_choice(
        "连接消息平台？（Telegram、Discord 等）",
        [
            "立即设置消息（推荐）",
            "跳过 — 稍后用 'hermes setup gateway' 设置",
        ],
        0,
    )

    if gateway_choice == 0:
        setup_gateway(config)
        save_config(config)

    print()
    print_success("安装完成！准备就绪。")
    print()
    print_info("  配置所有设置：hermes setup")
    if gateway_choice != 0:
        print_info("  连接 Telegram/Discord：hermes setup gateway")
    print()

    _print_setup_summary(config, hermes_home)


def _run_quick_setup(config: dict, hermes_home):
    """Quick setup — only configure items that are missing."""
    from hermes_cli.config import (
        get_missing_env_vars,
        get_missing_config_fields,
        check_config_version,
    )

    print()
    print_header("快速安装 — 仅补充缺失项")

    # Check what's missing
    missing_required = [
        v for v in get_missing_env_vars(required_only=False) if v.get("is_required")
    ]
    missing_optional = [
        v for v in get_missing_env_vars(required_only=False) if not v.get("is_required")
    ]
    missing_config = get_missing_config_fields()
    current_ver, latest_ver = check_config_version()

    has_anything_missing = (
        missing_required
        or missing_optional
        or missing_config
        or current_ver < latest_ver
    )

    if not has_anything_missing:
        print_success("一切已配置！无需操作。")
        print()
        print_info("运行 'hermes setup' 并选择 '完整安装' 重新配置，")
        print_info("或从菜单中选择特定章节。")
        return

    # Handle missing required env vars
    if missing_required:
        print()
        print_info(f"缺失 {len(missing_required)} 项必需设置：")
        for var in missing_required:
            print(f"     • {var['name']}")
        print()

        for var in missing_required:
            print()
            print(color(f"  {var['name']}", Colors.CYAN))
            print_info(f"  {var.get('description', '')}")
            if var.get("url"):
                print_info(f"  获取密钥：{var['url']}")

            if var.get("password"):
                value = prompt(f"  {var.get('prompt', var['name'])}", password=True)
            else:
                value = prompt(f"  {var.get('prompt', var['name'])}")

            if value:
                save_env_value(var["name"], value)
                print_success(f"  已保存 {var['name']}")
            else:
                print_warning(f"  已跳过 {var['name']}")

    # Split missing optional vars by category
    missing_tools = [v for v in missing_optional if v.get("category") == "tool"]
    missing_messaging = [
        v
        for v in missing_optional
        if v.get("category") == "messaging" and not v.get("advanced")
    ]

    # ── Tool API keys (checklist) ──
    if missing_tools:
        print()
        print_header("工具 API 密钥")

        checklist_labels = []
        for var in missing_tools:
            tools = var.get("tools", [])
            tools_str = f" → {', '.join(tools[:2])}" if tools else ""
            checklist_labels.append(f"{var.get('description', var['name'])}{tools_str}")

        selected_indices = prompt_checklist(
            "你想配置哪些工具？",
            checklist_labels,
        )

        for idx in selected_indices:
            var = missing_tools[idx]
            _prompt_api_key(var)

    # ── Messaging platforms (checklist then prompt for selected) ──
    if missing_messaging:
        print()
        print_header("消息平台")
        print_info("连接 Hermes 到消息应用，随时随地聊天。")
        print_info("稍后可通过 'hermes setup gateway' 配置。")

        # Group by platform (preserving order)
        platform_order = []
        platforms = {}
        for var in missing_messaging:
            name = var["name"]
            if "TELEGRAM" in name:
                plat = "Telegram"
            elif "DISCORD" in name:
                plat = "Discord"
            elif "SLACK" in name:
                plat = "Slack"
            else:
                continue
            if plat not in platforms:
                platform_order.append(plat)
            platforms.setdefault(plat, []).append(var)

        platform_labels = [
            {
                "Telegram": "📱 Telegram",
                "Discord": "💬 Discord",
                "Slack": "💼 Slack",
            }.get(p, p)
            for p in platform_order
        ]

        selected_indices = prompt_checklist(
            "你想设置哪些平台？",
            platform_labels,
        )

        for idx in selected_indices:
            plat = platform_order[idx]
            vars_list = platforms[plat]
            emoji = {"Telegram": "📱", "Discord": "💬", "Slack": "💼"}.get(plat, "")
            print()
            print(color(f"  ─── {emoji} {plat} ───", Colors.CYAN))
            print()
            for var in vars_list:
                print_info(f"  {var.get('description', '')}")
                if var.get("url"):
                    print_info(f"  {var['url']}")
                if var.get("password"):
                    value = prompt(f"  {var.get('prompt', var['name'])}", password=True)
                else:
                    value = prompt(f"  {var.get('prompt', var['name'])}")
                if value:
                    save_env_value(var["name"], value)
                    print_success("  ✓ 已保存")
                else:
                    print_warning("  已跳过")
                print()

    # Handle missing config fields
    if missing_config:
        print()
        print_info(
            f"正在添加 {len(missing_config)} 个新的配置选项（使用默认值）..."
        )
        for field in missing_config:
            print_success(f"  已添加 {field['key']} = {field['default']}")

        # Update config version
        config["_config_version"] = latest_ver
        save_config(config)

    # Jump to summary
    _print_setup_summary(config, hermes_home)

#!/bin/bash
# ============================================================================
# Nermes Agent 安装程序
# ============================================================================
# Linux、macOS 和 Android/Termux 的安装脚本。
# 桌面/服务器安装使用 uv，Termux 使用 Python 标准库 venv + pip。
#
# 用法：
#   curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
#
# 或带选项：
#   curl -fsSL ... | bash -s -- --no-venv --skip-setup
#
# ============================================================================

set -e

# Guard against environment leakage when the installer is launched from another
# Python-driven tool session (e.g. Hermes terminal tool). A pre-set PYTHONPATH
# can force pip/entrypoints to import a different checkout than the one being
# installed, which makes fresh installs appear broken or stale.
if [ -n "${PYTHONPATH:-}" ]; then
    echo "⚠ 安装期间忽略继承的 PYTHONPATH，以避免模块遮蔽"
    unset PYTHONPATH
fi
if [ -n "${PYTHONHOME:-}" ]; then
    echo "⚠ 安装期间忽略继承的 PYTHONHOME"
    unset PYTHONHOME
fi

# Prevent uv from discovering config files (uv.toml, pyproject.toml) from the
# wrong user's home directory when running under sudo -u <user>.  See #21269.
export UV_NO_CONFIG=1

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
# --- 中国镜像（可通过环境变量覆盖） ---
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
export PIP_INDEX_URL
# uv 自动读取 PIP_INDEX_URL；显式设置 UV_INDEX_URL 以防万一
export UV_INDEX_URL="${UV_INDEX_URL:-$PIP_INDEX_URL}"
# npm
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmmirror.com}"
export NPM_REGISTRY

REPO_URL_SSH="git@github.com:elliotmessi/nermes-core.git"
REPO_URL_HTTPS="https://github.com/elliotmessi/nermes-core.git"
NERMES_HOME="${NERMES_HOME:-$HOME/.nermes}"
# INSTALL_DIR is resolved AFTER arg parsing and OS detection so we can pick an
# FHS-style layout for root installs.  Track whether the user gave us an
# explicit directory — if so we never override it.
if [ -n "${NERMES_INSTALL_DIR:-}" ]; then
    INSTALL_DIR="$NERMES_INSTALL_DIR"
    INSTALL_DIR_EXPLICIT=true
else
    INSTALL_DIR=""
    INSTALL_DIR_EXPLICIT=false
fi
PYTHON_VERSION="3.11"
NODE_VERSION="22"

# FHS-style root install layout (set by resolve_install_layout when applicable):
#   code at /usr/local/lib/nermes-agent, command at /usr/local/bin/nermes,
#   data still at /root/.nermes (NERMES_HOME).  Matches Claude Code / Codex CLI
#   and keeps Docker bind-mounted /root/ volumes lean.
ROOT_FHS_LAYOUT=false
DETECTED_BROWSER_EXECUTABLE=""

# Options
USE_VENV=true
RUN_SETUP=true
SKIP_BROWSER=false
BRANCH="main"
ENSURE_DEPS=""
POSTINSTALL_MODE=false

# Detect non-interactive mode (e.g. curl | bash)
# When stdin is not a terminal, read -p will fail with EOF,
# causing set -e to silently abort the entire script.
if [ -t 0 ]; then
    IS_INTERACTIVE=true
else
    IS_INTERACTIVE=false
fi

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-venv)
            USE_VENV=false
            shift
            ;;
        --skip-setup)
            RUN_SETUP=false
            shift
            ;;
        --skip-browser|--no-playwright)
            SKIP_BROWSER=true
            shift
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --dir)
            INSTALL_DIR="$2"
            INSTALL_DIR_EXPLICIT=true
            shift 2
            ;;
        --nermes-home)
            NERMES_HOME="$2"
            shift 2
            ;;
        --ensure)
            ENSURE_DEPS="$2"
            shift 2
            ;;
        --postinstall)
            POSTINSTALL_MODE=true
            shift
            ;;
        -h|--help)
            echo "Nermes Agent 安装程序"
            echo ""
            echo "用法：install.sh [选项]"
            echo ""
            echo "选项："
            echo "  --no-venv      不创建虚拟环境"
            echo "  --skip-setup   跳过交互式设置向导"
            echo "  --skip-browser 跳过 Playwright/Chromium 安装（浏览器工具将不可用）"
            echo "  --branch NAME  要安装的 Git 分支（默认：main）"
            echo "  --dir PATH     安装目录"
            echo "                   默认（非 root）：    ~/.nermes/nermes-agent"
            echo "                   默认（root, Linux）：/usr/local/lib/nermes-agent"
            echo "  --nermes-home PATH  数据目录（默认：~/.nermes，或 \$NERMES_HOME）"
            echo "  -h, --help     显示此帮助"
            echo ""
            echo "说明："
            echo "  以 root 身份在 Linux 上运行时，Nermes 将代码安装到"
            echo "  /usr/local/lib/nermes-agent，并将命令链接到"
            echo "  /usr/local/bin/nermes（FHS 布局 — 与 Claude Code / Codex CLI 一致）。"
            echo "  数据、配置、会话和日志仍位于 \$NERMES_HOME"
            echo "  （默认 /root/.nermes）。这有助于保持 Docker 挂载卷"
            echo "  简洁，并确保命令在所有 shell 的 PATH 中。"
            echo "  已安装在 \$NERMES_HOME/nermes-agent 的现有安装将原地保留。"
            echo "  --ensure DEPS  仅安装指定依赖（逗号分隔）"
            echo "                  支持：node, browser, ripgrep, ffmpeg"
            echo "                  不克隆仓库或创建虚拟环境"
            echo "  --postinstall  仅运行安装后设置（适用于 pip 用户）"
            echo "                  安装可选依赖 + 运行 nermes setup"
            echo "                  不克隆仓库或创建虚拟环境"
            exit 0
            ;;
        *)
            echo "未知选项：$1"
            exit 1
            ;;
    esac
done

# ============================================================================
# Helper functions
# ============================================================================

print_banner() {
    echo ""
    echo -e "${MAGENTA}${BOLD}"
    echo "┌─────────────────────────────────────────────────────────┐"
    echo "│             ⚕ Nermes Agent 安装程序                     │"
    echo "├─────────────────────────────────────────────────────────┤"
    echo "│  Nous Research 开源 AI Agent                           │"
    echo "└─────────────────────────────────────────────────────────┘"
    echo -e "${NC}"
}

log_info() {
    echo -e "${CYAN}→${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

prompt_yes_no() {
    local question="$1"
    local default="${2:-yes}"
    local prompt_suffix
    local answer=""

    # Use case patterns (not ${var,,}) so this works on bash 3.2 (macOS /bin/bash).
    case "$default" in
        [yY]|[yY][eE][sS]|[tT][rR][uU][eE]|1) prompt_suffix="[Y/n]" ;;
        *) prompt_suffix="[y/N]" ;;
    esac

    if [ "$IS_INTERACTIVE" = true ]; then
        read -r -p "$question $prompt_suffix " answer || answer=""
    elif [ -r /dev/tty ] && [ -w /dev/tty ]; then
        printf "%s %s " "$question" "$prompt_suffix" > /dev/tty
        IFS= read -r answer < /dev/tty || answer=""
    else
        answer=""
    fi

    answer="${answer#"${answer%%[![:space:]]*}"}"
    answer="${answer%"${answer##*[![:space:]]}"}"

    if [ -z "$answer" ]; then
        case "$default" in
            [yY]|[yY][eE][sS]|[tT][rR][uU][eE]|1) return 0 ;;
            *) return 1 ;;
        esac
    fi

    case "$answer" in
        [yY]|[yY][eE][sS]) return 0 ;;
        *) return 1 ;;
    esac
}

is_termux() {
    [ -n "${TERMUX_VERSION:-}" ] || [[ "${PREFIX:-}" == *"com.termux/files/usr"* ]]
}

# Decide where the repo checkout + venv live, and where the `nermes` command
# symlink goes.  Called after detect_os so $OS/$DISTRO are known.
#
# Defaults:
#   - Non-root, any OS:       INSTALL_DIR = $NERMES_HOME/nermes-agent
#                             command link in $HOME/.local/bin
#   - Termux (any uid):       INSTALL_DIR = $NERMES_HOME/nermes-agent
#                             command link in $PREFIX/bin (already on PATH)
#   - Root on Linux (new):    INSTALL_DIR = /usr/local/lib/nermes-agent
#                             command link in /usr/local/bin
#                             (unless a legacy install already exists at
#                              $NERMES_HOME/nermes-agent — then preserve it)
#
# Always no-op when the user set --dir or $NERMES_INSTALL_DIR.
resolve_install_layout() {
    if [ "$INSTALL_DIR_EXPLICIT" = true ]; then
        log_info "安装目录：$INSTALL_DIR（用户指定）"
        return 0
    fi

    # Termux: package manager manages /data/data/..., keep code in NERMES_HOME.
    if is_termux; then
        INSTALL_DIR="$NERMES_HOME/nermes-agent"
        return 0
    fi

    # Root on Linux: prefer FHS layout unless a legacy install already exists.
    # macOS root installs keep the legacy layout because /usr/local/ on macOS
    # is Homebrew territory and we don't want to fight that.
    if [ "$OS" = "linux" ] && [ "$(id -u)" -eq 0 ]; then
        if [ -d "$NERMES_HOME/nermes-agent/.git" ]; then
            INSTALL_DIR="$NERMES_HOME/nermes-agent"
            log_info "检测到已有安装位于 $INSTALL_DIR — 保留旧版布局"
            log_info "  （新的 root 安装将使用 /usr/local/lib/nermes-agent）"
            return 0
        fi
        INSTALL_DIR="/usr/local/lib/nermes-agent"
        ROOT_FHS_LAYOUT=true
        log_info "Linux 上以 root 安装 — 使用 FHS 布局"
        log_info "  代码：    $INSTALL_DIR"
        log_info "  命令：    /usr/local/bin/nermes"
        log_info "  数据：    $NERMES_HOME（不变）"
        return 0
    fi

    # Default: non-root, non-Termux → legacy user-scoped layout.
    INSTALL_DIR="$NERMES_HOME/nermes-agent"
}

get_command_link_dir() {
    if is_termux && [ -n "${PREFIX:-}" ]; then
        echo "$PREFIX/bin"
    elif [ "$ROOT_FHS_LAYOUT" = true ]; then
        echo "/usr/local/bin"
    else
        echo "$HOME/.local/bin"
    fi
}

get_command_link_display_dir() {
    if is_termux && [ -n "${PREFIX:-}" ]; then
        echo '$PREFIX/bin'
    elif [ "$ROOT_FHS_LAYOUT" = true ]; then
        echo '/usr/local/bin'
    else
        echo '~/.local/bin'
    fi
}

get_hermes_command_path() {
    local link_dir
    link_dir="$(get_command_link_dir)"
    if [ -x "$link_dir/nermes" ]; then
        echo "$link_dir/nermes"
    else
        echo "nermes"
    fi
}

# ============================================================================
# System detection
# ============================================================================

detect_os() {
    case "$(uname -s)" in
        Linux*)
            if is_termux; then
                OS="android"
                DISTRO="termux"
            else
                OS="linux"
                if [ -f /etc/os-release ]; then
                    . /etc/os-release
                    DISTRO="$ID"
                else
                    DISTRO="unknown"
                fi
            fi
            ;;
        Darwin*)
            OS="macos"
            DISTRO="macos"
            ;;
        CYGWIN*|MINGW*|MSYS*)
            OS="windows"
            DISTRO="windows"
            log_error "检测到 Windows。请使用 PowerShell 安装程序："
            log_info "  iex (irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1)"
            exit 1
            ;;
        *)
            OS="unknown"
            DISTRO="unknown"
            log_warn "未知的操作系统"
            ;;
    esac

    log_success "检测到：$OS（$DISTRO）"
}

# ============================================================================
# Dependency checks
# ============================================================================

install_uv() {
    if [ "$DISTRO" = "termux" ]; then
        log_info "检测到 Termux — 使用 Python 标准库 venv + pip 替代 uv"
        UV_CMD=""
        return 0
    fi

    log_info "检查 uv 包管理器..."

    # Check common locations for uv
    if command -v uv &> /dev/null; then
        UV_CMD="uv"
        UV_VERSION=$($UV_CMD --version 2>/dev/null)
        log_success "找到 uv（$UV_VERSION）"
        return 0
    fi

    # Check ~/.local/bin (default uv install location) even if not on PATH yet
    if [ -x "$HOME/.local/bin/uv" ]; then
        UV_CMD="$HOME/.local/bin/uv"
        UV_VERSION=$($UV_CMD --version 2>/dev/null)
        log_success "在 ~/.local/bin 找到 uv（$UV_VERSION）"
        return 0
    fi

    # Check ~/.cargo/bin (alternative uv install location)
    if [ -x "$HOME/.cargo/bin/uv" ]; then
        UV_CMD="$HOME/.cargo/bin/uv"
        UV_VERSION=$($UV_CMD --version 2>/dev/null)
        log_success "在 ~/.cargo/bin 找到 uv（$UV_VERSION）"
        return 0
    fi

    # Install uv
    log_info "正在安装 uv（快速 Python 包管理器）..."
    # Capture installer output so a failure shows the user WHY (network,
    # glibc mismatch on old distros, missing curl, ~/.local/bin not
    # writable, disk full, corp proxy / TLS interception, etc.) instead
    # of the previous "✗ Failed to install uv" with zero diagnostic.
    #
    # Two-stage: download the installer, then run it.  Piping
    # `curl | sh` masks curl failures (sh exits 0 on empty stdin)
    # and conflates network errors with installer errors.
    local _uv_install_log _uv_installer
    _uv_install_log="$(mktemp 2>/dev/null || echo "/tmp/hermes-uv-install.$$.log")"
    _uv_installer="$(mktemp 2>/dev/null || echo "/tmp/hermes-uv-installer.$$.sh")"
    if ! curl -LsSf https://astral.sh/uv/install.sh -o "$_uv_installer" 2>"$_uv_install_log"; then
        log_error "下载 uv 安装程序失败（https://astral.sh/uv/install.sh）"
        log_info "curl 输出："
        sed 's/^/    /' "$_uv_install_log" >&2
        log_info "手动安装：https://docs.astral.sh/uv/getting-started/installation/"
        rm -f "$_uv_install_log" "$_uv_installer"
        exit 1
    fi
    if sh "$_uv_installer" >>"$_uv_install_log" 2>&1; then
        rm -f "$_uv_installer"
        # uv installs to ~/.local/bin by default
        if [ -x "$HOME/.local/bin/uv" ]; then
            UV_CMD="$HOME/.local/bin/uv"
        elif [ -x "$HOME/.cargo/bin/uv" ]; then
            UV_CMD="$HOME/.cargo/bin/uv"
        elif command -v uv &> /dev/null; then
            UV_CMD="uv"
        else
            log_error "uv 安装程序报告成功，但未在 PATH 中找到可执行文件"
            log_info "安装程序输出："
            sed 's/^/    /' "$_uv_install_log" >&2
            log_info "尝试将 ~/.local/bin 添加到 PATH 后重新运行"
            rm -f "$_uv_install_log"
            exit 1
        fi
        rm -f "$_uv_install_log"
        UV_VERSION=$($UV_CMD --version 2>/dev/null)
        log_success "uv 已安装（$UV_VERSION）"
    else
        log_error "安装 uv 失败"
        log_info "安装程序输出："
        sed 's/^/    /' "$_uv_install_log" >&2
        log_info "手动安装：https://docs.astral.sh/uv/getting-started/installation/"
        rm -f "$_uv_install_log" "$_uv_installer"
        exit 1
    fi
}

check_python() {
    if [ "$DISTRO" = "termux" ]; then
        log_info "检查 Termux Python..."
        if command -v python >/dev/null 2>&1; then
            PYTHON_PATH="$(command -v python)"
            if "$PYTHON_PATH" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
                PYTHON_FOUND_VERSION="$("$PYTHON_PATH" --version 2>/dev/null)"
                log_success "找到 Python：$PYTHON_FOUND_VERSION"
                return 0
            fi
        fi

        log_info "通过 pkg 安装 Python..."
        pkg install -y python >/dev/null
        PYTHON_PATH="$(command -v python)"
        PYTHON_FOUND_VERSION="$("$PYTHON_PATH" --version 2>/dev/null)"
        log_success "Python 已安装：$PYTHON_FOUND_VERSION"
        return 0
    fi

    log_info "检查 Python $PYTHON_VERSION..."

    # Let uv handle Python — it can download and manage Python versions
    # First check if a suitable Python is already available
    if PYTHON_PATH="$("$UV_CMD" python find "$PYTHON_VERSION" 2>/dev/null)"; then
        PYTHON_FOUND_VERSION="$("$PYTHON_PATH" --version 2>/dev/null)"
        log_success "找到 Python：$PYTHON_FOUND_VERSION"
        return 0
    fi

    # Python not found — use uv to install it (no sudo needed!)
    log_info "未找到 Python $PYTHON_VERSION，通过 uv 安装..."
    if "$UV_CMD" python install "$PYTHON_VERSION"; then
        PYTHON_PATH="$("$UV_CMD" python find "$PYTHON_VERSION")"
        PYTHON_FOUND_VERSION="$("$PYTHON_PATH" --version 2>/dev/null)"
        log_success "Python 已安装：$PYTHON_FOUND_VERSION"
    else
        log_error "安装 Python $PYTHON_VERSION 失败"
        log_info "请手动安装 Python $PYTHON_VERSION，然后重新运行此脚本"
        exit 1
    fi
}

check_git() {
    log_info "检查 Git..."

    if command -v git &> /dev/null; then
        GIT_VERSION=$(git --version | awk '{print $3}')
        log_success "找到 Git $GIT_VERSION"
        return 0
    fi

    log_error "未找到 Git"

    if [ "$DISTRO" = "termux" ]; then
        log_info "通过 pkg 安装 Git..."
        pkg install -y git >/dev/null
        if command -v git >/dev/null 2>&1; then
            GIT_VERSION=$(git --version | awk '{print $3}')
            log_success "Git $GIT_VERSION 已安装"
            return 0
        fi
    fi

    log_info "请安装 Git："

    case "$OS" in
        linux)
            case "$DISTRO" in
                ubuntu|debian)
                    log_info "  sudo apt update && sudo apt install git"
                    ;;
                fedora)
                    log_info "  sudo dnf install git"
                    ;;
                arch)
                    log_info "  sudo pacman -S git"
                    ;;
                *)
                    log_info "  请使用您的包管理器安装 git"
                    ;;
            esac
            ;;
        android)
            log_info "  pkg install git"
            ;;
        macos)
            log_info "  xcode-select --install"
            log_info "  或：brew install git"
            ;;
    esac

    exit 1
}

check_node() {
    log_info "检查 Node.js（用于浏览器工具）..."

    if command -v node &> /dev/null; then
        local found_ver=$(node --version)
        log_success "找到 Node.js $found_ver"
        HAS_NODE=true
        return 0
    fi

    # Check our own managed install from a previous run
    if [ -x "$NERMES_HOME/node/bin/node" ]; then
        export PATH="$NERMES_HOME/node/bin:$PATH"
        local found_ver=$("$NERMES_HOME/node/bin/node" --version)
        log_success "找到 Node.js $found_ver（Nermes 管理）"
        HAS_NODE=true
        return 0
    fi

    if [ "$DISTRO" = "termux" ]; then
        log_info "未找到 Node.js — 通过 pkg 安装 Node.js..."
    else
        log_info "未找到 Node.js — 安装 Node.js $NODE_VERSION LTS..."
    fi
    install_node
}

install_node() {
    if [ "$DISTRO" = "termux" ]; then
        log_info "通过 pkg 安装 Node.js..."
        if pkg install -y nodejs >/dev/null; then
            local installed_ver
            installed_ver=$(node --version 2>/dev/null)
            log_success "Node.js $installed_ver 已通过 pkg 安装"
            HAS_NODE=true
        else
            log_warn "通过 pkg 安装 Node.js 失败"
            HAS_NODE=false
        fi
        return 0
    fi

    local arch=$(uname -m)
    local node_arch
    case "$arch" in
        x86_64)        node_arch="x64"    ;;
        aarch64|arm64) node_arch="arm64"  ;;
        armv7l)        node_arch="armv7l" ;;
        *)
            log_warn "不支持的架构（$arch），无法自动安装 Node.js"
            log_info "手动安装：https://nodejs.org/en/download/"
            HAS_NODE=false
            return 0
            ;;
    esac

    local node_os
    case "$OS" in
        linux) node_os="linux"  ;;
        macos) node_os="darwin" ;;
        *)
            log_warn "不支持的操作系统，无法自动安装 Node.js"
            HAS_NODE=false
            return 0
            ;;
    esac

    # Resolve the latest v22.x.x tarball name from the index page
    local index_url="https://nodejs.org/dist/latest-v${NODE_VERSION}.x/"
    local tarball_name
    tarball_name=$(curl -fsSL "$index_url" \
        | grep -oE "node-v${NODE_VERSION}\\.[0-9]+\\.[0-9]+-${node_os}-${node_arch}\\.tar\\.xz" \
        | head -1)

    # Fallback to .tar.gz if .tar.xz not available
    if [ -z "$tarball_name" ]; then
        tarball_name=$(curl -fsSL "$index_url" \
            | grep -oE "node-v${NODE_VERSION}\\.[0-9]+\\.[0-9]+-${node_os}-${node_arch}\\.tar\\.gz" \
            | head -1)
    fi

    if [ -z "$tarball_name" ]; then
        log_warn "找不到 $node_os-$node_arch 架构的 Node.js $NODE_VERSION 二进制包"
        log_info "手动安装：https://nodejs.org/en/download/"
        HAS_NODE=false
        return 0
    fi

    local download_url="${index_url}${tarball_name}"
    local tmp_dir
    tmp_dir=$(mktemp -d)

    log_info "正在下载 $tarball_name..."
    if ! curl -fsSL "$download_url" -o "$tmp_dir/$tarball_name"; then
        log_warn "下载失败"
        rm -rf "$tmp_dir"
        HAS_NODE=false
        return 0
    fi

    log_info "解压到 ~/.nermes/node/..."
    if [[ "$tarball_name" == *.tar.xz ]]; then
        tar xf "$tmp_dir/$tarball_name" -C "$tmp_dir"
    else
        tar xzf "$tmp_dir/$tarball_name" -C "$tmp_dir"
    fi

    local extracted_dir
    extracted_dir=$(ls -d "$tmp_dir"/node-v* 2>/dev/null | head -1)

    if [ ! -d "$extracted_dir" ]; then
        log_warn "解压失败"
        rm -rf "$tmp_dir"
        HAS_NODE=false
        return 0
    fi

    # Place into ~/.nermes/node/ and symlink binaries to ~/.local/bin/
    rm -rf "$NERMES_HOME/node"
    mkdir -p "$NERMES_HOME"
    mv "$extracted_dir" "$NERMES_HOME/node"
    rm -rf "$tmp_dir"

    mkdir -p "$HOME/.local/bin"
    ln -sf "$NERMES_HOME/node/bin/node" "$HOME/.local/bin/node"
    ln -sf "$NERMES_HOME/node/bin/npm"  "$HOME/.local/bin/npm"
    ln -sf "$NERMES_HOME/node/bin/npx"  "$HOME/.local/bin/npx"

    export PATH="$NERMES_HOME/node/bin:$PATH"

    local installed_ver
    installed_ver=$("$NERMES_HOME/node/bin/node" --version 2>/dev/null)
    log_success "Node.js $installed_ver 已安装到 ~/.nermes/node/"
    HAS_NODE=true
}

check_network_prerequisites() {
    log_info "检查网络连接（用于包安装和 Web 工具）..."

    local url
    local failed=false
    local checks=("https://pypi.org/simple/" "https://duckduckgo.com/")

    if ! command -v curl >/dev/null 2>&1; then
        log_warn "未找到 curl；跳过网络连通性检测"
        return 0
    fi

    for url in "${checks[@]}"; do
        if ! curl -fsSI --max-time 8 "$url" >/dev/null 2>&1; then
            failed=true
            log_warn "无法访问 $url"
        fi
    done

    if [ "$failed" = false ]; then
        log_success "网络连接正常"
        return 0
    fi

    if [ "$DISTRO" = "termux" ]; then
        log_warn "Termux 网络前置条件可能不完整。"
        log_info "尝试：pkg install -y ca-certificates curl && pkg update"
        log_info "如果镜像过旧：termux-change-repo"
        log_info "然后测试：curl -I https://pypi.org/simple/ && curl -I https://duckduckgo.com/"
    else
        log_warn "网络检查失败。安装仍可完成，但 Web 搜索和依赖下载可能失败。"
        log_info "如果 pip 安装失败，请检查网络/DNS 后重试。"
    fi
}

install_system_packages() {
    # Detect what's missing
    HAS_RIPGREP=false
    HAS_FFMPEG=false
    local need_ripgrep=false
    local need_ffmpeg=false

    log_info "检查 ripgrep（快速文件搜索）..."
    if command -v rg &> /dev/null; then
        log_success "$(rg --version | head -1) 已找到"
        HAS_RIPGREP=true
    else
        need_ripgrep=true
    fi

    log_info "检查 ffmpeg（TTS 语音消息）..."
    if command -v ffmpeg &> /dev/null; then
        local ffmpeg_ver=$(ffmpeg -version 2>/dev/null | head -1 | awk '{print $3}')
        log_success "ffmpeg $ffmpeg_ver 已找到"
        HAS_FFMPEG=true
    else
        need_ffmpeg=true
    fi

    # Termux always needs the Android build toolchain for the tested pip path,
    # even when ripgrep/ffmpeg are already present.
    if [ "$DISTRO" = "termux" ]; then
        local termux_pkgs=(clang rust make pkg-config libffi openssl ca-certificates curl)
        if [ "$need_ripgrep" = true ]; then
            termux_pkgs+=("ripgrep")
        fi
        if [ "$need_ffmpeg" = true ]; then
            termux_pkgs+=("ffmpeg")
        fi

        log_info "正在安装 Termux 包：${termux_pkgs[*]}"
        if pkg install -y "${termux_pkgs[@]}" >/dev/null; then
            [ "$need_ripgrep" = true ] && HAS_RIPGREP=true && log_success "ripgrep 已安装"
            [ "$need_ffmpeg" = true ]  && HAS_FFMPEG=true  && log_success "ffmpeg 已安装"
            log_success "Termux 构建依赖已安装"
            return 0
        fi

        log_warn "无法自动安装所有 Termux 包"
        log_info "手动安装：pkg install ${termux_pkgs[*]}"
        return 0
    fi

    # Nothing to install — done
    if [ "$need_ripgrep" = false ] && [ "$need_ffmpeg" = false ]; then
        return 0
    fi

    # Build a human-readable description + package list
    local desc_parts=()
    local pkgs=()
    if [ "$need_ripgrep" = true ]; then
        desc_parts+=("ripgrep（用于更快的文件搜索）")
        pkgs+=("ripgrep")
    fi
    if [ "$need_ffmpeg" = true ]; then
        desc_parts+=("ffmpeg（用于 TTS 语音消息）")
        pkgs+=("ffmpeg")
    fi
    local description
    description=$(IFS=" 和 "; echo "${desc_parts[*]}")

    # ── macOS: brew ──
    if [ "$OS" = "macos" ]; then
        if command -v brew &> /dev/null; then
            log_info "通过 Homebrew 安装 ${pkgs[*]}..."
            if brew install "${pkgs[@]}"; then
                [ "$need_ripgrep" = true ] && HAS_RIPGREP=true && log_success "ripgrep 已安装"
                [ "$need_ffmpeg" = true ]  && HAS_FFMPEG=true  && log_success "ffmpeg 已安装"
                return 0
            fi
        fi
        log_warn "无法自动安装（未找到 brew 或安装失败）"
        log_info "手动安装：brew install ${pkgs[*]}"
        return 0
    fi

    # ── Linux: resolve package manager command ──
    local pkg_install=""
    case "$DISTRO" in
        ubuntu|debian) pkg_install="apt install -y"   ;;
        fedora)        pkg_install="dnf install -y"   ;;
        arch)          pkg_install="pacman -S --noconfirm" ;;
    esac

    if [ -n "$pkg_install" ]; then
        local install_cmd="$pkg_install ${pkgs[*]}"

        # Prevent needrestart/whiptail dialogs from blocking non-interactive installs
        case "$DISTRO" in
            ubuntu|debian) export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a ;;
        esac

        # Already root — just install
        if [ "$(id -u)" -eq 0 ]; then
            log_info "正在安装 ${pkgs[*]}..."
            if $install_cmd; then
                [ "$need_ripgrep" = true ] && HAS_RIPGREP=true && log_success "ripgrep 已安装"
                [ "$need_ffmpeg" = true ]  && HAS_FFMPEG=true  && log_success "ffmpeg 已安装"
                return 0
            fi
        # Passwordless sudo — just install
        elif command -v sudo &> /dev/null && sudo -n true 2>/dev/null; then
            log_info "正在安装 ${pkgs[*]}..."
            if sudo DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a $install_cmd; then
                [ "$need_ripgrep" = true ] && HAS_RIPGREP=true && log_success "ripgrep 已安装"
                [ "$need_ffmpeg" = true ]  && HAS_FFMPEG=true  && log_success "ffmpeg 已安装"
                return 0
            fi
        # sudo needs password — ask once for everything
        elif command -v sudo &> /dev/null; then
            if [ "$IS_INTERACTIVE" = true ]; then
                echo ""
                log_info "仅需 sudo 来通过包管理器安装可选系统包（${pkgs[*]}）。"
                log_info "Hermes Agent 本身不需要也不保留 root 权限。"
                if prompt_yes_no "安装 ${description}？（需要 sudo）" "no"; then
                    if sudo DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a $install_cmd; then
                        [ "$need_ripgrep" = true ] && HAS_RIPGREP=true && log_success "ripgrep 已安装"
                        [ "$need_ffmpeg" = true ]  && HAS_FFMPEG=true  && log_success "ffmpeg 已安装"
                        return 0
                    fi
                fi
            elif (: </dev/tty) 2>/dev/null; then
                # Non-interactive (e.g. curl | bash) but a terminal is available.
                # Read the prompt from /dev/tty (same approach the setup wizard uses).
                # Probe by actually opening /dev/tty: a bare existence test passes
                # in Docker builds where the device node is in the mount namespace
                # but opening fails with ENXIO. See #16746.
                echo ""
                log_info "仅需 sudo 来通过包管理器安装可选系统包（${pkgs[*]}）。"
                log_info "Hermes Agent 本身不需要也不保留 root 权限。"
                if prompt_yes_no "安装 ${description}？" "yes"; then
                    if sudo DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a $install_cmd < /dev/tty; then
                        [ "$need_ripgrep" = true ] && HAS_RIPGREP=true && log_success "ripgrep 已安装"
                        [ "$need_ffmpeg" = true ]  && HAS_FFMPEG=true  && log_success "ffmpeg 已安装"
                        return 0
                    fi
                fi
            else
                log_warn "非交互模式且无可用终端 — 无法安装系统包"
                log_info "安装完成后手动安装：sudo $install_cmd"
            fi
        fi
    fi

    # ── Fallback for ripgrep: cargo ──
    if [ "$need_ripgrep" = true ] && [ "$HAS_RIPGREP" = false ]; then
        if command -v cargo &> /dev/null; then
            log_info "尝试通过 cargo 安装 ripgrep（无需 sudo）..."
            if cargo install ripgrep; then
                log_success "通过 cargo 安装 ripgrep 成功"
                HAS_RIPGREP=true
            fi
        fi
    fi

    # ── Show manual instructions for anything still missing ──
    if [ "$HAS_RIPGREP" = false ] && [ "$need_ripgrep" = true ]; then
        log_warn "ripgrep 未安装（文件搜索将使用 grep 替代）"
        show_manual_install_hint "ripgrep"
    fi
    if [ "$HAS_FFMPEG" = false ] && [ "$need_ffmpeg" = true ]; then
        log_warn "ffmpeg 未安装（TTS 语音消息功能将受限）"
        show_manual_install_hint "ffmpeg"
    fi
}

show_manual_install_hint() {
    local pkg="$1"
    log_info "手动安装 $pkg："
    case "$OS" in
        linux)
            case "$DISTRO" in
                ubuntu|debian) log_info "  sudo apt install $pkg" ;;
                fedora)        log_info "  sudo dnf install $pkg" ;;
                arch)          log_info "  sudo pacman -S $pkg"   ;;
                *)             log_info "  请使用您的包管理器或访问项目主页" ;;
            esac
            ;;
        android)
            log_info "  pkg install $pkg"
            ;;
        macos) log_info "  brew install $pkg" ;;
    esac
}

# ============================================================================
# Installation
# ============================================================================

clone_repo() {
    log_info "正在安装到 $INSTALL_DIR..."

    if [ -d "$INSTALL_DIR" ]; then
        if [ -d "$INSTALL_DIR/.git" ]; then
            log_info "检测到已有安装，正在更新..."
            cd "$INSTALL_DIR"

            local autostash_ref=""
            if [ -n "$(git status --porcelain)" ]; then
                local stash_name
                stash_name="hermes-install-autostash-$(date -u +%Y%m%d-%H%M%S)"
                log_info "检测到本地修改，更新前暂存..."
                git stash push --include-untracked -m "$stash_name"
                autostash_ref="stash@{0}"
            fi

            git fetch origin
            git checkout "$BRANCH"
            git pull --ff-only origin "$BRANCH"

            if [ -n "$autostash_ref" ]; then
                local restore_now="yes"
                if [ -t 0 ] && [ -t 1 ]; then
                    echo
                    log_warn "更新前暂存了本地修改。"
                    log_warn "恢复可能会将本地自定义内容重新应用到更新后的代码上。"
                    printf "立即恢复本地修改？[Y/n] "
                    read -r restore_answer
                    case "$restore_answer" in
                        ""|y|Y|yes|YES|Yes) restore_now="yes" ;;
                        *) restore_now="no" ;;
                    esac
                fi

                if [ "$restore_now" = "yes" ]; then
                    log_info "正在恢复本地修改..."
                    if git stash apply "$autostash_ref"; then
                        git stash drop "$autostash_ref" >/dev/null
                        log_warn "本地修改已恢复到更新后的代码库上。"
                        log_warn "如果 Hermes 行为异常，请检查 git diff / git status。"
                    else
                        log_error "更新成功，但恢复本地修改失败。您的修改仍保存在 git stash 中。"
                        log_info "手动恢复：git stash apply $autostash_ref"
                        exit 1
                    fi
                else
                    log_info "跳过恢复本地修改。"
                    log_info "您的修改仍保存在 git stash 中。"
                    log_info "手动恢复：git stash apply $autostash_ref"
                fi
            fi
        else
            log_error "目录已存在但不是一个 git 仓库：$INSTALL_DIR"
            log_info "请删除它或使用 --dir 指定其他目录"
            exit 1
        fi
    else
        # Try SSH first (for private repo access), fall back to HTTPS
        # GIT_SSH_COMMAND disables interactive prompts and sets a short timeout
        # so SSH fails fast instead of hanging when no key is configured.
        log_info "尝试 SSH 克隆..."
        if GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=5" \
           git clone --branch "$BRANCH" "$REPO_URL_SSH" "$INSTALL_DIR" 2>/dev/null; then
            log_success "通过 SSH 克隆成功"
        else
            rm -rf "$INSTALL_DIR" 2>/dev/null  # Clean up partial SSH clone
            log_info "SSH 失败，尝试 HTTPS..."
            if git clone --branch "$BRANCH" "$REPO_URL_HTTPS" "$INSTALL_DIR"; then
                log_success "通过 HTTPS 克隆成功"
            else
                log_error "克隆仓库失败"
                exit 1
            fi
        fi
    fi

    cd "$INSTALL_DIR"

    log_success "仓库已就绪"
}

setup_venv() {
    if [ "$USE_VENV" = false ]; then
        log_info "跳过虚拟环境（--no-venv）"
        return 0
    fi

    if [ "$DISTRO" = "termux" ]; then
        log_info "使用 Termux Python 创建虚拟环境..."

        if [ -d "venv" ]; then
            log_info "虚拟环境已存在，正在重新创建..."
            rm -rf venv
        fi

        "$PYTHON_PATH" -m venv venv
        log_success "虚拟环境已就绪（$(./venv/bin/python --version 2>/dev/null)）"
        return 0
    fi

    log_info "使用 Python $PYTHON_VERSION 创建虚拟环境..."

    if [ -d "venv" ]; then
        log_info "虚拟环境已存在，正在重新创建..."
        rm -rf venv
    fi

    # uv creates the venv and pins the Python version in one step
    $UV_CMD venv venv --python "$PYTHON_VERSION"

    log_success "虚拟环境已就绪（Python $PYTHON_VERSION）"
}

install_deps() {
    log_info "正在安装依赖..."

    if [ "$DISTRO" = "termux" ]; then
        if [ "$USE_VENV" = true ]; then
            export VIRTUAL_ENV="$INSTALL_DIR/venv"
            PIP_PYTHON="$INSTALL_DIR/venv/bin/python"
        else
            PIP_PYTHON="$PYTHON_PATH"
        fi

        if [ -z "${ANDROID_API_LEVEL:-}" ]; then
            ANDROID_API_LEVEL="$(getprop ro.build.version.sdk 2>/dev/null || true)"
            if [ -z "$ANDROID_API_LEVEL" ]; then
                ANDROID_API_LEVEL=24
            fi
            export ANDROID_API_LEVEL
            log_info "使用 ANDROID_API_LEVEL=$ANDROID_API_LEVEL 构建 Android wheel"
        fi

        "$PIP_PYTHON" -m pip install --upgrade pip setuptools wheel >/dev/null

        # On Android, psutil's setup.py rejects sys.platform == 'android' before
        # it ever invokes the C build, so the next pip install would fail at
        # "platform android is not supported".  Prebuild psutil from the official
        # sdist with a one-line marker patch (Linux source path is fine on
        # Android).  Stopgap until psutil#2762 ships upstream.
        if "$PIP_PYTHON" -c 'import sys; raise SystemExit(0 if sys.platform == "android" else 1)' 2>/dev/null; then
            log_info "检测到 Android Python：正在预构建 psutil 兼容性补丁..."
            if ! "$PIP_PYTHON" "$INSTALL_DIR/scripts/install_psutil_android.py" --pip "$PIP_PYTHON -m pip"; then
                log_warn "psutil Android 预构建失败 — 下一步包安装可能失败。"
                log_info "解决方法：工具链就绪后，手动重新运行 'python scripts/install_psutil_android.py'"
            fi
        fi

        # Try the broad Termux profile first (best-effort "install all" for Android),
        # then fall back to the conservative Termux baseline, then base package.
        if ! "$PIP_PYTHON" -m pip install -e '.[termux-all]' -c constraints-termux.txt; then
            log_warn "Termux 宽泛配置（.[termux-all]）失败，尝试基础 Termux 配置..."
            if ! "$PIP_PYTHON" -m pip install -e '.[termux]' -c constraints-termux.txt; then
                log_warn "Termux 基础配置（.[termux]）失败，尝试基础安装..."
                if ! "$PIP_PYTHON" -m pip install -e '.' -c constraints-termux.txt; then
                    log_error "Termux 上的包安装失败。"
                    log_info "请确保已安装这些包：pkg install clang rust make pkg-config libffi openssl ca-certificates curl"
                    log_info "然后重新运行：cd $INSTALL_DIR && python -m pip install -e '.[termux-all]' -c constraints-termux.txt"
                    exit 1
                fi
            fi
        fi

        log_success "主包已安装"
        log_info "Termux 说明：matrix e2ee 和本地 faster-whisper 附加功能已从 .[termux-all] 中排除，因为上游 Android wheel/工具链存在阻塞问题。"
        log_info "Termux 说明：默认不安装浏览器/WhatsApp 工具；请参阅 Termux 指南中的可选后续步骤。"

        log_success "所有依赖已安装"
        return 0
    fi

    if [ "$USE_VENV" = true ]; then
        # Tell uv to install into our venv (no need to activate)
        export VIRTUAL_ENV="$INSTALL_DIR/venv"
    fi

    # On Debian/Ubuntu (including WSL), some Python packages need build tools.
    # Check and offer to install them if missing.
    if [ "$DISTRO" = "ubuntu" ] || [ "$DISTRO" = "debian" ]; then
        local need_build_tools=false
        for pkg in gcc python3-dev libffi-dev; do
            if ! dpkg -s "$pkg" &>/dev/null; then
                need_build_tools=true
                break
            fi
        done
        if [ "$need_build_tools" = true ]; then
            log_info "Python 包可能需要一些构建工具..."
            if command -v sudo &> /dev/null; then
                if sudo -n true 2>/dev/null; then
                    sudo DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a apt-get install -y -qq build-essential python3-dev libffi-dev >/dev/null 2>&1 || true
                    log_success "构建工具已安装"
                else
                    log_info "仅需 sudo 来通过 apt 安装构建工具（build-essential, python3-dev, libffi-dev）。"
                    log_info "Hermes Agent 本身不需要也不保留 root 权限。"
                    if prompt_yes_no "安装构建工具？" "yes"; then
                        sudo DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a apt-get install -y -qq build-essential python3-dev libffi-dev >/dev/null 2>&1 || true
                        log_success "构建工具已安装"
                    fi
                fi
            fi
        fi
    fi

    # Install the main package in editable mode with all extras.
    #
    # Hash-verified install (Tier 0) — when uv.lock is present, prefer
    # `uv sync --locked`. The lockfile records SHA256 hashes for every
    # transitive, so a compromised transitive (different hash than what
    # we shipped) is REJECTED by the resolver. This is the *only* path
    # that protects against the "direct dep is fine, but the dep's dep
    # got worm-poisoned overnight" failure mode. All `uv pip install`
    # tiers below re-resolve transitives fresh from PyPI without any
    # hash verification — they exist to keep installs working when the
    # lockfile is stale, missing, or out-of-sync with the current
    # extras spec, NOT because they're equivalent in posture.
    if [ -f "uv.lock" ]; then
        log_info "尝试层级：哈希验证（uv.lock）..."
        log_info "（这将解析并下载精选的 [all] 依赖集——在全新虚拟环境上首次运行"
        log_info " 可能需要 1-5 分钟；uv 会在下方打印进度）"
        # Stream uv's progress directly to the user instead of swallowing
        # it with `2>"$(mktemp)"`.  Two reasons:
        #   1. `--extra all --locked` against a fresh venv has to pull
        #      every transitive — silencing stderr makes the install
        #      look frozen for minutes on slow networks. Users see
        #      "Trying tier: hash-verified ..." and assume it's hung.
        #   2. The previous `2>"$(mktemp)"` substituted the path at
        #      command-build time but never saved it, so on failure the
        #      uv error message was unreachable — the user just got the
        #      generic "lockfile may be stale" warning.
        #
        # Critical flag choice: `--extra all`, NOT `--all-extras`.
        #   --all-extras = every [project.optional-dependencies] key.
        #                  This bypasses the curated `[all]` extra
        #                  entirely and pulls e.g. [matrix] (which
        #                  needs python-olm + make on Windows) and
        #                  [rl] (git+https deps that fail offline).
        #   --extra all  = install just the `[all]` extra's contents.
        #                  This respects the curation in pyproject.toml.
        # uv's own progress UI handles TTY detection and downgrades
        # gracefully when stdout/stderr aren't terminals.
        if UV_PROJECT_ENVIRONMENT="$INSTALL_DIR/venv" $UV_CMD sync --extra all --locked; then
            log_success "主包已安装（通过 uv.lock 哈希验证）"
            log_success "所有依赖已安装"
            return 0
        fi
        log_warn "uv.lock 同步失败（见上方 uv 输出），回退到 PyPI 解析..."
    else
        log_info "未找到 uv.lock — 回退到 PyPI 解析（无哈希验证）"
    fi

    # Multi-tier fallback. The point of the tiers is that ONE compromised
    # PyPI package (a worm-poisoned release that gets quarantined, like
    # mistralai 2.4.6 in May 2026) shouldn't be able to silently demote a
    # fresh install all the way down to "core only" — the user should keep
    # everything else they signed up for.
    #
    # Tier 1: [all] — the curated extra in pyproject.toml.
    # Tier 2: [all] minus the currently-broken extras list (_BROKEN_EXTRAS).
    #         Edit _BROKEN_EXTRAS below when something on PyPI breaks; this
    #         lets users keep the rest of [all] when one transitive is
    #         unavailable. The list of [all]'s contents is parsed from
    #         pyproject.toml at runtime — there is NO hand-mirrored copy
    #         to drift out of sync. If you want to change what [all]
    #         contains, edit pyproject.toml only.
    # Tier 3: bare `.` — last-resort so at least the core CLI launches.
    #         Skipped tiers like "PyPI-only extras (no git deps)" used to
    #         exist to dodge [rl] / [matrix] git+sdist deps; those are no
    #         longer in [all] post-2026-05-12 lazy-install migration, so
    #         a separate PyPI-only tier had no remaining content.
    local _BROKEN_EXTRAS=()  # populate when an extra becomes unresolvable

    # Parse [project.optional-dependencies].all from pyproject.toml.
    # tomllib is stdlib on Python 3.11+ which uv's bootstrap guarantees.
    # Falls back to a hand list if parse fails — defensive only.
    local _ALL_EXTRAS_CSV
    _ALL_EXTRAS_CSV="$(
        "$PYTHON_PATH" - <<'PY' 2>/dev/null
import re, sys, tomllib
try:
    with open("pyproject.toml", "rb") as fh:
        data = tomllib.load(fh)
    specs = data["project"]["optional-dependencies"]["all"]
    extras = []
    for s in specs:
        m = re.search(r"hermes-agent\[([\w-]+)\]", s)
        if m:
            extras.append(m.group(1))
    print(",".join(extras))
except Exception as e:
    print("", file=sys.stderr)
    sys.exit(1)
PY
    )"
    if [ -z "$_ALL_EXTRAS_CSV" ]; then
        log_warn "无法从 pyproject.toml 解析 [all] 依赖；仅回退到 .[all]。"
        _ALL_EXTRAS_CSV=""
    fi

    # Build "[all] minus broken" spec by filtering the parsed list.
    local _SAFE_SPEC=".[all]"
    if [ -n "$_ALL_EXTRAS_CSV" ] && [ "${#_BROKEN_EXTRAS[@]}" -gt 0 ]; then
        local _SAFE_EXTRAS=()
        local _e _b _skip
        IFS=',' read -ra _ALL_EXTRAS_ARR <<< "$_ALL_EXTRAS_CSV"
        for _e in "${_ALL_EXTRAS_ARR[@]}"; do
            _skip=false
            for _b in "${_BROKEN_EXTRAS[@]}"; do
                if [ "$_e" = "$_b" ]; then _skip=true; break; fi
            done
            if [ "$_skip" = false ]; then _SAFE_EXTRAS+=("$_e"); fi
        done
        _SAFE_SPEC=".[$(IFS=,; echo "${_SAFE_EXTRAS[*]}")]"
    fi

    ALL_INSTALL_LOG=$(mktemp)
    local _installed=false
    local _tier_name=""

    install_tier() {
        local name="$1"; local spec="$2"
        log_info "尝试层级：$name ..."
        if $UV_CMD pip install -e "$spec" 2>"$ALL_INSTALL_LOG"; then
            log_success "主包已安装（$name）"
            _installed=true
            _tier_name="$name"
            return 0
        fi
        log_warn "层级 '$name' 失败。pip 输出顶部："
        head -5 "$ALL_INSTALL_LOG" | sed 's/^/    /' >&2
        return 1
    }

    install_tier "all" ".[all]" \
        || install_tier "all minus known-broken (${_BROKEN_EXTRAS[*]:-none})" "$_SAFE_SPEC" \
        || install_tier "core only (no extras)" "."

    rm -f "$ALL_INSTALL_LOG"

    if [ "$_installed" = false ]; then
        log_error "即使没有附加功能，包安装也失败了。"
        log_info "请检查是否已安装构建工具：sudo apt install build-essential python3-dev"
        log_info "然后重新运行：cd $INSTALL_DIR && uv pip install -e '.[all]'"
        exit 1
    fi

    if [ "$_tier_name" != "all (with RL/matrix extras)" ]; then
        log_warn "注意：通过回退层级安装（$_tier_name）。"
        log_info "某些可选功能可能缺失。解决 PyPI/网络问题后，"
        log_info "重新运行：$UV_CMD pip install -e '.[all]'"
    fi

    log_success "主包已安装"

    log_success "所有依赖已安装"
}

setup_path() {
    log_info "正在设置 nermes 命令..."

    if [ "$USE_VENV" = true ]; then
        HERMES_BIN="$INSTALL_DIR/venv/bin/nermes"
    else
        HERMES_BIN="$(which nermes 2>/dev/null || echo "")"
        if [ -z "$HERMES_BIN" ]; then
            log_warn "安装后未在 PATH 中找到 nermes"
            return 0
        fi
    fi

    # Verify the entry point script was actually generated
    if [ ! -x "$HERMES_BIN" ]; then
        log_warn "在 $HERMES_BIN 未找到 nermes 入口点"
        log_info "这通常意味着 pip 安装未成功完成。"
        if [ "$DISTRO" = "termux" ]; then
            log_info "尝试：cd $INSTALL_DIR && python -m pip install -e '.[termux-all]' -c constraints-termux.txt"
        else
            log_info "尝试：cd $INSTALL_DIR && uv pip install -e '.[all]'"
        fi
        return 0
    fi

    local command_link_dir
    local command_link_display_dir
    command_link_dir="$(get_command_link_dir)"
    command_link_display_dir="$(get_command_link_display_dir)"

    # Create a user-facing shim for the nermes command.
    # We intentionally clear PYTHONPATH/PYTHONHOME here so inherited env vars
    # can't make this launcher import modules from another checkout.
    mkdir -p "$command_link_dir"
    # Older installs created this path as a symlink to $HERMES_BIN. Without
    # the rm, `cat >` follows the symlink and overwrites the venv pip entry
    # point with this shim — making `exec "$HERMES_BIN"` self-recurse. (#21454)
    rm -f "$command_link_dir/nermes"
    cat > "$command_link_dir/nermes" <<EOF
#!/usr/bin/env bash
unset PYTHONPATH
unset PYTHONHOME
exec "$HERMES_BIN" "\$@"
EOF
    chmod +x "$command_link_dir/nermes"
    log_success "nermes 启动器已安装 → $command_link_display_dir/nermes"

    if [ "$DISTRO" = "termux" ]; then
        export PATH="$command_link_dir:$PATH"
        log_info "$command_link_display_dir 是原生的 Termux 命令路径"
        log_success "nermes 命令已就绪"
        return 0
    fi

    # FHS layout: /usr/local/bin is normally on PATH for login shells (via
    # /etc/profile pathmunge), but on RHEL/CentOS/Rocky/Alma 8+ non-login
    # interactive root shells (su, sudo -s, tmux panes, some web terminals)
    # only source /etc/bashrc, which does NOT add /usr/local/bin — and
    # /root/.bash_profile doesn't either.  So verify with `command -v` and
    # fall back to writing a PATH guard into /root/.bashrc when needed.
    if [ "$ROOT_FHS_LAYOUT" = true ]; then
        export PATH="$command_link_dir:$PATH"
        # Probe a fresh non-login interactive bash the way the user will use it.
        # `bash -i -c` sources ~/.bashrc but NOT ~/.bash_profile or /etc/profile,
        # which is the exact scenario where RHEL root loses /usr/local/bin.
        if env -i HOME="$HOME" TERM="${TERM:-dumb}" bash -i -c 'command -v nermes' \
                >/dev/null 2>&1; then
            log_info "/usr/local/bin 已经在所有 shell 的 PATH 中"
            log_success "nermes 命令已就绪"
            return 0
        fi

        log_info "nermes 在非登录 shell 中不在 PATH 上（RHEL 系列常见）"
        PATH_LINE='export PATH="/usr/local/bin:$PATH"'
        PATH_COMMENT='# Nermes Agent — 确保 /usr/local/bin 在 PATH 中（RHEL 非登录 shell）'
        for SHELL_CONFIG in "$HOME/.bashrc" "$HOME/.bash_profile"; do
            [ -f "$SHELL_CONFIG" ] || continue
            if ! grep -v '^[[:space:]]*#' "$SHELL_CONFIG" 2>/dev/null \
                    | grep -qE 'PATH=.*(/usr/local/bin|\$command_link_dir)'; then
                echo "" >> "$SHELL_CONFIG"
                echo "$PATH_COMMENT" >> "$SHELL_CONFIG"
                echo "$PATH_LINE" >> "$SHELL_CONFIG"
                log_success "已将 /usr/local/bin 添加到 $SHELL_CONFIG 的 PATH 中"
            fi
        done
        log_success "nermes 命令已就绪"
        return 0
    fi

    # Check if ~/.local/bin is on PATH; if not, add it to shell config.
    # Detect the user's actual login shell (not the shell running this script,
    # which is always bash when piped from curl).
    if ! echo "$PATH" | tr ':' '\n' | grep -q "^$command_link_dir$"; then
        SHELL_CONFIGS=()
        IS_FISH=false
        LOGIN_SHELL="$(basename "${SHELL:-/bin/bash}")"
        case "$LOGIN_SHELL" in
            zsh)
                [ -f "$HOME/.zshrc" ] && SHELL_CONFIGS+=("$HOME/.zshrc")
                [ -f "$HOME/.zprofile" ] && SHELL_CONFIGS+=("$HOME/.zprofile")
                # If neither exists, create ~/.zshrc (common on fresh macOS installs)
                if [ ${#SHELL_CONFIGS[@]} -eq 0 ]; then
                    touch "$HOME/.zshrc"
                    SHELL_CONFIGS+=("$HOME/.zshrc")
                fi
                ;;
            bash)
                [ -f "$HOME/.bashrc" ] && SHELL_CONFIGS+=("$HOME/.bashrc")
                [ -f "$HOME/.bash_profile" ] && SHELL_CONFIGS+=("$HOME/.bash_profile")
                ;;
            fish)
                # fish uses ~/.config/fish/config.fish and fish_add_path — not export PATH=
                IS_FISH=true
                FISH_CONFIG="$HOME/.config/fish/config.fish"
                mkdir -p "$(dirname "$FISH_CONFIG")"
                touch "$FISH_CONFIG"
                ;;
            *)
                [ -f "$HOME/.bashrc" ] && SHELL_CONFIGS+=("$HOME/.bashrc")
                [ -f "$HOME/.zshrc" ] && SHELL_CONFIGS+=("$HOME/.zshrc")
                ;;
        esac
        # Also ensure ~/.profile has it (sourced by login shells on
        # Ubuntu/Debian/WSL even when ~/.bashrc is skipped)
        [ "$IS_FISH" = "false" ] && [ -f "$HOME/.profile" ] && SHELL_CONFIGS+=("$HOME/.profile")

        PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'

        for SHELL_CONFIG in "${SHELL_CONFIGS[@]}"; do
            if ! grep -v '^[[:space:]]*#' "$SHELL_CONFIG" 2>/dev/null | grep -qE 'PATH=.*\.local/bin'; then
                echo "" >> "$SHELL_CONFIG"
                echo "# Nermes Agent — 确保 ~/.local/bin 在 PATH 中" >> "$SHELL_CONFIG"
                echo "$PATH_LINE" >> "$SHELL_CONFIG"
                log_success "已将 ~/.local/bin 添加到 $SHELL_CONFIG 的 PATH 中"
            fi
        done

        # fish uses fish_add_path instead of export PATH=...
        if [ "$IS_FISH" = "true" ]; then
            if ! grep -q 'fish_add_path.*\.local/bin' "$FISH_CONFIG" 2>/dev/null; then
                echo "" >> "$FISH_CONFIG"
                echo "# Nermes Agent — 确保 ~/.local/bin 在 PATH 中" >> "$FISH_CONFIG"
                echo 'fish_add_path "$HOME/.local/bin"' >> "$FISH_CONFIG"
                log_success "已将 ~/.local/bin 添加到 $FISH_CONFIG 的 PATH 中"
            fi
        fi

        if [ "$IS_FISH" = "false" ] && [ ${#SHELL_CONFIGS[@]} -eq 0 ]; then
            log_warn "无法检测到 shell 配置文件以将 ~/.local/bin 添加到 PATH"
            log_info "手动添加：$PATH_LINE"
        fi
    else
        log_info "~/.local/bin 已在 PATH 中"
    fi

    # Export for current session so nermes works immediately
    export PATH="$command_link_dir:$PATH"

    log_success "nermes 命令已就绪"
}

copy_config_templates() {
    log_info "正在设置配置文件..."

    # Create ~/.nermes directory structure (config at top level, code in subdir)
    mkdir -p "$NERMES_HOME"/{cron,sessions,logs,pairing,hooks,image_cache,audio_cache,memories,skills}

    # Create .env at ~/.nermes/.env (top level, easy to find)
    if [ ! -f "$NERMES_HOME/.env" ]; then
        if [ -f "$INSTALL_DIR/.env.example" ]; then
            cp "$INSTALL_DIR/.env.example" "$NERMES_HOME/.env"
            log_success "已从模板创建 ~/.nermes/.env"
        else
            touch "$NERMES_HOME/.env"
            log_success "已创建 ~/.nermes/.env"
        fi
    else
        log_info "~/.nermes/.env 已存在，保持不变"
    fi
    # Restrict .env permissions — this file holds API keys and tokens.
    # 0600 ensures only the file owner can read/write, matching standard
    # practice for credential files (.netrc, .aws/credentials, .ssh/config).
    chmod 600 "$NERMES_HOME/.env"
    configure_browser_env_from_system_browser

    # Create config.yaml at ~/.nermes/config.yaml (top level, easy to find)
    if [ ! -f "$NERMES_HOME/config.yaml" ]; then
        if [ -f "$INSTALL_DIR/cli-config.yaml.example" ]; then
            cp "$INSTALL_DIR/cli-config.yaml.example" "$NERMES_HOME/config.yaml"
            log_success "已从模板创建 ~/.nermes/config.yaml"
        fi
    else
        log_info "~/.nermes/config.yaml 已存在，保持不变"
    fi

    # Create SOUL.md if it doesn't exist (global persona file)
    if [ ! -f "$NERMES_HOME/SOUL.md" ]; then
        cat > "$NERMES_HOME/SOUL.md" << 'SOUL_EOF'
# Nermes Agent Persona

<!--
This file defines the agent's personality and tone.
The agent will embody whatever you write here.
Edit this to customize how Nermes communicates with you.

Examples:
  - "You are a warm, playful assistant who uses kaomoji occasionally."
  - "You are a concise technical expert. No fluff, just facts."
  - "You speak like a friendly coworker who happens to know everything."

This file is loaded fresh each message -- no restart needed.
Delete the contents (or this file) to use the default personality.
-->
SOUL_EOF
        log_success "已创建 ~/.nermes/SOUL.md（编辑以自定义个性）"
    fi

    log_success "配置目录已就绪：~/.nermes/"

    # Seed bundled skills into ~/.nermes/skills/ (manifest-based, one-time per skill)
    log_info "正在同步内置技能到 ~/.nermes/skills/ ..."
    if "$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/tools/skills_sync.py" 2>/dev/null; then
        log_success "技能已同步到 ~/.nermes/skills/"
    else
        # Fallback: simple directory copy if Python sync fails
        if [ -d "$INSTALL_DIR/skills" ] && [ ! "$(ls -A "$NERMES_HOME/skills/" 2>/dev/null | grep -v '.bundled_manifest')" ]; then
            cp -r "$INSTALL_DIR/skills/"* "$NERMES_HOME/skills/" 2>/dev/null || true
            log_success "技能已复制到 ~/.nermes/skills/"
        fi
    fi
}

find_system_browser() {
    # Prefer a user-specified browser path, then common Linux/macOS Chrome and
    # Chromium command names.  Arch-family distributions commonly ship plain
    # `chromium`, while Debian-family systems often use `chromium-browser`.
    if [ -n "${AGENT_BROWSER_EXECUTABLE_PATH:-}" ]; then
        if [ -x "$AGENT_BROWSER_EXECUTABLE_PATH" ]; then
            echo "$AGENT_BROWSER_EXECUTABLE_PATH"
            return 0
        fi
        if command -v "$AGENT_BROWSER_EXECUTABLE_PATH" >/dev/null 2>&1; then
            command -v "$AGENT_BROWSER_EXECUTABLE_PATH"
            return 0
        fi
    fi

    local candidate
    for candidate in google-chrome google-chrome-stable chromium chromium-browser chrome; do
        if command -v "$candidate" >/dev/null 2>&1; then
            command -v "$candidate"
            return 0
        fi
    done

    if [ "$(uname)" = "Darwin" ]; then
        for app in \
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
            "/Applications/Chromium.app/Contents/MacOS/Chromium"; do
            if [ -x "$app" ]; then
                echo "$app"
                return 0
            fi
        done
    fi

    return 1
}

run_browser_install_with_timeout() {
    local timeout_seconds="$1"
    shift

    if command -v timeout >/dev/null 2>&1; then
        timeout "$timeout_seconds" "$@"
    else
        "$@"
    fi
}

configure_browser_env_from_system_browser() {
    local env_file="$NERMES_HOME/.env"
    local browser_path="${DETECTED_BROWSER_EXECUTABLE:-}"

    if [ -z "$browser_path" ]; then
        browser_path="$(find_system_browser 2>/dev/null || true)"
    fi

    if [ -z "$browser_path" ]; then
        return 0
    fi

    mkdir -p "$NERMES_HOME"
    if [ ! -f "$env_file" ]; then
        touch "$env_file"
    fi

    if grep -q '^AGENT_BROWSER_EXECUTABLE_PATH=' "$env_file" 2>/dev/null; then
        log_info "AGENT_BROWSER_EXECUTABLE_PATH 已配置"
        return 0
    fi

    {
        echo ""
        echo "# Nermes Agent browser tools — use the system Chrome/Chromium binary."
        echo "AGENT_BROWSER_EXECUTABLE_PATH=$browser_path"
    } >> "$env_file"
    log_success "已将浏览器工具配置为使用 $browser_path"
}

install_node_deps() {
    if [ "$HAS_NODE" = false ]; then
        log_info "跳过 Node.js 依赖（Node 未安装）"
        return 0
    fi

    if [ "$DISTRO" = "termux" ]; then
        log_info "跳过 Termux 上的自动 Node/浏览器依赖设置"
        log_info "浏览器自动化尚不属于经过测试的 Termux 安装路径。"
        log_info "如果以后想手动尝试，运行：cd $INSTALL_DIR && npm install"
        return 0
    fi

    if [ -f "$INSTALL_DIR/package.json" ]; then
        log_info "正在安装 Node.js 依赖（浏览器工具）..."
        cd "$INSTALL_DIR"
        npm install --silent 2>/dev/null || {
            log_warn "npm install 失败（浏览器工具可能无法工作）"
        }
        log_success "Node.js 依赖已安装"

        # Install Playwright browser + system dependencies.
        # Playwright's --with-deps only supports apt-based systems natively.
        # For Arch/Manjaro we install the system libs via pacman first.
        # Other systems must install Chromium dependencies manually.
        if [ "$SKIP_BROWSER" = true ]; then
            log_info "跳过 Playwright/Chromium 安装（--skip-browser）"
            log_info "浏览器工具将不可用，直到您手动运行："
            log_info "  cd $INSTALL_DIR && npx playwright install chromium"
            log_info "在 apt 系统上，管理员还需要运行："
            log_info "  sudo npx playwright install-deps chromium"
        else
        log_info "正在安装浏览器引擎（Playwright Chromium）..."
        DETECTED_BROWSER_EXECUTABLE="$(find_system_browser 2>/dev/null || true)"
        if [ -n "$DETECTED_BROWSER_EXECUTABLE" ]; then
            log_success "在 $DETECTED_BROWSER_EXECUTABLE 找到系统 Chrome/Chromium"
            log_info "跳过 Playwright 浏览器下载；Hermes 将使用系统浏览器。"
        else
            case "$DISTRO" in
                ubuntu|debian|raspbian|pop|linuxmint|elementary|zorin|kali|parrot)
                    # Use --with-deps only when sudo is available non-interactively
                    # (root, or a user with passwordless sudo). Non-sudo users
                    # — typical for systemd service accounts and unprivileged
                    # operator users — would otherwise get blocked on an
                    # interactive sudo prompt that they can't satisfy. Fall back
                    # to the browser-only install in that case, and print the
                    # exact command the admin needs to run separately.
                    if [ "$(id -u)" -eq 0 ] || (command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null); then
                        log_info "正在安装 Playwright Chromium 及系统依赖..."
                        cd "$INSTALL_DIR" && run_browser_install_with_timeout 600 npx playwright install --with-deps chromium 2>/dev/null || {
                            log_warn "Playwright 浏览器安装失败 — 浏览器工具将无法工作。"
                            log_warn "尝试手动运行：cd $INSTALL_DIR && npx playwright install --with-deps chromium"
                        }
                    else
                        log_warn "没有可用的 sudo — 跳过系统库安装（--with-deps）。"
                        log_info "请管理员以 root 身份运行一次："
                        log_info "  sudo npx playwright install-deps chromium"
                        log_info "  （从 $INSTALL_DIR 目录，Node.js 依赖安装后）"
                        log_info "正在将 Chromium 二进制包安装到当前用户的 Playwright 缓存..."
                        cd "$INSTALL_DIR" && run_browser_install_with_timeout 600 npx playwright install chromium 2>/dev/null || {
                            log_warn "Playwright 浏览器安装失败 — 浏览器工具将无法工作。"
                            log_warn "尝试手动运行：cd $INSTALL_DIR && npx playwright install chromium"
                        }
                    fi
                    ;;
                arch|manjaro|cachyos|endeavouros|garuda)
                    if command -v pacman &> /dev/null; then
                        log_info "检测到 Arch 系列发行版 — 通过 pacman 安装 Chromium 系统依赖..."
                        if command -v sudo &> /dev/null && sudo -n true 2>/dev/null; then
                            sudo NEEDRESTART_MODE=a pacman -S --noconfirm --needed \
                                nss atk at-spi2-core cups libdrm libxkbcommon mesa pango cairo alsa-lib >/dev/null 2>&1 || true
                        elif [ "$(id -u)" -eq 0 ]; then
                            pacman -S --noconfirm --needed \
                                nss atk at-spi2-core cups libdrm libxkbcommon mesa pango cairo alsa-lib >/dev/null 2>&1 || true
                        else
                            log_warn "没有 sudo 无法安装浏览器依赖。手动运行："
                            log_warn "  sudo pacman -S nss atk at-spi2-core cups libdrm libxkbcommon mesa pango cairo alsa-lib"
                        fi
                    fi
                    cd "$INSTALL_DIR" && run_browser_install_with_timeout 600 npx playwright install chromium 2>/dev/null || {
                        log_warn "Playwright 浏览器安装失败 — 浏览器工具将无法工作。"
                    }
                    ;;
                fedora|rhel|centos|rocky|alma)
                    log_warn "Playwright 不支持在 RPM 系统上自动安装依赖。"
                    log_info "使用浏览器工具前，请手动安装 Chromium 系统依赖："
                    log_info "  sudo dnf install nss atk at-spi2-core cups-libs libdrm libxkbcommon mesa-libgbm pango cairo alsa-lib"
                    cd "$INSTALL_DIR" && run_browser_install_with_timeout 600 npx playwright install chromium 2>/dev/null || {
                        log_warn "Playwright 浏览器安装失败 — 请先安装上述依赖后重试。"
                    }
                    ;;
                opensuse*|sles)
                    log_warn "Playwright 不支持在 zypper 系统上自动安装依赖。"
                    log_info "使用浏览器工具前，请手动安装 Chromium 系统依赖："
                    log_info "  sudo zypper install mozilla-nss libatk-1_0-0 at-spi2-core cups-libs libdrm2 libxkbcommon0 Mesa-libgbm1 pango cairo libasound2"
                    cd "$INSTALL_DIR" && run_browser_install_with_timeout 600 npx playwright install chromium 2>/dev/null || {
                        log_warn "Playwright 浏览器安装失败 — 请先安装上述依赖后重试。"
                    }
                    ;;
                *)
                    log_warn "Playwright 不支持在 $DISTRO 上自动安装依赖。"
                    log_info "请为您的发行版安装 Chromium/浏览器系统依赖，然后运行："
                    log_info "  cd $INSTALL_DIR && npx playwright install chromium"
                    log_info "浏览器工具在依赖安装完成之前将无法工作。"
                    cd "$INSTALL_DIR" && run_browser_install_with_timeout 600 npx playwright install chromium 2>/dev/null || true
                    ;;
            esac
        fi
        fi
        log_success "浏览器引擎设置完成"
    fi

    # Install TUI dependencies
    if [ -f "$INSTALL_DIR/ui-tui/package.json" ]; then
        log_info "正在安装 TUI 依赖..."
        cd "$INSTALL_DIR/ui-tui"
        npm install --silent 2>/dev/null || {
            log_warn "TUI npm install 失败（nermes --tui 可能无法工作）"
        }
        log_success "TUI 依赖已安装"
    fi


}

run_setup_wizard() {
    if [ "$RUN_SETUP" = false ]; then
        log_info "跳过设置向导（--skip-setup）"
        return 0
    fi

    # The setup wizard reads from /dev/tty, so it works even when the
    # install script itself is piped (curl | bash). Only skip if no
    # terminal is available at all (e.g. Docker build, CI).
    #
    # Probe by actually opening /dev/tty: a bare existence test passes
    # in Docker builds where the device node is in the mount namespace
    # but opening fails with ENXIO, so the wizard would proceed and
    # then crash on `< /dev/tty` below.
    if ! (: </dev/tty) 2>/dev/null; then
        log_info "跳过设置向导（无可用终端）。安装后运行 'nermes setup'。"
        return 0
    fi

    echo ""
    log_info "正在启动设置向导..."
    echo ""

    cd "$INSTALL_DIR"

    # Run nermes setup using the venv Python directly (no activation needed).
    # Redirect stdin from /dev/tty so interactive prompts work when piped from curl.
    if [ "$USE_VENV" = true ]; then
        "$INSTALL_DIR/venv/bin/python" -m hermes_cli.main setup < /dev/tty
    else
        python -m hermes_cli.main setup < /dev/tty
    fi
}

maybe_start_gateway() {
    # Check if any messaging platform tokens were configured
    ENV_FILE="$NERMES_HOME/.env"
    if [ ! -f "$ENV_FILE" ]; then
        return 0
    fi

    HAS_MESSAGING=false
    for VAR in TELEGRAM_BOT_TOKEN DISCORD_BOT_TOKEN SLACK_BOT_TOKEN SLACK_APP_TOKEN WHATSAPP_ENABLED; do
        VAL=$(grep "^${VAR}=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2-)
        if [ -n "$VAL" ] && [ "$VAL" != "your-token-here" ]; then
            HAS_MESSAGING=true
            break
        fi
    done

    if [ "$HAS_MESSAGING" = false ]; then
        return 0
    fi

    echo ""
    log_info "检测到消息平台令牌！"
    log_info "需要保持网关运行，Hermes 才能收发消息。"

    # If WhatsApp is enabled and no session exists yet, run foreground first for QR scan
    WHATSAPP_VAL=$(grep "^WHATSAPP_ENABLED=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2-)
    WHATSAPP_SESSION="$NERMES_HOME/whatsapp/session/creds.json"
    if [ "$WHATSAPP_VAL" = "true" ] && [ ! -f "$WHATSAPP_SESSION" ]; then
        if [ "$IS_INTERACTIVE" = true ]; then
            echo ""
            log_info "WhatsApp 已启用但尚未配对。"
            log_info "运行 'nermes whatsapp' 通过二维码配对..."
            echo ""
            if prompt_yes_no "立即配对 WhatsApp？" "yes"; then
                HERMES_CMD="$(get_hermes_command_path)"
                $HERMES_CMD whatsapp || true
            fi
        else
            log_info "跳过 WhatsApp 配对（非交互模式）。运行 'nermes whatsapp' 进行配对。"
        fi
    fi

    # Probe by actually opening /dev/tty: a bare existence test passes
    # in Docker builds where the device node is in the mount namespace
    # but opening fails with ENXIO. See #16746.
    if ! (: </dev/tty) 2>/dev/null; then
        log_info "跳过网关设置（无可用终端）。稍后运行 'nermes gateway install'。"
        return 0
    fi

    echo ""
    local should_install_gateway=false
    if [ "$DISTRO" = "termux" ]; then
        if prompt_yes_no "是否在后台启动网关？" "yes"; then
            should_install_gateway=true
        fi
    else
        if prompt_yes_no "是否将网关安装为后台服务？" "yes"; then
            should_install_gateway=true
        fi
    fi

    if [ "$should_install_gateway" = true ]; then
        HERMES_CMD="$(get_hermes_command_path)"

        if [ "$DISTRO" != "termux" ] && command -v systemctl &> /dev/null; then
            log_info "正在安装 systemd 服务..."
            if $HERMES_CMD gateway install 2>/dev/null; then
                log_success "网关服务已安装"
                if $HERMES_CMD gateway start 2>/dev/null; then
                    log_success "网关已启动！您的机器人现已在线。"
                else
                    log_warn "服务已安装但启动失败。尝试：nermes gateway start"
                fi
            else
                log_warn "Systemd 安装失败。您可以手动启动：nermes gateway"
            fi
        else
            if [ "$DISTRO" = "termux" ]; then
                log_info "检测到 Termux — 以后台尽力模式启动网关..."
            else
                log_info "systemd 不可用 — 在后台启动网关..."
            fi
            nohup $HERMES_CMD gateway > "$NERMES_HOME/logs/gateway.log" 2>&1 &
            GATEWAY_PID=$!
            log_success "网关已启动（PID $GATEWAY_PID）。日志：~/.nermes/logs/gateway.log"
            log_info "停止：kill $GATEWAY_PID"
            log_info "稍后重新启动：nermes gateway"
            if [ "$DISTRO" = "termux" ]; then
                log_warn "当 Termux 被挂起或系统回收资源时，Android 可能会停止后台进程。"
            fi
        fi
    else
        log_info "已跳过。稍后启动网关：nermes gateway"
    fi
}

print_success() {
    echo ""
    echo -e "${GREEN}${BOLD}"
    echo "┌─────────────────────────────────────────────────────────┐"
    echo "│              ✓ 安装完成！                                │"
    echo "└─────────────────────────────────────────────────────────┘"
    echo -e "${NC}"
    echo ""

    # Show file locations
    echo -e "${CYAN}${BOLD}📁 文件位置：${NC}"
    echo ""
    echo -e "   ${YELLOW}配置：${NC}    $NERMES_HOME/config.yaml"
    echo -e "   ${YELLOW}API 密钥：${NC}  $NERMES_HOME/.env"
    echo -e "   ${YELLOW}数据：${NC}      $NERMES_HOME/cron/, sessions/, logs/"
    echo -e "   ${YELLOW}代码：${NC}      $INSTALL_DIR"
    echo ""

    echo -e "${CYAN}─────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "${CYAN}${BOLD}🚀 命令：${NC}"
    echo ""
    echo -e "   ${GREEN}nermes${NC}              开始对话"
    echo -e "   ${GREEN}nermes setup${NC}        配置 API 密钥和设置"
    echo -e "   ${GREEN}nermes config${NC}       查看/编辑配置"
    echo -e "   ${GREEN}nermes config edit${NC}  在编辑器中打开配置"
    echo -e "   ${GREEN}nermes gateway install${NC} 安装网关服务（消息 + 定时任务）"
    echo -e "   ${GREEN}nermes update${NC}       更新到最新版本"
    echo ""

    echo -e "${CYAN}─────────────────────────────────────────────────────────${NC}"
    echo ""
    if [ "$DISTRO" = "termux" ]; then
        echo -e "${YELLOW}⚡ 'nermes' 已链接到 $(get_command_link_display_dir)，该目录在 Termux 的 PATH 中。${NC}"
        echo ""
    elif [ "$ROOT_FHS_LAYOUT" = true ]; then
        echo -e "${YELLOW}⚡ 'nermes' 已链接到 /usr/local/bin，可直接使用 — 无需重新加载 shell。${NC}"
        echo ""
    else
        echo -e "${YELLOW}⚡ 请重新加载 shell 以使用 'nermes' 命令：${NC}"
        echo ""
        LOGIN_SHELL="$(basename "${SHELL:-/bin/bash}")"
        if [ "$LOGIN_SHELL" = "zsh" ]; then
            echo "   source ~/.zshrc"
        elif [ "$LOGIN_SHELL" = "bash" ]; then
            echo "   source ~/.bashrc"
        elif [ "$LOGIN_SHELL" = "fish" ]; then
            echo "   source ~/.config/fish/config.fish"
        else
            echo "   source ~/.bashrc   # 或 ~/.zshrc"
        fi
        echo ""
    fi

    # Show Node.js warning if auto-install failed
    if [ "$HAS_NODE" = false ]; then
        echo -e "${YELLOW}"
        echo "注意：无法自动安装 Node.js。"
        echo "浏览器工具需要 Node.js。请手动安装："
        if [ "$DISTRO" = "termux" ]; then
            echo "  pkg install nodejs"
        else
            echo "  https://nodejs.org/en/download/"
        fi
        echo -e "${NC}"
    fi

    # Show ripgrep note if not installed
    if [ "$HAS_RIPGREP" = false ]; then
        echo -e "${YELLOW}"
        echo "注意：未找到 ripgrep（rg）。文件搜索将使用"
        echo "grep 作为替代。如需在大型代码库中更快搜索，"
        if [ "$DISTRO" = "termux" ]; then
            echo "请安装 ripgrep：pkg install ripgrep"
        else
            echo "请安装 ripgrep：sudo apt install ripgrep（或 brew install ripgrep）"
        fi
        echo -e "${NC}"
    fi
}

ensure_browser() {
    if ! command -v node >/dev/null 2>&1; then
        local node_bin="$NERMES_HOME/node/bin/node"
        if [ -x "$node_bin" ]; then
            export PATH="$NERMES_HOME/node/bin:$PATH"
        else
            log_error "未找到 Node.js。请先使用 --ensure node。"
            return 1
        fi
    fi

    local npm_bin
    npm_bin="$(command -v npm 2>/dev/null || echo "$NERMES_HOME/node/bin/npm")"
    if [ ! -x "$npm_bin" ]; then
        log_error "未找到 npm"
        return 1
    fi

    log_info "正在安装 agent-browser..."
    local log_file
    log_file="$(mktemp)"
    if ! "$npm_bin" install -g --prefix "$NERMES_HOME/node" --silent --ignore-scripts \
        "agent-browser@^0.26.0" \
        "@askjo/camofox-browser@^1.5.2" \
        >"$log_file" 2>&1; then
        log_error "npm install 失败："
        cat "$log_file" >&2
        rm -f "$log_file"
        return 1
    fi
    rm -f "$log_file"
    export PATH="$NERMES_HOME/node/bin:$PATH"

    local sys_browser
    sys_browser="$(find_system_browser 2>/dev/null || true)"
    if [ -n "$sys_browser" ]; then
        configure_browser_env_from_system_browser "$sys_browser"
        log_info "检测到系统浏览器 — 跳过 Chromium 下载"
        return 0
    fi

    log_info "正在通过 agent-browser install 安装 Chromium..."
    local ab_bin="$NERMES_HOME/node/bin/agent-browser"
    if [ -x "$ab_bin" ]; then
        "$ab_bin" install 2>/dev/null || {
            log_warn "Chromium 安装失败。如果没有系统浏览器，浏览器工具可能无法工作。"

            # OS-specific hints (detect_os sets $DISTRO)
            case "${DISTRO:-unknown}" in
                ubuntu|debian)
                    log_info "尝试：sudo apt-get install -y chromium-browser"
                    ;;
                arch)
                    log_info "尝试：sudo pacman -S chromium"
                    ;;
                fedora|rhel|centos)
                    log_info "尝试：sudo dnf install -y chromium"
                    ;;
            esac
        }
    else
        log_warn "在 $ab_bin 未找到 agent-browser"
    fi

    return 0
}

ensure_mode() {
    detect_os

    IFS=',' read -ra DEPS <<< "$ENSURE_DEPS"
    for dep in "${DEPS[@]}"; do
        dep="$(echo "$dep" | tr -d '[:space:]')"
        case "$dep" in
            node)
                check_node
                ;;
            browser)
                check_node
                if [ "$HAS_NODE" = true ]; then
                    ensure_browser
                fi
                ;;
            ripgrep)
                if ! command -v rg &>/dev/null; then
                    HAS_RIPGREP=false
                    HAS_FFMPEG=true
                    install_system_packages
                fi
                ;;
            ffmpeg)
                if ! command -v ffmpeg &>/dev/null; then
                    HAS_FFMPEG=false
                    HAS_RIPGREP=true
                    install_system_packages
                fi
                ;;
            *)
                log_warn "未知依赖：$dep"
                ;;
        esac
    done
}

postinstall_mode() {
    print_banner
    detect_os

    log_info "安装后模式：为 pip 安装设置 Nermes"

    check_node
    check_network_prerequisites
    install_system_packages

    if [ "$HAS_NODE" = true ] && [ "$SKIP_BROWSER" = false ]; then
        ensure_browser
    fi

    HERMES_CMD="$(command -v nermes 2>/dev/null || echo "")"
    if [ -n "$HERMES_CMD" ]; then
        log_info "正在运行 nermes setup..."
        "$HERMES_CMD" setup
    else
        log_warn "在 PATH 中未找到 nermes 命令"
        log_info "尝试：python -m hermes_cli.main setup"
    fi
}

# ============================================================================
# Profession selection
# ============================================================================

profession_selector() {
    local professions_dir="$INSTALL_DIR/professions"
    local selected=""

    # 检测是否有职业预设
    if [ ! -d "$professions_dir" ]; then
        return 0
    fi

    local available=()
    local display=()
    while IFS= read -r dir; do
        local name
        name="$(basename "$dir")"
        if [ -f "$dir/apply.sh" ]; then
            available+=("$name")
            # 中文显示名映射
            case "$name" in
                finance) display+=("财务（会计核算·税务·报表）") ;;
                ecommerce) display+=("电商运营（淘宝/京东/拼多多/抖音）") ;;
                *) display+=("$name") ;;
            esac
        fi
    done < <(find "$professions_dir" -maxdepth 1 -mindepth 1 -type d ! -name '.*' 2>/dev/null | sort)

    if [ ${#available[@]} -eq 0 ]; then
        return 0
    fi

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}🎯 可选：安装职业预设${NC}"
    echo ""
    echo "Nermes 支持针对不同职业优化的 AI 助手预设，"
    echo "包括专业人格、知识库和专属技能包。"
    echo ""
    echo -e "可用职业："
    for i in "${!available[@]}"; do
        echo -e "  ${GREEN}$((i+1))${NC}) ${display[$i]}"
    done
    echo -e "  ${GREEN}0${NC}) 跳过，以后再说"
    echo ""

    if [ "$IS_INTERACTIVE" = true ]; then
        read -r -p "请选择职业 [0-${#available[@]}，默认 0]: " choice || choice=""
    elif [ -r /dev/tty ] && [ -w /dev/tty ]; then
        printf "请选择职业 [0-%d，默认 0]: " "${#available[@]}" > /dev/tty
        IFS= read -r choice < /dev/tty || choice=""
    fi

    choice="${choice:-0}"
    choice="${choice#\"}\"; choice=\"${choice%\\\"}\""

    if [ "$choice" -ge 1 ] 2>/dev/null && [ "$choice" -le "${#available[@]}" ]; then
        selected="${available[$((choice-1))]}"
        echo ""
        log_info "正在应用「${display[$((choice-1))]}」职业预设..."
        if bash "$professions_dir/$selected/apply.sh"; then
            log_success "职业预设安装完成！"
            echo ""
            echo "📚 后续可安装更多专属技能包，运行："
            echo "   nermes skills install <技能名>"
        else
            log_warn "职业预设安装失败，可稍后手动安装："
            log_info "  bash $professions_dir/$selected/apply.sh"
        fi
    fi
}

# ============================================================================
# Main
# ============================================================================

main() {
    print_banner

    detect_os
    resolve_install_layout
    install_uv
    check_python
    check_git
    check_node
    check_network_prerequisites
    install_system_packages

    clone_repo
    setup_venv
    install_deps
    install_node_deps
    setup_path
    copy_config_templates
    run_setup_wizard
    maybe_start_gateway

    print_success

    echo "git" > "$NERMES_HOME/.install_method"

    profession_selector
}

if [ -n "$ENSURE_DEPS" ]; then
    ensure_mode
elif [ "$POSTINSTALL_MODE" = true ]; then
    postinstall_mode
else
    main
fi

#!/usr/bin/env python3
"""知识库维护工具 — 增/改/删知识条目，记录更新历史。

Agent 遇到以下情况时调用此工具：
- 用户纠正了某个错误知识 → update_knowledge()
- 对话中发现值得沉淀的新知识 → add_knowledge()
- 发现某条知识已过时 → mark_stale()
- 用户要求查看知识库更新历史 → get_maintenance_log()
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict


# ── 路径工具 ────────────────────────────────────────────────────

def _resolve_knowledge_dir() -> str:
    """解析知识库目录，优先使用有 .md 文件的目录。"""
    nermes_home = os.environ.get(
        "NERMES_HOME",
        os.environ.get("HERMES_HOME", os.path.expanduser("~/.nermes"))
    )

    candidates = [
        os.path.join(nermes_home, "professions", "finance", "knowledge"),
    ]

    # 项目目录（knowledge_maintain.py 在 professions/finance/tools/ 下）
    tool_dir = os.path.dirname(os.path.abspath(__file__))
    finance_dir = os.path.dirname(tool_dir)
    candidates.append(os.path.join(finance_dir, "knowledge"))

    # 项目根目录
    if finance_dir.endswith("professions"):
        project_root = os.path.dirname(finance_dir)
        candidates.append(os.path.join(
            os.path.dirname(project_root), "professions", "finance", "knowledge"
        ))

    # 返回第一个包含 .md 文件的目录
    for candidate in candidates:
        if os.path.isdir(candidate):
            has_md = any(f.endswith(".md") for f in os.listdir(candidate))
            if has_md:
                return candidate

    # 都为空时创建并返回用户目录
    user_knowledge = candidates[0]
    os.makedirs(user_knowledge, exist_ok=True)
    return user_knowledge


def _get_maintenance_log_path() -> str:
    """获取维护日志路径。"""
    nermes_home = os.environ.get(
        "NERMES_HOME",
        os.environ.get("HERMES_HOME", os.path.expanduser("~/.nermes"))
    )
    return os.path.join(nermes_home, "knowledge_maintenance_log.jsonl")


# ═══════════════════════════════════════════════════════════════
# 文件操作
# ═══════════════════════════════════════════════════════════════

def _list_knowledge_files() -> List[str]:
    """列出所有知识库 .md 文件。"""
    kb_dir = _resolve_knowledge_dir()
    return sorted([
        f for f in os.listdir(kb_dir)
        if f.endswith(".md") and not f.startswith(".")
    ])


def _read_file(filepath: str) -> List[str]:
    """读取文件为行列表。"""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.readlines()


def _write_file(filepath: str, lines: List[str]):
    """写入行列表到文件。"""
    with open(filepath, "r", encoding="utf-8") as f:
        original = f.read()
    new_content = "".join(lines)
    if new_content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)


def _log_action(action: str, detail: dict):
    """记录维护日志。"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        **detail,
    }
    log_path = _get_maintenance_log_path()
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ═══════════════════════════════════════════════════════════════
# 核心操作
# ═══════════════════════════════════════════════════════════════

def add_knowledge(
    file_name: str,
    section_title: str,
    content: str,
) -> dict:
    """向指定知识库文件追加一个新的章节。

    Args:
        file_name: 目标文件名，如 'tax-rates.md'。不存在则创建新文件。
        section_title: 章节标题（不含 # 号，会自动添加 ## 前缀）
        content: 章节内容（markdown 格式）

    Returns:
        dict: {"status": "added", "file": ..., "section": ..., "preview": ...}
    """
    kb_dir = _resolve_knowledge_dir()
    filepath = os.path.join(kb_dir, file_name)

    section = f"\n## {section_title}\n\n{content.strip()}\n"

    if os.path.exists(filepath):
        lines = _read_file(filepath)
        lines.append("\n")
        lines.append(section)
    else:
        # 创建新文件
        lines = [
            f"# {file_name.replace('.md', '').replace('-', ' ').title()}\n",
            "\n",
            "> 用户通过对话新增的知识条目。\n",
            "\n",
            section,
        ]

    _write_file(filepath, lines)
    _log_action("add", {"file": file_name, "section": section_title, "preview": content[:200]})

    return {
        "status": "added",
        "file": file_name,
        "section": section_title,
        "preview": content[:200],
    }


def update_knowledge(
    file_name: str,
    section_title: str,
    old_text: str,
    new_text: str,
) -> dict:
    """更新知识库文件中指定章节的内容。

    Args:
        file_name: 目标文件名
        section_title: 章节标题（用于定位）
        old_text: 要替换的旧文本片段（必须能在文件中找到）
        new_text: 替换后的新文本

    Returns:
        dict: {"status": "updated"|"not_found", "file": ..., "section": ...}
    """
    kb_dir = _resolve_knowledge_dir()
    filepath = os.path.join(kb_dir, file_name)

    if not os.path.exists(filepath):
        return {"status": "not_found", "error": f"文件 {file_name} 不存在"}

    content = "".join(_read_file(filepath))
    if old_text not in content:
        return {
            "status": "not_found",
            "error": f"未找到匹配的旧文本",
            "hint": "请提供更精确的原文片段（包含30字以上）",
        }

    new_content = content.replace(old_text, new_text, 1)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    _log_action("update", {
        "file": file_name,
        "section": section_title,
        "old_preview": old_text[:200],
        "new_preview": new_text[:200],
    })

    return {
        "status": "updated",
        "file": file_name,
        "section": section_title,
    }


def mark_stale(
    file_name: str,
    section_title: str,
    reason: str,
) -> dict:
    """标记某章节已过时（在章节标题后添加 ⚠️ 标记和说明）。

    Args:
        file_name: 目标文件名
        section_title: 章节标题
        reason: 过时原因（如"2027年税率调整"）

    Returns:
        dict: {"status": "marked_stale", "file": ..., "section": ...}
    """
    kb_dir = _resolve_knowledge_dir()
    filepath = os.path.join(kb_dir, file_name)

    if not os.path.exists(filepath):
        return {"status": "not_found", "error": f"文件 {file_name} 不存在"}

    lines = _read_file(filepath)
    stale_marker = f"> ⚠️ **已过时** — {reason}\n>\n"

    heading_pattern = re.compile(rf"^(##\s+{re.escape(section_title)})\s*$")
    inserted = False
    new_lines = []

    for i, line in enumerate(lines):
        new_lines.append(line)
        if heading_pattern.match(line.strip()):
            # 在标题后的空行前插入标记
            if i + 1 < len(lines) and lines[i + 1].strip() == "":
                new_lines.append(stale_marker)
                inserted = True

    if not inserted:
        return {"status": "not_found", "error": f"未找到章节「{section_title}」"}

    _write_file(filepath, new_lines)
    _log_action("mark_stale", {
        "file": file_name,
        "section": section_title,
        "reason": reason,
    })

    return {
        "status": "marked_stale",
        "file": file_name,
        "section": section_title,
    }


def get_maintenance_log(limit: int = 20) -> dict:
    """查看知识库维护历史。

    Returns:
        dict: {"total": N, "recent": [...]}
    """
    log_path = _get_maintenance_log_path()
    if not os.path.exists(log_path):
        return {"total": 0, "recent": []}

    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return {
        "total": len(entries),
        "recent": entries[-limit:],
    }


def get_knowledge_stats() -> dict:
    """获取知识库统计信息。

    Returns:
        dict: {"files": N, "total_lines": N, "file_list": [...]}
    """
    kb_dir = _resolve_knowledge_dir()
    files = _list_knowledge_files()
    total_lines = 0
    file_info = []

    for f in files:
        path = os.path.join(kb_dir, f)
        with open(path, "r", encoding="utf-8") as fh:
            lines = len(fh.readlines())
        total_lines += lines
        file_info.append({"name": f, "lines": lines})

    return {
        "files": len(files),
        "total_lines": total_lines,
        "file_list": file_info,
    }


# ═══════════════════════════════════════════════════════════════
# 命令行入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python knowledge_maintain.py <action> [args...]")
        print("  stats    — 知识库统计")
        print("  log      — 查看维护历史")
        sys.exit(0)

    action = sys.argv[1]
    if action == "stats":
        stats = get_knowledge_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    elif action == "log":
        log = get_maintenance_log(limit=int(sys.argv[2]) if len(sys.argv) > 2 else 20)
        print(json.dumps(log, ensure_ascii=False, indent=2))
    else:
        print(f"未知操作: {action}")

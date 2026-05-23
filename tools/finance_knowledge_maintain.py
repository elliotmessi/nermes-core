#!/usr/bin/env python3
"""注册知识库维护工具 — add / update / mark_stale / stats。

Agent 在以下场景自动调用：
- 用户说"记住..."/"这个不对，应该是..." → update_knowledge
- 发现对话中有值得沉淀的新知识 → add_knowledge
- 用户询问知识库状态 → get_knowledge_stats
"""

import os
import sys

# 将 professions/finance/tools/ 加入路径
_FINANCE_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "professions", "finance", "tools"
)
if _FINANCE_TOOLS_DIR not in sys.path:
    sys.path.insert(0, _FINANCE_TOOLS_DIR)

from knowledge_maintain import (
    add_knowledge,
    update_knowledge,
    mark_stale,
    get_maintenance_log,
    get_knowledge_stats,
    _list_knowledge_files,
)

from tools.registry import registry

# ── Schema ──────────────────────────────────────────────────────

KNOWLEDGE_MAINTAIN_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["add", "update", "mark_stale", "stats", "log", "list"],
            "description": (
                "操作类型：\n"
                "- add: 新增知识条目\n"
                "- update: 更新已有内容\n"
                "- mark_stale: 标记过时\n"
                "- stats: 查看知识库统计\n"
                "- log: 查看维护历史\n"
                "- list: 列出所有知识文件"
            ),
        },
        "file_name": {
            "type": "string",
            "description": (
                "目标文件名（add/update/mark_stale 时必填），"
                "如 'tax-rates.md'。新增时会自动创建。"
            ),
        },
        "section_title": {
            "type": "string",
            "description": "章节标题（add/update/mark_stale 时必填），不含 # 号。",
        },
        "content": {
            "type": "string",
            "description": "新增的完整内容（add 时必填），markdown 格式。",
        },
        "old_text": {
            "type": "string",
            "description": "要替换的旧文本（update 时必填），至少30字以确保唯一匹配。",
        },
        "new_text": {
            "type": "string",
            "description": "替换后的新文本（update 时必填）。",
        },
        "reason": {
            "type": "string",
            "description": "过时原因（mark_stale 时必填），如 '2027年税率调整'。",
        },
    },
    "required": ["action"],
}


# ── Handler ─────────────────────────────────────────────────────

def finance_knowledge_maintain_handler(args, **kwargs):
    """执行知识库维护操作。"""
    action = args.get("action", "stats")

    if action == "stats":
        stats = get_knowledge_stats()
        lines = ["## 📚 知识库统计\n"]
        lines.append(f"- 文件数：{stats['files']}")
        lines.append(f"- 总行数：{stats['total_lines']}")
        lines.append("\n### 文件列表\n")
        for f in stats["file_list"]:
            lines.append(f"- {f['name']}（{f['lines']} 行）")
        return "\n".join(lines)

    if action == "log":
        log = get_maintenance_log(limit=args.get("limit", 10))
        lines = [f"## 📝 维护历史（共 {log['total']} 条）\n"]
        for entry in log["recent"][-10:]:
            lines.append(
                f"- {entry['timestamp'][:19]} | {entry['action']} | "
                f"{entry.get('file', '')} | {entry.get('section', '')}"
            )
        return "\n".join(lines) if len(log["recent"]) > 0 else "暂无维护记录。"

    if action == "list":
        files = _list_knowledge_files()
        return "## 📁 知识库文件\n\n" + "\n".join(f"- {f}" for f in files)

    # 需要参数的操作
    file_name = args.get("file_name", "")
    section_title = args.get("section_title", "")

    if not file_name or not section_title:
        return "❌ add/update/mark_stale 操作需要 file_name 和 section_title 参数。"

    if action == "add":
        content = args.get("content", "")
        if not content:
            return "❌ add 操作需要 content 参数。"
        result = add_knowledge(file_name, section_title, content)
        if result["status"] == "added":
            return (
                f"✅ 已添加知识条目\n"
                f"- 文件：{file_name}\n"
                f"- 章节：{section_title}\n"
                f"- 预览：{result['preview'][:150]}..."
            )

    elif action == "update":
        old_text = args.get("old_text", "")
        new_text = args.get("new_text", "")
        if not old_text or not new_text:
            return "❌ update 操作需要 old_text 和 new_text 参数。"
        result = update_knowledge(file_name, section_title, old_text, new_text)
        if result["status"] == "updated":
            return f"✅ 已更新 {file_name} → {section_title}"
        return f"❌ 更新失败：{result.get('error', '未知错误')}"

    elif action == "mark_stale":
        reason = args.get("reason", "")
        if not reason:
            return "❌ mark_stale 操作需要 reason 参数。"
        result = mark_stale(file_name, section_title, reason)
        if result["status"] == "marked_stale":
            return f"⚠️ 已标记为过时：{file_name} → {section_title}（{reason}）"
        return f"❌ 标记失败：{result.get('error', '未知错误')}"

    return "❌ 未知操作。"


# ── Register ─────────────────────────────────────────────────────

registry.register(
    name="finance_knowledge_maintain",
    toolset="nermes",
    schema=KNOWLEDGE_MAINTAIN_SCHEMA,
    handler=finance_knowledge_maintain_handler,
    check_fn=lambda: os.path.isdir(
        os.path.join(
            _FINANCE_TOOLS_DIR, "..", "..", "..",
            "professions", "finance", "knowledge"
        )
    ),
    emoji="📝",
    description="维护本地财务知识库：新增、更新、标记过时、查看统计。用户纠正错误或提供新知识点时自动调用。",
    max_result_size_chars=20_000,
)

__all__ = ["finance_knowledge_maintain_handler"]

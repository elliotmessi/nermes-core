#!/usr/bin/env python3
"""Nermes 财务知识库检索工具 — 注册为 Hermes 原生工具。

加载 professions/finance/knowledge/ 目录下所有 .md 文件，
使用 TF-IDF 进行语义检索，返回最相关段落。

当用户提出财务、税务、会计、审计、预算、成本等专业问题时，
Agent 会通过此工具自动检索本地知识库，精准返回相关章节。
"""

import os
import sys

# 将 professions/finance/tools/ 加入路径以导入 search_knowledge
_FINANCE_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "professions", "finance", "tools"
)
if _FINANCE_TOOLS_DIR not in sys.path:
    sys.path.insert(0, _FINANCE_TOOLS_DIR)

from search_knowledge import search_knowledge, reload_knowledge

from tools.registry import registry

# ── Schema ──────────────────────────────────────────────────────

FINANCE_KNOWLEDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "搜索关键词或问题，中文/英文均可。例如：'增值税税率'、'差旅费分录'、'现金流断裂怎么办'",
        },
        "top_k": {
            "type": "integer",
            "description": "返回结果数量，默认 5，最大 10",
            "default": 5,
        },
    },
    "required": ["query"],
}

# ── Handler ─────────────────────────────────────────────────────

def finance_knowledge_search_handler(args, **kwargs):
    """执行财务知识库搜索。

    从 ~/.nermes/professions/finance/knowledge/ 或
    {project_root}/professions/finance/knowledge/ 加载 md 文件，
    返回 top_k 个最相关段落。
    """
    query = args.get("query", "")
    top_k = min(args.get("top_k", 5), 10)
    results = search_knowledge(query, top_k=top_k)
    if not results:
        return "未找到与「{}」相关的知识段落。".format(query)

    lines = ["## 财务知识库检索结果\n"]
    lines.append("查询：「{}」\n".format(query))
    for i, r in enumerate(results, 1):
        lines.append("### {}. {}（来源：{}，相关度：{}）".format(
            i, r["title"], r["file"], r["relevance"]
        ))
        # 截断过长的内容（保留前 2000 字符作为上下文）
        content = r["content"]
        if len(content) > 2000:
            content = content[:2000] + "\n...（内容过长，已截断。可缩小查询范围获取精确结果）"
        lines.append(content)
        lines.append("")
    return "\n".join(lines)


# ── Check ────────────────────────────────────────────────────────

def _check_knowledge_dir():
    """检查知识库目录是否存在且非空。"""
    for candidate in [
        os.path.expanduser("~/.nermes/professions/finance/knowledge"),
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "professions", "finance", "knowledge"
        ),
    ]:
        if os.path.isdir(candidate) and any(
            f.endswith(".md") for f in os.listdir(candidate)
        ):
            return True
    return False


# ── Register ─────────────────────────────────────────────────────

registry.register(
    name="finance_knowledge_search",
    toolset="nermes",
    schema=FINANCE_KNOWLEDGE_SCHEMA,
    handler=finance_knowledge_search_handler,
    check_fn=_check_knowledge_dir,
    emoji="📚",
    description="搜索本地财务专业知识库（会计准则、税务、分录、审计、预算、成本等）。"
                "当用户提出专业财务问题时自动调用。",
    max_result_size_chars=50_000,
)

# ── 模块导出 ─────────────────────────────────────────────────────

__all__ = ["finance_knowledge_search_handler", "reload_knowledge"]

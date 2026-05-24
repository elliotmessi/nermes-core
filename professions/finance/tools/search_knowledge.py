#!/usr/bin/env python3
"""财务知识库全文搜索工具 — 加载 knowledge/*.md，TF-IDF 关键词匹配搜索。

功能：
1. 加载 knowledge/ 目录下所有 .md 文件内容
2. 根据用户查询关键词搜索匹配段落
3. 返回相关段落 + 来源文件

工具函数接口：search_knowledge(query: str, top_k: int = 3) -> list[dict]
每个结果包含：file(文件名), title(段落标题), content(内容), relevance(相关度分数)

使用 Python 标准库实现，无需外部依赖。
"""

import glob
import math
import os
import re
from collections import Counter
from typing import List, Dict

# ── 路径配置 ────────────────────────────────────────────────────

def _resolve_knowledge_dir() -> str:
    """解析知识库目录，优先使用用户数据目录 ~/.nermes/ 中有内容的版本。"""
    nermes_home = os.environ.get(
        "NERMES_HOME",
        os.path.expanduser("~/.nermes")
    )

    # 候选路径列表（按优先级）
    candidates = [
        os.path.join(nermes_home, "professions", "finance", "knowledge"),
    ]

    # 工具所在目录的上级（professions/finance/）
    tool_dir = os.path.dirname(os.path.abspath(__file__))
    finance_dir = os.path.dirname(tool_dir)
    candidates.append(os.path.join(finance_dir, "knowledge"))

    # 项目根目录下的 professions/finance/knowledge/
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

    # 都为空时返回用户目录（用于后续写入）
    return candidates[0]


_KNOWLEDGE_DIR = _resolve_knowledge_dir()

# ── 预处理 ──────────────────────────────────────────────────────

# 分词：中文字符 + 英文字母数字（单独处理）
_CHINESE_CHAR = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]", re.UNICODE)
_ALPHA_NUM = re.compile(r"[a-zA-Z0-9]+", re.UNICODE)


def _tokenize(text: str) -> List[str]:
    """将文本分词为词项列表（中文单字 + 连续中文字符作 bigram + 英文单词）。
    
    中文使用 unigram + bigram 组合以保证匹配效果。
    """
    text = text.lower()
    tokens = []
    
    # 1. 提取英文单词
    for m in _ALPHA_NUM.finditer(text):
        word = m.group()
        if len(word) >= 2:
            tokens.append(word)
    
    # 2. 提取所有中文字符
    chinese_chars = _CHINESE_CHAR.findall(text)
    # 中文字符 unigram
    tokens.extend(chinese_chars)
    # 中文字符 bigram（连续两个中文字符）
    for i in range(len(chinese_chars) - 1):
        tokens.append(chinese_chars[i] + chinese_chars[i+1])
    
    return tokens


def _load_markdown(filepath: str) -> List[Dict]:
    """加载单个 .md 文件，按标题分割为段落。

    返回 [{"title": str, "content": str, "file": str, "tokens": [str]}, ...]
    """
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    filename = os.path.basename(filepath)
    paragraphs = []

    # 按 Markdown 标题行分割（# ## ### ####）
    lines = text.split("\n")
    current_title = filename  # 默认段落标题为文件名
    current_lines = []

    heading_pattern = re.compile(r"^(#{1,4})\s+(.+)$")

    for line in lines:
        m = heading_pattern.match(line)
        if m:
            # 保存上一段落
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    paragraphs.append({
                        "file": filename,
                        "title": current_title,
                        "content": content,
                        "tokens": _tokenize(content),
                    })
            current_title = m.group(2).strip()
            current_lines = []
        else:
            # 跳过注释行 <!--...-->
            if line.strip().startswith("<!--"):
                continue
            current_lines.append(line)

    # 保存最后一段
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            paragraphs.append({
                "file": filename,
                "title": current_title,
                "content": content,
                "tokens": _tokenize(content),
            })

    return paragraphs


def _load_all_knowledge() -> List[Dict]:
    """加载 knowledge/ 目录下所有 .md 文件，返回段落列表。"""
    md_files = glob.glob(os.path.join(_KNOWLEDGE_DIR, "*.md"))
    all_paragraphs = []
    for fp in sorted(md_files):
        try:
            all_paragraphs.extend(_load_markdown(fp))
        except Exception as e:
            print(f"[search_knowledge] 警告：加载 {fp} 失败 — {e}")
    return all_paragraphs


# ── TF-IDF 实现 ─────────────────────────────────────────────────

class _TfIdfIndex:
    """基于标准库构建的轻量 TF-IDF 索引。"""

    def __init__(self, documents: List[Dict]):
        self.documents = documents
        self.n_docs = len(documents)

        # 构建词项 → 包含该词项的文档数
        self.df: Dict[str, int] = Counter()
        for doc in documents:
            unique_tokens = set(doc["tokens"])
            for token in unique_tokens:
                self.df[token] += 1

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """对查询做 TF-IDF 相似度排序，返回 top_k 结果。"""
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        # 查询词频（query 内）
        q_tf = Counter(query_tokens)

        # 对每个文档计算 TF-IDF 余弦相似度
        scored = []
        for idx, doc in enumerate(self.documents):
            doc_tokens = doc["tokens"]
            if not doc_tokens:
                continue

            # 文档词频
            doc_tf = Counter(doc_tokens)
            doc_norm = math.sqrt(
                sum((1.0 + math.log(tf)) ** 2 for tf in doc_tf.values())
            )
            if doc_norm == 0:
                continue

            # 计算点积：∑ TF(t,q) * TF(t,d) * IDF(t)
            dot = 0.0
            for token, qtf in q_tf.items():
                if token not in doc_tf:
                    continue
                # TF(t,q) = 1 + log(qtf)
                tf_q = 1.0 + math.log(qtf)
                # TF(t,d) = 1 + log(tf_d)
                tf_d = 1.0 + math.log(doc_tf[token])
                # IDF(t) = log(1 + N / df)
                idf = 1.0 + math.log(self.n_docs / (1.0 + self.df.get(token, 0)))
                dot += tf_q * tf_d * idf

            if dot == 0:
                continue

            # 简化的余弦归一化（仅用文档向量范数）
            similarity = dot / doc_norm
            # 添加命中比例增益（提升包含更多查询词的文档）
            hit_ratio = len(set(query_tokens) & set(doc_tokens)) / len(query_tokens)
            score = similarity * (0.7 + 0.3 * hit_ratio)

            scored.append({
                "file": doc["file"],
                "title": doc["title"],
                "content": doc["content"],
                "relevance": round(score, 4),
            })

        # 按相关度降序
        scored.sort(key=lambda x: x["relevance"], reverse=True)
        return scored[:top_k]


# ── 全局索引（懒加载） ─────────────────────────────────────────

_INDEX: _TfIdfIndex = None


def _get_index() -> _TfIdfIndex:
    """获取或构建全局 TF-IDF 索引（单例模式）。"""
    global _INDEX
    if _INDEX is None:
        docs = _load_all_knowledge()
        _INDEX = _TfIdfIndex(docs)
    return _INDEX


# ── 搜索日志（知识缺口发现） ───────────────────────────────────

def _log_search(query: str, result_count: int, top_score: float):
    """记录搜索日志，用于发现知识缺口。"""
    import json as _json
    from datetime import datetime as _dt

    nermes_home = os.environ.get(
        "NERMES_HOME",
        os.path.expanduser("~/.nermes")
    )
    log_dir = os.path.join(nermes_home, "logs")
    os.makedirs(log_dir, exist_ok=True)

    entry = {
        "timestamp": _dt.now().isoformat(),
        "query": query,
        "results": result_count,
        "top_score": round(top_score, 4) if top_score else 0,
        "found": result_count > 0 and top_score > 0.5,
    }

    log_path = os.path.join(log_dir, "knowledge_search_log.jsonl")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(_json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 日志写入失败不影响搜索功能


def get_search_gaps(min_queries: int = 3) -> list:
    """分析搜索日志，返回可能的知识缺口（频繁搜索但无结果或低相关度的查询）。

    Returns:
        list[dict]: [{"query": ..., "count": N, "avg_score": ...}, ...]
    """
    import json as _json
    from collections import defaultdict as _dd

    nermes_home = os.environ.get(
        "NERMES_HOME",
        os.path.expanduser("~/.nermes")
    )
    log_path = os.path.join(nermes_home, "logs", "knowledge_search_log.jsonl")
    if not os.path.exists(log_path):
        return []

    # 按查询关键词聚合
    query_stats = _dd(lambda: {"count": 0, "scores": [], "found_count": 0})

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = _json.loads(line)
                q = entry.get("query", "")
                # 用前20字符作为聚合键（去重近似查询）
                key = q[:30]
                query_stats[key]["count"] += 1
                query_stats[key]["scores"].append(entry.get("top_score", 0))
                if entry.get("found"):
                    query_stats[key]["found_count"] += 1
            except (ValueError, KeyError):
                continue

    gaps = []
    for query, stats in query_stats.items():
        if stats["count"] >= min_queries:
            avg_score = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0
            found_ratio = stats["found_count"] / stats["count"]
            # 找到率低于50%的视为缺口
            if found_ratio < 0.5 or avg_score < 0.3:
                gaps.append({
                    "query": query,
                    "count": stats["count"],
                    "avg_score": round(avg_score, 3),
                    "found_ratio": round(found_ratio, 2),
                })

    gaps.sort(key=lambda g: g["count"], reverse=True)
    return gaps[:10]


# ── 公开接口 ─────────────────────────────────────────────────────

def search_knowledge(query: str, top_k: int = 3) -> List[Dict]:
    """财务知识库全文搜索。

    Args:
        query: 用户查询关键词（中文/英文均可）
        top_k: 返回结果数量，默认 3

    Returns:
        list[dict]: 每个结果包含：
            - file(str):     来源文件名
            - title(str):    段落标题
            - content(str):  段落内容
            - relevance(float): 相关度分数（0~1，越高越相关）
    """
    index = _get_index()
    results = index.search(query, top_k=top_k)
    top_score = results[0]["relevance"] if results else 0
    _log_search(query, len(results), top_score)
    return results


def reload_knowledge():
    """重新加载知识库（文件增删后调用）。"""
    global _INDEX
    _INDEX = None
    _get_index()


# ── 命令行入口 ───────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "增值税"
    top_k = 5
    results = search_knowledge(query, top_k=top_k)
    if not results:
        print(f"未找到与「{query}」相关的内容。（knowledge/ 目录可能为空）")
    else:
        print(f"搜索「{query}」的结果（top {top_k}）：")
        print("=" * 60)
        for i, r in enumerate(results, 1):
            print(f"\n{i}. 文件：{r['file']}")
            print(f"   标题：{r['title']}")
            print(f"   相关度：{r['relevance']}")
            # 显示前 200 字符的摘要
            preview = r["content"][:200].replace("\n", " ")
            print(f"   摘要：{preview}...")

#!/usr/bin/env python3
"""全量扫描源码中的英文字符串，评估是否为需要汉化的英文文案。

扫描策略：
  1. Python 文件 (.py): 用 ast 模块解析，提取所有字符串常量
  2. TypeScript/JavaScript (.ts/.tsx/.js/.mjs): 用正则提取引号/模板字符串
  3. 启发式过滤：去掉路径、URL、flag、纯标识符，保留可能的英文文案
  4. 分类：user_visible（用户可见）/ developer_facing（开发者文档）/ unknown
  5. 输出 JSON 报告 + 人类可读摘要

用法：
  python scripts/scan_english_strings.py [--dir DIR] [--output FILE] [--max-per-file N]
"""

import argparse
import ast
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# ── 排除目录 ──
EXCLUDE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".tox",
    "dist", "build", ".eggs", "*.egg-info", "website/.docusaurus",
    "website/build", "ui-tui/node_modules", ".mypy_cache", ".pytest_cache",
    "assets",  # 静态资源常有 minified code
}

# ── 排除文件模式 ──
EXCLUDE_FILE_PATTERNS = [
    r".*\.min\.(js|ts|css)$",
    r".*/package-lock\.json$",
    r".*/pnpm-lock\.yaml$",
    r".*/poetry\.lock$",
    r".*\.pyc$",
    r".*/site-packages/.*",
]

# ── 非英文文案的典型模式 ──
NON_COPY_PATTERNS = [
    # 路径
    r"^(\.{1,2}/|/[\w/]+|[A-Za-z]:\\)",  # ./ ../ /path C:\
    # URL
    r"^https?://",
    r"^wss?://",
    # CLI flags
    r"^--?[a-z][a-z-]*$",
    # 纯格式字符串
    r"^\{(0*:?\.?\d*[dfxs]?)\}$",
    r"^\{[a-zA-Z_]\w*\}$",
    r"^%[dsr]\)?$",
    # 版本号
    r"^\d+\.\d+(\.\d+)?(-[\w.]+)?$",
    # 纯标识符（无空格，snake_case 或 camelCase）
    r"^[a-z_][a-z0-9_]*$",
    r"^[a-z][a-zA-Z0-9]*$",
    # MIME 类型
    r"^[\w-]+/[\w.+-]+$",
    # 文件扩展名
    r"^\.[a-z][a-z0-9]*$",
    # 纯数字/编码
    r"^[\d\s.,;:_\-+*/%=<>!@#$^&*()\[\]{}|~`]+$",
    # JSON Schema / config key
    r"^[a-z][a-zA-Z]*(?:\.[a-z][a-zA-Z]*)+$",
    # HTML/XML 标签
    r"^</?[a-z][a-z0-9]*(?:\s+[\w-]+(?:=\"[^\"]*\")?)*\s*/?>$",
    # 单个单词（太短无法判断）
    r"^[A-Za-z]{1,10}$",
    # SQL 语句
    r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|GRANT|REVOKE|BEGIN|COMMIT|ROLLBACK|EXPLAIN|PRAGMA)\s",
    # 正则表达式
    r"^\(\?[imsx]?[imsx]?\)",
    # 纯变量插值占位
    r"^%[sd](\s|$)",
]

# ── 英文文案的典型信号 ──
COPY_SIGNALS = [
    r"\b(the|and|you|your|this|that|with|from|have|will|can|should|would|could|please|click|select|choose|enter|type|search|find|view|show|hide|open|close|save|delete|create|update|remove|add|edit|copy|paste|send|receive|download|upload|install|setup|configure|enable|disable|start|stop|restart|run|build|test|deploy|check|verify|confirm|cancel|submit|reset|clear|filter|sort|export|import|backup|restore|refresh|reload|retry|skip|continue|abort|exit|quit|help|error|warning|info|success|failed|complete|done|ready|loading|processing|connecting|waiting|welcome|goodbye|hello|thanks|sorry|oops)\b",
    r"[.!?]\s*$",       # 以标点结尾（句子）
    r"^[A-Z]",          # 大写开头（句子或标题）
    r"\s{2,}",          # 多空格（格式化文本）
    r"\n",              # 多行文本
    r"[:;,]?\s+(and|or|but|so|because|if|when|while|after|before)\s+",  # 连词
    r"['\u2018\u2019\u201c\u201d]",  # 含引号（对话/引用）
    r"\([^)]+\)",       # 括号内说明
]

# ── Python AST 扫描 ──

def _get_docstring_nodes(tree: ast.AST) -> set:
    """收集所有 docstring 节点（模块/类/函数的第一条语句）。"""
    docstrings = set()

    def _check_body(body):
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            if isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))

    # 模块级
    if hasattr(tree, "body"):
        _check_body(tree.body)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            _check_body(node.body)

    return docstrings


def _get_string_context(node: ast.AST) -> str:
    """通过 AST 节点属性推断字符串所在上下文。"""
    # 检查是否是字典 key
    # 简单启发式：看字符串是否在赋值语句中作为 key
    ctx = "unknown"
    # 用源码行做进一步推断（在后续处理中完成）
    return ctx


def extract_python_strings(filepath: str) -> list[dict]:
    """用 AST 提取 Python 文件中的所有字符串字面量。"""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, UnicodeDecodeError, RecursionError):
        return []

    docstring_ids = _get_docstring_nodes(tree)
    results = []
    lines = source.split("\n")

    class StringCollector(ast.NodeVisitor):
        def visit_Constant(self, node):
            if isinstance(node.value, str) and len(node.value) >= 3:
                is_doc = id(node) in docstring_ids
                results.append({
                    "text": node.value,
                    "line": node.lineno if hasattr(node, "lineno") else 0,
                    "col": node.col_offset if hasattr(node, "col_offset") else 0,
                    "is_docstring": is_doc,
                    "context": "docstring" if is_doc else "string",
                })

        def visit_JoinedStr(self, node):
            # f-string: 提取其中非表达式的字符串部分
            for part in node.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    if len(part.value) >= 3:
                        results.append({
                            "text": part.value,
                            "line": node.lineno if hasattr(node, "lineno") else 0,
                            "col": node.col_offset if hasattr(node, "col_offset") else 0,
                            "is_docstring": False,
                            "context": "f-string",
                        })

    StringCollector().visit(tree)

    # 用行号获取源码行作为上下文
    for item in results:
        if item["line"] > 0 and item["line"] <= len(lines):
            src_line = lines[item["line"] - 1].strip()
            item["src_line"] = src_line[:200]
        else:
            item["src_line"] = ""

    return results


# ── TypeScript/JavaScript 正则扫描 ──

# 字符串正则：匹配单引号、双引号、模板字符串
# 简化策略：用字符级扫描避免跨行和转义的复杂性
TS_STRING_RE = re.compile(
    r"""(?<!\\)(['"])((?:(?!\1).|\\.)*?)\1""",  # 单/双引号字符串
    re.DOTALL,
)
TS_TEMPLATE_RE = re.compile(
    r"(?<!\\)`((?:(?!`).|\\.)*?)`",  # 模板字符串
    re.DOTALL,
)


def extract_ts_strings(filepath: str) -> list[dict]:
    """用正则提取 TS/JS 文件中的字符串字面量。"""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except (UnicodeDecodeError, IsADirectoryError):
        return []

    lines = source.split("\n")
    results = []

    for regex, quote_type in [(TS_STRING_RE, "quote"), (TS_TEMPLATE_RE, "template")]:
        for match in regex.finditer(source):
            text = match.group(1) if quote_type == "template" else match.group(2)
            if len(text) < 3:
                continue
            # 跳过纯 JSX/HTML 属性值（过于短或只有变量插值）
            if quote_type == "template" and re.match(r"^\s*\$\{[^}]*\}\s*$", text):
                continue

            # 计算行号
            line_num = source[: match.start()].count("\n") + 1
            if line_num <= len(lines):
                src_line = lines[line_num - 1].strip()[:200]
            else:
                src_line = ""

            results.append({
                "text": text,
                "line": line_num,
                "col": 0,
                "is_docstring": False,
                "context": f"ts-{quote_type}",
                "src_line": src_line,
            })

    return results


# ── 启发式过滤 ──

def is_likely_copy(item: dict) -> tuple[bool, str, float]:
    """判断字符串是否为英文文案。

    接受完整的 item dict（含 text, is_docstring, src_line, context 等），
    综合 AST 上下文和文本内容进行判断。

    Returns:
        (is_copy, classification, confidence)
        classification: "user_visible" | "developer_facing" | "not_copy"
        confidence: 0.0 - 1.0
    """
    text = item.get("text", "")
    stripped = text.strip()

    if len(stripped) < 10:
        return False, "not_copy", 0.0

    # ── 快速排除：纯代码/路径/URL 模式 ──
    for pattern in NON_COPY_PATTERNS:
        if re.match(pattern, stripped):
            return False, "not_copy", 0.0

    # ── 计算英文单词数量 ──
    words = re.findall(r"[a-zA-Z]{2,}", stripped)
    if not words:
        return False, "not_copy", 0.0

    # ── docstring 直接归为 developer_facing ──
    if item.get("is_docstring"):
        return True, "developer_facing", 0.85

    # ── 源码行上下文信号 ──
    src_line = item.get("src_line", "")

    # 用户可见信号（源码行中包含这些模式）
    user_line_signals = [
        r"\bhelp\s*=\s*",           # argparse help=
        r"\bdescription\s*=\s*",    # argparse description=
        r"\bepilog\s*=\s*",         # argparse epilog=
        r"\bmetavar\s*=\s*",        # argparse metavar=
        r"\bprompt\s*=\s*",         # prompt text
        r"click\.echo\(|console\.print\(|rich\.print\(",
        r"print_info\(|print_success\(|print_warning\(|print_error\(|print_header\(",
        r"\.say\(|\.reply\(|\.send_message\(|\.answer\(",
        r"\.info\(|\.success\(|\.warning\(|\.error\(|\.confirm\(|\.prompt\(",
        r"Prompt\.ask\(|Confirm\.ask\(|questionary\.|inquirer\.",
        r"input\s*\(\s*$",          # input() prompt
        r"panel\(|Panel\(|Table\(|Column\(|Row\(",
        r"Text\(|Markdown\(|Syntax\(",
        r"renderable|Renderable",
    ]

    # 开发者信号
    dev_line_signals = [
        r"logger\.|_logger\.|LOG\.|logging\.",
        r"raise\s+\w+Error|raise\s+\w+Exception",
        r"assert\s+",
        r"warnings\.warn",
        r"DEBUG|_DEBUG",
        r"traceback|Traceback",
        r"__doc__\s*=",
        r"#\s*(TODO|FIXME|HACK|XXX|NOTE)",
        r"@deprecated|@abstractmethod|@override",
        r"typing\.|TypeVar|Generic\[",
        r"isinstance\(|hasattr\(|getattr\(",
        r"re\.compile\(|re\.match\(|re\.search\(",
        r"test_|\.test\(|TestCase|@pytest",
    ]

    # 统计源码行信号
    user_line_score = sum(1 for p in user_line_signals if re.search(p, src_line))
    dev_line_score = sum(1 for p in dev_line_signals if re.search(p, src_line))

    # ── 文本内容信号 ──
    text_signals = 0
    for pattern in COPY_SIGNALS:
        if re.search(pattern, stripped):
            text_signals += 1

    # 额外文本信号
    if len(words) >= 4:
        text_signals += 1
    if len(stripped) > 40:
        text_signals += 0.5
    if re.search(r"[A-Z][a-z]+\s+[a-z]+", stripped):
        text_signals += 1

    max_text_signals = len(COPY_SIGNALS) + 2.5
    text_confidence = min(text_signals / max_text_signals, 1.0)

    # ── 文本中的用户/开发者信号 ──
    user_text = re.findall(
        r"\b(click|select|choose|enter|type|search|find|view|show|hide|"
        r"open|close|save|delete|create|update|remove|add|edit|welcome|"
        r"hello|goodbye|please|error|warning|success|failed|try|retry|"
        r"confirm|cancel|submit|setup|install|download|upload|"
        r"press|key|button|menu|dialog|window|screen|page|tab|panel|"
        r"\byou\b|\byour\b)",
        stripped,
        re.IGNORECASE,
    )

    dev_text = re.findall(
        r"(^\s*(Args?|Returns?|Raises?|Example|Usage|Note|See also|"
        r"Parameters?|Attributes?|Methods?|Properties?)[\s:]+"
        r"|TODO|FIXME|NOTE:|Warning:|Deprecated:"
        r"|\.\.\.\s*$"
        r"|@param|@return|@raise|@deprecated|@type|@rtype"
        r"|should\s+return|should\s+raise|should\s+be"
        r"|test\s+that|test\s+the|test\s+if|test\s+when"
        r"|mock|fixture|stub|spy|dummy|fake"
        r"|\bassert|\bassertEqual|\bassertTrue|\bassertFalse)",
        stripped,
        re.IGNORECASE,
    )

    # ── 综合判断 ──

    # 1. 源码行明确的用户/开发者信号 → 直接分类
    if user_line_score > 0 and dev_line_score == 0 and text_signals >= 2:
        return True, "user_visible", min(0.7 + user_line_score * 0.1, 1.0)
    if dev_line_score > 0 and user_line_score == 0:
        return True, "developer_facing", min(0.7 + dev_line_score * 0.1, 1.0)

    # 2. 文本内容明确信号
    if len(user_text) >= 3 and len(dev_text) <= 1:
        return True, "user_visible", min(0.6 + len(user_text) * 0.05, 1.0)
    if len(dev_text) >= 3 and len(user_text) <= 1:
        return True, "developer_facing", min(0.6 + len(dev_text) * 0.05, 1.0)

    # 3. 综合文本置信度
    if text_confidence >= 0.35:
        # 比较两种信号
        user_total = user_line_score * 2 + len(user_text)
        dev_total = dev_line_score * 2 + len(dev_text)
        if user_total > dev_total:
            return True, "user_visible", text_confidence
        elif dev_total > user_total:
            return True, "developer_facing", text_confidence
        else:
            return True, "unknown", text_confidence

    return False, "not_copy", text_confidence


# ── 主扫描 ──

def should_skip_path(filepath: str, root_dir: str) -> bool:
    """判断是否应跳过该文件。"""
    rel = os.path.relpath(filepath, root_dir)

    # 检查排除目录
    parts = Path(rel).parts
    for part in parts:
        if part in EXCLUDE_DIRS:
            return True

    # 检查排除文件模式
    for pattern in EXCLUDE_FILE_PATTERNS:
        if re.match(pattern, rel):
            return True

    return False


def scan_directory(root_dir: str, max_per_file: int = 50) -> dict:
    """扫描目录下所有源码文件中的英文字符串。"""
    # 按文件类型选择提取器
    extractors = {
        ".py": extract_python_strings,
        ".ts": extract_ts_strings,
        ".tsx": extract_ts_strings,
        ".js": extract_ts_strings,
        ".mjs": extract_ts_strings,
        ".jsx": extract_ts_strings,
    }

    all_findings = []  # 所有找到的字符串（含分类）
    file_counts = defaultdict(lambda: {"total": 0, "user_visible": 0, "developer_facing": 0, "unknown": 0})
    total_files_scanned = 0
    total_strings_found = 0

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 原地过滤排除目录
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            ext = os.path.splitext(filename)[1].lower()

            if ext not in extractors:
                continue
            if should_skip_path(filepath, root_dir):
                continue

            string_items = extractors[ext](filepath)
            total_strings_found += len(string_items)
            total_files_scanned += 1

            file_findings = []
            for item in string_items:
                is_copy, classification, confidence = is_likely_copy(item)
                if is_copy:
                    finding = {
                        "file": os.path.relpath(filepath, root_dir),
                        "line": item["line"],
                        "text": item["text"][:300],  # 截断长文本
                        "classification": classification,
                        "confidence": round(confidence, 2),
                        "context": item.get("context", ""),
                        "src_line": item.get("src_line", ""),
                    }
                    file_findings.append(finding)
                    file_counts[os.path.relpath(filepath, root_dir)]["total"] += 1
                    file_counts[os.path.relpath(filepath, root_dir)][classification] += 1

                    if len(file_findings) >= max_per_file:
                        break

            all_findings.extend(file_findings)

    # 生成摘要
    summary = {
        "total_files_scanned": total_files_scanned,
        "total_strings_checked": total_strings_found,
        "total_english_copy": len(all_findings),
        "by_classification": {
            "user_visible": sum(1 for f in all_findings if f["classification"] == "user_visible"),
            "developer_facing": sum(1 for f in all_findings if f["classification"] == "developer_facing"),
            "unknown": sum(1 for f in all_findings if f["classification"] == "unknown"),
        },
        "top_files": sorted(
            [
                {"file": f, **counts}
                for f, counts in file_counts.items()
            ],
            key=lambda x: x["user_visible"],
            reverse=True,
        )[:20],
    }

    return {
        "summary": summary,
        "findings": all_findings,
    }


# ── 输出 ──

def print_summary(result: dict):
    """打印人类可读摘要。"""
    s = result["summary"]
    print("=" * 60)
    print("📊 英文文案扫描报告")
    print("=" * 60)
    print(f"  扫描文件: {s['total_files_scanned']} 个")
    print(f"  检查字符串: {s['total_strings_checked']} 处")
    print(f"  发现英文文案: {s['total_english_copy']} 处")
    print(f"    - 用户可见: {s['by_classification']['user_visible']} 处")
    print(f"    - 开发者文档: {s['by_classification']['developer_facing']} 处")
    print(f"    - 未分类: {s['by_classification']['unknown']} 处")
    print()

    if s["top_files"]:
        print("📁 英文文案最多的文件 (Top 20):")
        for item in s["top_files"][:20]:
            if item["user_visible"] > 0:
                flag = "⚠️ " if item["user_visible"] > 5 else "  "
                print(f"  {flag}{item['file']} (用户可见:{item['user_visible']}, 文档:{item['developer_facing']}, 未分类:{item['unknown']})")

    print()
    print("💡 建议优先处理 marked ⚠️ 的文件中的 user_visible 文案。")


def print_samples(result: dict, classification: str = "user_visible", n: int = 20):
    """打印样例字符串。"""
    samples = [f for f in result["findings"] if f["classification"] == classification]
    if not samples:
        print(f"  没有 {classification} 类型的字符串。")
        return

    print(f"\n📝 {classification} 样例 (前 {n} 条):")
    print("-" * 60)
    for item in samples[:n]:
        print(f"  📍 {item['file']}:{item['line']}")
        print(f"     \"{item['text'][:120]}\"")
        print()


def main():
    parser = argparse.ArgumentParser(description="全量扫描源码中的英文字符串")
    parser.add_argument(
        "--dir",
        default=os.path.expanduser("~/projects/nermes-core"),
        help="扫描目录 (默认: ~/projects/nermes-core)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出 JSON 文件路径",
    )
    parser.add_argument(
        "--max-per-file",
        type=int,
        default=50,
        help="每个文件最多报告多少条 (默认: 50)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "both"],
        default="text",
        help="输出格式",
    )
    parser.add_argument(
        "--show-samples",
        type=int,
        default=20,
        help="显示多少条样例 (默认: 20)",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="最低置信度阈值 (0.0-1.0)",
    )
    parser.add_argument(
        "--priority-only",
        action="store_true",
        help="仅扫描核心代码，排除 tests/ 和 optional-skills/ 目录",
    )
    args = parser.parse_args()

    scan_dir = os.path.expanduser(args.dir)
    if not os.path.isdir(scan_dir):
        print(f"❌ 目录不存在: {scan_dir}", file=sys.stderr)
        sys.exit(1)

    # Priority-only: 排除 tests/ 和 optional-skills/
    if args.priority_only:
        EXCLUDE_DIRS.update({"tests", "optional-skills"})
        print(f"🔍 扫描目录: {scan_dir} (核心代码模式)")
    print()

    result = scan_directory(scan_dir, max_per_file=args.max_per_file)

    # 按置信度过滤
    if args.min_confidence > 0:
        result["findings"] = [
            f for f in result["findings"]
            if f["confidence"] >= args.min_confidence
        ]

    if args.format in ("text", "both"):
        print_summary(result)
        print_samples(result, "user_visible", args.show_samples)

    if args.format in ("json", "both"):
        output_path = args.output or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "scan_english_strings_output.json"
        )
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n📄 JSON 报告已保存: {output_path}")


if __name__ == "__main__":
    main()

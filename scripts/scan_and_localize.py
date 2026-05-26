#!/usr/bin/env python3
"""合并后自动汉化扫描与修复。

检测合并入的上游代码中需要汉化的内容：
  1. Python 文件中新增的英文 help/description/print_* 文案
  2. locales/en.yaml 中新增但 zh.yaml 缺失的 key
"""

import subprocess
import sys
import os
import re
import yaml

REPO = os.path.expanduser("~/projects/nermes-core")

# ── 已知英文→中文映射表（自动翻译安全短语） ──
SAFE_TRANSLATIONS = {
    # CLI args
    "Print version and exit": "输出版本号并退出",
    "Verbose output": "详细输出",
    "Show this help message and exit": "显示此帮助信息并退出",
    "Force operation": "强制执行",
    "Dry run (no changes)": "试运行（不实际修改）",
    "Dry run": "试运行",
    "Show status": "显示状态",
    "Show status only": "仅显示状态",
    "Enable debug logging": "启用调试日志",
    "Comma-separated list of": "逗号分隔的列表",
    "Path to config file": "配置文件路径",
    "Output format": "输出格式",
    "Output as JSON": "以 JSON 格式输出",
    
    # Common actions
    "Archive one or more tasks": "归档一个或多个任务",
    "List all tasks": "列出所有任务",
    "Create a new task": "创建新任务",
    "Delete a task": "删除任务",
    "Search for skills": "搜索技能",
    "Install a skill": "安装技能",
    "Remove a skill": "移除技能",
    "Update a skill": "更新技能",
    
    # Gateway
    "Start the messaging gateway": "启动消息网关",
    "Stop the messaging gateway": "停止消息网关",
    "Restart the messaging gateway": "重启消息网关",
    
    # Common
    "Enabled": "已启用",
    "Disabled": "已禁用",
    "Yes": "是",
    "No": "否",
    "OK": "确定",
    "Cancel": "取消",
    "Error": "错误",
    "Warning": "警告",
    "Success": "成功",
    "None": "无",
    "Default": "默认",
}


def run(cmd, cwd=REPO):
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def scan_python_strings(merge_base="main"):
    """扫描上游新增的 Python 用户可见文案。"""
    # 从 merge 的 diff 中找新增的英文文案
    rc, diff, _ = run(f"git diff {merge_base}..HEAD -- '*.py' | grep '^+' | grep -v '^+++'")
    
    patterns = [
        (r'help\s*=\s*"([^"]*[a-zA-Z]{4,}[^"]*)"', "help"),
        (r'description\s*=\s*"([^"]*[a-zA-Z]{4,}[^"]*)"', "description"),
        (r"help\s*=\s*'([^']*[a-zA-Z]{4,}[^']*)'", "help"),
        (r'print_info\("([^"]*[a-zA-Z]{3,}[^"]*)"\)', "print_info"),
        (r'print_header\("([^"]*[a-zA-Z]{3,}[^"]*)"\)', "print_header"),
        (r'print_success\("([^"]*[a-zA-Z]{3,}[^"]*)"\)', "print_success"),
        (r'print_warning\("([^"]*[a-zA-Z]{3,}[^"]*)"\)', "print_warning"),
        (r'print_error\("([^"]*[a-zA-Z]{3,}[^"]*)"\)', "print_error"),
        (r'prompt\("([^"]*[a-zA-Z]{3,}[^"]*)"\)', "prompt"),
        (r'epilogue\s*=\s*"([^"]*[a-zA-Z]{4,}[^"]*)"', "epilogue"),
    ]
    
    found = []
    for line in diff.split("\n"):
        line = line[1:] if line.startswith("+") else line  # strip +
        for pattern, ptype in patterns:
            m = re.search(pattern, line)
            if m:
                text = m.group(1)
                # 跳过纯代码路径、变量名等非文案内容
                if re.match(r'^[a-z_]+$', text) or text.count("/") > 2:
                    continue
                if text not in [f[0] for f in found]:
                    found.append((text, ptype))
                break
    
    return found


def scan_locale_keys(merge_base="main"):
    """扫描 en.yaml 新增但 zh.yaml 缺失的 key。"""
    en_path = os.path.join(REPO, "locales/en.yaml")
    zh_path = os.path.join(REPO, "locales/zh.yaml")
    
    if not os.path.exists(en_path) or not os.path.exists(zh_path):
        return []
    
    with open(en_path, encoding='utf-8') as f:
        en_data = yaml.safe_load(f) or {}
    with open(zh_path, encoding='utf-8') as f:
        zh_data = yaml.safe_load(f) or {}
    
    def flatten(d, prefix=""):
        result = {}
        if isinstance(d, dict):
            for k, v in d.items():
                key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    result.update(flatten(v, key))
                else:
                    result[key] = v
        return result
    
    en_flat = flatten(en_data)
    zh_flat = flatten(zh_data)
    
    missing = []
    for key, value in en_flat.items():
        if key not in zh_flat and isinstance(value, str) and len(value) > 3:
            missing.append((key, value))
    
    return missing


def auto_translate(text):
    """尝试自动翻译，返回 (translated, needs_review)。"""
    # 精确匹配
    if text in SAFE_TRANSLATIONS:
        return SAFE_TRANSLATIONS[text], False
    
    # 前缀匹配（如 "Comma-separated list of tools"）
    for en, zh in SAFE_TRANSLATIONS.items():
        if text.startswith(en):
            suffix = text[len(en):]
            return zh + suffix, True  # needs review for suffix
    
    # 太短或太简单的跳过
    if len(text) < 20 and text.isascii():
        return None, False  # 不自动翻译短句
    
    return None, False


def main():
    merge_base = "main"  # 合并前的 main
    
    print("🔍 汉化扫描中...\n")
    
    # 1. 扫描 Python 文案
    py_strings = scan_python_strings(merge_base)
    print(f"📄 Python 新增英文文案: {len(py_strings)} 处\n")
    
    # 2. 扫描 i18n key
    locale_keys = scan_locale_keys(merge_base)
    print(f"🌐 locales/en.yaml 新增 key: {len(locale_keys)} 个\n")
    
    if not py_strings and not locale_keys:
        print("✅ 无需汉化，上游没有新增英文文案。")
        return
    
    # 3. 自动翻译
    auto_fixed = 0
    needs_review = []
    
    for text, ptype in py_strings:
        translated, review = auto_translate(text)
        if translated is None:
            if len(text) > 10 and not text.startswith("--"):
                needs_review.append(("python", ptype, text, ""))
        elif review:
            needs_review.append(("python", ptype, text, translated))
        else:
            auto_fixed += 1
            print(f"  ✅ 自动翻译 [{ptype}]: {text[:60]} → {translated[:60]}")
    
    for key, value in locale_keys:
        translated, review = auto_translate(value)
        if translated is None:
            needs_review.append(("locale", key, value, ""))
        elif review:
            needs_review.append(("locale", key, value, translated))
        else:
            auto_fixed += 1
            print(f"  ✅ 自动翻译 [{key}]: {value[:60]} → {translated[:60]}")
    
    # 4. 报告待人工审核
    if needs_review:
        print(f"\n⚠️  {len(needs_review)} 处需要人工审核/翻译：\n")
        for source, loc, text, suggestion in needs_review:
            print(f"  📍 [{source}] {loc}")
            print(f"     EN: {text[:100]}")
            if suggestion:
                print(f"     ZH: {suggestion[:100]} (自动建议，需审核)")
            else:
                print(f"     ZH: ??? (需要人工翻译)")
            print()
    
    print(f"\n📊 统计: 自动翻译 {auto_fixed} 处, 待审核 {len(needs_review)} 处")


if __name__ == "__main__":
    main()

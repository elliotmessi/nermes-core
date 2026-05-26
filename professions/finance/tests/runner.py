#!/usr/bin/env python3
"""Nermes 财务版效果测试运行器。

用法：
  nermes test finance              # 运行全部 18 个场景
  nermes test finance --category 税务计算  # 按分类筛选
  nermes test finance --id F-001          # 运行指定场景
  nermes test finance --list              # 列出所有场景

每个场景通过 nermes -z "prompt" 单次模式运行，然后评估响应是否满足预期标准。
"""

import json
import os
import subprocess
import sys
import time
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


# ── 路径 ────────────────────────────────────────────────────
TESTS_DIR = Path(__file__).parent
SCENARIOS_PATH = TESTS_DIR / "scenarios.json"
REPORT_DIR = TESTS_DIR / "reports"


def green(s): return f"\033[32m{s}\033[0m"
def red(s): return f"\033[31m{s}\033[0m"
def yellow(s): return f"\033[33m{s}\033[0m"
def bold(s): return f"\033[1m{s}\033[0m"
def dim(s): return f"\033[2m{s}\033[0m"


def load_scenarios() -> List[Dict]:
    with open(SCENARIOS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["scenarios"]


def run_agent(prompt: str, timeout: int = 120) -> str:
    """通过 nermes oneshot 模式执行一个 prompt，返回响应文本。"""
    try:
        result = subprocess.run(
            ["nermes", "-z", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NERMES_LANGUAGE": "zh"},
        )
        return (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return "[TIMEOUT]"
    except FileNotFoundError:
        return "[NERMES_NOT_FOUND]"


def evaluate_response(response: str, scenario: Dict) -> Dict:
    """评估响应是否符合预期标准。"""
    expect = scenario.get("expect", {})
    results = {
        "passed": True,
        "checks": [],
    }

    # 1. 检查必须出现的关键词
    for kw in expect.get("keywords", []):
        if kw.lower() in response.lower():
            results["checks"].append({"check": f"关键词「{kw}」", "result": "✅", "detail": "已找到"})
        else:
            results["checks"].append({"check": f"关键词「{kw}」", "result": "❌", "detail": "未找到"})
            results["passed"] = False

    # 2. 检查不应出现的关键词
    for kw in expect.get("not_keywords", []):
        if kw.lower() in response.lower():
            results["checks"].append({"check": f"禁止词「{kw}」", "result": "❌", "detail": "不应该出现"})
            results["passed"] = False
        else:
            results["checks"].append({"check": f"禁止词「{kw}」", "result": "✅", "detail": "未出现"})

    # 3. 检查是否包含实质性回答（至少有足够长度）
    if len(response) < 50 and response not in ("[TIMEOUT]", "[NERMES_NOT_FOUND]"):
        results["checks"].append({"check": "响应长度", "result": "❌", "detail": f"仅 {len(response)} 字符"})
        results["passed"] = False
    elif response in ("[TIMEOUT]",):
        results["checks"].append({"check": "执行", "result": "❌", "detail": "超时"})
        results["passed"] = False
    elif response in ("[NERMES_NOT_FOUND]",):
        results["checks"].append({"check": "执行", "result": "❌", "detail": "nermes 命令未找到"})
        results["passed"] = False

    return results


def run_scenario(scenario: Dict, verbose: bool = True) -> Dict:
    """执行单个测试场景。"""
    if verbose:
        print(f"\n{bold('━' * 60)}")
        print(f"{bold(scenario['id'])}  {scenario['category']} › {scenario['name']}")
        print(f"{bold('━' * 60)}")
        print(f"\n{dim('📝 提示词：')}")
        print(f"   {scenario['prompt'][:200]}{'…' if len(scenario['prompt']) > 200 else ''}")
        print(f"\n{dim('⏳ 正在请求 Nermes...')}")

    start = time.time()
    response = run_agent(scenario["prompt"])
    elapsed = time.time() - start

    evaluation = evaluate_response(response, scenario)

    if verbose:
        print(f"\n{dim('📤 Nermes 响应（耗时 {elapsed:.1f}s）：')}")
        # 截断过长响应
        display = response[:800] + "…" if len(response) > 800 else response
        for line in display.split("\n")[:20]:
            print(f"   {line}")
        if len(response.split("\n")) > 20:
            print(f"   {dim('… 共 ' + str(len(response.split(chr(10)))) + ' 行')}")

        print(f"\n{dim('🔍 评估结果：')}")
        for check in evaluation["checks"]:
            icon = check["result"]
            print(f"   {icon}  {check['check']}: {check['detail']}")

        status = green("✅ 通过") if evaluation["passed"] else red("❌ 未通过")
        print(f"\n   {bold('状态：')}{status}")

    return {
        "id": scenario["id"],
        "name": scenario["name"],
        "category": scenario["category"],
        "passed": evaluation["passed"],
        "elapsed": round(elapsed, 1),
        "checks": evaluation["checks"],
        "response_preview": response[:300],
    }


def run_all(category: Optional[str] = None, scenario_id: Optional[str] = None):
    """运行全部场景并生成报告。"""
    scenarios = load_scenarios()

    if scenario_id:
        scenarios = [s for s in scenarios if s["id"] == scenario_id]
        if not scenarios:
            print(f"❌ 未找到场景 {scenario_id}")
            sys.exit(1)
    elif category:
        scenarios = [s for s in scenarios if s["category"] == category]
        if not scenarios:
            print(f"❌ 未找到分类 {category}")
            sys.exit(1)

    print(f"\n{bold('🧪 Nermes 财务版效果测试')}")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"{dim(f'   共 {len(scenarios)} 个场景 · {now_str}')}")

    results = []
    for scenario in scenarios:
        result = run_scenario(scenario)
        results.append(result)

    # ── 汇总报告 ──
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    total_time = sum(r["elapsed"] for r in results)

    print(f"\n\n{bold('═' * 60)}")
    print(f"{bold('📊 测试报告')}")
    print(f"{bold('═' * 60)}")
    print(f"   总场景：{len(results)}")
    print(f"   通过：{green(str(passed))}")
    if failed > 0:
        print(f"   失败：{red(str(failed))}")
    else:
        print(f"   失败：0")
    print(f"   总耗时：{total_time:.1f}s")
    print(f"   通过率：{passed/len(results)*100:.0f}%")

    if failed > 0:
        print(f"\n{bold('❌ 未通过的场景：')}")
        for r in results:
            if not r["passed"]:
                print(f"   {r['id']} {r['category']} › {r['name']}")
                for check in r["checks"]:
                    if "❌" in check["result"]:
                        print(f"      {check['result']} {check['check']}: {check['detail']}")

    # ── 保存 JSON 报告 ──
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{passed/len(results)*100:.0f}%",
            "total_time": total_time,
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n{dim(f'📄 详细报告已保存到 {report_path}')}")

    # 返回退出码
    sys.exit(0 if failed == 0 else 1)


def list_scenarios():
    """列出所有测试场景。"""
    scenarios = load_scenarios()
    print(f"\n{bold(f'📋 Nermes 财务版测试场景（共 {len(scenarios)} 个）')}\n")
    
    by_category = {}
    for s in scenarios:
        by_category.setdefault(s["category"], []).append(s)
    
    for cat, items in by_category.items():
        print(f"  {bold(cat)}（{len(items)} 个）")
        for item in items:
            print(f"    {dim(item['id'])}  {item['name']}")
        print()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Nermes 财务版效果测试")
    parser.add_argument("--list", action="store_true", help="列出所有测试场景")
    parser.add_argument("--category", type=str, help="按分类筛选（如：税务计算、发票OCR）")
    parser.add_argument("--id", type=str, help="运行指定场景 ID（如：F-001）")
    parser.add_argument("--quiet", action="store_true", help="静默模式（仅输出报告）")
    
    args = parser.parse_args()
    
    if args.list:
        list_scenarios()
        return
    
    run_all(category=args.category, scenario_id=args.id)


if __name__ == "__main__":
    main()

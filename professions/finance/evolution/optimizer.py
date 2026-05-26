#!/usr/bin/env python3
"""技能自动优化器 — 分析反馈数据，生成改进方案并自动更新技能。

工作原理：
1. 定期扫描 feedback/ 目录
2. 对需要优化的技能，生成改进提示词
3. Agent 根据提示词更新 SKILL.md
4. 记录优化历史到 evolution_log.jsonl
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from feedback import (
    get_skill_stats,
    should_optimize,
    generate_improvement_prompt,
    extract_learnings,
)


# ── 优化记录 ──────────────────────────────────────────────────

def _get_evolution_log() -> Path:
    nermes_home = os.environ.get("NERMES_HOME") or os.path.expanduser("~/.nermes")
    return Path(nermes_home) / "evolution_log.jsonl"


def get_optimization_candidates(skills_dir: str, min_uses: int = 5) -> List[Dict]:
    """扫描技能目录，返回需要优化的技能列表。
    
    Args:
        skills_dir: SKILL.md 所在目录
        min_uses: 最少使用次数
        
    Returns:
        list[dict]: [{"name": ..., "stats": ..., "prompt": ...}, ...]
    """
    candidates = []
    
    # 遍历所有子目录
    for skill_dir in Path(skills_dir).iterdir():
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        
        skill_name = skill_dir.name
        
        if should_optimize(skill_name, min_uses=min_uses):
            stats = get_skill_stats(skill_name)
            prompt = generate_improvement_prompt(skill_name)
            candidates.append({
                "name": skill_name,
                "path": str(skill_file),
                "stats": stats,
                "improvement_prompt": prompt,
            })
    
    # 按成功率升序（最需要优化的排前面）
    candidates.sort(key=lambda c: c["stats"].get("success_rate", 1.0))
    return candidates


def record_optimization(skill_name: str, before_stats: dict, after_changes: str = "") -> dict:
    """记录一次优化操作。"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "skill": skill_name,
        "before_success_rate": before_stats.get("success_rate", 0),
        "before_uses": before_stats.get("total_uses", 0),
        "changes": after_changes[:1000],
    }
    
    log_file = _get_evolution_log()
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    return entry


def get_evolution_summary() -> dict:
    """获取自进化系统总览。"""
    skills_dir = os.path.join(
        os.environ.get("NERMES_HOME", os.path.expanduser("~/.nermes")),
        "skills"
    )
    
    total_skills = 0
    total_feedback = 0
    optimized = 0
    
    feedback_dir = os.path.join(
        os.environ.get("NERMES_HOME", os.path.expanduser("~/.nermes")),
        "feedback"
    )
    
    if os.path.isdir(feedback_dir):
        for f in os.listdir(feedback_dir):
            if f.endswith(".jsonl"):
                with open(os.path.join(feedback_dir, f), encoding="utf-8") as fh:
                    total_feedback += sum(1 for _ in fh)
    
    log_file = _get_evolution_log()
    if log_file.exists():
        with open(log_file, encoding="utf-8") as f:
            optimized = sum(1 for _ in f)
    
    return {
        "total_skills": total_skills,
        "total_feedback_entries": total_feedback,
        "optimizations_done": optimized,
    }


if __name__ == "__main__":
    import sys
    
    # 扫描需要优化的技能
    skills_path = os.path.expanduser("~/.nermes/skills")
    if not os.path.isdir(skills_path):
        skills_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "skills"
        )
    
    candidates = get_optimization_candidates(skills_path, min_uses=1)
    
    print(f"=== 自进化优化器 ===\n")
    print(f"反馈数据: {get_evolution_summary()['total_feedback_entries']} 条")
    print(f"待优化技能: {len(candidates)} 个\n")
    
    for c in candidates[:5]:
        s = c["stats"]
        print(f"  📝 {c['name']}")
        print(f"     成功率: {s['success_rate']:.0%} | 使用: {s['total_uses']}次 | 纠正: {len(s.get('common_corrections', []))}条")

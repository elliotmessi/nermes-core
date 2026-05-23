#!/usr/bin/env python3
"""自进化反馈收集系统 — 记录技能使用效果，驱动自动优化。

每个技能使用后，Agent 应调用 record_feedback() 记录：
- 任务是否成功
- 用户是否满意
- 用户做了什么纠正
- 耗时/步骤数等指标
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List


# ── 反馈存储路径 ──────────────────────────────────────────────

def _get_feedback_dir() -> Path:
    """获取反馈数据目录。"""
    nermes_home = os.environ.get("NERMES_HOME") or os.environ.get("HERMES_HOME") or os.path.expanduser("~/.nermes")
    fb_dir = Path(nermes_home) / "feedback"
    fb_dir.mkdir(parents=True, exist_ok=True)
    return fb_dir


def _get_feedback_file(skill_name: str) -> Path:
    """获取特定技能的反馈文件路径。"""
    return _get_feedback_dir() / f"{skill_name}.jsonl"


# ── 反馈记录 ──────────────────────────────────────────────────

def record_feedback(
    skill_name: str,
    success: bool,
    user_satisfied: Optional[bool] = None,
    corrections: str = "",
    task_description: str = "",
    duration_seconds: float = 0.0,
    tool_calls: int = 0,
    user_comment: str = "",
) -> dict:
    """记录一次技能使用反馈。
    
    Args:
        skill_name: 使用的技能名称
        success: 任务是否成功完成
        user_satisfied: 用户是否满意（None=未询问）
        corrections: 用户做的纠正内容
        task_description: 任务描述
        duration_seconds: 耗时（秒）
        tool_calls: 工具调用次数
        user_comment: 用户评价
        
    Returns:
        dict: 记录的反馈条目
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "skill": skill_name,
        "success": success,
        "user_satisfied": user_satisfied,
        "corrections": corrections,
        "task": task_description[:500],
        "duration_s": round(duration_seconds, 1),
        "tool_calls": tool_calls,
        "comment": user_comment[:500],
    }
    
    fb_file = _get_feedback_file(skill_name)
    with open(fb_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    return entry


def get_skill_stats(skill_name: str) -> dict:
    """获取技能的使用统计。
    
    Returns:
        dict: {
            "total_uses": 总使用次数,
            "success_rate": 成功率,
            "satisfaction_rate": 满意度,
            "avg_duration": 平均耗时,
            "common_corrections": [常见纠正],
            "recent_feedback": [最近5条反馈]
        }
    """
    fb_file = _get_feedback_file(skill_name)
    if not fb_file.exists():
        return {"total_uses": 0, "skill": skill_name}
    
    entries = []
    with open(fb_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    
    if not entries:
        return {"total_uses": 0, "skill": skill_name}
    
    total = len(entries)
    successes = sum(1 for e in entries if e.get("success"))
    satisfied = sum(1 for e in entries if e.get("user_satisfied") is True)
    satisfied_count = sum(1 for e in entries if e.get("user_satisfied") is not None)
    durations = [e.get("duration_s", 0) for e in entries if e.get("duration_s")]
    
    # 收集纠正内容
    corrections = [e["corrections"] for e in entries if e.get("corrections")]
    
    return {
        "skill": skill_name,
        "total_uses": total,
        "success_rate": round(successes / total, 3) if total else 0,
        "satisfaction_rate": round(satisfied / satisfied_count, 3) if satisfied_count else None,
        "avg_duration_s": round(sum(durations) / len(durations), 1) if durations else 0,
        "common_corrections": corrections[-10:],  # 最近10条纠正
        "recent_feedback": entries[-5:],
    }


def should_optimize(skill_name: str, min_uses: int = 5, low_success_threshold: float = 0.7) -> bool:
    """判断技能是否需要优化。
    
    满足任一条件即触发优化：
    - 成功率低于阈值
    - 有新的用户纠正积累（>=2条）
    
    Args:
        skill_name: 技能名称
        min_uses: 最少使用次数才考虑优化
        low_success_threshold: 成功率低于此值触发优化
        
    Returns:
        bool: 是否需要优化
    """
    stats = get_skill_stats(skill_name)
    if stats["total_uses"] < min_uses:
        return False
    
    # 成功率低
    if stats["success_rate"] < low_success_threshold:
        return True
    
    # 有纠正积累
    corrections = stats.get("common_corrections", [])
    if len(corrections) >= 2:
        return True
    
    return False


def generate_improvement_prompt(skill_name: str) -> str:
    """生成技能改进提示词，供 Agent 用于更新技能。
    
    Returns:
        str: 改进提示词，包含统计数据+用户纠正+改进建议模板
    """
    stats = get_skill_stats(skill_name)
    
    prompt = f"""## 技能优化：{skill_name}

### 使用统计
- 总使用次数：{stats['total_uses']}
- 成功率：{stats['success_rate']:.0%}
- 满意度：{stats.get('satisfaction_rate', 'N/A')}
- 平均耗时：{stats['avg_duration_s']}秒

### 用户纠正记录
"""
    for i, corr in enumerate(stats.get("common_corrections", [])[-5:], 1):
        prompt += f"{i}. {corr}\n"
    
    if not stats.get("common_corrections"):
        prompt += "（暂无用户纠正）\n"
    
    prompt += f"""
### 改进建议
基于以上数据，请分析该技能的瓶颈并提出改进方案：
1. 最常见的用户纠正是什么？如何预防？
2. 哪些步骤可以优化或自动化？
3. 是否有遗漏的边界情况？
4. 是否需要增加验证步骤？

请生成改进后的 SKILL.md（保持 YAML frontmatter + markdown 格式）。
"""
    return prompt


# ── 经验积累 ──────────────────────────────────────────────────

def extract_learnings(skill_name: str) -> List[str]:
    """从反馈中提取可转化为持久记忆的经验。
    
    Returns:
        list[str]: 经验条目，适合写入 MEMORY.md
    """
    stats = get_skill_stats(skill_name)
    learnings = []
    
    corrections = stats.get("common_corrections", [])
    if not corrections:
        return learnings
    
    # 去重并生成经验
    seen = set()
    for corr in corrections[-10:]:
        key = corr[:50]
        if key not in seen:
            seen.add(key)
            learnings.append(f"[{skill_name}] 使用技巧：{corr[:200]}")
    
    return learnings


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        name = sys.argv[2] if len(sys.argv) > 2 else "test-skill"
        
        if cmd == "stats":
            print(json.dumps(get_skill_stats(name), ensure_ascii=False, indent=2))
        elif cmd == "check":
            print(f"需要优化: {should_optimize(name)}")
        elif cmd == "learn":
            for l in extract_learnings(name):
                print(f"  • {l}")

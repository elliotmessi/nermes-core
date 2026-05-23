---
name: self-evolution
description: "自进化系统：技能使用反馈收集、自动优化建议、经验积累与记忆更新"
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [自进化, 反馈, 优化, 经验积累, 持续学习, evolution]
    related_skills: [all]
---

# 自进化系统

## 概述

Nermes 的护城河不是功能多，而是**越用越准**。自进化系统让 Nermes 在每次交互中学习：

1. **反馈收集** — 每次使用技能后，记录效果和用户纠正
2. **自动分析** — 当某技能成功率下降或积累≥2条纠正时，触发优化
3. **技能更新** — Agent 自动改写 SKILL.md，消除已知问题
4. **经验积累** — 将用户纠正转化为 MEMORY.md 持久记忆

## 使用方式

### Agent 侧（自动执行）

每次完成涉及专业技能的任务后，Agent 应调用：

```python
from professions.finance.evolution.feedback import record_feedback

record_feedback(
    skill_name="voucher-entry",
    success=True,
    user_satisfied=True,
    corrections="",  # 用户没有纠正
    task_description="根据发票生成记账凭证",
    duration_seconds=15.3,
    tool_calls=3,
)
```

### 用户纠正被记录

当用户说"不对，应该是管理费用-办公费，不是销售费用"：
```python
record_feedback(
    skill_name="account-suggest",
    success=False,
    user_satisfied=False,
    corrections="管理费用-办公费 ≠ 销售费用，需根据发票内容精确匹配",
    task_description="购买办公用品科目推荐",
)
```

### 触发优化

```python
from professions.finance.evolution.optimizer import get_optimization_candidates

candidates = get_optimization_candidates("~/.nermes/skills")
for c in candidates:
    # c['improvement_prompt'] 包含改进方案
    # Agent 据此更新 c['path'] 中的 SKILL.md
```

### 经验持久化

```python
from professions.finance.evolution.feedback import extract_learnings

learnings = extract_learnings("account-suggest")
# → 将 learnings 追加到 ~/.nermes/MEMORY.md
```

## 自进化循环

```
用户任务 → 加载技能 → 执行 → 收集反馈
                                    ↓
                            反馈积累 ≥ 阈值？
                              ↙        ↘
                            是          否
                            ↓           ↓
                      生成改进方案    继续积累
                            ↓
                      更新 SKILL.md
                            ↓
                      提取经验→MEMORY.md
                            ↓
                      下次自动使用新版本 ✅
```

## 指标监控

关键指标（Agent 可用 `/evolution status` 查看）：
- 总反馈条目数
- 各技能成功率/满意度
- 优化历史记录
- 待优化技能列表

---
name: knowledge-maintenance
description: 财务知识库维护：新增、更新、标记过时。用户纠正错误或沉淀新知识时使用。
version: 1.0.0
author: nermes
triggers:
  - 用户说"记住"/"记一下"/"这个知识点记下来"
  - 用户纠正了一个错误"不对""应该是""你记错了"
  - 用户问"知识库有哪些""怎么更新知识库"
  - 对话中发现了可沉淀的财务专业知识
---

# 知识库维护

维护本地财务专业知识库，让知识随使用不断增长。

## 触发条件

以下情况必须使用 `finance_knowledge_maintain` 工具：

1. **用户纠正知识错误** — 你说错了，用户指出正确做法
2. **用户主动要求记录** — "记住这个"/"记下来"/"存到知识库"
3. **发现新知识** — 对话中用户提供了知识库里没有的专业内容
4. **法规政策更新** — 税率变了、新准则生效了

## 操作步骤

### 场景一：用户纠正错误

```
用户："不对，现在小规模纳税人已经改成1%了，不是3%"

→ 调用 finance_knowledge_maintain({
    action: "update",
    file_name: "tax-rates.md",
    section_title: "小规模纳税人",
    old_text: "原征收率3%，...",  // 从知识库搜索结果中取原文
    new_text: "1%征收率（2026年延续）",
})
```

### 场景二：沉淀新知识

```
用户："研发费用加计扣除还有行业限制的，只有制造业和科技型中小企业能享受"

→ 调用 finance_knowledge_maintain({
    action: "add",
    file_name: "tax-rates.md",
    section_title: "研发费用加计扣除适用行业",
    content: "根据财税〔2015〕119号...（完整内容）",
})
```

### 场景三：标记过时（不删除）

如果某条知识的准确性存疑但又不确定新值，用 `mark_stale`：

```
→ 调用 finance_knowledge_maintain({
    action: "mark_stale",
    file_name: "tax-rates.md",
    section_title: "增值税税率体系",
    reason: "2027年税率可能调整，需核实最新政策"
})
```

### 场景四：查看知识库状态

```
→ 调用 finance_knowledge_maintain({ action: "stats" })
→ 调用 finance_knowledge_maintain({ action: "log" })
→ 调用 finance_knowledge_maintain({ action: "list" })
```

## 更新原则

1. **保留原表述风格** — 用中文，专业术语可附英文缩写
2. **标注来源** — 如果是法规，注明文号（如"财税〔2015〕119号"）
3. **不要删除旧内容** — 用 `mark_stale` 标记而非直接删除，保留审计追溯
4. **更新后告知用户** — "已更新知识库「税率速查」→ 小规模纳税人 1%"
5. **撤销旧标记** — 如果发现 `check_fn` 或预检查显示内容已解旧，直接覆盖

## 知识缺口发现

定期（每周或用户要求时）检查搜索日志中的知识缺口：

```python
from professions.finance.tools.search_knowledge import get_search_gaps
gaps = get_search_gaps(min_queries=3)
# 返回频繁搜索但无结果的查询 → 建议用户补充这些知识点
```

如果发现明显的知识空白点，主动建议用户补充。

## 分类归档规则

- **税务** → `tax-rates.md`
- **会计** → `accounting-standards.md` 或 `common-entries.md`
- **差错/纠错** → `common-errors.md`
- **操作流程** → `tax-filing-guide.md` 或 `audit-preparation.md`
- **管理知识** → `budget-management.md`、`cost-accounting.md`、`cash-flow-management.md`、`internal-control.md`
- **分析** → `financial-analysis.md`
- **全新领域** → 创建新文件，如 `new-topic.md`

## 故障排查

如果 `update` 返回 "未找到匹配的旧文本"：
- 用 `finance_knowledge_search` 先搜索出完整原文
- 复制 ≥30 字的精确片段作为 `old_text`
- 确保包含了周围的上下文（标点、换行也属于匹配内容）

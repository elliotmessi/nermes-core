---
name: depreciation
description: "固定资产折旧：年限平均法/双倍余额递减法/年数总和法计算、残值估算、折旧表生成"
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [财务核算, 固定资产, 折旧管理]
---

# 固定资产折旧

## 概述

本技能覆盖固定资产折旧的多种计算方法、残值的合理估算以及折旧表自动生成。正确计算折旧对于准确反映资产价值、匹配收入与费用、以及税务合规至关重要。

## 折旧方法详解

### 1. 年限平均法（直线法）

最常用、最简单的折旧方法，将资产成本在预计使用年限内平均分摊。

**计算公式：**
```
年折旧额 = (原值 - 预计净残值) ÷ 预计使用年限
月折旧额 = 年折旧额 ÷ 12
年折旧率 = (1 - 预计净残值率) ÷ 预计使用年限 × 100%
```

**示例：**
- 资产原值 120,000 元，净残值 6,000 元（残值率 5%），使用年限 10 年
- 年折旧额 = (120,000 - 6,000) ÷ 10 = 11,400 元
- 月折旧额 = 11,400 ÷ 12 = 950 元

**适用场景：** 使用强度均衡的资产，如房屋建筑物、办公家具、长期设备

### 2. 双倍余额递减法

加速折旧法，前期折旧额大、后期逐年递减。**注意：最后两年改为直线法。**

**计算公式：**
```
年折旧率 = 2 ÷ 预计使用年限 × 100%
年折旧额 = 期初账面净值 × 年折旧率
最后两年：年折旧额 = (账面净值 - 预计净残值) ÷ 2
```

**示例：**
原值 100,000 元，净残值 5,000 元，使用年限 5 年

| 年份 | 期初净值 | 折旧率 | 年折旧额 | 累计折旧 | 期末净值 |
|------|---------|--------|---------|---------|---------|
| 1    | 100,000 | 40%    | 40,000  | 40,000  | 60,000  |
| 2    | 60,000  | 40%    | 24,000  | 64,000  | 36,000  |
| 3    | 36,000  | 40%    | 14,400  | 78,400  | 21,600  |
| 4    | 21,600  | —      | 8,300   | 86,700  | 13,300  |
| 5    | 13,300  | —      | 8,300   | 95,000  | 5,000   |

> 第 4 年起改用直线法：(21,600 - 5,000) ÷ 2 = 8,300

**适用场景：** 技术更新快的资产，如电子设备、计算机、数控机床

### 3. 年数总和法（年限积数法）

加速折旧法，折旧额逐年以固定比率递减。

**计算公式：**
```
年折旧率 = 尚可使用年数 ÷ 年数总和
年数总和 = n(n+1) ÷ 2  （n为使用年限）
年折旧额 = (原值 - 预计净残值) × 年折旧率
```

**示例：** 原值 100,000 元，净残值 5,000 元，使用年限 5 年
- 年数总和 = 5 × 6 ÷ 2 = 15

| 年份 | 尚可使用年数 | 折旧率 | 年折旧额 | 累计折旧 |
|------|------------|--------|---------|---------|
| 1    | 5          | 5/15   | 31,667  | 31,667  |
| 2    | 4          | 4/15   | 25,333  | 57,000  |
| 3    | 3          | 3/15   | 19,000  | 76,000  |
| 4    | 2          | 2/15   | 12,667  | 88,667  |
| 5    | 1          | 1/15   | 6,333   | 95,000  |

**适用场景：** 技术进步较快、前期效益高的设备

### 方法对比

| 方法 | 折旧模式 | 年度费用 | 税务影响 | 推荐场景 |
|------|---------|---------|---------|---------|
| 年限平均法 | 均衡 | 各年相同 | 稳定 | 房屋、通用设备 |
| 双倍余额递减法 | 前期高后期低 | 逐年递减 | 前期抵税多 | 电子设备 |
| 年数总和法 | 前期高后期低 | 逐年递减 | 前期抵税多 | 机械设备 |

## 残值估算

### 残值率确定
- **税法基准**：一般资产残值率建议在 **3%~5%** 之间
- **行业惯例**：
  - 房屋建筑物：3%~5%（因存在拆除成本，部分残值率为 0）
  - 机器设备：3%~5%
  - 运输设备：3%~5%
  - 电子设备：0%~3%（更新快、残值极低）
- **特殊情况**：有明确残值回收合同的，按合同价确定

### 残值估算方法
```python
def estimate_residual_value(asset_cost: float, asset_category: str,
                            expected_disposal_cost: float = 0) -> float:
    """估算固定资产预计净残值"""
    rate_map = {
        "building": 0.05,       # 房屋建筑 5%
        "machinery": 0.05,      # 机器设备 5%
        "vehicle": 0.05,        # 运输设备 5%
        "electronic": 0.03,     # 电子设备 3%
        "furniture": 0.05,      # 办公家具 5%
        "other": 0.04,          # 其他 4%
    }
    residual_rate = rate_map.get(asset_category, 0.04)
    residual_value = asset_cost * residual_rate - expected_disposal_cost
    return max(residual_value, 0)
```

### 残值调整情形
- 残值发生重大变化时（如原预计报废处理变为有回收价值），应重新评估
- 调整残值属于会计估计变更，采用**未来适用法**，不追溯调整已提折旧

## 折旧表生成

### 完整折旧计算函数

```python
def calculate_depreciation_schedule(
    asset_id: str,
    cost: float,
    residual_value: float,
    useful_life_years: int,
    method: str = "straight_line",
    acquisition_date: str = "2024-01-01"
) -> list:
    """生成固定资产折旧明细表"""
    depreciable_base = cost - residual_value
    schedule = []

    if method == "straight_line":
        annual_dep = depreciable_base / useful_life_years
        for year in range(1, useful_life_years + 1):
            schedule.append({
                "asset_id": asset_id,
                "year": year,
                "opening_net": cost - annual_dep * (year - 1),
                "annual_depreciation": round(annual_dep, 2),
                "accumulated_depreciation": round(annual_dep * year, 2),
                "closing_net": round(cost - annual_dep * year, 2)
            })

    elif method == "double_declining":
        rate = 2 / useful_life_years
        net_value = cost
        for year in range(1, useful_life_years + 1):
            # 最后两年改用直线法
            if year >= useful_life_years - 1:
                annual_dep = (net_value - residual_value) / \
                    (useful_life_years - year + 1)
            else:
                annual_dep = net_value * rate
            schedule.append({
                "asset_id": asset_id,
                "year": year,
                "opening_net": round(net_value, 2),
                "annual_depreciation": round(annual_dep, 2),
                "accumulated_depreciation": round(cost - (net_value - annual_dep), 2),
                "closing_net": round(net_value - annual_dep, 2)
            })
            net_value -= annual_dep

    elif method == "sum_of_years":
        total_years = useful_life_years * (useful_life_years + 1) // 2
        for year in range(1, useful_life_years + 1):
            rate = (useful_life_years - year + 1) / total_years
            annual_dep = depreciable_base * rate
            schedule.append({
                "asset_id": asset_id,
                "year": year,
                "opening_net": round(cost - sum(s["annual_depreciation"]
                    for s in schedule), 2) if schedule else cost,
                "annual_depreciation": round(annual_dep, 2),
                "accumulated_depreciation": round(
                    depreciable_base * sum((useful_life_years - y + 1) / total_years
                    for y in range(1, year + 1)), 2),
                "closing_net": round(cost - depreciable_base * sum(
                    (useful_life_years - y + 1) / total_years
                    for y in range(1, year + 1)), 2)
            })

    return schedule
```

### 月度折旧计提分录

```python
def generate_monthly_entry(asset_id: str, monthly_amount: float,
                           department: str = "管理费用"):
    """生成月度折旧计提会计分录"""
    return {
        "date": "2024-01-31",
        "description": f"计提{asset_id} {department}折旧",
        "entries": [
            {"account": department, "debit": monthly_amount, "credit": 0},
            {"account": "累计折旧", "debit": 0, "credit": monthly_amount}
        ]
    }
```

### 部门分配比例
| 资产用途 | 借方科目 | 说明 |
|---------|---------|------|
| 生产车间 | 制造费用 | 计入产品成本 |
| 管理部门 | 管理费用 | 期间费用 |
| 销售部门 | 销售费用 | 期间费用 |
| 研发部门 | 研发支出 | 资本化或费用化 |

## 折旧政策变更

- **方法变更**：属于会计估计变更，未来适用
- **年限变更**：发现原估计年限不合理的，重新估计剩余年限
- **减值影响**：资产发生减值的，以减值后账面价值为基础重新计算
- **变更披露**：财务报表附注中说明变更原因及影响金额

## 最佳实践

1. **资产卡片管理**：每项固定资产建立独立卡片，记录原值、折旧方法、使用年限等
2. **年度复核**：每年至少复核一次折旧方法与年限的合理性
3. **自动化计提**：利用财务软件按月自动生成折旧凭证，减少人工错误
4. **税务差异管理**：会计折旧与税法允许扣除额不一致时，做好递延所得税台账
5. **定期盘点**：核对资产实物状态，对已报废、毁损资产及时清理

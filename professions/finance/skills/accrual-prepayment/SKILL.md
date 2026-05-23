---
name: accrual-prepayment
description: "预提待摊：预提费用/待摊费用计算与分录、权责发生制调整"
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [财务核算, 预提待摊, 权责发生制]
---

# 预提与待摊费用

## 概述

预提费用与待摊费用是权责发生制下重要的跨期调整项目。**预提费用**（预提费用/应付类）指已受益但尚未支付的费用；**待摊费用**（预付类）指已付款但尚未受益的费用。合理处理这两类业务是确保各期损益准确的前提。

## 预提费用

### 概念与原则

预提费用是指企业**先受益、后付款**的支出，按权责发生制原则应在费用发生当期确认，即使款项尚未实际支付。

**常见预提项目：**
- 借款利息（按月预提、按季支付）
- 水电费（月底已消耗但账单未到）
- 租金（后付租金）
- 工资薪酬（月末计提、次月发放）
- 各项税费（计提后次月申报缴纳）

### 预提利息计算

```python
def calculate_accrued_interest(
    principal: float,
    annual_rate: float,
    days_in_period: int,
    days_in_year: int = 360
) -> float:
    """
    计算预提利息（银行通常按 360 天/年）

    参数:
        principal: 本金
        annual_rate: 年利率（如 0.045 表示 4.5%）
        days_in_period: 本期计息天数
        days_in_year: 年计息天数（银行360天/实际365天）
    """
    interest = principal * annual_rate * days_in_period / days_in_year
    return round(interest, 2)

# 示例：贷款 5,000,000 元，年利率 4.5%，本月 30 天
accrued = calculate_accrued_interest(5_000_000, 0.045, 30)
# 结果：18,750 元
```

### 预提分录模板

**按月预提利息：**
```
借：财务费用              18,750
  贷：应付利息            18,750
```

**预提水电费（账单未到）：**
```
借：管理费用——水电费       XXX
    制造费用——水电费       XXX   （生产车间）
  贷：其他应付款——应付水电费  XXX
```

**预提年终奖：**
```
借：管理费用/销售费用/主营业务成本   XXX
  贷：应付职工薪酬——年终奖          XXX
```

### 预提费用调整

- **多提冲回**：预提金额超过实际支付时，差额红字冲回
- **少提补充**：预提不足时，差额补充计提
- **跨年调整**：影响重大的预提差异通过"以前年度损益调整"科目处理

## 待摊费用

### 概念与原则

待摊费用（新准则下通常通过"预付账款"等科目核算）指企业**先付款、后受益**的支出，应按受益期间分期摊销。

**常见待摊项目：**
- 预付房租（一次性支付半年/全年租金）
- 预付保险费（年度保险费用）
- 预付订阅费（报刊、杂志、软件年费）
- 一次性支付的许可证费/认证费
- 大额广告费（受益期超过一个会计期间的）

### 摊销计算

```python
def calculate_amortization(
    total_amount: float,
    start_date: str,
    end_date: str,
    amortization_method: str = "straight_line"
) -> list:
    """
    计算待摊费用分期摊销表

    参数:
        total_amount: 待摊总额
        start_date: 摊销起始日期 "YYYY-MM-DD"
        end_date: 摊销结束日期 "YYYY-MM-DD"
        amortization_method: 摊销方法（目前仅支持直线法）

    返回:
        [{"period": "2024-01", "amount": XXX, "remaining": XXX}, ...]
    """
    from datetime import datetime, date
    import calendar

    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    # 计算总月数
    months = (end.year - start.year) * 12 + (end.month - start.month) + 1

    if amortization_method == "straight_line":
        monthly_amount = round(total_amount / months, 2)
        schedule = []
        remaining = total_amount

        current = date(start.year, start.month, 1)
        for _ in range(months):
            amount = monthly_amount
            # 最后一个月调整尾差
            if _ == months - 1:
                amount = round(remaining, 2)
            remaining -= amount
            schedule.append({
                "period": current.strftime("%Y-%m"),
                "amount": amount,
                "remaining": round(remaining, 2)
            })
            # 下个月
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)

        return schedule

    raise ValueError(f"不支持的摊销方法: {amortization_method}")

# 示例：预付全年租金 120,000 元（2024年1月~12月）
schedule = calculate_amortization(120_000, "2024-01-01", "2024-12-31")
# 每月摊销 10,000 元，最后一个月调整尾差
```

### 待摊分录模板

**支付时（初始确认）：**
```
借：预付账款——房租          120,000
  贷：银行存款              120,000
```

**每月摊销时：**
```
借：管理费用——房租           10,000
  贷：预付账款——房租          10,000
```

**预付保险费示例：**
```
支付时：
借：预付账款——保险费          36,000
  贷：银行存款                36,000

每月摊销（保险期12个月）：
借：管理费用——保险费           3,000
  贷：预付账款——保险费          3,000
```

## 权责发生制调整

### 调整逻辑

| 情形 | 已付款？ | 已受益？ | 处理方式 |
|------|---------|---------|---------|
| 正常费用 | ✅ | ✅ | 直接计入当期费用 |
| 待摊费用 | ✅ | ❌ | 先挂预付，按月摊销 |
| 预提费用 | ❌ | ✅ | 按月计提，到期支付 |
| 未付未受益 | ❌ | ❌ | 暂不处理 |

### 期末调整汇总表

```python
def generate_accrual_prepayment_adjustments(
    prepaid_items: list,
    accrued_items: list,
    period: str
) -> dict:
    """
    生成期末预提待摊调整分录汇总

    参数:
        prepaid_items: [{"name": "房租", "monthly": 10000, "account": "管理费用"}, ...]
        accrued_items: [{"name": "利息", "amount": 18750, "account": "财务费用"}, ...]
        period: 调整期间 "2024-01"

    返回:
        {"entries": [...], "total_debit": X, "total_credit": X}
    """
    entries = []

    # 待摊调整
    for item in prepaid_items:
        entries.append({
            "date": f"{period}-31",
            "description": f"摊销{item['name']}",
            "account_debit": item["account"],
            "amount_debit": item["monthly"],
            "account_credit": "预付账款",
            "amount_credit": item["monthly"]
        })

    # 预提调整
    for item in accrued_items:
        entries.append({
            "date": f"{period}-31",
            "description": f"预提{item['name']}",
            "account_debit": item["account"],
            "amount_debit": item["amount"],
            "account_credit": item.get("credit_account", "其他应付款"),
            "amount_credit": item["amount"]
        })

    total_debit = sum(e["amount_debit"] for e in entries)
    total_credit = sum(e["amount_credit"] for e in entries)

    return {"entries": entries, "total_debit": total_debit, "total_credit": total_credit}
```

### 期末结转前检查清单

- [ ] 所有预提费用（利息、税费、水电费等）是否已计提？
- [ ] 所有待摊费用（房租、保险、订阅费等）是否已摊销？
- [ ] 长期待摊费用（超过1年）是否转入"长期待摊费用"科目？
- [ ] 预提与实际支付的差异是否已调整？
- [ ] 摊销方法是否符合企业会计政策？

## 新旧准则对比

| 项目 | 旧准则科目 | 新准则（企业会计准则） |
|------|-----------|---------------------|
| 预提费用 | 预提费用（负债类） | 其他应付款/应付利息/预计负债 |
| 待摊费用 | 待摊费用（资产类） | 预付账款/其他非流动资产 |
| 长期待摊 | 长期待摊费用 | 长期待摊费用（保留） |

> 小企业会计准则仍可使用"预提费用"和"待摊费用"科目。

## 最佳实践

1. **预提清单制度**：建立月度预提费用清单，避免漏提
2. **摊销核对**：每月摊销前核对预付余额与摊销计划
3. **差异及时处理**：预提与实际差异超过 10% 应及时调整
4. **台账管理**：建立预提/待摊台账，逐项记录发生额、摊销进度、余额
5. **年度清理**：年末检查所有预提待摊项目，确保跨年项目合理
6. **自动摊销**：在财务系统中设置自动摊销模板，减少人工操作失误

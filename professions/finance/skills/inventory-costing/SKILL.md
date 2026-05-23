---
name: inventory-costing
description: "存货成本核算：先进先出(FIFO)/加权平均法/个别计价法计算、存货跌价准备"
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [财务核算, 存货管理, 成本核算]
---

# 存货成本核算

## 概述

本技能涵盖存货发出的三种主要计价方法（先进先出法、加权平均法、个别计价法）的计算过程，以及存货跌价准备的计提与转回操作。准确的存货成本核算直接影响当期损益与资产负债表存货项目的列报。

## 存货计价方法

### 1. 先进先出法（FIFO）

假设**先购入的存货先发出**，期末存货按最近购货成本计价。

**计算规则：**
- 发出存货时，按最早批次的单位成本结转
- 同一批次库存不足时，依次使用下一个批次
- 期末库存成本按最后几批入库成本确定

**示例：**

| 日期 | 业务 | 数量 | 单价 | 金额 |
|------|------|------|------|------|
| 1月1日 | 期初 | 100 | 10 | 1,000 |
| 1月5日 | 购入 | 200 | 12 | 2,400 |
| 1月10日 | 发出 150 件 | -150 | — | — |

发出 150 件成本计算：
- 从第一批（期初 100×10=1,000）
- 不足部分从第二批（50×12=600）
- 发出成本 = 1,000 + 600 = **1,600 元**
- 结存：第二批剩余 150×12 = **1,800 元**

**适用场景：** 商品保质期短、价格呈上涨趋势的行业（如食品、电子产品）

### 2. 加权平均法（全月一次加权平均）

月末计算加权平均单价，统一结转当月全部发出成本。

**计算公式：**
```
加权平均单价 = (期初库存金额 + 本月入库金额) ÷ (期初库存数量 + 本月入库数量)
发出成本 = 加权平均单价 × 发出数量
期末库存 = 加权平均单价 × 期末数量
```

**示例：**

| 业务 | 数量 | 单价 | 金额 |
|------|------|------|------|
| 期初 | 100 | 10.00 | 1,000 |
| 购入 | 200 | 12.00 | 2,400 |
| 购入 | 150 | 11.50 | 1,725 |
| **合计** | **450** | — | **5,125** |

```
加权平均单价 = 5,125 ÷ 450 ≈ 11.39 元
本月发出 300 件成本 = 300 × 11.39 = 3,417 元
期末结存 150 件 = 150 × 11.39 = 1,708 元
```

**注意：** 移动加权平均法（每购入一次就重新计算平均单价）适用于实时成本核算场景。

**适用场景：** 价格波动平稳、收发频繁的企业（如批发零售、制造业）

### 3. 个别计价法（具体辨认法）

每件存货按**实际采购成本**单独计价，发出时直接匹配对应批次。

**要求：**
- 必须有完善的存货标识系统（如条码、批次号、序列号）
- 每批存货单独存放或标记，能够明确辨认
- 适用于数量少、价值高、可单独识别的存货

**示例：**
```
购入 A 设备 3 台：
  第 1 台：10,000 元（序列号 SN001）
  第 2 台：10,500 元（序列号 SN002）
  第 3 台：11,000 元（序列号 SN003）

卖出 SN002：发出成本 = 10,500 元
期末结存：SN001 + SN003 = 10,000 + 11,000 = 21,000 元
```

**适用场景：** 珠宝、艺术品、定制设备、汽车、大型机械等

### 方法对比

| 方法 | 发出成本 | 期末成本 | 利润影响（物价上涨） | 利润影响（物价下跌） |
|------|---------|---------|-------------------|-------------------|
| 先进先出 | 较低（早期低价） | 较高（近期高价） | 利润偏高 | 利润偏低 |
| 加权平均 | 居中 | 居中 | 利润居中 | 利润居中 |
| 个别计价 | 按实际辨认 | 按实际辨认 | 最真实 | 最真实 |

## 成本核算实现

### 通用成本核算函数

```python
def calculate_inventory_cost(
    opening_qty: int,
    opening_cost: float,
    purchases: list,
    sales_qty: int,
    method: str = "fifo"
) -> dict:
    """
    计算存货发出成本及期末结存

    参数:
        opening_qty: 期初数量
        opening_cost: 期初总成本
        purchases: [(数量, 单价), ...] 入库记录
        sales_qty: 发出数量
        method: fifo / weighted_average / specific

    返回:
        {"cost_of_goods_sold": float, "closing_stock": float}
    """
    if method == "fifo":
        batches = [{"qty": opening_qty, "unit_cost": opening_cost / opening_qty}]
        for qty, unit_cost in purchases:
            batches.append({"qty": qty, "unit_cost": unit_cost})

        remaining = sales_qty
        cog_total = 0
        idx = 0
        while remaining > 0 and idx < len(batches):
            take = min(remaining, batches[idx]["qty"])
            cog_total += take * batches[idx]["unit_cost"]
            batches[idx]["qty"] -= take
            remaining -= take
            if batches[idx]["qty"] == 0:
                idx += 1

        closing_stock = sum(b["qty"] * b["unit_cost"] for b in batches if b["qty"] > 0)
        return {"cost_of_goods_sold": cog_total, "closing_stock": round(closing_stock, 2)}

    elif method == "weighted_average":
        total_qty = opening_qty + sum(q for q, _ in purchases)
        total_cost = opening_cost + sum(q * p for q, p in purchases)
        avg_cost = total_cost / total_qty if total_qty > 0 else 0
        cog_total = sales_qty * avg_cost
        closing_stock = (total_qty - sales_qty) * avg_cost
        return {"cost_of_goods_sold": round(cog_total, 2),
                "closing_stock": round(closing_stock, 2)}

    elif method == "specific":
        # 需外部传入各件存货的实际成本
        raise NotImplementedError(
            "个别计价法需要每件存货的实际成本数据，请提供 specific_costs 参数")
    else:
        raise ValueError(f"不支持的计价方法: {method}")
```

### 自动结转成本分录

```
借：主营业务成本          XXX
  贷：库存商品            XXX
```

## 存货跌价准备

### 计提原则

当存货的**成本**高于**可变现净值**（NRV）时，差额计提存货跌价准备。

```
可变现净值 = 估计售价 - 估计完工成本 - 估计销售费用及税金
应计提跌价 = max(成本 - 可变现净值, 0)
```

### 计提测试层级

1. **单项测试**：有明确合同的存货，按合同价确定售价
2. **类别测试**：数量多、单价低且难以单独辨认的，按存货类别计提
3. **合并测试**：在同一地区生产和销售、具有相同用途的系列产品

### 多产品跌价计算示例

```python
def assess_inventory_impairment(inventory_items: list) -> list:
    """
    逐项评估存货跌价准备

    参数格式:
        [{"name": "商品A", "cost": 10000, "nrv": 8500}, ...]

    返回:
        [{"name": "商品A", "cost": 10000, "nrv": 8500,
          "impairment": 1500, "status": "需计提"}, ...]
    """
    results = []
    for item in inventory_items:
        impairment = max(item["cost"] - item["nrv"], 0)
        results.append({
            **item,
            "impairment": impairment,
            "status": "需计提" if impairment > 0 else "正常"
        })
    return results
```

### 会计分录

**计提跌价准备：**
```
借：资产减值损失           XXX
  贷：存货跌价准备         XXX
```

**已计提跌价的存货出售时：**
```
借：主营业务成本           XXX
    存货跌价准备           XXX
  贷：库存商品             XXX
```

### 跌价转回

- 以前减记存货价值的影响因素已经消失的，可**在原计提范围内转回**
- 转回金额以原计提的存货跌价准备余额为上限
- 转回分录：与原计提相反

```
借：存货跌价准备           XXX
  贷：资产减值损失         XXX
```

## 最佳实践

1. **计价方法一贯性**：一经选定不得随意变更，确需变更需在报表附注披露
2. **定期盘点核实**：每月盘点核查账实是否相符
3. **跌价测试时点**：资产负债表日（月度/季度/年度）进行跌价测试
4. **残次冷背管理**：对过时、变质、滞销存货及时评估并计提全額跌价
5. **永续盘存制**：实时更新存货收发存记录，减少期末盘点压力
6. **税务差异关注**：会计跌价准备不得税前扣除，需做纳税调增

---
name: invoice-to-voucher
description: "发票→凭证全流程：拍照/上传发票 → OCR识别 → 科目建议 → 自动生成记账凭证"
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [发票, OCR, 凭证, 记账, 会计分录, 报销, invoice, voucher]
    related_skills: [account-reconciliation, voucher-entry]
---

# 发票→凭证 全流程

## 功能

拍一张发票照片，自动完成：
1. **OCR 识别** — 提取金额/税额/对方单位/发票号码等
2. **科目建议** — 根据业务内容推荐最匹配的会计科目
3. **凭证生成** — 输出标准借贷分录，借方贷方自动平衡

## 操作流程

### 步骤 1：用户上传发票图片

用户通过微信/CLI 发送发票照片（支持 jpg/png/pdf）。

### 步骤 2：调用发票 OCR

```python
from professions.finance.tools.invoice_ocr import extract_invoice_info

invoice = extract_invoice_info("发票图片路径")
# → {invoice_no, date, seller_name, amount, tax, total, items, ...}
```

同时用 `vision_analyze` 工具分析图片，将 OCR 提示词传给视觉模型。

### 步骤 3：科目建议

```python
from professions.finance.tools.account_suggest import suggest_from_invoice

suggestion = suggest_from_invoice(invoice)
# → {debit, debit_amount, tax_debit, tax_amount, credit, credit_amount, confidence}
```

### 步骤 4：生成凭证

```python
from professions.finance.tools.voucher_generate import generate_voucher

voucher = generate_voucher(suggestion, invoice=invoice)
# → 完整的借贷分录，含摘要、凭证编号
```

### 步骤 5：展示结果

向用户展示：
- 📄 发票基本信息
- 📝 建议会计分录
- ✅ 借方贷方平衡确认
- 📋 备选科目方案

## 输出示例

```
📄 发票号码：12345678
📅 开票日期：2026-05-22
🏢 对方：XX办公用品有限公司
💰 金额：¥1,000.00
📊 税额：¥130.00
💵 价税合计：¥1,130.00

📝 建议分录：
  借：管理费用-办公费                  ¥1,000.00
  借：应交税费-应交增值税-进项税额        ¥130.00
      贷：银行存款                      ¥1,130.00

置信度：95%
```

## 注意事项

1. **发票类型识别**：自动识别专票/普票/全电发票，专票自动提取进项税额
2. **小规模纳税人**：如果用户是小规模纳税人，进项税额计入成本，不单独列示
3. **模糊匹配**：对于无法精确匹配的发票内容，提供多个备选方案
4. **金额校验**：自动校验价税合计 = 金额 + 税额
5. **实际入账前请人工审核**：工具建议仅供参考，最终分录以财务人员判断为准

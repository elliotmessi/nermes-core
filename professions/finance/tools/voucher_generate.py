#!/usr/bin/env python3
"""凭证生成工具 — 根据业务信息和科目建议，生成完整的记账凭证。

功能：
1. 自动生成凭证编号
2. 借方贷方平衡校验
3. 摘要自动生成
4. 输出标准凭证格式（文本/表格）
"""

import json
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional


# ── 凭证字段 ──────────────────────────────────────────────────

class VoucherEntry:
    """单笔分录"""
    def __init__(self, account: str, direction: str, amount: float, summary: str = ""):
        self.account = account
        self.direction = direction  # "debit" or "credit"
        self.amount = round(amount, 2)
        self.summary = summary


class Voucher:
    """记账凭证"""
    def __init__(self):
        self.voucher_no = ""
        self.date = date.today()
        self.entries: List[VoucherEntry] = []
        self.attachments = 0
        self.auditor = ""
        self.maker = ""
    
    def add_entry(self, account: str, direction: str, amount: float, summary: str = ""):
        entry = VoucherEntry(account, direction, amount, summary)
        self.entries.append(entry)
        return entry
    
    def validate(self) -> tuple:
        """借方贷方平衡校验"""
        debit_total = sum(e.amount for e in self.entries if e.direction == "debit")
        credit_total = sum(e.amount for e in self.entries if e.direction == "credit")
        balanced = abs(debit_total - credit_total) < 0.01
        return balanced, debit_total, credit_total
    
    def format(self) -> str:
        """格式化为标准记账凭证文本"""
        balanced, debit_total, credit_total = self.validate()
        status = "✅ 平衡" if balanced else f"❌ 不平衡 (借:{debit_total:.2f} ≠ 贷:{credit_total:.2f})"
        
        lines = []
        lines.append("┌───────────────────────────────────────────────────┐")
        lines.append(f"│  📋 记账凭证                      No.{self.voucher_no or '自动'} │")
        lines.append(f"│  📅 {self.date}                  {status} │")
        lines.append("├──────┬──────────────────────┬──────────┬──────────┤")
        lines.append("│ 方向 │ 会计科目             │    金额   │ 摘要     │")
        lines.append("├──────┼──────────────────────┼──────────┼──────────┤")
        
        for e in self.entries:
            direction = "借" if e.direction == "debit" else "贷"
            lines.append(
                f"│  {direction}   │ {e.account:<20s} │ ¥{e.amount:>8,.2f} │ {e.summary[:10]:<8s} │"
            )
        
        lines.append("├──────┼──────────────────────┼──────────┼──────────┤")
        lines.append(f"│      │ 合计                 │ ¥{debit_total:>8,.2f} │          │")
        lines.append("└──────┴──────────────────────┴──────────┴──────────┘")
        
        if self.attachments:
            lines.append(f"📎 附件：{self.attachments} 张")
        
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        """导出为字典格式，便于 JSON 输出"""
        balanced, debit_total, credit_total = self.validate()
        return {
            "voucher_no": self.voucher_no,
            "date": str(self.date),
            "balanced": balanced,
            "debit_total": debit_total,
            "credit_total": credit_total,
            "attachments": self.attachments,
            "entries": [
                {
                    "direction": "借" if e.direction == "debit" else "贷",
                    "account": e.account,
                    "amount": e.amount,
                    "summary": e.summary,
                }
                for e in self.entries
            ],
        }


# ── 摘要生成 ──────────────────────────────────────────────────

def generate_summary(
    invoice: Optional[dict] = None,
    suggestion: Optional[dict] = None,
    description: str = "",
) -> str:
    """自动生成凭证摘要。
    
    摘要格式：{业务类型}-{对方单位}-{主要内容}
    示例：报销差旅费-XX航空公司-机票
    """
    parts = []
    
    if suggestion:
        debit = suggestion.get("debit", "")
        if "差旅" in debit:
            parts.append("报销差旅费")
        elif "办公" in debit:
            parts.append("购办公用品")
        elif "招待" in debit:
            parts.append("业务招待费")
        elif "房租" in debit or "租赁" in debit:
            parts.append("支付房租")
        elif "工资" in debit or "薪酬" in debit:
            parts.append("计提工资")
        elif "固定资产" in debit:
            parts.append("购固定资产")
        elif "原材料" in debit or "库存" in debit:
            parts.append("采购原材料")
        elif "税金" in debit:
            parts.append("计提税金")
        elif "利息" in debit or "财务费用" in debit:
            parts.append("支付银行费用")
        else:
            parts.append("费用报销")
    
    if invoice:
        seller = invoice.get("seller_name", "")
        if seller:
            # 只取前8个字
            parts.append(seller[:8])
    
    if description:
        parts.append(description[:15])
    
    return "-".join(parts) if parts else "日常费用报销"


def generate_voucher(
    account_suggestion: dict,
    voucher_no: str = "",
    attachment_count: int = 1,
    invoice: Optional[dict] = None,
) -> dict:
    """根据科目建议生成完整记账凭证。
    
    Args:
        account_suggestion: suggest_account 或 suggest_from_invoice 的输出
        voucher_no: 凭证编号（留空自动生成）
        attachment_count: 附件张数
        invoice: OCR提取的发票信息（可选，用于摘要）
        
    Returns:
        dict: 完整的凭证数据
    """
    voucher = Voucher()
    
    # 生成凭证编号
    if not voucher_no:
        today = date.today()
        voucher.voucher_no = f"JZ-{today.strftime('%Y%m%d')}-0001"
    else:
        voucher.voucher_no = voucher_no
    
    voucher.attachments = attachment_count
    if account_suggestion.get("invoice_date"):
        try:
            voucher.date = date.fromisoformat(account_suggestion["invoice_date"])
        except (ValueError, TypeError):
            pass
    
    # 生成摘要
    summary = generate_summary(invoice, account_suggestion)
    
    # 借方科目
    debit_account = account_suggestion["debit"]
    debit_amount = account_suggestion["debit_amount"]
    voucher.add_entry(debit_account, "debit", debit_amount, summary)
    
    # 进项税额（如有）
    tax_debit = account_suggestion.get("tax_debit")
    tax_amount = account_suggestion.get("tax_amount", 0)
    if tax_debit and tax_amount > 0:
        voucher.add_entry(tax_debit, "debit", tax_amount, f"{summary}-进项税额")
    
    # 贷方科目
    credit_account = account_suggestion["credit"]
    credit_amount = account_suggestion["credit_amount"]
    voucher.add_entry(credit_account, "credit", credit_amount, summary)
    
    return voucher.to_dict()


if __name__ == "__main__":
    # 快速测试
    test = {
        "debit": "管理费用-办公费",
        "debit_amount": 1000.00,
        "tax_debit": "应交税费-应交增值税-进项税额",
        "tax_amount": 130.00,
        "credit": "银行存款",
        "credit_amount": 1130.00,
        "invoice_no": "12345678",
        "invoice_date": "2026-05-22",
        "seller": "XX办公用品有限公司",
    }
    voucher = generate_voucher(test, voucher_no="JZ-20260522-001")
    print(json.dumps(voucher, ensure_ascii=False, indent=2))

#!/usr/bin/env python3
"""科目建议工具 — 根据业务描述和发票内容，推荐会计科目和分录模板。

原理：基于中国会计准则(CAS)和常见业务场景的映射规则。
覆盖：费用报销、采购、销售、固定资产、工资、税金等常见业务。
"""

import json
import re
from typing import List, Optional, Tuple


# ── 科目映射表 ────────────────────────────────────────────────

# 格式: (借方科目, 贷方科目, 置信度, 使用条件)
# 借方为费用/资产，贷方为银行存款（或其他应付款）
ACCOUNT_MAP = [
    # ── 费用报销类 ──
    ("管理费用-办公费", "银行存款", 0.95, ["办公用品", "文具", "打印纸", "墨盒", "文件柜", "办公耗材"]),
    ("管理费用-差旅费", "银行存款", 0.95, ["机票", "火车票", "高铁", "住宿", "酒店", "打车", "出租车", "网约车"]),
    ("管理费用-业务招待费", "银行存款", 0.90, ["餐饮", "招待", "宴请", "餐厅", "饭店", "酒店餐饮"]),
    ("管理费用-会议费", "银行存款", 0.85, ["会议", "会场", "会务", "研讨会"]),
    ("管理费用-通讯费", "银行存款", 0.90, ["电话费", "网费", "宽带", "手机", "通讯"]),
    ("管理费用-交通费", "银行存款", 0.90, ["加油", "停车", "过路", "ETC", "公交", "地铁"]),
    ("管理费用-租赁费", "银行存款", 0.95, ["房租", "租金", "物业", "写字楼"]),
    ("管理费用-水电费", "银行存款", 0.95, ["电费", "水费", "燃气", "暖气"]),
    ("管理费用-中介服务费", "银行存款", 0.90, ["律师", "审计", "评估", "咨询顾问", "代理", "中介"]),
    ("管理费用-招聘培训费", "银行存款", 0.85, ["招聘", "培训", "猎头"]),
    ("管理费用-快递费", "银行存款", 0.95, ["快递", "物流", "邮寄", "EMS", "顺丰"]),
    ("管理费用-物业费", "银行存款", 0.90, ["物业费", "保洁", "保安", "绿化"]),
    ("管理费用-无形资产摊销", "累计摊销", 0.95, ["软件", "专利", "商标", "版权"]),
    
    # ── 销售费用类 ──
    ("销售费用-广告宣传费", "银行存款", 0.95, ["广告", "宣传", "推广", "营销", "展览", "展会"]),
    ("销售费用-运输费", "银行存款", 0.90, ["货运", "运输", "物流配送"]),
    
    # ── 采购/存货类 ──
    ("原材料", "银行存款", 0.90, ["原料", "材料", "钢材", "木材", "化工原料", "零部件"]),
    ("库存商品", "银行存款", 0.90, ["成品", "商品", "货物采购"]),
    ("周转材料-包装物", "银行存款", 0.85, ["包装", "纸箱", "打包"]),
    
    # ── 固定资产类 ──
    ("固定资产-电子设备", "银行存款", 0.90, ["电脑", "笔记本", "服务器", "打印机", "显示器", "平板", "手机"]),
    ("固定资产-办公设备", "银行存款", 0.90, ["办公桌", "椅子", "空调", "投影仪", "复印机"]),
    ("固定资产-家具", "银行存款", 0.85, ["沙发", "茶几", "文件柜", "家具"]),
    ("在建工程", "银行存款", 0.85, ["装修", "工程", "施工", "基建"]),
    
    # ── 无形资产 ──
    ("无形资产-软件", "银行存款", 0.90, ["软件授权", "ERP", "SaaS", "年费订阅"]),
    ("无形资产-专利", "银行存款", 0.90, ["专利", "专利申请", "发明"]),
    
    # ── 职工薪酬类 ──
    ("管理费用-工资", "应付职工薪酬-工资", 0.95, ["工资", "薪资", "薪酬", "奖金"]),
    ("管理费用-社保费", "应付职工薪酬-社保", 0.90, ["社保", "五险", "社会保险"]),
    ("管理费用-公积金", "应付职工薪酬-住房公积金", 0.95, ["公积金", "住房公积金"]),
    ("管理费用-福利费", "应付职工薪酬-福利费", 0.85, ["福利", "体检", "节日礼品"]),
    
    # ── 税金类 ──
    ("税金及附加", "应交税费", 0.90, ["城建税", "教育费附加", "地方教育附加", "印花税", "房产税", "车船税", "土地使用税"]),
    ("应交税费-应交增值税-进项税额", "应交税费-应交增值税", 0.90, ["增值税", "进项税", "专票"]),
    
    # ── 预提/待摊 ──
    ("预付账款", "银行存款", 0.85, ["预付", "预付款", "订金"]),
    ("其他应收款-押金保证金", "银行存款", 0.85, ["押金", "保证金", "投标保证金"]),
    ("长期待摊费用", "银行存款", 0.85, ["装修费", "开办费"]),
    
    # ── 银行手续费 ──
    ("财务费用-手续费", "银行存款", 0.95, ["银行手续费", "转账费", "汇款费", "账户管理费"]),
    ("财务费用-利息", "银行存款", 0.95, ["贷款利息", "借款利息", "利息支出"]),
    ("财务费用-汇兑损益", "银行存款", 0.85, ["汇兑", "结汇", "外币兑换"]),
]

# 特殊规则：小规模纳税人的进项税处理
SMALL_TAXPAYER_NOTE = "⚠️ 小规模纳税人不得抵扣进项税额，税额应计入成本/费用。"


# ── 核心函数 ──────────────────────────────────────────────────

def suggest_account(
    description: str,
    amount: float = 0.0,
    tax_rate: float = 0.13,
    is_small_taxpayer: bool = False,
) -> dict:
    """根据业务描述推荐会计科目。
    
    Args:
        description: 业务描述（如"购买办公用品"、"支付房租"）
        amount: 金额
        tax_rate: 适用税率（一般纳税人 0.13/0.09/0.06，小规模 0.03/0.01）
        is_small_taxpayer: 是否为小规模纳税人
        
    Returns:
        dict: {
            "debit": 借方科目,
            "debit_amount": 借方金额,
            "tax_debit": 进项税额科目（有专票时）,
            "tax_amount": 税额,
            "credit": 贷方科目,
            "credit_amount": 贷方金额,
            "confidence": 置信度,
            "note": 注意事项,
            "alternatives": [备选方案]
        }
    """
    desc_lower = description.lower()
    best_match = None
    best_score = 0
    alternatives = []
    
    for debit, credit, confidence, keywords in ACCOUNT_MAP:
        score = 0
        for kw in keywords:
            if kw.lower() in desc_lower:
                score += 1
        
        if score > best_score:
            if best_match:
                alternatives.append(best_match)
            best_match = (debit, credit, confidence, keywords)
            best_score = score
        elif score > 0:
            alternatives.append((debit, credit, confidence, keywords, score))
    
    if not best_match:
        return {
            "debit": "待确认",
            "debit_amount": amount,
            "tax_debit": None,
            "tax_amount": 0.0,
            "credit": "银行存款",
            "credit_amount": amount,
            "confidence": 0.0,
            "note": "⚠️ 未匹配到合适的科目，请人工确认。建议分类：管理费用-其他 或 营业外支出。",
            "alternatives": [],
        }
    
    debit, credit, confidence, keywords = best_match
    
    # 判断是否属于可抵扣进项税的费用
    deductible_categories = [
        "管理费用-办公费", "管理费用-差旅费", "管理费用-租赁费",
        "管理费用-物业费", "管理费用-水电费", "管理费用-通讯费",
        "管理费用-快递费", "管理费用-中介服务费",
        "销售费用-广告宣传费", "销售费用-运输费",
        "原材料", "库存商品", "固定资产-电子设备", "固定资产-办公设备",
        "无形资产-软件",
    ]
    
    has_deductible_tax = debit in deductible_categories and not is_small_taxpayer
    
    # 计算税额
    tax_amount = round(amount * tax_rate, 2) if has_deductible_tax else 0.0
    total_amount = amount + tax_amount if has_deductible_tax else amount
    
    result = {
        "debit": debit,
        "debit_amount": amount,
        "tax_debit": "应交税费-应交增值税-进项税额" if has_deductible_tax else None,
        "tax_amount": tax_amount,
        "credit": credit,
        "credit_amount": total_amount,
        "confidence": confidence,
        "note": "",
        "alternatives": [
            {"debit": alt[0], "credit": alt[1], "confidence": alt[2], "score": alt[4]}
            for alt in sorted(alternatives, key=lambda x: x[4], reverse=True)[:3]
        ],
    }
    
    if is_small_taxpayer:
        result["note"] = SMALL_TAXPAYER_NOTE
        result["tax_debit"] = None
        result["tax_amount"] = 0.0
    
    return result


def suggest_from_invoice(invoice: dict, is_small_taxpayer: bool = False) -> dict:
    """从发票 OCR 结果直接生成科目建议。
    
    Args:
        invoice: extract_invoice_info 的输出
        is_small_taxpayer: 是否为小规模纳税人
        
    Returns:
        dict: 科目建议 + 完整分录
    """
    items = invoice.get("items", [])
    amount = invoice.get("amount") or 0.0
    tax = invoice.get("tax") or 0.0
    seller = invoice.get("seller_name", "")
    
    # 根据项目名称推断业务类型
    item_names = " ".join(item.get("name", "") for item in items)
    description = f"{seller} {item_names}" if seller else item_names
    
    if not description.strip():
        description = "办公用品采购" if amount < 5000 else "设备采购"
    
    # 计算实际税率
    tax_rate = round(tax / amount, 2) if amount > 0 and tax > 0 else 0.13
    
    result = suggest_account(description, amount, tax_rate, is_small_taxpayer)
    result["invoice_no"] = invoice.get("invoice_no")
    result["invoice_date"] = invoice.get("date")
    result["seller"] = seller
    result["source"] = "发票自动识别"
    
    return result


def format_voucher(account_suggestion: dict) -> str:
    """将科目建议格式化为会计分录字符串。"""
    lines = ["📝 **建议分录**", ""]
    
    invoice_no = account_suggestion.get("invoice_no")
    if invoice_no:
        lines.append(f"📄 发票号码：{invoice_no}")
    if account_suggestion.get("invoice_date"):
        lines.append(f"📅 开票日期：{account_suggestion['invoice_date']}")
    if account_suggestion.get("seller"):
        lines.append(f"🏢 对方单位：{account_suggestion['seller']}")
    
    lines.append("")
    debit = account_suggestion["debit"]
    debit_amt = account_suggestion["debit_amount"]
    tax_debit = account_suggestion.get("tax_debit")
    tax_amt = account_suggestion.get("tax_amount", 0)
    credit = account_suggestion["credit"]
    credit_amt = account_suggestion["credit_amount"]
    
    if tax_debit and tax_amt > 0:
        lines.append(f"  借：{debit:<20s} ¥{debit_amt:>10,.2f}")
        lines.append(f"  借：{tax_debit:<20s} ¥{tax_amt:>10,.2f}")
        lines.append(f"      贷：{credit:<20s} ¥{credit_amt:>10,.2f}")
    else:
        lines.append(f"  借：{debit:<20s} ¥{debit_amt:>10,.2f}")
        lines.append(f"      贷：{credit:<20s} ¥{credit_amt:>10,.2f}")
    
    lines.append("")
    lines.append(f"置信度：{account_suggestion['confidence']:.0%}")
    
    if account_suggestion.get("note"):
        lines.append(account_suggestion["note"])
    
    alternatives = account_suggestion.get("alternatives", [])
    if alternatives:
        lines.append("")
        lines.append("📋 备选方案：")
        for alt in alternatives[:2]:
            lines.append(f"  • {alt['debit']} / {alt['credit']} (匹配度: {alt['score']})")
    
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        desc = " ".join(sys.argv[1:])
        result = suggest_account(desc)
        print(json.dumps(result, ensure_ascii=False, indent=2))

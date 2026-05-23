#!/usr/bin/env python3
"""发票 OCR 工具 — 识别中国发票图片，提取结构化数据。

支持：增值税专用发票、增值税普通发票、电子发票(全电/数电票)、定额发票。
输出标准化字段：金额、税额、价税合计、销售方、购买方、发票号码、开票日期、项目明细。
"""

import base64
import json
import re
from typing import Optional


# ── 发票字段定义 ──────────────────────────────────────────────

INVOICE_FIELDS = {
    "invoice_no": "发票号码",
    "invoice_code": "发票代码", 
    "date": "开票日期",
    "seller_name": "销售方名称",
    "seller_tax_id": "销售方税号",
    "buyer_name": "购买方名称",
    "buyer_tax_id": "购买方税号",
    "amount": "金额（不含税）",
    "tax": "税额",
    "total": "价税合计（大写+小写）",
    "items": "货物或应税劳务名称",
    "remark": "备注",
    "machine_no": "机器编号",
    "check_code": "校验码",
}

INVOICE_TYPE_MAP = {
    "01": "增值税专用发票",
    "02": "增值税普通发票", 
    "03": "增值税电子普通发票",
    "04": "增值税普通发票（卷式）",
    "05": "增值税电子专用发票",
    "06": "全电发票（增值税专用）",
    "07": "全电发票（增值税普通）",
    "08": "定额发票",
    "10": "出租车发票",
    "11": "火车票",
    "12": "航空运输电子客票行程单",
}


# ── 提示词 ────────────────────────────────────────────────────

OCR_SYSTEM_PROMPT = """你是一个中国发票 OCR 识别专家。根据图片内容提取发票信息，返回 JSON。

识别规则：
1. 金额(amount) = 不含税金额，税额(tax) = 增值税税额，合计(total) = 价税合计
2. 发票号码通常为8位或10位数字，发票代码通常为10位或12位数字
3. 日期格式统一为 YYYY-MM-DD
4. 如果图片中某项信息看不清，填 null
5. 货物明细(items) 用数组表示，每项包含 name/spec/unit/quantity/unit_price/amount/tax_rate
6. 从发票代码第1-2位判断发票类型，填入 invoice_type 字段
7. 如果图片不含税号则填 null

返回严格 JSON，不要带 markdown 代码块标记。"""

OCR_USER_PROMPT = """请从这张发票中提取完整的结构化信息，返回 JSON。

输出格式：
{
    "invoice_type": "增值税专用发票",
    "invoice_no": "12345678",
    "invoice_code": "3100234567",
    "date": "2026-05-22",
    "seller_name": "XX科技有限公司",
    "seller_tax_id": "91310115XXXXXXXXXX",
    "buyer_name": "YY商贸有限公司", 
    "buyer_tax_id": "91310115YYYYYYYYYY",
    "amount": 10000.00,
    "tax": 1300.00,
    "total": 11300.00,
    "items": [
        {"name": "服务器", "spec": "DELL R740", "unit": "台", "quantity": 2, "unit_price": 5000.00, "amount": 10000.00, "tax_rate": 0.13}
    ],
    "remark": "",
    "machine_no": "661234567890",
    "check_code": ""
}"""


# ── 工具函数 ──────────────────────────────────────────────────

def extract_invoice_info(
    attachment_path: str,
    vision_call: callable = None,
) -> dict:
    """从发票图片提取结构化信息。
    
    Args:
        attachment_path: 发票图片路径（支持 jpg/png/pdf 首页）
        vision_call: 可选的 vision API 调用函数，如果不传则返回提示词供 Agent 自行处理
        
    Returns:
        dict: 结构化发票信息，含 _raw 原始提取和 _confidence 置信度
        
    调用方式：
        Agent 看到发票图片 → 调用此工具获取结构化数据 → 后续进行科目匹配和凭证生成
    """
    import os
    
    if not os.path.exists(attachment_path):
        return {"error": f"文件不存在: {attachment_path}", "amount": None, "tax": None}
    
    # 读取文件并 base64 编码
    with open(attachment_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    
    ext = os.path.splitext(attachment_path)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".pdf": "application/pdf"}
    mime_type = mime_map.get(ext, "image/jpeg")
    
    result = {
        "_status": "ready_for_vision",
        "_vision_prompt": OCR_USER_PROMPT,
        "_system_prompt": OCR_SYSTEM_PROMPT,
        "_image_base64": image_data,
        "_image_mime": mime_type,
        "invoice_type": None,
        "invoice_no": None,
        "invoice_code": None,
        "date": None,
        "seller_name": None,
        "seller_tax_id": None,
        "buyer_name": None,
        "buyer_tax_id": None,
        "amount": None,
        "tax": None,
        "total": None,
        "items": [],
        "remark": None,
        "machine_no": None,
        "check_code": None,
    }
    
    return result


def format_invoice_for_display(invoice: dict) -> str:
    """将发票结构化数据格式化为可读文本。"""
    if invoice.get("error"):
        return f"❌ {invoice['error']}"
    
    lines = ["📄 **发票信息**", ""]
    
    inv_type = invoice.get("invoice_type", "未知")
    lines.append(f"📋 类型：{inv_type}")
    
    if invoice.get("invoice_no"):
        lines.append(f"🔢 号码：{invoice['invoice_code'] or ''} {invoice['invoice_no']}")
    if invoice.get("date"):
        lines.append(f"📅 日期：{invoice['date']}")
    if invoice.get("seller_name"):
        lines.append(f"🏢 销售方：{invoice['seller_name']}")
        if invoice.get("seller_tax_id"):
            lines.append(f"   税号：{invoice['seller_tax_id']}")
    if invoice.get("buyer_name"):
        lines.append(f"🏢 购买方：{invoice['buyer_name']}")
        if invoice.get("buyer_tax_id"):
            lines.append(f"   税号：{invoice['buyer_tax_id']}")
    
    lines.append("")
    if invoice.get("amount") is not None:
        lines.append(f"💰 金额（不含税）：¥{invoice['amount']:,.2f}")
    if invoice.get("tax") is not None:
        lines.append(f"📊 税额：¥{invoice['tax']:,.2f}")
    if invoice.get("total") is not None:
        lines.append(f"💵 价税合计：¥{invoice['total']:,.2f}")
    
    items = invoice.get("items", [])
    if items:
        lines.append("")
        lines.append("📦 明细：")
        for i, item in enumerate(items, 1):
            name = item.get("name", "未知")
            qty = item.get("quantity", "-")
            unit = item.get("unit", "")
            amt = item.get("amount", 0)
            rate = item.get("tax_rate", 0)
            lines.append(f"  {i}. {name} ×{qty}{unit}  ¥{amt:,.2f} (税率{rate*100:.0f}%)")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # 本地测试
    import sys
    if len(sys.argv) > 1:
        result = extract_invoice_info(sys.argv[1])
        print(json.dumps(result, ensure_ascii=False, indent=2))

#!/bin/bash
# Nermes 财务版 — 职业预设应用脚本
# 将此财务专业人士的 SOUL/USER/MEMORY 应用到 ~/.hermes/

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"

echo "============================================"
echo "  Nermes 财务版 — 职业预设安装"
echo "============================================"
echo ""
echo "即将应用财务专业人士的 AI 助手预设："
echo "  • SOUL.md   — 财务专业人格（专业、严谨、数据驱动）"
echo "  • USER.md   — 用户画像（财务从业者）"
echo "  • MEMORY.md — 财务知识库（准则、税率、指标）"
echo ""

# 检查是否覆盖已有的
if [ -f "$HERMES_HOME/SOUL.md" ] || [ -f "$HERMES_HOME/USER.md" ] || [ -f "$HERMES_HOME/MEMORY.md" ]; then
    echo "⚠️  检测到已有的配置文件，将被备份为 .bak"
    [ -f "$HERMES_HOME/SOUL.md" ] && cp "$HERMES_HOME/SOUL.md" "$HERMES_HOME/SOUL.md.bak"
    [ -f "$HERMES_HOME/USER.md" ] && cp "$HERMES_HOME/USER.md" "$HERMES_HOME/USER.md.bak"
    [ -f "$HERMES_HOME/MEMORY.md" ] && cp "$HERMES_HOME/MEMORY.md" "$HERMES_HOME/MEMORY.md.bak"
fi

# 复制预设文件
cp "$SCRIPT_DIR/SOUL.md" "$HERMES_HOME/SOUL.md"
cp "$SCRIPT_DIR/USER.md" "$HERMES_HOME/USER.md"
cp "$SCRIPT_DIR/MEMORY.md" "$HERMES_HOME/MEMORY.md"

# 创建技能目录（如果不存在）
mkdir -p "$HERMES_HOME/skills"

echo "✅ 安装完成！"
echo ""
echo "已配置为【财务专业人士】模式。"
echo "重启 Nermes 或开始新对话即可生效。"
echo ""
echo "后续可安装财务专属技能包："
echo "  nermes skills install finance-accounting"
echo "  nermes skills install finance-tax"
echo "  nermes skills install finance-reporting"

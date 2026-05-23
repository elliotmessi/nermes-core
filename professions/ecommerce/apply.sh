#!/bin/bash
# Nermes 电商运营版 — 职业预设应用脚本
# 将此电商运营专家的 SOUL/USER/MEMORY 应用到 ~/.nermes/

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NERMES_HOME="${NERMES_HOME:-${HERMES_HOME:-$HOME/.nermes}}"

echo "============================================"
echo "  Nermes 电商运营版 — 职业预设安装"
echo "============================================"
echo ""
echo "即将应用电商运营专家的 AI 助手预设："
echo "  • SOUL.md   — 电商运营专业人格（数据驱动、平台敏感）"
echo "  • USER.md   — 用户画像（电商从业者）"
echo "  • MEMORY.md — 电商知识库（费率、术语、活动日历、话术模板）"
echo ""

# 检查是否覆盖已有的
if [ -f "$NERMES_HOME/SOUL.md" ] || [ -f "$NERMES_HOME/USER.md" ] || [ -f "$NERMES_HOME/MEMORY.md" ]; then
    echo "⚠️  检测到已有的配置文件，将被备份为 .bak"
    [ -f "$NERMES_HOME/SOUL.md" ] && cp "$NERMES_HOME/SOUL.md" "$NERMES_HOME/SOUL.md.bak"
    [ -f "$NERMES_HOME/USER.md" ] && cp "$NERMES_HOME/USER.md" "$NERMES_HOME/USER.md.bak"
    [ -f "$NERMES_HOME/MEMORY.md" ] && cp "$NERMES_HOME/MEMORY.md" "$NERMES_HOME/MEMORY.md.bak"
fi

# 复制预设文件
cp "$SCRIPT_DIR/SOUL.md" "$NERMES_HOME/SOUL.md"
cp "$SCRIPT_DIR/USER.md" "$NERMES_HOME/USER.md"
cp "$SCRIPT_DIR/MEMORY.md" "$NERMES_HOME/MEMORY.md"

# 创建技能目录（如果不存在）
mkdir -p "$NERMES_HOME/skills"

echo "✅ 安装完成！"
echo ""
echo "已配置为【电商运营专家】模式。"
echo "重启 Nermes 或开始新对话即可生效。"
echo ""
echo "后续可安装电商专属技能包："
echo "  nermes skills install ecommerce-product-optimization"
echo "  nermes skills install ecommerce-data-analysis"
echo "  nermes skills install ecommerce-customer-service"

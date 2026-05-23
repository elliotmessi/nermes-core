# Nermes 职业预设

此目录包含各行业/职业的 AI 助手预设包。

每个职业预设包含：
- `SOUL.md` — Agent 人格和语气设定
- `USER.md` — 用户画像描述
- `MEMORY.md` — 初始知识库记忆
- `apply.sh` — 一键应用脚本
- `skills/` — 职业专属技能（可选）
- `knowledge/` — 知识库文档（可选）
- `tools/` — 自定义工具（可选）

## 使用方法

```bash
# 安装财务版预设
./professions/finance/apply.sh

# 安装其他职业预设（后续开发）
./professions/lawyer/apply.sh
./professions/teacher/apply.sh
```

## 已支持职业

| 职业 | 目录 | 状态 |
|------|------|------|
| 财务专业人士 | `finance/` | ✅ 已发布 |
| 电商运营 | `ecommerce/` | ✅ 已发布 |
| 律师 | `lawyer/` | 🔜 计划中 |
| 教师 | `teacher/` | 🔜 计划中 |
| 保险代理 | `insurance/` | 🔜 计划中 |

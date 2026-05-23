<p align="center">
  <img src="assets/banner.png" alt="Nermes Agent" width="100%">
</p>

# Nermes Agent 🐂

<p align="center">
  <a href="https://nermes.nousresearch.com/docs/"><img src="https://img.shields.io/badge/文档-nermes.nousresearch.com-FFD700?style=for-the-badge" alt="文档"></a>
  <a href="https://github.com/nousresearch/nermes-core/blob/main/LICENSE"><img src="https://img.shields.io/badge/许可证-MIT-green?style=for-the-badge" alt="许可证: MIT"></a>
  <a href="https://nousresearch.com"><img src="https://img.shields.io/badge/基于-Hermes%20Agent-blueviolet?style=for-the-badge" alt="基于 Hermes Agent"></a>
</p>

**面向中国专业人士的自进化 AI 工作助手。** 基于 Nous Research 的 Hermes Agent，专为中国市场深度定制：全中文交互、DeepSeek 原生支持、国内镜像加速、行业专属技能包。它不是通用聊天机器人——它会记住你的习惯，从每次任务中学习，越用越懂你。

## 什么是「自进化」？

Nermes 是唯一一个内置闭环学习系统的 AI 助手：

- **技能自生成** — 完成复杂任务后，自动创建可复用的技能模块
- **技能自优化** — 每次使用技能时自动修正错误、补充遗漏步骤
- **记忆自整理** — 自动提示保存重要信息，定期回顾优化知识库
- **跨会话回忆** — 搜索所有历史对话，不用重复解释
- **用户画像深化** — 随着使用逐步建立对你的深度理解

在第一版中，我们为**财务专业人士**提供了完整的职业套件（18 个专属技能 + 专业人格 + 知识库）。

## 安装

### Linux / macOS / WSL2

```bash
curl -fsSL https://raw.githubusercontent.com/nousresearch/nermes-core/main/scripts/install.sh | bash
```

安装脚本会自动处理一切：Python、依赖、配置。安装完成后会询问是否安装职业预设包。

### 启动

```bash
source ~/.bashrc    # 刷新 shell
nermes              # 开始对话！
```

## 快速上手

```bash
nermes              # 交互式对话
nermes model        # 选择模型（推荐 DeepSeek）
nermes tools        # 配置工具
nermes gateway      # 启动消息网关（微信/企微/钉钉/飞书等）
nermes setup        # 运行完整配置向导
nermes doctor       # 系统诊断
```

📖 **[完整文档 →](https://nermes.nousresearch.com/docs/)**

## 平台支持

Nermes 支持全部主流中国即时通讯平台：

| 平台 | 状态 |
|------|------|
| 微信（个人号） | ✅ 支持 |
| 企业微信 | ✅ 支持 |
| 钉钉 | ✅ 支持 |
| 飞书 | ✅ 支持 |
| QQ 机器人 | ✅ 支持 |
| Telegram / Discord / Slack | ✅ 支持 |

## 财务版包含

### 18 个专属技能

**核算类（6 个）**：凭证录入、银行对账、折旧计算、存货核算、预提待摊、合并报表

**税务类（6 个）**：增值税计算、所得税计提、纳税申报、发票管理、税收优惠匹配、税务风险扫描

**报表类（6 个）**：资产负债表、利润表、现金流量表、财务比率、预算差异、管理报表

### 专业知识库

- 中国企业会计准则（CAS）
- 最新税率与优惠政策
- 关键财务指标参考值
- 常用 ERP 操作指南

## 为什么选择 Nermes？

| 对比维度 | Nermes | 通用 AI |
|----------|--------|---------|
| 中文体验 | 全中文交互，专业术语准确 | 翻译腔，术语常出错 |
| 国内适配 | 微信/企微/钉钉/飞书原生支持 | 需要自行配置 |
| 访问速度 | 国内镜像，DeepSeek 直连 | 需科学上网 |
| 专业深度 | 18个财务专属技能 + 知识库 | 通用知识，不够精准 |
| 自进化 | 越用越准，经验可积累 | 每次从零开始 |

## 许可

MIT — 详见 [LICENSE](LICENSE)。

基于 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 构建，由 [Nous Research](https://nousresearch.com) 提供技术支持。

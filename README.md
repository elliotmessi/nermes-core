<p align="center">
  <img src="assets/banner.png" alt="Nermes" width="100%">
</p>

# Nermes 🐂

<p align="center">
  <a href="https://github.com/elliotmessi/nermes-core/blob/main/README.zh-CN.md"><img src="https://img.shields.io/badge/文档-中文-red?style=for-the-badge" alt="中文文档"></a>
  <a href="https://github.com/elliotmessi/nermes-core/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://github.com/NousResearch/hermes-agent"><img src="https://img.shields.io/badge/Based%20on-Hermes%20Agent-blueviolet?style=for-the-badge" alt="Based on Hermes Agent"></a>
</p>

**A self-evolving AI work assistant built for Chinese professionals.** Forked from [Hermes Agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com) and deeply customized for the Chinese market: native Chinese interaction throughout, DeepSeek-first model support, domestic mirror acceleration, and profession-specific skill packs for finance, legal, and more.

> **Nermes = Hermes + 牛马 (niúmǎ)** — the workhorse that learns your craft and gets better every day.

## What Makes Nermes Different

Nermes is the only AI assistant with a **built-in closed learning loop**:

- **Self-generating skills** — after completing a complex task, Nermes automatically creates a reusable skill module
- **Self-improving skills** — every time a skill is used, Nermes patches errors and fills in missing steps
- **Self-curating memory** — proactively prompts you to save important information; periodically reviews and optimizes its knowledge base
- **Cross-session recall** — searches all your past conversations so you never have to repeat yourself
- **Deepening user model** — builds an increasingly nuanced understanding of who you are and how you work

**The first release ships with a complete profession suite for finance professionals** (18 specialized skills + professional persona + knowledge base).

## Why Choose Nermes Over General-Purpose AI?

| | Nermes | General AI |
|---|--------|------------|
| **Chinese experience** | Native Chinese throughout, accurate professional terminology | Translation artifacts, frequent terminology errors |
| **China platform support** | WeChat, WeCom, DingTalk, Feishu, QQ Bot — all native | Requires manual setup, often unsupported |
| **Access speed** | Domestic mirrors, DeepSeek direct connection | May require VPN |
| **Professional depth** | 18 finance-specific skills + knowledge base | General knowledge, lacks precision |
| **Self-evolution** | Gets better with use, experience accumulates | Starts from scratch every time |

## Quick Install

### Linux, macOS, WSL2

```bash
curl -fsSL https://raw.githubusercontent.com/elliotmessi/nermes-core/main/scripts/install.sh | bash
```

The installer handles everything: Python, dependencies, configuration. After installation, you'll be prompted to install the profession preset pack.

### Start

```bash
source ~/.bashrc    # reload shell
nermes              # start chatting!
```

## Getting Started

```bash
nermes              # Interactive CLI — start a conversation
nermes model        # Choose your LLM provider and model (DeepSeek recommended)
nermes tools        # Configure which tools are enabled
nermes gateway      # Start the messaging gateway (WeChat, WeCom, DingTalk, etc.)
nermes setup        # Run the full setup wizard
nermes doctor       # Diagnose any issues
```

## Platform Support

Nermes supports all major Chinese instant messaging platforms natively:

| Platform | Status |
|----------|--------|
| WeChat (Personal) | ✅ Supported |
| WeCom (企业微信) | ✅ Supported |
| DingTalk (钉钉) | ✅ Supported |
| Feishu (飞书) | ✅ Supported |
| QQ Bot | ✅ Supported |
| Telegram / Discord / Slack | ✅ Supported |

## Finance Edition Includes

### 18 Specialized Skills

**Accounting (6):** Voucher entry, bank reconciliation, depreciation calculation, inventory accounting, accruals & deferrals, consolidated statements

**Tax (6):** VAT calculation, income tax provision, tax filing, invoice management, tax incentive matching, tax risk scanning

**Reporting (6):** Balance sheet, income statement, cash flow statement, financial ratios, budget variance, management reports

### Professional Knowledge Base

- China Accounting Standards (CAS)
- Latest tax rates & preferential policies
- Key financial indicator reference values
- Common ERP operation guides

## Supported Models

Use any model you want — [DeepSeek](https://platform.deepseek.com), [OpenRouter](https://openrouter.ai) (200+ models), [NovitaAI](https://novita.ai), OpenAI, or your own endpoint. Switch with `nermes model` — no code changes, no lock-in.

## Features

| Feature | Description |
|---------|-------------|
| **Lives where you do** | WeChat, WeCom, DingTalk, Feishu, QQ, Telegram, Discord, Slack — all from a single gateway process. Cross-platform conversation continuity. |
| **A closed learning loop** | Agent-curated memory with periodic nudges. Autonomous skill creation after complex tasks. Skills self-improve during use. FTS5 session search with LLM summarization for cross-session recall. |
| **Scheduled automations** | Built-in cron scheduler with delivery to any platform. Daily reports, nightly backups, weekly audits — all in natural language, running unattended. |
| **Delegates and parallelizes** | Spawn isolated subagents for parallel workstreams. Write Python scripts that call tools via RPC, collapsing multi-step pipelines into zero-context-cost turns. |
| **Runs anywhere** | Seven terminal backends — local, Docker, SSH, Singularity, Modal, Daytona, and Vercel Sandbox. Run on a $5 VPS or a GPU cluster. |

## License

MIT — see [LICENSE](LICENSE).

**Modified from [Hermes Agent](https://github.com/NousResearch/hermes-agent)** by [Nous Research](https://nousresearch.com). Nermes is an independent fork customized for the Chinese market. Original copyright remains with Nous Research; modifications copyright Nermes contributors.

---

Built with ❤️ for Chinese professionals. Based on [Hermes Agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com).

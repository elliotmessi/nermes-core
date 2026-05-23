# 5 分钟快速上手

本指南将带你从零开始，在 5 分钟内完成 Nermes 的安装、配置，并完成你的第一笔记账。

---

## 第一步：安装 Nermes

打开终端，执行以下命令：

```bash
pip install nermes-core
```

安装完成后，验证版本：

```bash
nermes --version
```

> **提示**：如果 `pip` 命令找不到，请尝试 `pip3 install nermes-core`。

---

## 第二步：配置 API Key

Nermes 需要调用大语言模型来实现对话和任务处理。你需要准备一个 API Key。

### 支持的模型提供商

| 提供商 | 获取方式 |
|--------|---------|
| OpenAI | https://platform.openai.com/api-keys |
| Anthropic | https://console.anthropic.com/ |
| DeepSeek | https://platform.deepseek.com/ |
| 本地模型 | 通过 Ollama / vLLM 自行部署 |

### 配置方法

运行初始化向导：

```bash
nermes init
```

向导会询问以下信息：

1. **选择模型提供商** — 用方向键选择（推荐 OpenAI 或 DeepSeek）
2. **输入 API Key** — 粘贴你的密钥（输入时不会显示）
3. **选择默认模型** — 通常选择列表中的第一个即可
4. **设定语言** — 选择 `中文`

配置完成后，向导会提示"配置成功！"。

### 手动配置（可选）

如果你更倾向于直接编辑配置文件：

```bash
nermes config
```

这会打开 `~/.nermes/config.yaml`，你可以在其中手动填入：

```yaml
provider: openai
model: gpt-4o
api_key: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
language: zh-CN
```

> ⚠️ **安全提示**：务必保管好你的 API Key。建议将 Key 放在 `~/.nermes/.env` 文件中而非 `config.yaml`，Nermes 会自动读取。

---

## 第三步：启动 Nermes

```bash
nermes
```

看到如下界面表示启动成功：

```
✨ Nermes v1.0.0 已就绪
输入你的问题，或输入 /help 查看命令列表
>>
```

---

## 第四步：完成第一笔记账

Nermes 内置了记账功能。在对话界面中，直接输入自然语言即可：

```
>> 帮我记一笔账：早餐花了 15 元
```

Nermes 会自动解析并记录：

```
✅ 已记录：早餐 — 15.00 元
   类别：餐饮
   时间：2026-05-23 09:58
   账户：默认账户
```

再记几笔试试：

```
>> 打车花了 32 元
>> 给朋友发红包 200 元
>> 买了一杯咖啡 28 元
```

### 查询账单

```
>> 今天花了多少钱？
```

输出示例：

```
📊 今日消费汇总
━━━━━━━━━━━━━━━━━━━
餐饮     │  43.00 元
交通     │  32.00 元
社交      │ 200.00 元
━━━━━━━━━━━━━━━━━━━
合计     │ 275.00 元
```

### 更多记账技巧

| 你想做什么 | 试试这样说 |
|-----------|-----------|
| 记一笔收入 | "今天发了工资 10000 元" |
| 修改账单 | "把早餐的 15 元改成 20 元" |
| 删除账单 | "删掉刚才那笔打车记录" |
| 查上周账单 | "上周花了多少钱？" |
| 分类统计 | "这个月餐饮花了多少？" |

---

## 第五步：探索更多功能

记账只是 Nermes 的众多功能之一。试试这些命令：

### 基础功能

```
>> 今天天气怎么样？
>> 帮我查一下美元汇率
>> 设置明天早上 8 点的闹钟
>> 创建一个待办：周五前提交报告
```

### 使用命令模式

输入 `/` 查看所有可用命令：

```
/help      — 查看帮助
/plugins   — 管理插件
/config    — 查看当前配置
/memory    — 查看记忆管理
/logs      — 查看运行日志
/clear     — 清除对话历史
/exit      — 退出程序
```

### 安装更多插件

```
>> 帮我安装一个汇率查询插件
>> 搜索一下有没有便签插件
```

---

## 下一步

🎉 恭喜！你已经完成了所有基本操作。接下来可以：

- 阅读 [FAQ](faq.md) 解决常见疑问
- 将 Nermes 绑定到你的 [微信](https://docs.nermes.dev/wechat-bind)
- 了解如何 [自定义插件](https://docs.nermes.dev/plugin-dev)
- 加入 [社区讨论](https://discord.gg/nermes) 获取帮助

---

## 常见问题速查

| 问题 | 解决方案 |
|------|---------|
| `pip install` 失败 | 检查 Python ≥ 3.10，尝试 `pip install --upgrade pip` |
| 启动后没反应 | 检查 API Key 是否正确配置 |
| 记账没有反应 | 确认已启用记账插件：`/plugins list` |
| 忘记 API Key | 运行 `nermes config` 重新设置 |
| 想切换模型 | 运行 `nermes init` 重新选择提供商 |

> 更多问题请参考 [FAQ 文档](faq.md)。

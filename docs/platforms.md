# Nermes 平台适配状态

## 中国即时通讯平台

| 平台 | 适配器 | 行数 | 状态 | 说明 |
|------|--------|------|------|------|
| 微信（个人号） | `gateway/platforms/weixin.py` | 2,169 | ✅ 已完成 | 扫码登录，支持群聊/DM |
| 企业微信 | `gateway/platforms/wecom.py` | 1,610 | ✅ 已完成 | 企业应用接入 |
| 钉钉 | `gateway/platforms/dingtalk.py` | 1,490 | ✅ 已完成 | 机器人+Webhook |
| 飞书 | `gateway/platforms/feishu.py` | 5,058 | ✅ 已完成 | 应用+机器人双模式 |
| QQ 机器人 | — | — | 🔜 计划中 | 待开发 |

## 国际化平台（自带）

| 平台 | 状态 |
|------|------|
| Telegram | ✅ |
| Discord | ✅ |
| Slack | ✅ |
| WhatsApp | ✅ |
| Signal | ✅ |
| Matrix | ✅ |
| Email | ✅ |
| SMS | ✅ |

## 配置方式

所有平台通过 `nermes gateway setup` 配置：

```bash
nermes gateway setup weixin     # 微信
nermes gateway setup wecom      # 企业微信
nermes gateway setup dingtalk   # 钉钉
nermes gateway setup feishu     # 飞书
nermes gateway start            # 启动网关
```

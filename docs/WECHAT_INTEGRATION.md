# 微信公众号模板消息集成指南

## 一、功能概述

本系统支持通过**微信公众号模板消息**推送溢价提醒到用户的微信，与 Web PWA 主动查询配合使用：

- **Web PWA**：主动查询，随时查看任意基金溢价率
- **微信推送**：被动提醒，当自选基金溢价触发阈值时自动推送

## 二、准备工作

### 1. 注册微信公众号

1. 访问 [微信公众平台](https://mp.weixin.qq.com/)
2. 点击"立即注册" → 选择"订阅号"
3. 用个人身份信息完成认证（个人可注册订阅号）

### 2. 获取配置信息

登录公众号后台，依次获取以下信息：

| 配置项 | 获取路径 | 说明 |
|--------|---------|------|
| AppID | 开发 → 基本配置 | 公众号的唯一标识 |
| AppSecret | 开发 → 基本配置 | 点击"重置"生成 |
| Token | 开发 → 基本配置 | 自定义字符串，用于验证回调 |
| EncodingAESKey | 开发 → 基本配置 | 点击"生成"获得 |

### 3. 申请模板消息

**⚠️ 重要限制：个人订阅号可用的模板类别有限，金融/投资类模板可能无法申请。**

1. 登录公众号后台 → **功能** → **模板消息**
2. 点击"模板库"，搜索可用模板
3. 个人订阅号可申请的模板类别包括：
   - ✅ 通用通知类（如"您的{thing1}已{thing2}"）
   - ✅ 服务通知类（如"您的{thing1}将于{time1}到期"）
   - ❌ 金融/投资类（通常需要服务号）

**推荐方案**：先申请一个**通用通知模板**用于测试，模板内容示例：
```
您的{thing1}已{thing2}，{thing3}
```

申请后，在"我的模板"中获取 **模板ID**（形如 `xxxxxxxxxxxxxxxxxxxxxxxx`）

### 4. 配置回调域名

1. 公众号后台 → **开发** → **基本配置**
2. 找到"JS安全域名"，填写你的后端域名（不带 http://）
   - 本地测试：`localhost`
   - 线上部署：`your-domain.com`

## 三、配置环境变量

在 `backend/.env` 文件中添加以下配置：

```bash
# 微信公众号配置
WECHAT_APP_ID=wx1234567890abcdef
WECHAT_APP_SECRET=1234567890abcdef1234567890abcdef12345678
WECHAT_TOKEN=your_custom_token_string
WECHAT_ENCODING_AES_KEY=abcdefghijklmnopqrstuvwxyz123456

# 模板消息模板ID（从公众号后台获取）
WECHAT_TEMPLATE_ID=xxxxxxxxxxxxxxxxxxxxxxxx

# JS安全域名（不带http://）
WECHAT_CALLBACK_URL=your-domain.com

# 是否使用客服消息替代模板消息（48小时内有效）
WECHAT_USE_CUSTOMER_SERVICE=false
```

## 四、API 接口说明

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/wechat/oauth/authorize` | GET | 引导用户跳转到微信 OAuth 授权页面 |
| `/api/v1/wechat/oauth/callback` | GET | 微信 OAuth 回调处理，换取 openid |
| `/api/v1/wechat/subscribe` | POST | 用户订阅溢价提醒 |
| `/api/v1/wechat/send-test` | POST | 发送测试模板消息 |
| `/api/v1/wechat/callback` | GET | 微信服务器回调验证 |

## 五、用户使用流程

### 1. 绑定公众号

1. 用户打开 Web PWA 页面
2. 进入"提醒"页面
3. 点击"绑定公众号"按钮
4. 自动跳转到微信授权页面（需用户在微信内打开）
5. 授权后，openid 自动保存

### 2. 添加提醒规则

1. 在"提醒"页面点击"+ 添加提醒规则"
2. 搜索并选择基金
3. 设置溢价/折价阈值
4. 保存

### 3. 接收推送

当基金溢价率触发阈值时：
1. 后端检测到阈值触发
2. 调用微信模板消息 API
3. 用户微信收到推送消息
4. 点击消息可跳转到基金详情页

## 六、注意事项

### ⚠️ 个人订阅号限制

| 限制项 | 说明 | 解决方案 |
|--------|------|---------|
| 金融模板不可用 | 个人订阅号无法申请金融/投资类模板 | 使用通用通知模板替代 |
| 只能发给关注用户 | 模板消息只能发送给已关注公众号的用户 | 引导用户关注公众号 |
| 模板数量限制 | 个人订阅号模板数量有限 | 优先使用通用模板 |

### ⚠️ 使用场景限制

1. **必须在微信内打开网页**：OAuth 授权需要在微信内置浏览器中完成
2. **用户需关注公众号**：否则无法接收模板消息
3. **模板内容受限**：无法使用专业金融术语，只能用通用模板

### ⚠️ 备用方案

如果个人订阅号无法申请到合适的模板，可以考虑：

1. **企业微信机器人**（推荐）：推送到企业微信群，正常微信用户也能收到
2. **客服消息**：用户互动后 48 小时内可发送，不需要模板 ID
3. **邮件推送**：用 Resend + Cloudflare Workers 实现邮件通知

## 七、测试方法

### 1. 测试 OAuth 授权

```bash
# 在微信内打开以下 URL
http://localhost:8000/api/v1/wechat/oauth/authorize
```

授权成功后，会跳转到首页并保存 openid。

### 2. 测试模板消息发送

```bash
# 先获取 openid（通过 OAuth 授权）
# 然后调用测试接口
curl -X POST "http://localhost:8000/api/v1/wechat/send-test?openid=USER_OPENID_HERE"
```

### 3. 测试提醒触发

1. 添加一个提醒规则
2. 等待溢价率更新（或手动触发 `check_all_alerts()`）
3. 检查微信是否收到推送消息

## 八、代码结构

```
backend/
  wechat_config.py          # 微信配置
  api/
    wechat.py               # 微信 API 路由（OAuth、模板消息、回调）
  services/
    alert_engine.py         # 提醒引擎（已集成微信推送）

web/
  src/
    views/
      Alerts.vue            # 提醒页面（已集成微信绑定 UI）
```

"""微信公众配置"""
import os
from dotenv import load_dotenv

load_dotenv()

# 微信公众号配置
WECHAT_APP_ID = os.getenv("WECHAT_APP_ID", "")
WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET", "")
WECHAT_TOKEN = os.getenv("WECHAT_TOKEN", "")
WECHAT_ENCODING_AES_KEY = os.getenv("WECHAT_ENCODING_AES_KEY", "")

# 模板消息配置
# 注意：个人订阅号可用的模板类别有限，金融类模板可能无法申请
# 建议先在公众号后台 -> 功能 -> 模板消息 -> 模板库中搜索可用的模板
WECHAT_TEMPLATE_ID = os.getenv("WECHAT_TEMPLATE_ID", "")  # 模板ID

# 订阅通知配置（替代方案，需要用户主动订阅）
WECHAT_SUBSCRIBE_TEMPLATE_ID = os.getenv("WECHAT_SUBSCRIBE_TEMPLATE_ID", "")

# 客服消息配置（48小时内有效）
# 客服消息不需要模板ID，但只能在用户最后一次互动后48小时内发送
WECHAT_USE_CUSTOMER_SERVICE = os.getenv("WECHAT_USE_CUSTOMER_SERVICE", "false").lower() == "true"

# 回调配置
WECHAT_CALLBACK_URL = os.getenv("WECHAT_CALLBACK_URL", "")  # 公众号后台配置的JS安全域名

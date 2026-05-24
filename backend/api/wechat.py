"""微信公众号模板消息服务"""
import os
import json
import hashlib
import time
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

import wechat_config as config

# 临时存储用户 openid（生产环境应存入数据库）
_user_openids: dict[str, dict] = {}  # {code: {openid, expires_at}}

# 模板消息数据格式参考：
# 个人订阅号可申请的模板类别有限，建议先在公众号后台搜索可用模板
# 常见可用模板示例：
# - "您的{thing1}已{thing2}" 通用通知模板
# - "金额：{money1} 时间：{time1}" 金融类模板（需服务号）

# 模板参数定义（根据实际申请的模板ID调整）
TEMPLATE_DATA = {
    # 模板1：通用通知类（个人订阅号较容易申请到）
    # 模板内容示例：您的{thing1}已{thing2}，{thing3}
    "generic": {
        "thing1": {"value": ""},
        "thing2": {"value": ""},
        "thing3": {"value": ""},
    },
    # 模板2：基金溢价提醒（需要金融类模板，个人订阅号可能无法申请）
    # 模板内容示例：基金{fund_name}溢价率{premium_rate}，{remark}
    "fund_premium": {
        "fund_name": {"value": ""},
        "fund_code": {"value": ""},
        "premium_rate": {"value": ""},
        "market_price": {"value": ""},
        "nav": {"value": ""},
        "remark": {"value": ""},
    }
}


async def get_access_token() -> str:
    """获取公众号 access_token"""
    if not config.WECHAT_APP_ID or not config.WECHAT_APP_SECRET:
        raise ValueError("WECHAT_APP_ID 或 WECHAT_APP_SECRET 未配置")

    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": config.WECHAT_APP_ID,
        "secret": config.WECHAT_APP_SECRET,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=10)
        data = resp.json()

    if "access_token" not in data:
        raise HTTPException(status_code=500, detail=f"获取access_token失败: {data}")

    return data["access_token"]


async def send_template_message(
    openid: str,
    template_id: str,
    data: dict,
    url: str = "",
    miniprogram_appid: str = "",
    miniprogram_pagepath: str = "",
) -> dict:
    """
    发送模板消息

    Args:
        openid: 用户openid
        template_id: 模板ID（在公众号后台->模板消息->模板库中获取）
        data: 模板数据，格式如 {"thing1": {"value": "基金"}, ...}
        url: 点击消息跳转的URL
        miniprogram_appid: 跳转小程序的appid（可选）
        miniprogram_pagepath: 跳转小程序的页面路径（可选）

    Returns:
        {"errcode": 0, "errmsg": "ok"} 表示成功
    """
    access_token = await get_access_token()

    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"

    payload = {
        "touser": openid,
        "template_id": template_id,
        "url": url,
        "miniprogram": {
            "appid": miniprogram_appid,
            "pagepath": miniprogram_pagepath,
        } if miniprogram_appid else None,
        "data": data,
    }

    # 移除None值
    payload = {k: v for k, v in payload.items() if v is not None}

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, timeout=10)
        result = resp.json()

    if result.get("errcode") != 0:
        raise HTTPException(status_code=500, detail=f"发送模板消息失败: errcode={result.get('errcode')}, errmsg={result.get('errmsg')}")

    return result


async def send_premium_alert(openid: str, fund_code: str, fund_name: str, premium_rate: float, threshold_type: str) -> bool:
    """
    发送溢价提醒模板消息

    Args:
        openid: 用户openid
        fund_code: 基金代码
        fund_name: 基金名称
        premium_rate: 溢价率
        threshold_type: 触发类型 (above/below)

    Returns:
        是否发送成功
    """
    if not config.WECHAT_TEMPLATE_ID:
        print(f"[WARN] WECHAT_TEMPLATE_ID 未配置，跳过模板消息发送")
        return False

    # 构建模板数据（根据实际模板ID调整字段）
    # 这里使用通用模板格式，实际需要根据申请的模板ID调整
    threshold_label = "溢价" if threshold_type == "above" else "折价"
    sign = "+" if threshold_type == "above" else ""

    data = {
        "thing1": {"value": fund_name},
        "thing2": {"value": f"{threshold_label}提醒"},
        "thing3": {"value": f"当前{threshold_label}率{sign}{premium_rate}%，请及时关注"},
    }

    # 构建跳转URL（指向你的Web PWA详情页）
    # 注意：需要先在公众号后台配置JS安全域名
    callback_url = config.WECHAT_CALLBACK_URL or ""
    if callback_url:
        jump_url = f"{callback_url}/detail/{fund_code}"
    else:
        jump_url = ""

    try:
        result = await send_template_message(
            openid=openid,
            template_id=config.WECHAT_TEMPLATE_ID,
            data=data,
            url=jump_url,
        )
        print(f"[OK] 模板消息发送成功: {fund_code} 溢价率{premium_rate}%")
        return True
    except Exception as e:
        print(f"[ERROR] 模板消息发送失败: {e}")
        return False


def verify_signature(token: str, timestamp: str, nonce: str, signature: str) -> bool:
    """验证微信服务器签名"""
    if not token:
        return False

    # 将token、timestamp、nonce三个参数进行字典序排序
    tmp_list = sorted([token, timestamp, nonce])
    # 拼接成字符串
    tmp_str = "".join(tmp_list)
    # SHA1加密
    sha1 = hashlib.sha1()
    sha1.update(tmp_str.encode("utf-8"))
    digest = sha1.hexdigest()

    return digest == signature


async def handle_wechat_callback(request: Request):
    """处理微信服务器回调（验证URL和接收事件推送）"""
    signature = request.query_params.get("signature", "")
    timestamp = request.query_params.get("timestamp", "")
    nonce = request.query_params.get("nonce", "")
    echostr = request.query_params.get("echostr", None)

    # 验证签名
    if not verify_signature(config.WECHAT_TOKEN, timestamp, nonce, signature):
        raise HTTPException(status_code=400, detail="签名验证失败")

    # URL验证：微信会发送GET请求，返回echostr
    if echostr is not None:
        return HTMLResponse(content=echostr)

    # 事件推送：微信会发送POST请求（XML格式）
    # 这里简化处理，实际需要根据事件类型做不同处理
    body = await request.body()
    # TODO: 解析XML，处理订阅/取消订阅等事件

    return JSONResponse(content={"status": "ok"})


# ========== API 路由 ==========

router = APIRouter(prefix="/api/v1/wechat", tags=["wechat"])


@router.get("/oauth/authorize")
async def oauth_authorize():
    """
    引导用户跳转到微信OAuth授权页面

    用户访问此接口后，会被重定向到微信授权页面
    授权后，微信会回调 /api/v1/wechat/oauth/callback
    """
    if not config.WECHAT_APP_ID:
        raise HTTPException(status_code=500, detail="WECHAT_APP_ID 未配置")

    # 生成随机state（防止CSRF攻击）
    state = hashlib.md5(str(time.time()).encode()).hexdigest()[:16]

    # 保存state到临时存储（生产环境应存入Redis/数据库）
    redirect_uri = urllib.parse.quote(
        f"{config.WECHAT_CALLBACK_URL or 'http://localhost:8000'}/api/v1/wechat/oauth/callback"
    )

    auth_url = (
        f"https://open.weixin.qq.com/connect/oauth2/authorize"
        f"?appid={config.WECHAT_APP_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=snsapi_base"  # snsapi_base: 静默获取openid；snsapi_userinfo: 需要用户授权
        f"&state={state}#wechat_redirect"
    )

    # 返回HTML页面，自动跳转到微信授权
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>微信授权</title>
        <script>
            window.location.href = '{auth_url}';
        </script>
    </head>
    <body>
        <p>正在跳转到微信授权页面...</p>
        <p>如果未自动跳转，请<a href="{auth_url}">点击这里</a></p>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/oauth/callback")
async def oauth_callback(code: str = Query(""), state: str = Query("")):
    """
    微信OAuth回调处理

    用户授权后，微信会重定向到此页面，携带code参数
    用code换取openid，然后重定向到前端页面
    """
    if not code:
        return JSONResponse(status_code=400, content={"error": "缺少code参数"})

    if not config.WECHAT_APP_ID or not config.WECHAT_APP_SECRET:
        return JSONResponse(status_code=500, content={"error": "微信配置未完善"})

    # 用code换取access_token和openid
    url = "https://api.weixin.qq.com/sns/oauth2/access_token"
    params = {
        "appid": config.WECHAT_APP_ID,
        "secret": config.WECHAT_APP_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=10)
        data = resp.json()

    if "openid" not in data:
        return JSONResponse(status_code=500, content={"error": f"换取openid失败: {data}"})

    openid = data["openid"]
    access_token = data.get("access_token", "")
    expires_in = data.get("expires_in", 7200)

    # 保存用户openid（生产环境应存入数据库，关联用户账号）
    _user_openids[openid] = {
        "access_token": access_token,
        "expires_at": time.time() + expires_in,
        "authorized_at": datetime.now().isoformat(),
    }

    # 重定向到前端页面，携带openid（前端可用openid来订阅提醒）
    # 注意：实际生产环境应将openid存入后端数据库，前端通过session/token关联
    redirect_url = f"/?wechat_openid={openid}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>授权成功</title>
        <script>
            // 将openid写入localStorage，并跳转到首页
            localStorage.setItem('wechat_openid', '{openid}');
            window.location.href = '{redirect_url}';
        </script>
    </head>
    <body>
        <p>授权成功！正在跳转...</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/user/openid")
async def get_user_openid():
    """获取当前用户的openid（从localStorage读取并验证）"""
    # 此接口需要前端先调用 /api/v1/wechat/oauth/authorize 完成授权
    # 实际生产环境应通过JWT/session验证用户身份
    return JSONResponse(content={
        "message": "请先访问 /api/v1/wechat/oauth/authorize 完成微信授权",
        "hint": "授权完成后，openid会存储在localStorage中",
    })


@router.post("/subscribe")
async def subscribe_alert(openid: str = Query(""), fund_code: str = Query(""), threshold_above: float = 5.0, threshold_below: float = -2.0):
    """
    用户订阅溢价提醒

    注意：此接口仅记录订阅关系，实际推送需要：
    1. 用户已完成微信授权（有openid）
    2. 用户已关注公众号
    3. 后端定时检测溢价率并调用模板消息API

    个人订阅号限制：
    - 模板消息只能发送给已关注公众号的用户
    - 模板类别有限，金融类模板可能无法申请
    - 建议先用通用通知模板测试
    """
    if not openid:
        return JSONResponse(status_code=400, content={"error": "缺少openid参数，请先完成微信授权"})

    if not fund_code:
        return JSONResponse(status_code=400, content={"error": "缺少fund_code参数"})

    # TODO: 将订阅关系存入数据库
    # 这里简化处理，实际应调用后端alerts API
    print(f"[INFO] 用户 {openid} 订阅了基金 {fund_code} 的溢价提醒 (>{threshold_above}%, <{threshold_below}%)")

    return JSONResponse(content={
        "success": True,
        "message": "订阅成功！当溢价率触发阈值时，会通过微信推送通知",
        "note": "请确保已关注公众号，否则无法收到模板消息",
    })


@router.post("/send-test")
async def send_test_message(openid: str = Query("")):
    """发送测试模板消息（用于调试）"""
    if not openid:
        return JSONResponse(status_code=400, content={"error": "缺少openid参数"})

    if not config.WECHAT_TEMPLATE_ID:
        return JSONResponse(status_code=500, content={
            "error": "WECHAT_TEMPLATE_ID 未配置",
            "hint": "请在公众号后台->模板消息->模板库中申请模板，并将ID填入环境变量",
        })

    # 测试数据
    test_data = {
        "thing1": {"value": "测试基金"},
        "thing2": {"value": "溢价提醒"},
        "thing3": {"value": "当前溢价率+5.23%，请及时关注"},
    }

    try:
        result = await send_template_message(
            openid=openid,
            template_id=config.WECHAT_TEMPLATE_ID,
            data=test_data,
            url=config.WECHAT_CALLBACK_URL or "",
        )
        return JSONResponse(content={
            "success": True,
            "message": "测试消息发送成功",
            "result": result,
        })
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={
            "success": False,
            "error": str(e.detail),
        })


@router.get("/callback")
async def wechat_callback_handler(request: Request):
    """微信服务器回调验证和事件接收"""
    return await handle_wechat_callback(request)

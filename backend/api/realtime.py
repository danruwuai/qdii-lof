"""WebSocket 实时推送端点"""
import asyncio
import json
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.premium_service import get_cached_premium, get_all_cached_premiums

router = APIRouter(tags=["realtime"])

# 管理 WebSocket 连接和订阅关系
# {openid: WebSocket}
_connections: dict[str, WebSocket] = {}
# {openid: set(fund_codes)}
_subscriptions: dict[str, Set[str]] = {}


@router.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket, openid: str = "default_user"):
    await websocket.accept()
    _connections[openid] = websocket
    _subscriptions.setdefault(openid, set())

    try:
        while True:
            # 接收客户端消息（订阅请求 / 心跳）
            data = await websocket.receive_text()
            if data == "ping":
                # 心跳回复
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue
            try:
                msg = json.loads(data)
                if msg.get("type") == "subscribe":
                    codes = msg.get("fund_codes", [])
                    _subscriptions[openid] = set(codes)
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "fund_codes": codes,
                    }))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        _connections.pop(openid, None)
        _subscriptions.pop(openid, None)


async def broadcast_premium_update(fund_code: str, premium_data: dict):
    """向订阅该基金的客户端推送更新"""
    msg = json.dumps({
        "type": "premium_update",
        "data": {
            "code": fund_code,
            **premium_data,
        },
    })

    disconnected = []
    for openid, ws in _connections.items():
        subscribed_codes = _subscriptions.get(openid, set())
        if fund_code in subscribed_codes:
            try:
                await ws.send_text(msg)
            except Exception:
                disconnected.append(openid)

    for openid in disconnected:
        _connections.pop(openid, None)
        _subscriptions.pop(openid, None)


async def send_alert_notification(openid: str, alert_msg: dict):
    """向指定用户发送提醒通知"""
    ws = _connections.get(openid)
    if ws:
        try:
            await ws.send_text(json.dumps({
                "type": "alert_triggered",
                "data": alert_msg,
            }))
        except Exception:
            _connections.pop(openid, None)
            _subscriptions.pop(openid, None)

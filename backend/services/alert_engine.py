"""提醒引擎：阈值检测"""
from datetime import datetime

from database import SessionLocal
from models import UserAlert
from services.premium_service import get_cached_premium
from api.realtime import send_alert_notification


async def send_wechat_alert(openid: str, fund_code: str, fund_name: str, rate: float, threshold_type: str):
    """发送微信模板消息提醒（非阻塞，失败不影响主流程）"""
    try:
        from api.wechat import send_premium_alert
        await send_premium_alert(openid, fund_code, fund_name, rate, threshold_type)
    except Exception as e:
        print(f"[WARN] 微信推送失败: {e}")


async def check_all_alerts():
    """检测所有活跃提醒规则"""
    db = SessionLocal()
    try:
        alerts = db.query(UserAlert).filter(UserAlert.is_active == True).all()

        for alert in alerts:
            premium = get_cached_premium(alert.fund_code)
            if not premium or premium.get("premium_rate") is None:
                continue

            rate = premium["premium_rate"]
            should_trigger = False
            trigger_type = ""  # above / below
            trigger_msg = ""

            if alert.threshold_above is not None and rate > alert.threshold_above:
                should_trigger = True
                trigger_type = "above"
                trigger_msg = f"{alert.fund_code} 溢价率 {rate:.2f}% 超过上限 {alert.threshold_above:.2f}%"

            if alert.threshold_below is not None and rate < alert.threshold_below:
                should_trigger = True
                trigger_type = "below"
                trigger_msg = f"{alert.fund_code} 溢价率 {rate:.2f}% 低于下限 {alert.threshold_below:.2f}%"

            if should_trigger:
                # 冷却：5 分钟内不重复触发
                now = datetime.now()
                if alert.last_triggered_at and (now - alert.last_triggered_at).seconds < 300:
                    continue

                alert.last_triggered_at = now
                db.commit()

                # 1. WebSocket 推送（实时连接的用户）
                await send_alert_notification(alert.user_openid, {
                    "fund_code": alert.fund_code,
                    "premium_rate": rate,
                    "message": trigger_msg,
                })

                # 2. 微信模板消息推送（异步，非阻塞）
                # 注意：需要用户已完成微信授权并绑定 openid
                if alert.user_openid:
                    from models import Fund
                    fund = db.query(Fund).filter(Fund.code == alert.fund_code).first()
                    fund_name = fund.name if fund else alert.fund_code
                    await send_wechat_alert(
                        openid=alert.user_openid,
                        fund_code=alert.fund_code,
                        fund_name=fund_name,
                        rate=rate,
                        threshold_type=trigger_type,
                    )
    finally:
        db.close()

"""提醒规则 CRUD API"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import UserAlert
from schemas import AlertCreate, AlertUpdate, AlertResponse

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

DEFAULT_USER = "default_user"


@router.get("")
async def list_alerts(db: Session = Depends(get_db)):
    """获取用户提醒规则列表"""
    alerts = db.query(UserAlert).filter(UserAlert.user_openid == DEFAULT_USER).all()
    return {
        "items": [
            AlertResponse(
                id=a.id,
                fund_code=a.fund_code,
                threshold_above=a.threshold_above,
                threshold_below=a.threshold_below,
                is_active=a.is_active,
            )
            for a in alerts
        ]
    }


@router.post("")
async def create_alert(data: AlertCreate, db: Session = Depends(get_db)):
    """创建提醒规则"""
    alert = UserAlert(
        user_openid=DEFAULT_USER,
        fund_code=data.fund_code,
        threshold_above=data.threshold_above,
        threshold_below=data.threshold_below,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return {"id": alert.id, "success": True}


@router.put("/{alert_id}")
async def update_alert(alert_id: int, data: AlertUpdate, db: Session = Depends(get_db)):
    """更新提醒规则"""
    alert = db.query(UserAlert).filter(
        UserAlert.id == alert_id,
        UserAlert.user_openid == DEFAULT_USER,
    ).first()
    if not alert:
        return {"success": False, "message": "未找到"}

    if data.threshold_above is not None:
        alert.threshold_above = data.threshold_above
    if data.threshold_below is not None:
        alert.threshold_below = data.threshold_below
    if data.is_active is not None:
        alert.is_active = data.is_active

    db.commit()
    return {"success": True}


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """删除提醒规则"""
    alert = db.query(UserAlert).filter(
        UserAlert.id == alert_id,
        UserAlert.user_openid == DEFAULT_USER,
    ).first()
    if alert:
        db.delete(alert)
        db.commit()
        return {"success": True}
    return {"success": False, "message": "未找到"}

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Alarm, Device, User
from app.schemas import AlarmOut, AlarmResolve

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alarms", tags=["告警中心"])


@router.get("", response_model=list[AlarmOut])
def list_alarms(
    status: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AlarmOut]:
    query = db.query(Alarm, Device.name).join(Device, Alarm.device_id == Device.id)
    if status:
        query = query.filter(Alarm.status == status)

    rows = query.order_by(Alarm.created_at.desc()).all()
    return [
        AlarmOut(
            id=alarm.id,
            device_id=alarm.device_id,
            device_name=device_name,
            level=alarm.level,
            title=alarm.title,
            content=alarm.content,
            status=alarm.status,
            created_at=alarm.created_at,
            resolved_at=alarm.resolved_at,
        )
        for alarm, device_name in rows
    ]


@router.patch("/{alarm_id}", response_model=AlarmOut)
def resolve_alarm(
    alarm_id: int,
    payload: AlarmResolve,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AlarmOut:
    alarm = db.query(Alarm).filter(Alarm.id == alarm_id).first()
    if alarm is None:
        raise HTTPException(status_code=404, detail="告警不存在")

    alarm.status = payload.status
    alarm.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(alarm)

    device_name = db.query(Device.name).filter(Device.id == alarm.device_id).scalar() or "未知设备"
    logger.info("告警已处理，alarm_id=%s", alarm_id)

    return AlarmOut(
        id=alarm.id,
        device_id=alarm.device_id,
        device_name=device_name,
        level=alarm.level,
        title=alarm.title,
        content=alarm.content,
        status=alarm.status,
        created_at=alarm.created_at,
        resolved_at=alarm.resolved_at,
    )

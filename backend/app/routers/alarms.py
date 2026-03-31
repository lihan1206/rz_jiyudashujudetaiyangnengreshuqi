import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Alarm, Device, User
from app.schemas import AlarmOut, AlarmResolve

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alarms", tags=["告警中心"])


def _get_alarm_by_id(db: Session, alarm_id: int) -> Optional[Alarm]:
    """
    根据ID获取告警
    :param db: 数据库会话
    :param alarm_id: 告警ID
    :return: 告警对象或None
    """
    return db.query(Alarm).filter(Alarm.id == alarm_id).first()


def _get_device_name_by_id(db: Session, device_id: int) -> str:
    """
    根据设备ID获取设备名称
    :param db: 数据库会话
    :param device_id: 设备ID
    :return: 设备名称，默认返回"未知设备"
    """
    device_name = db.query(Device.name).filter(Device.id == device_id).scalar()
    return device_name or "未知设备"


def _build_alarm_response(alarm: Alarm, device_name: str) -> AlarmOut:
    """
    构建告警响应对象
    :param alarm: 告警对象
    :param device_name: 设备名称
    :return: 告警响应对象
    """
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


@router.get("", response_model=list[AlarmOut])
def list_alarms(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AlarmOut]:
    """
    获取告警列表
    :param status_filter: 可选，按状态过滤
    :param db: 数据库会话
    :param _: 当前用户
    :return: 告警列表
    :raises HTTPException: 如果查询失败
    """
    # 验证状态参数
    valid_statuses = {"unresolved", "resolved"}
    if status_filter is not None and status_filter not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的状态参数，有效值为: {', '.join(valid_statuses)}",
        )

    try:
        query = db.query(Alarm, Device.name).join(Device, Alarm.device_id == Device.id)

        if status_filter:
            query = query.filter(Alarm.status == status_filter)

        rows = query.order_by(Alarm.created_at.desc()).all()

        return [
            _build_alarm_response(alarm, device_name) for alarm, device_name in rows
        ]

    except SQLAlchemyError as e:
        logger.error("查询告警列表失败，error=%s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="查询告警列表失败，请稍后重试",
        ) from e


@router.patch("/{alarm_id}", response_model=AlarmOut)
def resolve_alarm(
    alarm_id: int,
    payload: AlarmResolve,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AlarmOut:
    """
    处理告警，标记为已解决
    :param alarm_id: 告警ID
    :param payload: 告警处理请求
    :param db: 数据库会话
    :param _: 当前用户
    :return: 处理后的告警响应
    :raises HTTPException: 如果告警不存在或处理失败
    """
    # 参数验证
    if alarm_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的告警ID，必须大于0",
        )

    if payload.status != "resolved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持标记为 resolved 状态",
        )

    try:
        # 查询告警
        alarm = _get_alarm_by_id(db, alarm_id)
        if alarm is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"告警不存在，alarm_id: {alarm_id}",
            )

        # 检查是否已经处理
        if alarm.status == "resolved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该告警已经被处理",
            )

        # 更新告警状态
        alarm.status = payload.status
        alarm.resolved_at = datetime.utcnow()
        db.commit()
        db.refresh(alarm)

        # 获取设备名称
        device_name = _get_device_name_by_id(db, alarm.device_id)

        logger.info(
            "告警已处理，alarm_id=%s, device_id=%s, device_name=%s",
            alarm_id,
            alarm.device_id,
            device_name,
        )

        return _build_alarm_response(alarm, device_name)

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError as e:
        db.rollback()
        logger.error("处理告警失败，alarm_id=%s, error=%s", alarm_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="处理告警失败，请稍后重试",
        ) from e

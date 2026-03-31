import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Alarm, Device, HealthAssessment, SensorData, User
from app.schemas import DashboardSummary, DashboardTrendItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["监控大屏"])

# 常量定义
DEFAULT_TREND_LIMIT: int = 24
MIN_TREND_LIMIT: int = 6
MAX_TREND_LIMIT: int = 120


def _get_total_devices_count(db: Session) -> int:
    """获取总设备数量"""
    count = db.query(func.count(Device.id)).scalar()
    return count or 0


def _get_active_devices_count(db: Session) -> int:
    """获取活跃设备数量"""
    count = db.query(func.count(Device.id)).filter(Device.status == "active").scalar()
    return count or 0


def _get_high_risk_devices_count(db: Session) -> int:
    """获取高风险设备数量"""
    try:
        # 获取每个设备最新的评估时间
        latest_assessment_subquery = (
            db.query(
                HealthAssessment.device_id,
                func.max(HealthAssessment.assessment_time).label("latest_time"),
            )
            .group_by(HealthAssessment.device_id)
            .subquery()
        )

        # 统计高风险设备数量
        count = (
            db.query(func.count(HealthAssessment.id))
            .join(
                latest_assessment_subquery,
                (HealthAssessment.device_id == latest_assessment_subquery.c.device_id)
                & (HealthAssessment.assessment_time == latest_assessment_subquery.c.latest_time),
            )
            .filter(HealthAssessment.risk_level == "high")
            .scalar()
        )
        return count or 0
    except SQLAlchemyError as e:
        logger.error("统计高风险设备失败，error=%s", str(e))
        return 0


def _get_unresolved_alarms_count(db: Session) -> int:
    """获取未处理告警数量"""
    count = db.query(func.count(Alarm.id)).filter(Alarm.status == "unresolved").scalar()
    return count or 0


def _get_avg_health_score(db: Session) -> float:
    """获取平均健康评分"""
    avg_score = db.query(func.avg(HealthAssessment.health_score)).scalar()
    return round(float(avg_score or 0), 2)


def _get_device_trend_data(
    db: Session, device_id: int, limit: int
) -> list[tuple[SensorData, Optional[HealthAssessment]]]:
    """获取设备趋势数据"""
    return (
        db.query(SensorData, HealthAssessment)
        .join(
            HealthAssessment,
            (SensorData.device_id == HealthAssessment.device_id)
            & (
                func.date_format(SensorData.collected_at, "%Y-%m-%d %H:%i")
                == func.date_format(HealthAssessment.assessment_time, "%Y-%m-%d %H:%i")
            ),
            isouter=True,
        )
        .filter(SensorData.device_id == device_id)
        .order_by(SensorData.collected_at.desc())
        .limit(limit)
        .all()
    )


def _build_trend_item(
    sensor_data: SensorData, assessment: Optional[HealthAssessment]
) -> DashboardTrendItem:
    """构建趋势数据项"""
    return DashboardTrendItem(
        collected_at=sensor_data.collected_at,
        temperature_out=sensor_data.temperature_out,
        pressure=sensor_data.pressure,
        flow_rate=sensor_data.flow_rate,
        health_score=assessment.health_score if assessment else 0,
    )


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DashboardSummary:
    """
    获取监控大屏汇总数据
    :param db: 数据库会话
    :param _: 当前用户
    :return: 监控汇总数据
    :raises HTTPException: 如果查询失败
    """
    try:
        total_devices = _get_total_devices_count(db)
        active_devices = _get_active_devices_count(db)
        high_risk_devices = _get_high_risk_devices_count(db)
        unresolved_alarms = _get_unresolved_alarms_count(db)
        avg_health_score = _get_avg_health_score(db)

        return DashboardSummary(
            total_devices=total_devices,
            active_devices=active_devices,
            high_risk_devices=high_risk_devices,
            unresolved_alarms=unresolved_alarms,
            avg_health_score=avg_health_score,
        )

    except SQLAlchemyError as e:
        logger.error("查询仪表盘汇总数据失败，error=%s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="查询汇总数据失败，请稍后重试",
        ) from e


@router.get("/trend/{device_id}", response_model=list[DashboardTrendItem])
def get_device_trend(
    device_id: int,
    limit: int = DEFAULT_TREND_LIMIT,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[DashboardTrendItem]:
    """
    获取设备趋势数据
    :param device_id: 设备ID
    :param limit: 数据点数量限制
    :param db: 数据库会话
    :param _: 当前用户
    :return: 设备趋势数据列表
    :raises HTTPException: 如果参数无效或查询失败
    """
    # 参数验证
    if device_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的设备ID，必须大于0",
        )

    # 限制数据点数量范围
    limit = min(max(limit, MIN_TREND_LIMIT), MAX_TREND_LIMIT)

    try:
        data_rows = _get_device_trend_data(db, device_id, limit)

        if not data_rows:
            logger.warning("设备暂无趋势数据，device_id=%s", device_id)
            return []

        # 构建响应并按时间升序排列
        trend_items = [
            _build_trend_item(sensor_data, assessment) for sensor_data, assessment in data_rows
        ]

        return list(reversed(trend_items))

    except SQLAlchemyError as e:
        logger.error("查询设备趋势数据失败，device_id=%s, error=%s", device_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="查询趋势数据失败，请稍后重试",
        ) from e

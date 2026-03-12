from sqlalchemy import func
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.db import get_db
from app.deps import get_current_user
from app.models import Alarm, Device, HealthAssessment, SensorData, User
from app.schemas import DashboardSummary, DashboardTrendItem

router = APIRouter(prefix="/dashboard", tags=["监控大屏"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DashboardSummary:
    total_devices = db.query(func.count(Device.id)).scalar() or 0
    active_devices = db.query(func.count(Device.id)).filter(Device.status == "active").scalar() or 0

    high_risk_subquery = (
        db.query(
            HealthAssessment.device_id,
            func.max(HealthAssessment.assessment_time).label("latest_time"),
        )
        .group_by(HealthAssessment.device_id)
        .subquery()
    )

    high_risk_devices = (
        db.query(func.count(HealthAssessment.id))
        .join(
            high_risk_subquery,
            (HealthAssessment.device_id == high_risk_subquery.c.device_id)
            & (HealthAssessment.assessment_time == high_risk_subquery.c.latest_time),
        )
        .filter(HealthAssessment.risk_level == "high")
        .scalar()
        or 0
    )

    unresolved_alarms = (
        db.query(func.count(Alarm.id)).filter(Alarm.status == "unresolved").scalar() or 0
    )
    avg_health_score = (
        db.query(func.avg(HealthAssessment.health_score)).scalar() or 0
    )

    return DashboardSummary(
        total_devices=total_devices,
        active_devices=active_devices,
        high_risk_devices=high_risk_devices,
        unresolved_alarms=unresolved_alarms,
        avg_health_score=round(float(avg_health_score), 2),
    )


@router.get("/trend/{device_id}", response_model=list[DashboardTrendItem])
def device_trend(
    device_id: int,
    limit: int = 24,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[DashboardTrendItem]:
    limit = min(max(limit, 6), 120)

    data_rows = (
        db.query(SensorData, HealthAssessment)
        .join(
            HealthAssessment,
            (SensorData.device_id == HealthAssessment.device_id)
            & (func.date_format(SensorData.collected_at, "%Y-%m-%d %H:%i")
               == func.date_format(HealthAssessment.assessment_time, "%Y-%m-%d %H:%i")),
            isouter=True,
        )
        .filter(SensorData.device_id == device_id)
        .order_by(SensorData.collected_at.desc())
        .limit(limit)
        .all()
    )

    items = [
        DashboardTrendItem(
            collected_at=sensor.collected_at,
            temperature_out=sensor.temperature_out,
            pressure=sensor.pressure,
            flow_rate=sensor.flow_rate,
            health_score=assessment.health_score if assessment else 0,
        )
        for sensor, assessment in data_rows
    ]

    return list(reversed(items))

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Alarm, Device, HealthAssessment, SensorData, User
from app.schemas import HealthAssessmentOut, SensorDataCreate, SensorDataOut
from app.services.health import evaluate_health

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telemetry", tags=["数据采集"])


@router.post("", response_model=SensorDataOut, status_code=status.HTTP_201_CREATED)
def ingest_sensor_data(
    payload: SensorDataCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> SensorDataOut:
    device = db.query(Device).filter(Device.id == payload.device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="设备不存在，无法写入采集数据")

    record = SensorData(**payload.model_dump())
    db.add(record)
    db.flush()

    health_result = evaluate_health(payload)
    assessment = HealthAssessment(
        device_id=payload.device_id,
        health_score=health_result.score,
        risk_level=health_result.risk_level,
        diagnosis=health_result.diagnosis,
    )
    db.add(assessment)

    if health_result.should_alert:
        alarm = Alarm(
            device_id=payload.device_id,
            level=health_result.alert_level,
            title="设备健康风险预警",
            content=f"{device.name} 当前评分 {health_result.score}，诊断结果：{health_result.diagnosis}",
        )
        db.add(alarm)

    db.commit()
    db.refresh(record)

    logger.info(
        "采集数据写入成功，device_id=%s, score=%s", payload.device_id, health_result.score
    )

    return SensorDataOut(
        id=record.id,
        device_id=record.device_id,
        temperature_in=record.temperature_in,
        temperature_out=record.temperature_out,
        pressure=record.pressure,
        flow_rate=record.flow_rate,
        solar_irradiance=record.solar_irradiance,
        water_level=record.water_level,
        pump_status=record.pump_status,
        collected_at=record.collected_at,
    )


@router.get("/latest/{device_id}", response_model=HealthAssessmentOut)
def latest_health_assessment(
    device_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> HealthAssessmentOut:
    assessment = (
        db.query(HealthAssessment)
        .filter(HealthAssessment.device_id == device_id)
        .order_by(HealthAssessment.assessment_time.desc())
        .first()
    )

    if assessment is None:
        raise HTTPException(status_code=404, detail="暂无健康评估数据")

    return HealthAssessmentOut(
        id=assessment.id,
        device_id=assessment.device_id,
        health_score=assessment.health_score,
        risk_level=assessment.risk_level,
        diagnosis=assessment.diagnosis,
        assessment_time=assessment.assessment_time,
    )

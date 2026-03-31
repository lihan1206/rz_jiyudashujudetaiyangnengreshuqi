import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Alarm, Device, HealthAssessment, SensorData, User
from app.schemas import HealthAssessmentOut, SensorDataCreate, SensorDataOut
from app.services.health import HealthResult, get_health_evaluator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telemetry", tags=["数据采集"])


def _get_device_by_id(db: Session, device_id: int) -> Optional[Device]:
    """
    根据ID获取设备
    :param db: 数据库会话
    :param device_id: 设备ID
    :return: 设备对象或None
    """
    return db.query(Device).filter(Device.id == device_id).first()


def _create_sensor_data(db: Session, payload: SensorDataCreate) -> SensorData:
    """
    创建传感器数据记录
    :param db: 数据库会话
    :param payload: 传感器数据
    :return: 创建的传感器数据对象
    """
    sensor_data = SensorData(**payload.model_dump())
    db.add(sensor_data)
    db.flush()
    return sensor_data


def _create_health_assessment(
    db: Session, device_id: int, health_result: HealthResult
) -> HealthAssessment:
    """
    创建健康评估记录
    :param db: 数据库会话
    :param device_id: 设备ID
    :param health_result: 健康评估结果
    :return: 创建的健康评估对象
    """
    assessment = HealthAssessment(
        device_id=device_id,
        health_score=health_result.score,
        risk_level=health_result.risk_level,
        diagnosis=health_result.diagnosis,
    )
    db.add(assessment)
    return assessment


def _create_alarm_if_needed(
    db: Session, device: Device, health_result: HealthResult
) -> Optional[Alarm]:
    """
    根据健康评估结果创建告警
    :param db: 数据库会话
    :param device: 设备对象
    :param health_result: 健康评估结果
    :return: 创建的告警对象或None
    """
    if not health_result.should_alert:
        return None

    alarm = Alarm(
        device_id=device.id,
        level=health_result.alert_level,
        title="设备健康风险预警",
        content=f"{device.name} 当前评分 {health_result.score}，诊断结果：{health_result.diagnosis}",
    )
    db.add(alarm)
    return alarm


@router.post("", response_model=SensorDataOut, status_code=status.HTTP_201_CREATED)
def ingest_sensor_data(
    payload: SensorDataCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> SensorDataOut:
    """
    采集传感器数据并进行健康评估
    :param payload: 传感器数据
    :param db: 数据库会话
    :param _: 当前用户
    :return: 传感器数据响应
    :raises HTTPException: 如果设备不存在或处理失败
    """
    # 检查设备是否存在
    device = _get_device_by_id(db, payload.device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备不存在，device_id: {payload.device_id}",
        )

    try:
        # 保存传感器数据
        sensor_data = _create_sensor_data(db, payload)

        # 健康评估
        health_evaluator = get_health_evaluator()
        health_result = health_evaluator.evaluate(payload)

        # 保存健康评估
        _create_health_assessment(db, payload.device_id, health_result)

        # 创告警
        _create_alarm_if_needed(db, device, health_result)

        # 提交事务
        db.commit()
        db.refresh(sensor_data)

        logger.info(
            "采集数据写入成功，device_id=%s, health_score=%s, risk_level=%s",
            payload.device_id,
            health_result.score,
            health_result.risk_level,
        )

        return SensorDataOut(
            id=sensor_data.id,
            device_id=sensor_data.device_id,
            temperature_in=sensor_data.temperature_in,
            temperature_out=sensor_data.temperature_out,
            pressure=sensor_data.pressure,
            flow_rate=sensor_data.flow_rate,
            solar_irradiance=sensor_data.solar_irradiance,
            water_level=sensor_data.water_level,
            pump_status=sensor_data.pump_status,
            collected_at=sensor_data.collected_at,
        )

    except ValueError as e:
        db.rollback()
        logger.warning("传感器数据验证失败，device_id=%s, error=%s", payload.device_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"数据验证失败: {str(e)}",
        ) from e

    except SQLAlchemyError as e:
        db.rollback()
        logger.error("数据库操作失败，device_id=%s, error=%s", payload.device_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="数据持久化失败，请稍后重试",
        ) from e

    except Exception as e:
        db.rollback()
        logger.exception("处理传感器数据时发生未知错误，device_id=%s", payload.device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务内部错误",
        ) from e


@router.get("/latest/{device_id}", response_model=HealthAssessmentOut)
def get_latest_health_assessment(
    device_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> HealthAssessmentOut:
    """
    获取设备最新的健康评估数据
    :param device_id: 设备ID
    :param db: 数据库会话
    :param _: 当前用户
    :return: 健康评估响应
    :raises HTTPException: 如果设备不存在或无评估数据
    """
    # 参数验证
    if device_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的设备ID，必须大于0",
        )

    # 检查设备是否存在
    device = _get_device_by_id(db, device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备不存在，device_id: {device_id}",
        )

    try:
        # 查询最新健康评估
        assessment = (
            db.query(HealthAssessment)
            .filter(HealthAssessment.device_id == device_id)
            .order_by(HealthAssessment.assessment_time.desc())
            .first()
        )

        if assessment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"设备暂无健康评估数据，device_id: {device_id}",
            )

        return HealthAssessmentOut(
            id=assessment.id,
            device_id=assessment.device_id,
            health_score=assessment.health_score,
            risk_level=assessment.risk_level,
            diagnosis=assessment.diagnosis,
            assessment_time=assessment.assessment_time,
        )

    except SQLAlchemyError as e:
        logger.error("查询健康评估失败，device_id=%s, error=%s", device_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="查询健康评估数据失败",
        ) from e

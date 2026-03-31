import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Device, User
from app.schemas import DeviceCreate, DeviceOut, DeviceUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/devices", tags=["设备管理"])


def _get_device_by_id(db: Session, device_id: int) -> Optional[Device]:
    """
    根据ID获取设备
    :param db: 数据库会话
    :param device_id: 设备ID
    :return: 设备对象或None
    """
    return db.query(Device).filter(Device.id == device_id).first()


def _get_device_by_code(db: Session, device_code: str) -> Optional[Device]:
    """
    根据设备编号获取设备
    :param db: 数据库会话
    :param device_code: 设备编号
    :return: 设备对象或None
    """
    return db.query(Device).filter(Device.device_code == device_code).first()


def _build_device_response(device: Device) -> DeviceOut:
    """
    构建设备响应对象
    :param device: 设备对象
    :return: 设备响应对象
    """
    return DeviceOut(
        id=device.id,
        device_code=device.device_code,
        name=device.name,
        location=device.location,
        device_type=device.device_type,
        status=device.status,
        installed_at=device.installed_at,
    )


@router.get("", response_model=list[DeviceOut])
def list_devices(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[DeviceOut]:
    """
    获取设备列表
    :param db: 数据库会话
    :param _: 当前用户
    :return: 设备列表
    :raises HTTPException: 如果查询失败
    """
    try:
        devices = db.query(Device).order_by(Device.id.desc()).all()
        return [_build_device_response(device) for device in devices]

    except SQLAlchemyError as e:
        logger.error("查询设备列表失败，error=%s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="查询设备列表失败，请稍后重试",
        ) from e


@router.post("", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def create_device(
    payload: DeviceCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DeviceOut:
    """
    创建设备
    :param payload: 设备创建请求
    :param db: 数据库会话
    :param _: 当前用户
    :return: 创建的设备响应
    :raises HTTPException: 如果设备编号重复或创建失败
    """
    try:
        # 检查设备编号是否重复
        duplicated = _get_device_by_code(db, payload.device_code)
        if duplicated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"设备编号已存在，请更换，device_code: {payload.device_code}",
            )

        # 创建设备
        device = Device(**payload.model_dump())
        db.add(device)
        db.commit()
        db.refresh(device)

        logger.info("设备创建成功，device_code=%s, device_id=%s", device.device_code, device.id)
        return _build_device_response(device)

    except SQLAlchemyError as e:
        db.rollback()
        logger.error("创建设备失败，device_code=%s, error=%s", payload.device_code, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建设备失败，请稍后重试",
        ) from e


@router.put("/{device_id}", response_model=DeviceOut)
def update_device(
    device_id: int,
    payload: DeviceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DeviceOut:
    """
    更新设备信息
    :param device_id: 设备ID
    :param payload: 设备更新请求
    :param db: 数据库会话
    :param _: 当前用户
    :return: 更新后的设备响应
    :raises HTTPException: 如果设备不存在或更新失败
    """
    # 参数验证
    if device_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的设备ID，必须大于0",
        )

    try:
        # 查询设备
        device = _get_device_by_id(db, device_id)
        if device is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"设备不存在，device_id: {device_id}",
            )

        # 更新设备属性
        for key, value in payload.model_dump().items():
            setattr(device, key, value)

        db.commit()
        db.refresh(device)

        logger.info("设备更新成功，device_id=%s", device_id)
        return _build_device_response(device)

    except SQLAlchemyError as e:
        db.rollback()
        logger.error("更新设备失败，device_id=%s, error=%s", device_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新设备失败，请稍后重试",
        ) from e


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    """
    删除设备
    :param device_id: 设备ID
    :param db: 数据库会话
    :param _: 当前用户
    :raises HTTPException: 如果设备不存在或删除失败
    """
    # 参数验证
    if device_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的设备ID，必须大于0",
        )

    try:
        # 查询设备
        device = _get_device_by_id(db, device_id)
        if device is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"设备不存在，device_id: {device_id}",
            )

        # 删除设备
        db.delete(device)
        db.commit()

        logger.warning("设备已删除，device_id=%s, device_code=%s", device_id, device.device_code)

    except SQLAlchemyError as e:
        db.rollback()
        logger.error("删除设备失败，device_id=%s, error=%s", device_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除设备失败，请稍后重试",
        ) from e

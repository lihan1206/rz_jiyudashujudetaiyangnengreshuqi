import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Device, User
from app.schemas import DeviceCreate, DeviceOut, DeviceUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/devices", tags=["设备管理"])


@router.get("", response_model=list[DeviceOut])
def list_devices(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[DeviceOut]:
    devices = db.query(Device).order_by(Device.id.desc()).all()
    return [
        DeviceOut(
            id=item.id,
            device_code=item.device_code,
            name=item.name,
            location=item.location,
            device_type=item.device_type,
            status=item.status,
            installed_at=item.installed_at,
        )
        for item in devices
    ]


@router.post("", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def create_device(
    payload: DeviceCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DeviceOut:
    duplicated = db.query(Device).filter(Device.device_code == payload.device_code).first()
    if duplicated:
        raise HTTPException(status_code=400, detail="设备编号已存在，请更换")

    device = Device(**payload.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    logger.info("设备创建成功，device_code=%s", device.device_code)
    return DeviceOut(
        id=device.id,
        device_code=device.device_code,
        name=device.name,
        location=device.location,
        device_type=device.device_type,
        status=device.status,
        installed_at=device.installed_at,
    )


@router.put("/{device_id}", response_model=DeviceOut)
def update_device(
    device_id: int,
    payload: DeviceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DeviceOut:
    device = db.query(Device).filter(Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="设备不存在")

    for key, value in payload.model_dump().items():
        setattr(device, key, value)

    db.commit()
    db.refresh(device)
    logger.info("设备更新成功，device_id=%s", device_id)
    return DeviceOut(
        id=device.id,
        device_code=device.device_code,
        name=device.name,
        location=device.location,
        device_type=device.device_type,
        status=device.status,
        installed_at=device.installed_at,
    )


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    device = db.query(Device).filter(Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="设备不存在")

    db.delete(device)
    db.commit()
    logger.warning("设备已删除，device_id=%s", device_id)

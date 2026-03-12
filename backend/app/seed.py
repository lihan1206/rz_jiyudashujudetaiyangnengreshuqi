import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models import Alarm, Device, HealthAssessment, SensorData, User

logger = logging.getLogger(__name__)


def seed_data(db: Session) -> None:
    if db.query(User).count() == 0:
        admin = User(
            username="admin",
            hashed_password=get_password_hash("123456"),
            role="admin",
            is_active=True,
        )
        db.add(admin)

    if db.query(Device).count() == 0:
        devices = [
            Device(
                device_code="SH-1001",
                name="一号楼太阳能热水器",
                location="上海市浦东新区一号楼屋顶",
                device_type="solar_heater",
                status="active",
            ),
            Device(
                device_code="SH-1002",
                name="二号楼太阳能热水器",
                location="上海市浦东新区二号楼屋顶",
                device_type="solar_heater",
                status="active",
            ),
            Device(
                device_code="SH-1003",
                name="运维实验设备",
                location="上海市浦东新区测试中心",
                device_type="solar_thermal",
                status="inactive",
            ),
        ]
        db.add_all(devices)
        db.flush()

        now = datetime.utcnow()
        sensor_records: list[SensorData] = []
        assessments: list[HealthAssessment] = []
        alarms: list[Alarm] = []

        for device in devices:
            for i in range(24):
                timestamp = now - timedelta(hours=24 - i)
                temperature_in = 25 + i * 0.2
                temperature_out = 45 + i * 0.3
                pressure = 0.25 + (i % 6) * 0.02
                flow_rate = 9 + (i % 5)
                solar_irradiance = 300 + (i % 8) * 60
                water_level = 80 - (i % 10)

                if device.device_code == "SH-1003":
                    temperature_out -= 10
                    flow_rate -= 4
                    pressure += 0.2

                sensor = SensorData(
                    device_id=device.id,
                    temperature_in=round(temperature_in, 2),
                    temperature_out=round(temperature_out, 2),
                    pressure=round(pressure, 2),
                    flow_rate=round(flow_rate, 2),
                    solar_irradiance=round(solar_irradiance, 2),
                    water_level=water_level,
                    pump_status="off" if device.device_code == "SH-1003" and i % 4 == 0 else "on",
                    collected_at=timestamp,
                )
                sensor_records.append(sensor)

                score = 88 if device.device_code != "SH-1003" else 56
                risk_level = "low" if score >= 80 else "high"
                diagnosis = "系统运行正常" if score >= 80 else "循环效率下降，建议检查水泵和管路保温"

                assessments.append(
                    HealthAssessment(
                        device_id=device.id,
                        health_score=score,
                        risk_level=risk_level,
                        diagnosis=diagnosis,
                        assessment_time=timestamp,
                    )
                )

                if risk_level == "high" and i % 3 == 0:
                    alarms.append(
                        Alarm(
                            device_id=device.id,
                            level="严重",
                            title="设备健康风险预警",
                            content=f"{device.name} 评分 {score}，诊断：{diagnosis}",
                            status="unresolved",
                            created_at=timestamp,
                        )
                    )

        db.add_all(sensor_records)
        db.add_all(assessments)
        db.add_all(alarms)

    db.commit()
    logger.info("种子数据初始化完成")

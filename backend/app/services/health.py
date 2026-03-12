from dataclasses import dataclass

from app.schemas import SensorDataCreate


@dataclass
class HealthResult:
    score: int
    risk_level: str
    diagnosis: str
    should_alert: bool
    alert_level: str


def evaluate_health(payload: SensorDataCreate) -> HealthResult:
    score = 100
    diagnosis_items: list[str] = []

    if payload.temperature_out < 45:
        score -= 18
        diagnosis_items.append("出水温度偏低")

    if payload.pressure < 0.15 or payload.pressure > 0.55:
        score -= 16
        diagnosis_items.append("管路压力异常")

    if payload.flow_rate < 6:
        score -= 12
        diagnosis_items.append("循环流量偏低")

    if payload.water_level < 20:
        score -= 10
        diagnosis_items.append("水位不足")

    if payload.solar_irradiance > 600 and payload.temperature_out < 45:
        score -= 20
        diagnosis_items.append("高光照下加热效率不足")

    if payload.pump_status == "off" and payload.solar_irradiance > 500:
        score -= 14
        diagnosis_items.append("光照充足但循环泵未启动")

    score = max(score, 0)

    if score >= 80:
        risk_level = "low"
    elif score >= 60:
        risk_level = "medium"
    else:
        risk_level = "high"

    diagnosis = "，".join(diagnosis_items) if diagnosis_items else "系统运行正常"

    should_alert = risk_level in {"medium", "high"}
    alert_level = "严重" if risk_level == "high" else "警告" if risk_level == "medium" else "提醒"

    return HealthResult(
        score=score,
        risk_level=risk_level,
        diagnosis=diagnosis,
        should_alert=should_alert,
        alert_level=alert_level,
    )

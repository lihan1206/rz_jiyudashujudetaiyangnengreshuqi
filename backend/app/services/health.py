from dataclasses import dataclass
from typing import Optional

from app.schemas import SensorDataCreate


@dataclass
class HealthResult:
    score: int
    risk_level: str
    diagnosis: str
    should_alert: bool
    alert_level: str


class HealthEvaluator:
    """
    设备健康评估类
    封装健康评估逻辑，提供可配置的评估规则和阈值
    """

    # 评分阈值常量
    MIN_SCORE: int = 0
    MAX_SCORE: int = 100
    LOW_RISK_THRESHOLD: int = 80
    MEDIUM_RISK_THRESHOLD: int = 60

    # 健康规则权重
    TEMPERATURE_WEIGHT: int = 18
    PRESSURE_WEIGHT: int = 16
    FLOW_RATE_WEIGHT: int = 12
    WATER_LEVEL_WEIGHT: int = 10
    EFFICIENCY_WEIGHT: int = 20
    PUMP_STATUS_WEIGHT: int = 14

    def __init__(self) -> None:
        """初始化健康评估器，设置默认阈值"""
        self._min_temperature_out: float = 45.0
        self._min_pressure: float = 0.15
        self._max_pressure: float = 0.55
        self._min_flow_rate: float = 6.0
        self._min_water_level: int = 20
        self._high_irradiance: float = 600.0
        self._pump_irradiance_threshold: float = 500.0

    def _validate_input(self, payload: SensorDataCreate) -> None:
        """
        验证输入数据的有效性
        :param payload: 传感器数据
        :raises ValueError: 如果数据无效
        """
        if payload.device_id <= 0:
            raise ValueError("设备ID必须大于0")

        if not (0 <= payload.temperature_in <= 100):
            raise ValueError(f"进水温度必须在0-100范围内，当前值: {payload.temperature_in}")

        if not (0 <= payload.temperature_out <= 120):
            raise ValueError(f"出水温度必须在0-120范围内，当前值: {payload.temperature_out}")

        if payload.temperature_out < payload.temperature_in - 0.5:
            raise ValueError("出水温度不能明显低于进水温度")

        if not (0 <= payload.pressure <= 2):
            raise ValueError(f"压力必须在0-2范围内，当前值: {payload.pressure}")

        if not (0 <= payload.flow_rate <= 100):
            raise ValueError(f"流量必须在0-100范围内，当前值: {payload.flow_rate}")

        if not (0 <= payload.solar_irradiance <= 1500):
            raise ValueError(f"太阳辐照度必须在0-1500范围内，当前值: {payload.solar_irradiance}")

        if not (0 <= payload.water_level <= 100):
            raise ValueError(f"水位必须在0-100范围内，当前值: {payload.water_level}")

        if payload.pump_status not in {"on", "off"}:
            raise ValueError(f"泵状态必须是'on'或'off'，当前值: {payload.pump_status}")

    def _calculate_score_and_diagnosis(self, payload: SensorDataCreate) -> tuple[int, list[str]]:
        """
        计算健康评分和诊断项
        :param payload: 传感器数据
        :return: (评分, 诊断项列表)
        """
        score: int = self.MAX_SCORE
        diagnosis_items: list[str] = []

        # 出水温度检查
        if payload.temperature_out < self._min_temperature_out:
            score -= self.TEMPERATURE_WEIGHT
            diagnosis_items.append("出水温度偏低")

        # 压力检查
        if not (self._min_pressure <= payload.pressure <= self._max_pressure):
            score -= self.PRESSURE_WEIGHT
            diagnosis_items.append("管路压力异常")

        # 流量检查
        if payload.flow_rate < self._min_flow_rate:
            score -= self.FLOW_RATE_WEIGHT
            diagnosis_items.append("循环流量偏低")

        # 水位检查
        if payload.water_level < self._min_water_level:
            score -= self.WATER_LEVEL_WEIGHT
            diagnosis_items.append("水位不足")

        # 加热效率检查
        if payload.solar_irradiance > self._high_irradiance and payload.temperature_out < self._min_temperature_out:
            score -= self.EFFICIENCY_WEIGHT
            diagnosis_items.append("高光照下加热效率不足")

        # 泵状态检查
        if payload.pump_status == "off" and payload.solar_irradiance > self._pump_irradiance_threshold:
            score -= self.PUMP_STATUS_WEIGHT
            diagnosis_items.append("光照充足但循环泵未启动")

        return max(score, self.MIN_SCORE), diagnosis_items

    def _determine_risk_level(self, score: int) -> tuple[str, bool, str]:
        """
        根据评分确定风险等级
        :param score: 健康评分
        :return: (风险等级, 是否需要告警, 告警级别)
        """
        if score >= self.LOW_RISK_THRESHOLD:
            risk_level = "low"
            should_alert = False
            alert_level = "提醒"
        elif score >= self.MEDIUM_RISK_THRESHOLD:
            risk_level = "medium"
            should_alert = True
            alert_level = "警告"
        else:
            risk_level = "high"
            should_alert = True
            alert_level = "严重"

        return risk_level, should_alert, alert_level

    def evaluate(self, payload: SensorDataCreate) -> HealthResult:
        """
        评估设备健康状态
        :param payload: 传感器数据
        :return: 健康评估结果
        :raises ValueError: 如果输入数据无效
        """
        # 输入验证
        self._validate_input(payload)

        # 计算评分和诊断
        score, diagnosis_items = self._calculate_score_and_diagnosis(payload)

        # 确定风险等级
        risk_level, should_alert, alert_level = self._determine_risk_level(score)

        # 生成诊断信息
        diagnosis = "，".join(diagnosis_items) if diagnosis_items else "系统运行正常"

        return HealthResult(
            score=score,
            risk_level=risk_level,
            diagnosis=diagnosis,
            should_alert=should_alert,
            alert_level=alert_level,
        )


# 全局实例，便于兼容原有代码
_health_evaluator: Optional[HealthEvaluator] = None


def get_health_evaluator() -> HealthEvaluator:
    """获取健康评估器单例"""
    global _health_evaluator
    if _health_evaluator is None:
        _health_evaluator = HealthEvaluator()
    return _health_evaluator


def evaluate_health(payload: SensorDataCreate) -> HealthResult:
    """
    兼容原有代码的函数接口
    新代码建议直接使用 HealthEvaluator 类
    """
    return get_health_evaluator().evaluate(payload)

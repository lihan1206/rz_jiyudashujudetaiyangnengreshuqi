"""
设备健康评估服务模块。

提供太阳能热水器设备健康状态的评估功能，包括健康分数计算、
风险等级判定和诊断建议生成。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Final

from app.schemas import SensorDataCreate


class RiskLevel(str, Enum):
    """风险等级枚举。"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlertLevel(str, Enum):
    """告警等级枚举。"""
    REMINDER = "提醒"
    WARNING = "警告"
    CRITICAL = "严重"


class PumpStatus(str, Enum):
    """泵状态枚举。"""
    ON = "on"
    OFF = "off"


@dataclass(frozen=True)
class HealthResult:
    """
    健康评估结果数据类。

    Attributes:
        score: 健康分数（0-100）
        risk_level: 风险等级（low/medium/high）
        diagnosis: 诊断描述
        should_alert: 是否应触发告警
        alert_level: 告警等级
    """
    score: int
    risk_level: str
    diagnosis: str
    should_alert: bool
    alert_level: str


@dataclass
class DiagnosisItem:
    """
    诊断项数据类。

    Attributes:
        condition: 诊断条件描述
        score_penalty: 分数扣减值
    """
    condition: str
    score_penalty: int


class HealthEvaluator:
    """
    设备健康评估器类。

    封装设备健康评估的逻辑和数据，支持对太阳能热水器设备的
    传感器数据进行健康状态评估。

    Attributes:
        DEFAULT_SCORE: 默认初始健康分数
        MIN_SCORE: 最小健康分数
        TEMPERATURE_OUTLET_THRESHOLD: 出水温度阈值（℃）
        PRESSURE_MIN_THRESHOLD: 最小压力阈值（MPa）
        PRESSURE_MAX_THRESHOLD: 最大压力阈值（MPa）
        FLOW_RATE_THRESHOLD: 流量阈值（L/min）
        WATER_LEVEL_THRESHOLD: 水位阈值（%）
        SOLAR_IRRADIANCE_HIGH: 高光照阈值（W/m²）
        SOLAR_IRRADIANCE_MEDIUM: 中光照阈值（W/m²）
    """

    DEFAULT_SCORE: Final[int] = 100
    MIN_SCORE: Final[int] = 0

    TEMPERATURE_OUTLET_THRESHOLD: Final[float] = 45.0
    PRESSURE_MIN_THRESHOLD: Final[float] = 0.15
    PRESSURE_MAX_THRESHOLD: Final[float] = 0.55
    FLOW_RATE_THRESHOLD: Final[float] = 6.0
    WATER_LEVEL_THRESHOLD: Final[int] = 20
    SOLAR_IRRADIANCE_HIGH: Final[float] = 600.0
    SOLAR_IRRADIANCE_MEDIUM: Final[float] = 500.0

    SCORE_THRESHOLD_HIGH: Final[int] = 80
    SCORE_THRESHOLD_MEDIUM: Final[int] = 60

    def __init__(self, sensor_data: SensorDataCreate) -> None:
        """
        初始化健康评估器。

        Args:
            sensor_data: 传感器数据创建模型

        Raises:
            TypeError: 当 sensor_data 不是 SensorDataCreate 类型时
            ValueError: 当传感器数据包含无效值时
        """
        if not isinstance(sensor_data, SensorDataCreate):
            raise TypeError(
                f"期望 SensorDataCreate 类型，但收到 {type(sensor_data).__name__}"
            )

        self._sensor_data: SensorDataCreate = sensor_data
        self._score: int = self.DEFAULT_SCORE
        self._diagnosis_items: list[DiagnosisItem] = []

        self._validate_sensor_data()

    def _validate_sensor_data(self) -> None:
        """
        验证传感器数据的有效性。

        Raises:
            ValueError: 当传感器数据包含无效值时
        """
        data = self._sensor_data

        if data.temperature_in < 0 or data.temperature_in > 100:
            raise ValueError(
                f"进水温度必须在 0-100℃ 范围内，当前值: {data.temperature_in}"
            )

        if data.temperature_out < 0 or data.temperature_out > 120:
            raise ValueError(
                f"出水温度必须在 0-120℃ 范围内，当前值: {data.temperature_out}"
            )

        if data.pressure < 0 or data.pressure > 2:
            raise ValueError(
                f"压力必须在 0-2 MPa 范围内，当前值: {data.pressure}"
            )

        if data.flow_rate < 0 or data.flow_rate > 100:
            raise ValueError(
                f"流量必须在 0-100 L/min 范围内，当前值: {data.flow_rate}"
            )

        if data.solar_irradiance < 0 or data.solar_irradiance > 1500:
            raise ValueError(
                f"太阳辐照度必须在 0-1500 W/m² 范围内，当前值: {data.solar_irradiance}"
            )

        if data.water_level < 0 or data.water_level > 100:
            raise ValueError(
                f"水位必须在 0-100% 范围内，当前值: {data.water_level}"
            )

        if data.pump_status not in {PumpStatus.ON.value, PumpStatus.OFF.value}:
            raise ValueError(
                f"泵状态必须是 'on' 或 'off'，当前值: {data.pump_status}"
            )

    def _check_temperature_outlet(self) -> None:
        """检查出水温度是否偏低。"""
        if self._sensor_data.temperature_out < self.TEMPERATURE_OUTLET_THRESHOLD:
            self._diagnosis_items.append(
                DiagnosisItem("出水温度偏低", 18)
            )
            self._score -= 18

    def _check_pressure(self) -> None:
        """检查管路压力是否异常。"""
        pressure = self._sensor_data.pressure
        if pressure < self.PRESSURE_MIN_THRESHOLD or pressure > self.PRESSURE_MAX_THRESHOLD:
            self._diagnosis_items.append(
                DiagnosisItem("管路压力异常", 16)
            )
            self._score -= 16

    def _check_flow_rate(self) -> None:
        """检查循环流量是否偏低。"""
        if self._sensor_data.flow_rate < self.FLOW_RATE_THRESHOLD:
            self._diagnosis_items.append(
                DiagnosisItem("循环流量偏低", 12)
            )
            self._score -= 12

    def _check_water_level(self) -> None:
        """检查水位是否不足。"""
        if self._sensor_data.water_level < self.WATER_LEVEL_THRESHOLD:
            self._diagnosis_items.append(
                DiagnosisItem("水位不足", 10)
            )
            self._score -= 10

    def _check_heating_efficiency(self) -> None:
        """检查高光照下的加热效率。"""
        if (self._sensor_data.solar_irradiance > self.SOLAR_IRRADIANCE_HIGH and
                self._sensor_data.temperature_out < self.TEMPERATURE_OUTLET_THRESHOLD):
            self._diagnosis_items.append(
                DiagnosisItem("高光照下加热效率不足", 20)
            )
            self._score -= 20

    def _check_pump_status(self) -> None:
        """检查光照充足时泵是否未启动。"""
        if (self._sensor_data.pump_status == PumpStatus.OFF.value and
                self._sensor_data.solar_irradiance > self.SOLAR_IRRADIANCE_MEDIUM):
            self._diagnosis_items.append(
                DiagnosisItem("光照充足但循环泵未启动", 14)
            )
            self._score -= 14

    def _calculate_score(self) -> int:
        """
        计算健康分数。

        Returns:
            计算后的健康分数（不小于 MIN_SCORE）
        """
        self._check_temperature_outlet()
        self._check_pressure()
        self._check_flow_rate()
        self._check_water_level()
        self._check_heating_efficiency()
        self._check_pump_status()

        return max(self._score, self.MIN_SCORE)

    def _determine_risk_level(self, score: int) -> RiskLevel:
        """
        根据分数确定风险等级。

        Args:
            score: 健康分数

        Returns:
            风险等级枚举值
        """
        if score >= self.SCORE_THRESHOLD_HIGH:
            return RiskLevel.LOW
        elif score >= self.SCORE_THRESHOLD_MEDIUM:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.HIGH

    def _generate_diagnosis(self) -> str:
        """
        生成诊断描述。

        Returns:
            诊断描述字符串
        """
        if not self._diagnosis_items:
            return "系统运行正常"
        return "，".join(item.condition for item in self._diagnosis_items)

    def _determine_alert_level(self, risk_level: RiskLevel) -> AlertLevel:
        """
        根据风险等级确定告警等级。

        Args:
            risk_level: 风险等级

        Returns:
            告警等级枚举值
        """
        if risk_level == RiskLevel.HIGH:
            return AlertLevel.CRITICAL
        elif risk_level == RiskLevel.MEDIUM:
            return AlertLevel.WARNING
        else:
            return AlertLevel.REMINDER

    def evaluate(self) -> HealthResult:
        """
        执行健康评估。

        Returns:
            HealthResult: 包含健康分数、风险等级、诊断和告警信息的结果对象
        """
        score = self._calculate_score()
        risk_level = self._determine_risk_level(score)
        diagnosis = self._generate_diagnosis()
        should_alert = risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH}
        alert_level = self._determine_alert_level(risk_level)

        return HealthResult(
            score=score,
            risk_level=risk_level.value,
            diagnosis=diagnosis,
            should_alert=should_alert,
            alert_level=alert_level.value,
        )


def evaluate_health(sensor_data: SensorDataCreate) -> HealthResult:
    """
    评估设备健康状态的便捷函数。

    这是 HealthEvaluator 类的便捷包装函数，保持向后兼容性。

    Args:
        sensor_data: 传感器数据创建模型

    Returns:
        HealthResult: 健康评估结果

    Raises:
        TypeError: 当 sensor_data 类型无效时
        ValueError: 当传感器数据包含无效值时

    Example:
        >>> payload = SensorDataCreate(
        ...     device_id=1,
        ...     temperature_in=25.0,
        ...     temperature_out=50.0,
        ...     pressure=0.3,
        ...     flow_rate=8.0,
        ...     solar_irradiance=800.0,
        ...     water_level=80,
        ...     pump_status="on"
        ... )
        >>> result = evaluate_health(payload)
        >>> print(f"健康分数: {result.score}")
    """
    evaluator = HealthEvaluator(sensor_data)
    return evaluator.evaluate()

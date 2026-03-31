"""
太阳能热水器健康诊断模块

模块结构:
- 数据类: SensorData, ValidationResult, DiagnosisResult
- 常量配置类: DiagnosisConfig
- 主诊断类: SolarHeaterHealthAnalyzer
- 便捷函数: analyze_health()
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class FaultType(Enum):
    NORMAL = "normal"
    LOW_HEATING = "low_heating"
    PUMP_FAILURE = "pump_failure"
    TEMP_SENSOR_ERROR = "temp_sensor_error"
    HEAT_LOSS = "heat_loss"
    SYSTEM_IDLE = "system_idle"
    DATA_ERROR = "data_error"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlertType(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


FAULT_DESCRIPTIONS: dict[FaultType, str] = {
    FaultType.NORMAL: "系统运行正常",
    FaultType.LOW_HEATING: "加热效率不足",
    FaultType.PUMP_FAILURE: "循环泵异常",
    FaultType.TEMP_SENSOR_ERROR: "温度传感器异常",
    FaultType.HEAT_LOSS: "热损失过大",
    FaultType.SYSTEM_IDLE: "系统待机",
    FaultType.DATA_ERROR: "数据错误",
}

RISK_LEVEL_DESCRIPTIONS: dict[RiskLevel, str] = {
    RiskLevel.LOW: "低风险",
    RiskLevel.MEDIUM: "中风险",
    RiskLevel.HIGH: "高风险",
}

ALERT_TYPE_DESCRIPTIONS: dict[AlertType, str] = {
    AlertType.INFO: "信息",
    AlertType.WARNING: "警告",
    AlertType.CRITICAL: "严重",
}


@dataclass
class SensorData:
    inlet_temperature: float
    outlet_temperature: float
    pump_status: str
    ambient_temperature: float
    timestamp: str

    def __post_init__(self) -> None:
        self.pump_status = self.pump_status.lower()

    @property
    def temperature_rise(self) -> float:
        return self.outlet_temperature - self.inlet_temperature

    @property
    def heat_loss_indicator(self) -> float:
        return self.outlet_temperature - self.ambient_temperature


@dataclass
class ValidationResult:
    is_valid: bool
    data: SensorData | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class DiagnosisResult:
    alert_type: AlertType
    fault: FaultType
    risk_level: RiskLevel
    diagnosis: str
    suggestion: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_type": self.alert_type.value,
            "fault": self.fault.value,
            "risk_level": self.risk_level.value,
            "diagnosis": self.diagnosis,
            "suggestion": self.suggestion,
            "language": "zh-CN",
        }


class SensorDataValidationError(ValueError):
    pass


class DiagnosisConfig:
    REQUIRED_FIELDS: dict[str, tuple[type, ...]] = {
        "inlet_temperature": (float, int),
        "outlet_temperature": (float, int),
        "pump_status": str,
        "ambient_temperature": (float, int),
        "timestamp": str,
    }

    VALID_PUMP_STATUS: set[str] = {"on", "off"}

    TEMP_MIN: float = -50.0
    TEMP_MAX: float = 150.0

    TEMP_RISE_LOW_THRESHOLD: float = 3.0
    TEMP_RISE_CRITICAL_THRESHOLD: float = 1.0
    TEMP_RISE_GOOD_THRESHOLD: float = 30.0

    HEAT_LOSS_THRESHOLD: float = -5.0


class SolarHeaterHealthAnalyzer:
    def __init__(self, config: DiagnosisConfig | None = None) -> None:
        self._config = config or DiagnosisConfig()

    def validate_sensor_data(
        self, sensor_data: dict[str, Any]
    ) -> ValidationResult:
        errors: list[str] = []

        if not isinstance(sensor_data, dict):
            return ValidationResult(
                is_valid=False,
                errors=["输入数据必须是字典类型"]
            )

        validated_fields: dict[str, Any] = {}

        for field_name, expected_types in self._config.REQUIRED_FIELDS.items():
            if field_name not in sensor_data:
                errors.append(f"缺失必需字段: {field_name}")
                continue

            value = sensor_data[field_name]

            try:
                validated_value = self._validate_field(field_name, value, expected_types)
                validated_fields[field_name] = validated_value
            except SensorDataValidationError as e:
                errors.append(str(e))

        for field_name in ["inlet_temperature", "outlet_temperature", "ambient_temperature"]:
            if field_name in validated_fields:
                temp = validated_fields[field_name]
                if temp < self._config.TEMP_MIN or temp > self._config.TEMP_MAX:
                    errors.append(f"字段 {field_name} 值超出合理范围: {temp}°C")

        if errors:
            return ValidationResult(is_valid=False, errors=errors)

        try:
            data = SensorData(
                inlet_temperature=validated_fields["inlet_temperature"],
                outlet_temperature=validated_fields["outlet_temperature"],
                pump_status=validated_fields["pump_status"],
                ambient_temperature=validated_fields["ambient_temperature"],
                timestamp=validated_fields["timestamp"],
            )
            return ValidationResult(is_valid=True, data=data)
        except Exception as e:
            return ValidationResult(is_valid=False, errors=[f"数据构造失败: {str(e)}"])

    def _validate_field(
        self, field_name: str, value: Any, expected_types: type | tuple[type, ...]
    ) -> Any:
        if field_name == "pump_status":
            return self._validate_pump_status(value)
        elif field_name == "timestamp":
            return self._validate_timestamp(value)
        else:
            return self._validate_numeric_field(field_name, value, expected_types)

    def _validate_pump_status(self, value: Any) -> str:
        if not isinstance(value, str):
            raise SensorDataValidationError(
                f"字段 pump_status 类型错误: 期望 str, 实际 {type(value).__name__}"
            )
        normalized = value.lower()
        if normalized not in self._config.VALID_PUMP_STATUS:
            raise SensorDataValidationError(
                f"字段 pump_status 值无效: 必须是 'on' 或 'off'"
            )
        return normalized

    def _validate_timestamp(self, value: Any) -> str:
        if not isinstance(value, str):
            raise SensorDataValidationError(
                f"字段 timestamp 类型错误: 期望 str, 实际 {type(value).__name__}"
            )
        try:
            datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            return value
        except ValueError:
            raise SensorDataValidationError(
                f"字段 timestamp 格式错误: 期望 'YYYY-MM-DD HH:MM:SS'"
            )

    def _validate_numeric_field(
        self, field_name: str, value: Any, expected_types: type | tuple[type, ...]
    ) -> float:
        types_to_check = expected_types if isinstance(expected_types, tuple) else (expected_types,)
        if not isinstance(value, types_to_check):
            expected_names = "或".join(t.__name__ for t in types_to_check)
            raise SensorDataValidationError(
                f"字段 {field_name} 类型错误: 期望 {expected_names}, 实际 {type(value).__name__}"
            )
        return float(value) if isinstance(value, int) else value

    def diagnose_faults(self, data: SensorData) -> DiagnosisResult:
        if data.pump_status == "off":
            return self._diagnose_pump_off(data)
        return self._diagnose_pump_on(data)

    def _diagnose_pump_off(self, data: SensorData) -> DiagnosisResult:
        diagnosis_items: list[str] = []
        suggestion_items: list[str] = []

        diagnosis_items.append("循环泵处于关闭状态，系统待机中")
        suggestion_items.append("如需加热，请检查循环泵控制设置")

        if data.temperature_rise > 5:
            return DiagnosisResult(
                alert_type=AlertType.WARNING,
                fault=FaultType.PUMP_FAILURE,
                risk_level=RiskLevel.MEDIUM,
                diagnosis="检测到温差但循环泵未运行，可能存在控制故障",
                suggestion="检查循环泵控制线路和继电器状态",
            )

        return DiagnosisResult(
            alert_type=AlertType.INFO,
            fault=FaultType.SYSTEM_IDLE,
            risk_level=RiskLevel.LOW,
            diagnosis="；".join(diagnosis_items),
            suggestion="；".join(suggestion_items),
        )

    def _diagnose_pump_on(self, data: SensorData) -> DiagnosisResult:
        diagnosis_items: list[str] = []
        suggestion_items: list[str] = []

        fault = FaultType.NORMAL
        alert_type = AlertType.INFO
        risk_level = RiskLevel.LOW

        temp_rise = data.temperature_rise
        heat_loss = data.heat_loss_indicator

        if temp_rise < self._config.TEMP_RISE_LOW_THRESHOLD:
            fault, alert_type, risk_level = self._evaluate_low_temp_rise(
                temp_rise, diagnosis_items, suggestion_items
            )
        elif temp_rise > self._config.TEMP_RISE_GOOD_THRESHOLD:
            diagnosis_items.append(f"加热效果良好，温升达到 {temp_rise:.1f}°C")
            suggestion_items.append("系统运行正常，继续保持")
        else:
            diagnosis_items.append(f"系统运行正常，温升 {temp_rise:.1f}°C")
            suggestion_items.append("系统运行正常，继续保持")

        if heat_loss < self._config.HEAT_LOSS_THRESHOLD:
            fault, alert_type, risk_level = self._evaluate_heat_loss(
                fault, alert_type, risk_level, heat_loss, diagnosis_items, suggestion_items
            )

        diagnosis = "；".join(diagnosis_items) if diagnosis_items else "系统运行正常"
        suggestion = "；".join(suggestion_items) if suggestion_items else "无需操作"

        return DiagnosisResult(
            alert_type=alert_type,
            fault=fault,
            risk_level=risk_level,
            diagnosis=diagnosis,
            suggestion=suggestion,
        )

    def _evaluate_low_temp_rise(
        self,
        temp_rise: float,
        diagnosis_items: list[str],
        suggestion_items: list[str],
    ) -> tuple[FaultType, AlertType, RiskLevel]:
        diagnosis_items.append(f"温升不足，当前温升仅 {temp_rise:.1f}°C")
        suggestion_items.append("检查集热器表面是否有遮挡物")
        suggestion_items.append("检查真空管是否有破损或结垢")

        if temp_rise < self._config.TEMP_RISE_CRITICAL_THRESHOLD:
            diagnosis_items.append("温升几乎为零，可能存在温度传感器故障")
            suggestion_items.append("立即检查进水口和出水口温度传感器")
            return FaultType.TEMP_SENSOR_ERROR, AlertType.CRITICAL, RiskLevel.HIGH

        return FaultType.LOW_HEATING, AlertType.WARNING, RiskLevel.MEDIUM

    def _evaluate_heat_loss(
        self,
        current_fault: FaultType,
        current_alert: AlertType,
        current_risk: RiskLevel,
        heat_loss: float,
        diagnosis_items: list[str],
        suggestion_items: list[str],
    ) -> tuple[FaultType, AlertType, RiskLevel]:
        diagnosis_items.append(
            f"出水温度低于环境温度 {abs(heat_loss):.1f}°C，存在异常热损失"
        )
        suggestion_items.append("检查管道保温层是否完好")
        suggestion_items.append("检查是否存在管道泄漏")

        if current_fault == FaultType.NORMAL:
            return FaultType.HEAT_LOSS, AlertType.WARNING, RiskLevel.MEDIUM

        return current_fault, current_alert, current_risk

    def handle_error(self, errors: list[str]) -> dict[str, Any]:
        return {
            "alert_type": AlertType.CRITICAL.value,
            "fault": FaultType.DATA_ERROR.value,
            "risk_level": RiskLevel.HIGH.value,
            "diagnosis": f"数据验证失败: {'; '.join(errors)}",
            "suggestion": "请检查传感器数据采集系统，确保数据完整性和正确性",
            "language": "zh-CN",
        }

    def analyze(self, sensor_data: dict[str, Any]) -> dict[str, Any]:
        try:
            validation = self.validate_sensor_data(sensor_data)

            if not validation.is_valid:
                return self.handle_error(validation.errors)

            if validation.data is None:
                return self.handle_error(["验证通过但数据为空"])

            diagnosis = self.diagnose_faults(validation.data)
            return diagnosis.to_dict()

        except Exception as e:
            return self.handle_error([f"系统异常: {str(e)}"])


_analyzer: SolarHeaterHealthAnalyzer | None = None


def get_analyzer() -> SolarHeaterHealthAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SolarHeaterHealthAnalyzer()
    return _analyzer


def analyze_health(sensor_data: dict[str, Any]) -> dict[str, Any]:
    analyzer = get_analyzer()
    return analyzer.analyze(sensor_data)


if __name__ == "__main__":
    test_cases: list[dict[str, Any]] = [
        {
            "inlet_temperature": 15.0,
            "outlet_temperature": 22.0,
            "pump_status": "off",
            "ambient_temperature": 20.0,
            "timestamp": "2024-04-05 14:30:00"
        },
        {
            "inlet_temperature": 20.0,
            "outlet_temperature": 55.0,
            "pump_status": "on",
            "ambient_temperature": 25.0,
            "timestamp": "2024-04-05 14:30:00"
        },
        {
            "inlet_temperature": 25.0,
            "outlet_temperature": 26.0,
            "pump_status": "on",
            "ambient_temperature": 30.0,
            "timestamp": "2024-04-05 14:30:00"
        },
        {
            "inlet_temperature": 15.0,
            "outlet_temperature": 22.0,
            "pump_status": "invalid",
            "ambient_temperature": 20.0,
            "timestamp": "2024-04-05 14:30:00"
        },
        {
            "inlet_temperature": 15.0,
            "pump_status": "on",
            "ambient_temperature": 20.0,
            "timestamp": "2024-04-05 14:30:00"
        },
    ]

    import json

    analyzer = SolarHeaterHealthAnalyzer()

    for i, test_data in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试用例 {i}:")
        print(f"输入: {json.dumps(test_data, ensure_ascii=False, indent=2)}")
        result = analyzer.analyze(test_data)
        print(f"输出: {json.dumps(result, ensure_ascii=False, indent=2)}")

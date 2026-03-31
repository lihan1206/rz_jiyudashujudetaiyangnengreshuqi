"""
太阳能热水器健康诊断模块

模块结构:
- 数据验证模块: validate_sensor_data()
- 诊断逻辑模块: diagnose_faults()
- 错误处理模块: handle_error()
- 输出格式化模块: format_result()
- 主函数: analyze_health()
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ValidationResult:
    is_valid: bool
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass
class DiagnosisResult:
    alert_type: str
    fault: str
    risk_level: str
    diagnosis: str
    suggestion: str


REQUIRED_FIELDS = {
    "inlet_temp": (float, int),
    "outlet_temp": (float, int),
    "pump_status": str,
    "ambient_temp": (float, int),
    "time": str,
}

VALID_PUMP_STATUS = {"on", "off"}

FAULT_TYPES = {
    "normal": "系统运行正常",
    "low_heating": "加热效率不足",
    "pump_failure": "循环泵异常",
    "temp_sensor_error": "温度传感器异常",
    "heat_loss": "热损失过大",
    "system_idle": "系统待机",
}

RISK_LEVELS = {
    "low": "低风险",
    "medium": "中风险",
    "high": "高风险",
}

ALERT_TYPES = {
    "info": "信息",
    "warning": "警告",
    "critical": "严重",
}


def validate_sensor_data(sensor_data: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []
    validated_data: dict[str, Any] = {}

    if not isinstance(sensor_data, dict):
        return ValidationResult(
            is_valid=False,
            errors=["输入数据必须是字典类型"]
        )

    for field_name, expected_types in REQUIRED_FIELDS.items():
        if field_name not in sensor_data:
            errors.append(f"缺失必需字段: {field_name}")
            continue

        value = sensor_data[field_name]

        if field_name == "pump_status":
            if not isinstance(value, str):
                errors.append(f"字段 {field_name} 类型错误: 期望 str, 实际 {type(value).__name__}")
            elif value.lower() not in VALID_PUMP_STATUS:
                errors.append(f"字段 {field_name} 值无效: 必须是 'on' 或 'off'")
            else:
                validated_data[field_name] = value.lower()
        elif field_name == "time":
            if not isinstance(value, str):
                errors.append(f"字段 {field_name} 类型错误: 期望 str, 实际 {type(value).__name__}")
            else:
                try:
                    datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                    validated_data[field_name] = value
                except ValueError:
                    errors.append(f"字段 {field_name} 格式错误: 期望 'YYYY-MM-DD HH:MM:SS'")
        else:
            if not isinstance(value, expected_types if isinstance(expected_types, type) else expected_types):
                expected_type_names = expected_types if isinstance(expected_types, str) else "或".join(t.__name__ for t in expected_types)
                errors.append(f"字段 {field_name} 类型错误: 期望 {expected_type_names}, 实际 {type(value).__name__}")
            else:
                validated_data[field_name] = float(value) if isinstance(value, int) else value

    for field_name in validated_data:
        if field_name in ["inlet_temp", "outlet_temp", "ambient_temp"]:
            temp = validated_data[field_name]
            if temp < -50 or temp > 150:
                errors.append(f"字段 {field_name} 值超出合理范围: {temp}°C")

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, data=validated_data, errors=errors)


def diagnose_faults(data: dict[str, Any]) -> DiagnosisResult:
    inlet_temp = data["inlet_temp"]
    outlet_temp = data["outlet_temp"]
    pump_status = data["pump_status"]
    ambient_temp = data["ambient_temp"]

    temp_rise = outlet_temp - inlet_temp
    heat_loss = outlet_temp - ambient_temp

    fault = "normal"
    alert_type = "info"
    risk_level = "low"
    diagnosis_items: list[str] = []
    suggestion_items: list[str] = []

    if pump_status == "off":
        fault = "system_idle"
        alert_type = "info"
        risk_level = "low"
        diagnosis_items.append("循环泵处于关闭状态，系统待机中")
        suggestion_items.append("如需加热，请检查循环泵控制设置")

        if temp_rise > 5:
            fault = "pump_failure"
            alert_type = "warning"
            risk_level = "medium"
            diagnosis_items.clear()
            diagnosis_items.append("检测到温差但循环泵未运行，可能存在控制故障")
            suggestion_items.clear()
            suggestion_items.append("检查循环泵控制线路和继电器状态")
    else:
        if temp_rise < 3:
            fault = "low_heating"
            alert_type = "warning"
            risk_level = "medium"
            diagnosis_items.append(f"温升不足，当前温升仅 {temp_rise:.1f}°C")
            suggestion_items.append("检查集热器表面是否有遮挡物")
            suggestion_items.append("检查真空管是否有破损或结垢")

            if temp_rise < 1:
                fault = "temp_sensor_error"
                alert_type = "critical"
                risk_level = "high"
                diagnosis_items.append("温升几乎为零，可能存在温度传感器故障")
                suggestion_items.append("立即检查进水口和出水口温度传感器")
        elif temp_rise > 30:
            fault = "normal"
            alert_type = "info"
            risk_level = "low"
            diagnosis_items.append(f"加热效果良好，温升达到 {temp_rise:.1f}°C")
            suggestion_items.append("系统运行正常，继续保持")
        else:
            fault = "normal"
            alert_type = "info"
            risk_level = "low"
            diagnosis_items.append(f"系统运行正常，温升 {temp_rise:.1f}°C")
            suggestion_items.append("系统运行正常，继续保持")

        if heat_loss < -5:
            if fault == "normal":
                fault = "heat_loss"
                alert_type = "warning"
                risk_level = "medium"
            diagnosis_items.append(f"出水温度低于环境温度 {abs(heat_loss):.1f}°C，存在异常热损失")
            suggestion_items.append("检查管道保温层是否完好")
            suggestion_items.append("检查是否存在管道泄漏")

    diagnosis = "；".join(diagnosis_items) if diagnosis_items else "系统运行正常"
    suggestion = "；".join(suggestion_items) if suggestion_items else "无需操作"

    return DiagnosisResult(
        alert_type=alert_type,
        fault=fault,
        risk_level=risk_level,
        diagnosis=diagnosis,
        suggestion=suggestion,
    )


def handle_error(errors: list[str]) -> dict[str, Any]:
    return {
        "alert_type": "critical",
        "fault": "data_error",
        "risk_level": "high",
        "diagnosis": f"数据验证失败: {'; '.join(errors)}",
        "suggestion": "请检查传感器数据采集系统，确保数据完整性和正确性",
        "language": "zh-CN",
    }


def format_result(diagnosis: DiagnosisResult) -> dict[str, Any]:
    return {
        "alert_type": diagnosis.alert_type,
        "fault": diagnosis.fault,
        "risk_level": diagnosis.risk_level,
        "diagnosis": diagnosis.diagnosis,
        "suggestion": diagnosis.suggestion,
        "language": "zh-CN",
    }


def analyze_health(sensor_data: dict[str, Any]) -> dict[str, Any]:
    """
    分析太阳能热水器健康状态

    Args:
        sensor_data: 传感器数据字典，包含以下字段:
            - inlet_temp: 进水温度 (float)
            - outlet_temp: 出水温度 (float)
            - pump_status: 循环泵状态 ("on" 或 "off")
            - ambient_temp: 环境温度 (float)
            - time: 时间戳字符串 ("YYYY-MM-DD HH:MM:SS")

    Returns:
        结构化 JSON 字典，包含:
            - alert_type: 告警类型 ("info", "warning", "critical")
            - fault: 故障类型代码
            - risk_level: 风险等级 ("low", "medium", "high")
            - diagnosis: 诊断描述
            - suggestion: 建议措施
            - language: 语言标识

    Example:
        >>> sensor_data = {
        ...     "inlet_temp": 15.0,
        ...     "outlet_temp": 22.0,
        ...     "pump_status": "off",
        ...     "ambient_temp": 20.0,
        ...     "time": "2024-04-05 14:30:00"
        ... }
        >>> result = analyze_health(sensor_data)
        >>> print(result["fault"])
        'system_idle'
    """
    try:
        validation = validate_sensor_data(sensor_data)

        if not validation.is_valid:
            return handle_error(validation.errors)

        diagnosis = diagnose_faults(validation.data)

        return format_result(diagnosis)

    except Exception as e:
        return handle_error([f"系统异常: {str(e)}"])


if __name__ == "__main__":
    test_cases = [
        {
            "inlet_temp": 15.0,
            "outlet_temp": 22.0,
            "pump_status": "off",
            "ambient_temp": 20.0,
            "time": "2024-04-05 14:30:00"
        },
        {
            "inlet_temp": 20.0,
            "outlet_temp": 55.0,
            "pump_status": "on",
            "ambient_temp": 25.0,
            "time": "2024-04-05 14:30:00"
        },
        {
            "inlet_temp": 25.0,
            "outlet_temp": 26.0,
            "pump_status": "on",
            "ambient_temp": 30.0,
            "time": "2024-04-05 14:30:00"
        },
        {
            "inlet_temp": 15.0,
            "outlet_temp": 22.0,
            "pump_status": "invalid",
            "ambient_temp": 20.0,
            "time": "2024-04-05 14:30:00"
        },
        {
            "inlet_temp": 15.0,
            "pump_status": "on",
            "ambient_temp": 20.0,
            "time": "2024-04-05 14:30:00"
        },
    ]

    import json

    for i, test_data in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试用例 {i}:")
        print(f"输入: {json.dumps(test_data, ensure_ascii=False, indent=2)}")
        result = analyze_health(test_data)
        print(f"输出: {json.dumps(result, ensure_ascii=False, indent=2)}")

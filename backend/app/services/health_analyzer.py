"""
太阳能热水器健康诊断分析系统
模块化设计：数据验证、诊断逻辑、错误处理、输出格式化
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from datetime import datetime
import json


# ==================== 模块1: 常量与配置 ====================

class AlertType(Enum):
    """告警类型枚举"""
    NORMAL = "normal"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FaultType(Enum):
    """故障类型枚举"""
    NONE = "none"
    LOW_HEATING = "low_heating"
    PUMP_FAILURE = "pump_failure"
    TEMPERATURE_ANOMALY = "temperature_anomaly"
    EFFICIENCY_LOW = "efficiency_low"
    SENSOR_ERROR = "sensor_error"
    SYSTEM_SHUTDOWN = "system_shutdown"


# 诊断阈值配置
DIAGNOSIS_THRESHOLDS = {
    "temp_rise_min": 5.0,          # 最小温升要求(°C)
    "temp_rise_normal": 15.0,      # 正常温升(°C)
    "temp_max": 90.0,              # 最高允许温度(°C)
    "temp_min": 5.0,               # 最低允许温度(°C)
    "ambient_temp_diff": 3.0,      # 与环境温度最小差值
    "pump_on_irradiance": 400,     # 泵应启动的光照阈值
    "high_irradiance": 600,        # 高光照阈值
}


# ==================== 模块2: 数据验证与获取 ====================

@dataclass
class ValidatedSensorData:
    """验证后的传感器数据结构"""
    inlet_temp: float
    outlet_temp: float
    pump_status: str
    ambient_temp: float
    time: str
    irradiance: Optional[float] = None
    pressure: Optional[float] = None
    flow_rate: Optional[float] = None
    water_level: Optional[float] = None
    is_valid: bool = True
    validation_errors: list[str] = field(default_factory=list)


class DataValidator:
    """数据验证器 - 处理输入数据验证和类型转换"""
    
    REQUIRED_FIELDS = ["inlet_temp", "outlet_temp", "pump_status", "ambient_temp", "time"]
    OPTIONAL_FIELDS = ["irradiance", "pressure", "flow_rate", "water_level"]
    VALID_PUMP_STATUSES = ["on", "off", "running", "stopped", "active", "inactive"]
    
    @classmethod
    def validate(cls, sensor_data: dict) -> ValidatedSensorData:
        """
        验证并转换传感器数据
        
        Args:
            sensor_data: 原始传感器数据字典
            
        Returns:
            ValidatedSensorData: 验证后的数据结构
        """
        errors = []
        
        # 检查缺失字段
        missing_fields = [f for f in cls.REQUIRED_FIELDS if f not in sensor_data]
        if missing_fields:
            errors.append(f"缺少必需字段: {', '.join(missing_fields)}")
        
        # 检查None值
        none_fields = [f for f in cls.REQUIRED_FIELDS if sensor_data.get(f) is None]
        if none_fields:
            errors.append(f"以下字段不能为None: {', '.join(none_fields)}")
        
        if errors:
            return ValidatedSensorData(
                inlet_temp=0.0, outlet_temp=0.0, pump_status="unknown",
                ambient_temp=0.0, time="", is_valid=False, validation_errors=errors
            )
        
        # 类型转换和验证
        try:
            inlet_temp = cls._to_float(sensor_data.get("inlet_temp"), "inlet_temp", errors)
            outlet_temp = cls._to_float(sensor_data.get("outlet_temp"), "outlet_temp", errors)
            ambient_temp = cls._to_float(sensor_data.get("ambient_temp"), "ambient_temp", errors)
            
            pump_status = cls._normalize_pump_status(sensor_data.get("pump_status"), errors)
            time_str = cls._validate_time(sensor_data.get("time"), errors)
            
            # 可选字段
            irradiance = cls._to_float_optional(sensor_data.get("irradiance"))
            pressure = cls._to_float_optional(sensor_data.get("pressure"))
            flow_rate = cls._to_float_optional(sensor_data.get("flow_rate"))
            water_level = cls._to_float_optional(sensor_data.get("water_level"))
            
            # 数值范围验证
            cls._validate_temp_range(inlet_temp, "inlet_temp", errors)
            cls._validate_temp_range(outlet_temp, "outlet_temp", errors)
            cls._validate_temp_range(ambient_temp, "ambient_temp", errors)
            
            if errors:
                return ValidatedSensorData(
                    inlet_temp=0.0, outlet_temp=0.0, pump_status="unknown",
                    ambient_temp=0.0, time="", is_valid=False, validation_errors=errors
                )
            
            return ValidatedSensorData(
                inlet_temp=inlet_temp,
                outlet_temp=outlet_temp,
                pump_status=pump_status,
                ambient_temp=ambient_temp,
                time=time_str,
                irradiance=irradiance,
                pressure=pressure,
                flow_rate=flow_rate,
                water_level=water_level,
                is_valid=True,
                validation_errors=[]
            )
            
        except Exception as e:
            errors.append(f"数据验证异常: {str(e)}")
            return ValidatedSensorData(
                inlet_temp=0.0, outlet_temp=0.0, pump_status="unknown",
                ambient_temp=0.0, time="", is_valid=False, validation_errors=errors
            )
    
    @staticmethod
    def _to_float(value: Any, field_name: str, errors: list) -> float:
        """转换为浮点数"""
        try:
            return float(value)
        except (TypeError, ValueError):
            errors.append(f"字段 '{field_name}' 必须是数字类型，当前值: {value}")
            return 0.0
    
    @staticmethod
    def _to_float_optional(value: Any) -> Optional[float]:
        """可选字段转换为浮点数"""
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    
    @classmethod
    def _normalize_pump_status(cls, value: Any, errors: list) -> str:
        """标准化泵状态"""
        if not isinstance(value, str):
            errors.append(f"字段 'pump_status' 必须是字符串类型")
            return "unknown"
        
        value_lower = value.lower().strip()
        
        # 映射各种表示方式到标准值
        on_values = ["on", "running", "active", "1", "true", "开", "启动"]
        off_values = ["off", "stopped", "inactive", "0", "false", "关", "停止"]
        
        if value_lower in on_values:
            return "on"
        elif value_lower in off_values:
            return "off"
        else:
            if value_lower not in cls.VALID_PUMP_STATUSES:
                errors.append(f"字段 'pump_status' 值无效: {value}")
            return value_lower
    
    @staticmethod
    def _validate_time(value: Any, errors: list) -> str:
        """验证时间格式"""
        if not isinstance(value, str):
            errors.append(f"字段 'time' 必须是字符串类型")
            return str(value) if value else ""
        return value
    
    @staticmethod
    def _validate_temp_range(value: float, field_name: str, errors: list):
        """验证温度范围"""
        if value < -50 or value > 150:
            errors.append(f"字段 '{field_name}' 温度值异常: {value}°C (合理范围: -50~150°C)")


# ==================== 模块3: 诊断逻辑 ====================

@dataclass
class DiagnosisResult:
    """诊断结果"""
    fault: FaultType
    fault_description: str
    risk_level: RiskLevel
    diagnosis_details: list[str]
    suggestions: list[str]
    temp_rise: float
    efficiency_score: int


class DiagnosisEngine:
    """诊断引擎 - 核心故障检测逻辑"""
    
    @classmethod
    def diagnose(cls, data: ValidatedSensorData) -> DiagnosisResult:
        """
        执行诊断分析
        
        Args:
            data: 验证后的传感器数据
            
        Returns:
            DiagnosisResult: 诊断结果
        """
        details = []
        suggestions = []
        
        # 计算温升
        temp_rise = data.outlet_temp - data.inlet_temp
        
        # 计算效率评分 (0-100)
        efficiency_score = cls._calculate_efficiency(data, temp_rise)
        
        # 检测各种故障
        fault_checks = [
            cls._check_pump_failure(data, details, suggestions),
            cls._check_low_heating(data, temp_rise, details, suggestions),
            cls._check_temperature_anomaly(data, details, suggestions),
            cls._check_efficiency_low(data, temp_rise, details, suggestions),
            cls._check_system_shutdown(data, details, suggestions),
        ]
        
        # 确定主要故障
        fault = cls._determine_primary_fault(fault_checks, data)
        fault_desc = cls._get_fault_description(fault)
        
        # 确定风险等级
        risk = cls._determine_risk_level(fault, efficiency_score, data)
        
        # 如果没有检测到故障
        if not details:
            details.append("系统运行正常")
            suggestions.append("继续保持当前运行状态")
        
        return DiagnosisResult(
            fault=fault,
            fault_description=fault_desc,
            risk_level=risk,
            diagnosis_details=details,
            suggestions=suggestions,
            temp_rise=temp_rise,
            efficiency_score=efficiency_score
        )
    
    @staticmethod
    def _calculate_efficiency(data: ValidatedSensorData, temp_rise: float) -> int:
        """计算系统效率评分"""
        score = 100
        
        # 温升效率
        if temp_rise < DIAGNOSIS_THRESHOLDS["temp_rise_min"]:
            score -= 30
        elif temp_rise < DIAGNOSIS_THRESHOLDS["temp_rise_normal"]:
            score -= 15
        
        # 泵状态影响
        if data.pump_status == "off":
            if data.irradiance and data.irradiance > DIAGNOSIS_THRESHOLDS["pump_on_irradiance"]:
                score -= 25
            else:
                score -= 10
        
        # 光照条件影响
        if data.irradiance and data.irradiance > DIAGNOSIS_THRESHOLDS["high_irradiance"]:
            if temp_rise < 10:
                score -= 20
        
        return max(score, 0)
    
    @staticmethod
    def _check_pump_failure(data: ValidatedSensorData, details: list, suggestions: list) -> bool:
        """检测泵故障"""
        if data.pump_status == "off":
            if data.irradiance and data.irradiance > DIAGNOSIS_THRESHOLDS["pump_on_irradiance"]:
                if data.outlet_temp > data.inlet_temp + 2:
                    # 可能是自然循环
                    return False
                details.append(f"光照充足(>{DIAGNOSIS_THRESHOLDS['pump_on_irradiance']}W/m²)但循环泵未启动")
                suggestions.append("检查循环泵电源和控制系统")
                suggestions.append("确认泵控制逻辑是否正常")
                return True
            elif data.outlet_temp > data.inlet_temp + 10:
                details.append("泵未启动但温升异常，可能存在自然循环或传感器误差")
                suggestions.append("检查泵状态传感器")
                return True
        return False
    
    @staticmethod
    def _check_low_heating(data: ValidatedSensorData, temp_rise: float, details: list, suggestions: list) -> bool:
        """检测加热不足"""
        if temp_rise < DIAGNOSIS_THRESHOLDS["temp_rise_min"]:
            if data.outlet_temp < data.ambient_temp + DIAGNOSIS_THRESHOLDS["ambient_temp_diff"]:
                details.append(f"出水温度({data.outlet_temp}°C)接近环境温度({data.ambient_temp}°C)，系统几乎无加热效果")
                suggestions.append("检查集热器是否被遮挡或损坏")
                suggestions.append("检查管路保温是否良好")
                return True
            else:
                details.append(f"温升不足: {temp_rise:.1f}°C (低于{DIAGNOSIS_THRESHOLDS['temp_rise_min']}°C)")
                suggestions.append("检查集热器效率")
                return True
        return False
    
    @staticmethod
    def _check_temperature_anomaly(data: ValidatedSensorData, details: list, suggestions: list) -> bool:
        """检测温度异常"""
        has_anomaly = False
        
        if data.outlet_temp > DIAGNOSIS_THRESHOLDS["temp_max"]:
            details.append(f"出水温度过高: {data.outlet_temp}°C (超过{DIAGNOSIS_THRESHOLDS['temp_max']}°C)")
            suggestions.append("检查温控系统和安全阀")
            has_anomaly = True
        
        if data.inlet_temp < DIAGNOSIS_THRESHOLDS["temp_min"]:
            details.append(f"进水温度过低: {data.inlet_temp}°C")
            suggestions.append("检查进水管道保温")
            has_anomaly = True
        
        if data.outlet_temp < data.inlet_temp - 1:
            details.append(f"出水温度({data.outlet_temp}°C)低于进水温度({data.inlet_temp}°C)，传感器可能存在故障")
            suggestions.append("校准或更换温度传感器")
            has_anomaly = True
        
        return has_anomaly
    
    @staticmethod
    def _check_efficiency_low(data: ValidatedSensorData, temp_rise: float, details: list, suggestions: list) -> bool:
        """检测效率低下"""
        if data.irradiance and data.irradiance > DIAGNOSIS_THRESHOLDS["high_irradiance"]:
            if temp_rise < 10:
                details.append(f"高光照条件下({data.irradiance}W/m²)温升仅{temp_rise:.1f}°C，集热效率低")
                suggestions.append("清洁集热器表面")
                suggestions.append("检查集热器管路是否堵塞")
                return True
        return False
    
    @staticmethod
    def _check_system_shutdown(data: ValidatedSensorData, details: list, suggestions: list) -> bool:
        """检测系统停机"""
        if data.pump_status == "off" and data.outlet_temp <= data.ambient_temp:
            if data.irradiance and data.irradiance < 100:
                # 夜间或低光照，正常情况
                return False
            details.append("系统处于停机状态，无加热输出")
            suggestions.append("检查系统电源和控制状态")
            return True
        return False
    
    @staticmethod
    def _determine_primary_fault(checks: list[bool], data: ValidatedSensorData) -> FaultType:
        """确定主要故障类型"""
        if not any(checks):
            return FaultType.NONE
        
        # 优先级判断
        if data.pump_status == "off":
            if data.irradiance and data.irradiance > DIAGNOSIS_THRESHOLDS["pump_on_irradiance"]:
                return FaultType.PUMP_FAILURE
        
        temp_rise = data.outlet_temp - data.inlet_temp
        if temp_rise < DIAGNOSIS_THRESHOLDS["temp_rise_min"]:
            if data.outlet_temp < data.ambient_temp + 3:
                return FaultType.LOW_HEATING
        
        if data.outlet_temp > DIAGNOSIS_THRESHOLDS["temp_max"]:
            return FaultType.TEMPERATURE_ANOMALY
        
        if data.irradiance and data.irradiance > DIAGNOSIS_THRESHOLDS["high_irradiance"]:
            if temp_rise < 10:
                return FaultType.EFFICIENCY_LOW
        
        if data.pump_status == "off":
            return FaultType.SYSTEM_SHUTDOWN
        
        return FaultType.SENSOR_ERROR
    
    @staticmethod
    def _get_fault_description(fault: FaultType) -> str:
        """获取故障描述"""
        descriptions = {
            FaultType.NONE: "无故障",
            FaultType.LOW_HEATING: "加热不足",
            FaultType.PUMP_FAILURE: "循环泵故障",
            FaultType.TEMPERATURE_ANOMALY: "温度异常",
            FaultType.EFFICIENCY_LOW: "集热效率低",
            FaultType.SENSOR_ERROR: "传感器故障",
            FaultType.SYSTEM_SHUTDOWN: "系统停机",
        }
        return descriptions.get(fault, "未知故障")
    
    @staticmethod
    def _determine_risk_level(fault: FaultType, efficiency: int, data: ValidatedSensorData) -> RiskLevel:
        """确定风险等级"""
        if fault == FaultType.NONE:
            return RiskLevel.LOW
        
        if fault in [FaultType.TEMPERATURE_ANOMALY, FaultType.PUMP_FAILURE]:
            if data.outlet_temp > 95:
                return RiskLevel.HIGH
            return RiskLevel.MEDIUM
        
        if fault == FaultType.LOW_HEATING and efficiency < 40:
            return RiskLevel.HIGH
        
        if efficiency < 60:
            return RiskLevel.MEDIUM
        
        return RiskLevel.LOW


# ==================== 模块4: 输出格式化 ====================

class OutputFormatter:
    """输出格式化器 - 生成结构化JSON输出"""
    
    @classmethod
    def format_output(
        cls,
        is_valid: bool,
        validation_errors: list[str],
        diagnosis: Optional[DiagnosisResult] = None,
        language: str = "zh"
    ) -> dict:
        """
        格式化输出结果
        
        Args:
            is_valid: 数据是否有效
            validation_errors: 验证错误列表
            diagnosis: 诊断结果
            language: 输出语言
            
        Returns:
            dict: 结构化JSON字典
        """
        if not is_valid:
            return cls._format_error_output(validation_errors, language)
        
        return cls._format_success_output(diagnosis, language)
    
    @classmethod
    def _format_error_output(cls, errors: list[str], language: str) -> dict:
        """格式化错误输出"""
        if language == "zh":
            return {
                "alert_type": AlertType.ERROR.value,
                "fault": FaultType.SENSOR_ERROR.value,
                "fault_description": "数据验证失败",
                "risk_level": RiskLevel.HIGH.value,
                "diagnosis": "；".join(errors),
                "suggestion": "请检查输入数据格式和完整性",
                "language": language,
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "validation_errors": errors
            }
        else:
            return {
                "alert_type": AlertType.ERROR.value,
                "fault": FaultType.SENSOR_ERROR.value,
                "fault_description": "Data validation failed",
                "risk_level": RiskLevel.HIGH.value,
                "diagnosis": "; ".join(errors),
                "suggestion": "Please check input data format and completeness",
                "language": language,
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "validation_errors": errors
            }
    
    @classmethod
    def _format_success_output(cls, diagnosis: DiagnosisResult, language: str) -> dict:
        """格式化成功输出"""
        # 确定告警类型
        alert_type = cls._determine_alert_type(diagnosis)
        
        if language == "zh":
            result = {
                "alert_type": alert_type.value,
                "fault": diagnosis.fault.value,
                "fault_description": diagnosis.fault_description,
                "risk_level": diagnosis.risk_level.value,
                "diagnosis": "；".join(diagnosis.diagnosis_details),
                "suggestion": "；".join(diagnosis.suggestions) if diagnosis.suggestions else "系统运行正常，无需特别处理",
                "language": language,
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "metrics": {
                    "temp_rise_celsius": round(diagnosis.temp_rise, 2),
                    "efficiency_score": diagnosis.efficiency_score,
                }
            }
        else:
            result = {
                "alert_type": alert_type.value,
                "fault": diagnosis.fault.value,
                "fault_description": diagnosis.fault_description,
                "risk_level": diagnosis.risk_level.value,
                "diagnosis": "; ".join(diagnosis.diagnosis_details),
                "suggestion": "; ".join(diagnosis.suggestions) if diagnosis.suggestions else "System operating normally",
                "language": language,
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "metrics": {
                    "temp_rise_celsius": round(diagnosis.temp_rise, 2),
                    "efficiency_score": diagnosis.efficiency_score,
                }
            }
        
        return result
    
    @staticmethod
    def _determine_alert_type(diagnosis: DiagnosisResult) -> AlertType:
        """确定告警类型"""
        if diagnosis.fault == FaultType.NONE:
            return AlertType.NORMAL
        
        if diagnosis.risk_level == RiskLevel.HIGH:
            return AlertType.CRITICAL
        elif diagnosis.risk_level == RiskLevel.MEDIUM:
            return AlertType.WARNING
        else:
            return AlertType.NORMAL


# ==================== 主函数 ====================

def analyze_health(sensor_data: dict, language: str = "zh") -> dict:
    """
    分析太阳能热水器健康状态
    
    该函数接收传感器数据，执行完整的数据验证、故障诊断和输出格式化流程，
    返回结构化的JSON格式诊断结果。
    
    Args:
        sensor_data: 传感器数据字典，必需字段包括:
            - inlet_temp: 进水温度 (float)
            - outlet_temp: 出水温度 (float)
            - pump_status: 泵状态 (str: "on"/"off")
            - ambient_temp: 环境温度 (float)
            - time: 时间戳 (str)
            可选字段:
            - irradiance: 光照强度 (float)
            - pressure: 管路压力 (float)
            - flow_rate: 流量 (float)
            - water_level: 水位 (float)
        language: 输出语言 ("zh" 中文, "en" 英文)
        
    Returns:
        dict: 结构化JSON字典，包含以下字段:
            - alert_type: 告警类型 (normal/warning/error/critical)
            - fault: 故障代码 (none/low_heating/pump_failure/...)
            - fault_description: 故障描述
            - risk_level: 风险等级 (low/medium/high)
            - diagnosis: 详细诊断信息
            - suggestion: 处理建议
            - language: 输出语言
            - timestamp: 时间戳
            - status: 处理状态 (success/error)
            - metrics: 性能指标 (temp_rise_celsius, efficiency_score)
            - validation_errors: 验证错误列表 (如有)
    
    Example:
        >>> sensor_data = {
        ...     "inlet_temp": 15.0,
        ...     "outlet_temp": 22.0,
        ...     "pump_status": "off",
        ...     "ambient_temp": 20.0,
        ...     "time": "2024-04-05 14:30:00",
        ...     "irradiance": 800
        ... }
        >>> result = analyze_health(sensor_data)
        >>> print(json.dumps(result, indent=2, ensure_ascii=False))
    """
    # 步骤1: 数据验证
    validated_data = DataValidator.validate(sensor_data)
    
    if not validated_data.is_valid:
        # 验证失败，返回错误输出
        return OutputFormatter.format_output(
            is_valid=False,
            validation_errors=validated_data.validation_errors,
            language=language
        )
    
    # 步骤2: 执行诊断
    diagnosis_result = DiagnosisEngine.diagnose(validated_data)
    
    # 步骤3: 格式化输出
    return OutputFormatter.format_output(
        is_valid=True,
        validation_errors=[],
        diagnosis=diagnosis_result,
        language=language
    )


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试用例1: 正常数据
    print("=" * 60)
    print("测试用例1: 正常数据")
    print("=" * 60)
    sensor_data_1 = {
        "inlet_temp": 15.0,
        "outlet_temp": 35.0,
        "pump_status": "on",
        "ambient_temp": 18.0,
        "time": "2024-04-05 14:30:00",
        "irradiance": 800
    }
    result_1 = analyze_health(sensor_data_1)
    print(json.dumps(result_1, indent=2, ensure_ascii=False))
    
    # 测试用例2: 加热不足 (用户示例 - 修改为温升低于阈值)
    print("\n" + "=" * 60)
    print("测试用例2: 加热不足 (用户示例)")
    print("=" * 60)
    sensor_data_2 = {
        "inlet_temp": 18.0,
        "outlet_temp": 22.0,  # 温升仅4°C，低于5°C阈值
        "pump_status": "off",
        "ambient_temp": 20.0,
        "time": "2024-04-05 14:30:00"
    }
    result_2 = analyze_health(sensor_data_2)
    print(json.dumps(result_2, indent=2, ensure_ascii=False))
    
    # 测试用例3: 泵故障
    print("\n" + "=" * 60)
    print("测试用例3: 泵故障 (高光照但泵未启动)")
    print("=" * 60)
    sensor_data_3 = {
        "inlet_temp": 20.0,
        "outlet_temp": 22.0,
        "pump_status": "off",
        "ambient_temp": 19.0,
        "time": "2024-04-05 12:00:00",
        "irradiance": 900
    }
    result_3 = analyze_health(sensor_data_3)
    print(json.dumps(result_3, indent=2, ensure_ascii=False))
    
    # 测试用例4: 缺失字段
    print("\n" + "=" * 60)
    print("测试用例4: 缺失字段")
    print("=" * 60)
    sensor_data_4 = {
        "inlet_temp": 15.0,
        "outlet_temp": 22.0,
        # 缺少 pump_status, ambient_temp, time
    }
    result_4 = analyze_health(sensor_data_4)
    print(json.dumps(result_4, indent=2, ensure_ascii=False))
    
    # 测试用例5: 类型错误
    print("\n" + "=" * 60)
    print("测试用例5: 类型错误")
    print("=" * 60)
    sensor_data_5 = {
        "inlet_temp": "invalid",
        "outlet_temp": 22.0,
        "pump_status": "off",
        "ambient_temp": 20.0,
        "time": "2024-04-05 14:30:00"
    }
    result_5 = analyze_health(sensor_data_5)
    print(json.dumps(result_5, indent=2, ensure_ascii=False))
    
    # 测试用例6: 英文输出
    print("\n" + "=" * 60)
    print("测试用例6: 英文输出")
    print("=" * 60)
    result_6 = analyze_health(sensor_data_2, language="en")
    print(json.dumps(result_6, indent=2, ensure_ascii=False))

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=64)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class UserInfo(BaseModel):
    id: int
    username: str
    role: str


class DeviceCreate(BaseModel):
    device_code: str = Field(min_length=3, max_length=64)
    name: str = Field(min_length=2, max_length=128)
    location: str = Field(min_length=2, max_length=255)
    device_type: str = Field(default="solar_heater", min_length=2, max_length=64)
    status: str = Field(default="active", pattern="^(active|inactive)$")


class DeviceUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    location: str = Field(min_length=2, max_length=255)
    device_type: str = Field(default="solar_heater", min_length=2, max_length=64)
    status: str = Field(default="active", pattern="^(active|inactive)$")


class DeviceOut(BaseModel):
    id: int
    device_code: str
    name: str
    location: str
    device_type: str
    status: str
    installed_at: datetime


class SensorDataCreate(BaseModel):
    device_id: int = Field(gt=0)
    temperature_in: float = Field(ge=0, le=100)
    temperature_out: float = Field(ge=0, le=120)
    pressure: float = Field(ge=0, le=2)
    flow_rate: float = Field(ge=0, le=100)
    solar_irradiance: float = Field(ge=0, le=1500)
    water_level: int = Field(ge=0, le=100)
    pump_status: str = Field(pattern="^(on|off)$")

    @field_validator("temperature_out")
    @classmethod
    def output_temp_must_not_lower_than_input(cls, value: float, info):
        input_temp = info.data.get("temperature_in")
        if input_temp is not None and value + 0.5 < input_temp:
            raise ValueError("出水温度不能明显低于进水温度")
        return value


class SensorDataOut(BaseModel):
    id: int
    device_id: int
    temperature_in: float
    temperature_out: float
    pressure: float
    flow_rate: float
    solar_irradiance: float
    water_level: int
    pump_status: str
    collected_at: datetime


class HealthAssessmentOut(BaseModel):
    id: int
    device_id: int
    health_score: int
    risk_level: str
    diagnosis: str
    assessment_time: datetime


class AlarmOut(BaseModel):
    id: int
    device_id: int
    device_name: str
    level: str
    title: str
    content: str
    status: str
    created_at: datetime
    resolved_at: datetime | None


class AlarmResolve(BaseModel):
    status: str = Field(pattern="^(resolved)$")


class DashboardSummary(BaseModel):
    total_devices: int
    active_devices: int
    high_risk_devices: int
    unresolved_alarms: int
    avg_health_score: float


class DashboardTrendItem(BaseModel):
    collected_at: datetime
    temperature_out: float
    pressure: float
    flow_rate: float
    health_score: int


class ReportItem(BaseModel):
    date: str
    avg_health_score: float
    high_risk_count: int
    alarm_count: int

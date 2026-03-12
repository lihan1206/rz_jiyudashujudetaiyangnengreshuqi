export interface TokenResponse {
  access_token: string
  token_type: string
  username: string
  role: string
}

export interface DeviceItem {
  id: number
  device_code: string
  name: string
  location: string
  device_type: string
  status: 'active' | 'inactive'
  installed_at: string
}

export interface DashboardSummary {
  total_devices: number
  active_devices: number
  high_risk_devices: number
  unresolved_alarms: number
  avg_health_score: number
}

export interface TrendItem {
  collected_at: string
  temperature_out: number
  pressure: number
  flow_rate: number
  health_score: number
}

export interface AlarmItem {
  id: number
  device_id: number
  device_name: string
  level: string
  title: string
  content: string
  status: 'unresolved' | 'resolved'
  created_at: string
  resolved_at: string | null
}

export interface ReportItem {
  date: string
  avg_health_score: number
  high_risk_count: number
  alarm_count: number
}

export interface SensorPayload {
  device_id: number
  temperature_in: number
  temperature_out: number
  pressure: number
  flow_rate: number
  solar_irradiance: number
  water_level: number
  pump_status: 'on' | 'off'
}

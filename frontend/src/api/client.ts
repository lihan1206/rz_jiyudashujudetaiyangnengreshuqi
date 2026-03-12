import axios from 'axios'

import {
  AlarmItem,
  DashboardSummary,
  DeviceItem,
  ReportItem,
  SensorPayload,
  TokenResponse,
  TrendItem,
} from './types'

const client = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export async function login(username: string, password: string): Promise<TokenResponse> {
  const response = await client.post<TokenResponse>('/auth/login', { username, password })
  return response.data
}

export async function fetchSummary(): Promise<DashboardSummary> {
  const response = await client.get<DashboardSummary>('/dashboard/summary')
  return response.data
}

export async function fetchDevices(): Promise<DeviceItem[]> {
  const response = await client.get<DeviceItem[]>('/devices')
  return response.data
}

export async function createDevice(payload: Omit<DeviceItem, 'id' | 'installed_at'>): Promise<DeviceItem> {
  const response = await client.post<DeviceItem>('/devices', payload)
  return response.data
}

export async function updateDevice(
  id: number,
  payload: Omit<DeviceItem, 'id' | 'device_code' | 'installed_at'>,
): Promise<DeviceItem> {
  const response = await client.put<DeviceItem>(`/devices/${id}`, payload)
  return response.data
}

export async function deleteDevice(id: number): Promise<void> {
  await client.delete(`/devices/${id}`)
}

export async function fetchTrend(deviceId: number): Promise<TrendItem[]> {
  const response = await client.get<TrendItem[]>(`/dashboard/trend/${deviceId}`)
  return response.data
}

export async function fetchAlarms(status?: 'unresolved' | 'resolved'): Promise<AlarmItem[]> {
  const response = await client.get<AlarmItem[]>('/alarms', { params: status ? { status } : {} })
  return response.data
}

export async function resolveAlarm(id: number): Promise<AlarmItem> {
  const response = await client.patch<AlarmItem>(`/alarms/${id}`, { status: 'resolved' })
  return response.data
}

export async function fetchWeeklyReport(): Promise<ReportItem[]> {
  const response = await client.get<ReportItem[]>('/reports/weekly')
  return response.data
}

export async function ingestSensorData(payload: SensorPayload): Promise<void> {
  await client.post('/telemetry', payload)
}

export function normalizeError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return String(error.response?.data?.detail ?? '请求失败，请稍后重试')
  }
  return '系统异常，请联系管理员'
}

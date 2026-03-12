import { Button, Card, Form, InputNumber, Select, Space, Typography, notification } from 'antd'
import { useState } from 'react'
import { z } from 'zod'

import { ingestSensorData, normalizeError } from '../api/client'
import { DeviceItem } from '../api/types'

const sensorSchema = z
  .object({
    device_id: z.number().int().positive(),
    temperature_in: z.number().min(0).max(100),
    temperature_out: z.number().min(0).max(120),
    pressure: z.number().min(0).max(2),
    flow_rate: z.number().min(0).max(100),
    solar_irradiance: z.number().min(0).max(1500),
    water_level: z.number().int().min(0).max(100),
    pump_status: z.enum(['on', 'off']),
  })
  .superRefine((value, ctx) => {
    if (value.temperature_out + 0.5 < value.temperature_in) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: '出水温度不能明显低于进水温度',
        path: ['temperature_out'],
      })
    }
  })

interface TelemetryPageProps {
  devices: DeviceItem[]
  onSubmitted: () => Promise<void>
}

export function TelemetryPage({ devices, onSubmitted }: TelemetryPageProps): JSX.Element {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [api, contextHolder] = notification.useNotification()

  const handleSubmit = async (): Promise<void> => {
    try {
      const values = await form.validateFields()
      const parsed = sensorSchema.parse({
        ...values,
        device_id: Number(values.device_id),
        temperature_in: Number(values.temperature_in),
        temperature_out: Number(values.temperature_out),
        pressure: Number(values.pressure),
        flow_rate: Number(values.flow_rate),
        solar_irradiance: Number(values.solar_irradiance),
        water_level: Number(values.water_level),
      })

      setLoading(true)
      await ingestSensorData(parsed)
      api.success({
        message: '采集数据上报成功',
        description: '系统已自动完成健康度评估与故障诊断。',
      })
      form.resetFields()
      await onSubmitted()
    } catch (error) {
      const message =
        error instanceof z.ZodError ? error.errors[0]?.message || '采集参数不合法' : normalizeError(error)
      api.error({ message: '上报失败', description: message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <section>
      {contextHolder}
      <Card className="glass-card">
        <Space direction="vertical" style={{ width: '100%' }}>
          <Typography.Title level={4} style={{ margin: 0 }}>
            数据采集上报
          </Typography.Title>
          <Typography.Text type="secondary">
            用于模拟设备通过 HTTP 上报实时传感器数据，提交后会写入数据库并生成评估记录。
          </Typography.Text>

          <Form
            form={form}
            layout="vertical"
            initialValues={{ pump_status: 'on', pressure: 0.3, flow_rate: 12, water_level: 80 }}
          >
            <Form.Item label="选择设备" name="device_id" rules={[{ required: true, message: '请选择设备' }]}>
              <Select
                placeholder="请选择设备"
                options={devices.map((item) => ({ value: item.id, label: `${item.name}（${item.device_code}）` }))}
              />
            </Form.Item>
            <Form.Item label="进水温度(°C)" name="temperature_in" rules={[{ required: true, message: '请输入进水温度' }]}>
              <InputNumber style={{ width: '100%' }} min={0} max={100} />
            </Form.Item>
            <Form.Item label="出水温度(°C)" name="temperature_out" rules={[{ required: true, message: '请输入出水温度' }]}>
              <InputNumber style={{ width: '100%' }} min={0} max={120} />
            </Form.Item>
            <Form.Item label="管路压力(MPa)" name="pressure" rules={[{ required: true, message: '请输入压力' }]}>
              <InputNumber style={{ width: '100%' }} min={0} max={2} step={0.01} />
            </Form.Item>
            <Form.Item label="循环流量(L/min)" name="flow_rate" rules={[{ required: true, message: '请输入流量' }]}>
              <InputNumber style={{ width: '100%' }} min={0} max={100} step={0.1} />
            </Form.Item>
            <Form.Item
              label="太阳辐照强度(W/m²)"
              name="solar_irradiance"
              rules={[{ required: true, message: '请输入太阳辐照强度' }]}
            >
              <InputNumber style={{ width: '100%' }} min={0} max={1500} />
            </Form.Item>
            <Form.Item label="水位(%)" name="water_level" rules={[{ required: true, message: '请输入水位' }]}>
              <InputNumber style={{ width: '100%' }} min={0} max={100} />
            </Form.Item>
            <Form.Item label="循环泵状态" name="pump_status" rules={[{ required: true, message: '请选择状态' }]}>
              <Select options={[{ value: 'on', label: '开启' }, { value: 'off', label: '关闭' }]} />
            </Form.Item>

            <Button type="primary" onClick={handleSubmit} loading={loading}>
              提交采集数据
            </Button>
          </Form>
        </Space>
      </Card>
    </section>
  )
}

import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { Button, Card, Form, Input, Space, Typography, notification } from 'antd'
import { useState } from 'react'
import { z } from 'zod'

import { login, normalizeError } from '../api/client'

const loginSchema = z.object({
  username: z.string().min(3, '用户名至少 3 个字符'),
  password: z.string().min(6, '密码至少 6 个字符'),
})

interface LoginPageProps {
  onLoginSuccess: () => void
}

export function LoginPage({ onLoginSuccess }: LoginPageProps): JSX.Element {
  const [api, contextHolder] = notification.useNotification()
  const [loading, setLoading] = useState(false)

  const onFinish = async (values: { username: string; password: string }): Promise<void> => {
    try {
      const parsed = loginSchema.parse(values)
      setLoading(true)
      const data = await login(parsed.username, parsed.password)
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('username', data.username)
      onLoginSuccess()
      api.success({ message: '登录成功', description: `欢迎回来，${data.username}` })
    } catch (error) {
      const message =
        error instanceof z.ZodError ? error.errors[0]?.message || '输入信息不完整' : normalizeError(error)
      api.error({ message: '登录失败', description: message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-wrapper">
      {contextHolder}
      <Card className="login-card" bordered={false}>
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <Typography.Title level={3} style={{ marginBottom: 0 }}>
            基于大数据的太阳能热水器健康度评估与故障诊断平台
          </Typography.Title>
          <Typography.Text type="secondary">请输入账号密码进入系统</Typography.Text>
        </Space>

        <Form layout="vertical" style={{ marginTop: 20 }} onFinish={onFinish}>
          <Form.Item label="用户名" name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="admin" />
          </Form.Item>
          <Form.Item label="密码" name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="请输入密码" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            登录系统
          </Button>
        </Form>
      </Card>
    </div>
  )
}

import { Avatar, Button, ConfigProvider, Layout, Menu, Space, Spin, Typography, notification, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import {
  AlertOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  LogoutOutlined,
  ToolOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { useEffect, useMemo, useState } from 'react'

import { fetchDevices, normalizeError } from './api/client'
import { DeviceItem } from './api/types'
import { ErrorBoundary } from './components/ErrorBoundary'
import { AlarmPage } from './pages/AlarmPage'
import { DashboardPage } from './pages/DashboardPage'
import { DevicePage } from './pages/DevicePage'
import { LoginPage } from './pages/LoginPage'
import { TelemetryPage } from './pages/TelemetryPage'

const { Header, Content, Footer, Sider } = Layout

export default function App(): JSX.Element {
  const [authed, setAuthed] = useState(Boolean(localStorage.getItem('access_token')))
  const [activeKey, setActiveKey] = useState('dashboard')
  const [devices, setDevices] = useState<DeviceItem[]>([])
  const [loadingDevices, setLoadingDevices] = useState(false)
  const [api, contextHolder] = notification.useNotification()

  const username = localStorage.getItem('username') || '管理员'

  const loadDevices = async (): Promise<void> => {
    try {
      setLoadingDevices(true)
      const list = await fetchDevices()
      setDevices(list)
    } catch (error) {
      api.error({ message: '设备数据加载失败', description: normalizeError(error) })
    } finally {
      setLoadingDevices(false)
    }
  }

  useEffect(() => {
    if (authed) {
      void loadDevices()
    }
  }, [authed])

  const logout = (): void => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('username')
    setAuthed(false)
    setDevices([])
    setActiveKey('dashboard')
  }

  const contentNode = useMemo(() => {
    if (!authed) {
      return <LoginPage onLoginSuccess={() => setAuthed(true)} />
    }

    if (loadingDevices && devices.length === 0) {
      return (
        <Space align="center" direction="vertical" style={{ width: '100%', marginTop: 120 }}>
          <Spin size="large" />
          <Typography.Text type="secondary">正在同步设备数据...</Typography.Text>
        </Space>
      )
    }

    if (activeKey === 'dashboard') {
      return <DashboardPage devices={devices} />
    }

    if (activeKey === 'devices') {
      return <DevicePage devices={devices} loading={loadingDevices} onRefresh={loadDevices} />
    }

    if (activeKey === 'alarms') {
      return <AlarmPage />
    }

    if (activeKey === 'telemetry') {
      return <TelemetryPage devices={devices} onSubmitted={loadDevices} />
    }

    return null
  }, [activeKey, authed, devices, loadingDevices])

  if (!authed) {
    return (
      <ConfigProvider locale={zhCN} theme={{ algorithm: theme.defaultAlgorithm }}>
        {contextHolder}
        <ErrorBoundary>{contentNode}</ErrorBoundary>
      </ConfigProvider>
    )
  }

  return (
    <ConfigProvider locale={zhCN} theme={{ algorithm: theme.defaultAlgorithm, token: { colorPrimary: '#0b7285' } }}>
      {contextHolder}
      <ErrorBoundary>
        <Layout className="app-root">
          <Sider breakpoint="lg" collapsedWidth="0" className="app-sider">
            <div className="brand">基于大数据的太阳能热水器健康度评估与故障诊断平台</div>
            <Menu
              mode="inline"
              theme="light"
              selectedKeys={[activeKey]}
              onClick={({ key }) => setActiveKey(key)}
              items={[
                { key: 'dashboard', icon: <DashboardOutlined />, label: '监控大屏' },
                { key: 'devices', icon: <ToolOutlined />, label: '设备管理' },
                { key: 'alarms', icon: <AlertOutlined />, label: '告警中心' },
                { key: 'telemetry', icon: <ExperimentOutlined />, label: '数据采集' },
              ]}
            />
          </Sider>

          <Layout>
            <Header className="app-header">
              <header className="header-inner">
                <Typography.Title level={5} style={{ margin: 0 }}>
                  基于大数据的健康评估与故障诊断
                </Typography.Title>
                <Space>
                  <Avatar icon={<UserOutlined />} />
                  <Typography.Text>{username}</Typography.Text>
                  <Button icon={<LogoutOutlined />} onClick={logout}>
                    退出登录
                  </Button>
                </Space>
              </header>
            </Header>

            <Content className="app-content">
              <main>{contentNode}</main>
            </Content>

            <Footer className="app-footer">
              <footer>太阳能热水器健康度评估平台 · 实时监控 · 风险预警 · 预测性维护</footer>
            </Footer>
          </Layout>
        </Layout>
      </ErrorBoundary>
    </ConfigProvider>
  )
}

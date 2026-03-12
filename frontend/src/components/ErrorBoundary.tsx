import { Alert, Button, Space, Typography } from 'antd'
import React from 'react'

interface State {
  hasError: boolean
  message: string
}

export class ErrorBoundary extends React.Component<React.PropsWithChildren, State> {
  public state: State = { hasError: false, message: '' }

  public static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      message: error.message || '页面发生异常',
    }
  }

  public componentDidCatch(error: Error): void {
    void error
  }

  private reloadPage = (): void => {
    window.location.reload()
  }

  public render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        <Space direction="vertical" style={{ width: '100%', marginTop: 48 }} align="center">
          <Alert
            type="error"
            message="页面加载失败"
            description={this.state.message || '请稍后重试，或联系管理员处理。'}
            showIcon
          />
          <Typography.Text type="secondary">系统已阻止错误继续扩散，数据不会丢失。</Typography.Text>
          <Button type="primary" onClick={this.reloadPage}>
            刷新页面
          </Button>
        </Space>
      )
    }

    return this.props.children
  }
}

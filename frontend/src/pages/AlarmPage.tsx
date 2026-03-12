import { CheckCircleOutlined } from '@ant-design/icons'
import { Button, Card, Segmented, Space, Table, Tag, Typography, notification } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useMemo, useState } from 'react'

import { fetchAlarms, normalizeError, resolveAlarm } from '../api/client'
import { AlarmItem } from '../api/types'

export function AlarmPage(): JSX.Element {
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<'all' | 'unresolved' | 'resolved'>('all')
  const [data, setData] = useState<AlarmItem[]>([])
  const [api, contextHolder] = notification.useNotification()

  const loadData = async (): Promise<void> => {
    try {
      setLoading(true)
      const list = await fetchAlarms(status === 'all' ? undefined : status)
      setData(list)
    } catch (error) {
      api.error({ message: '告警数据加载失败', description: normalizeError(error) })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [status])

  const handleResolve = async (id: number): Promise<void> => {
    try {
      await resolveAlarm(id)
      api.success({ message: '告警已标记为已处理' })
      await loadData()
    } catch (error) {
      api.error({ message: '处理失败', description: normalizeError(error) })
    }
  }

  const columns: ColumnsType<AlarmItem> = useMemo(
    () => [
      {
        title: '设备',
        dataIndex: 'device_name',
        key: 'device_name',
      },
      {
        title: '级别',
        dataIndex: 'level',
        key: 'level',
        render: (value: string) => (
          <Tag color={value === '严重' ? 'red' : value === '警告' ? 'orange' : 'blue'}>{value}</Tag>
        ),
      },
      {
        title: '告警标题',
        dataIndex: 'title',
        key: 'title',
      },
      {
        title: '详细说明',
        dataIndex: 'content',
        key: 'content',
        ellipsis: true,
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        render: (value: AlarmItem['status']) =>
          value === 'resolved' ? <Tag color="green">已处理</Tag> : <Tag color="volcano">未处理</Tag>,
      },
      {
        title: '操作',
        key: 'action',
        render: (_, record) => (
          <Button
            type="link"
            icon={<CheckCircleOutlined />}
            disabled={record.status === 'resolved'}
            onClick={() => handleResolve(record.id)}
          >
            标记已处理
          </Button>
        ),
      },
    ],
    [status],
  )

  return (
    <section>
      {contextHolder}
      <Card className="glass-card">
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Typography.Title level={4} style={{ margin: 0 }}>
              告警中心
            </Typography.Title>
            <Segmented
              value={status}
              onChange={(value) => setStatus(value as typeof status)}
              options={[
                { label: '全部', value: 'all' },
                { label: '未处理', value: 'unresolved' },
                { label: '已处理', value: 'resolved' },
              ]}
            />
          </Space>

          <Table<AlarmItem>
            rowKey="id"
            loading={loading}
            dataSource={data}
            columns={columns}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 960 }}
          />
        </Space>
      </Card>
    </section>
  )
}

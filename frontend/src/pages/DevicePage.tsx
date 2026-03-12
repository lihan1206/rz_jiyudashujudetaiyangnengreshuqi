import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons'
import {
  Button,
  Card,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  notification,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useMemo, useState } from 'react'
import { z } from 'zod'

import { createDevice, deleteDevice, normalizeError, updateDevice } from '../api/client'
import { DeviceItem } from '../api/types'

const deviceSchema = z.object({
  device_code: z.string().min(3, '设备编号至少 3 个字符').max(64),
  name: z.string().min(2, '设备名称至少 2 个字符').max(128),
  location: z.string().min(2, '安装位置至少 2 个字符').max(255),
  device_type: z.string().min(2, '设备类型不能为空').max(64),
  status: z.enum(['active', 'inactive']),
})

interface DevicePageProps {
  devices: DeviceItem[]
  loading: boolean
  onRefresh: () => Promise<void>
}

export function DevicePage({ devices, loading, onRefresh }: DevicePageProps): JSX.Element {
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<DeviceItem | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [api, contextHolder] = notification.useNotification()
  const [form] = Form.useForm()

  const openCreate = (): void => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ status: 'active', device_type: 'solar_heater' })
    setOpen(true)
  }

  const openEdit = (record: DeviceItem): void => {
    setEditing(record)
    form.setFieldsValue(record)
    setOpen(true)
  }

  const closeModal = (): void => {
    setOpen(false)
    setEditing(null)
    form.resetFields()
  }

  const handleSubmit = async (): Promise<void> => {
    try {
      const values = await form.validateFields()
      const parsed = deviceSchema.parse(values)

      setSubmitting(true)
      if (editing) {
        await updateDevice(editing.id, {
          name: parsed.name,
          location: parsed.location,
          device_type: parsed.device_type,
          status: parsed.status,
        })
        api.success({ message: '设备更新成功' })
      } else {
        await createDevice(parsed)
        api.success({ message: '设备创建成功' })
      }
      closeModal()
      await onRefresh()
    } catch (error) {
      const message =
        error instanceof z.ZodError ? error.errors[0]?.message || '输入参数不正确' : normalizeError(error)
      api.error({ message: editing ? '设备更新失败' : '设备创建失败', description: message })
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (id: number): Promise<void> => {
    try {
      await deleteDevice(id)
      api.success({ message: '设备删除成功' })
      await onRefresh()
    } catch (error) {
      api.error({ message: '设备删除失败', description: normalizeError(error) })
    }
  }

  const columns: ColumnsType<DeviceItem> = useMemo(
    () => [
      {
        title: '设备编号',
        dataIndex: 'device_code',
        key: 'device_code',
      },
      {
        title: '设备名称',
        dataIndex: 'name',
        key: 'name',
      },
      {
        title: '安装位置',
        dataIndex: 'location',
        key: 'location',
      },
      {
        title: '类型',
        dataIndex: 'device_type',
        key: 'device_type',
      },
      {
        title: '状态',
        key: 'status',
        render: (_, record) => (
          <Tag color={record.status === 'active' ? 'green' : 'default'}>
            {record.status === 'active' ? '在线' : '停用'}
          </Tag>
        ),
      },
      {
        title: '操作',
        key: 'action',
        render: (_, record) => (
          <Space>
            <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(record)}>
              编辑
            </Button>
            <Popconfirm
              title="确认删除该设备吗？"
              description="删除后会同时移除该设备的采集数据、评估结果和历史告警。"
              okText="确认删除"
              cancelText="取消"
              okButtonProps={{ danger: true }}
              onConfirm={() => handleDelete(record.id)}
            >
              <Button type="link" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [api, onRefresh],
  )

  return (
    <section>
      {contextHolder}
      <Card className="glass-card">
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Typography.Title level={4} style={{ margin: 0 }}>
              设备管理
            </Typography.Title>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              新增设备
            </Button>
          </Space>

          <Table<DeviceItem>
            rowKey="id"
            columns={columns}
            dataSource={devices}
            loading={loading}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 960 }}
          />
        </Space>
      </Card>

      <Modal
        title={editing ? '编辑设备' : '新增设备'}
        open={open}
        onCancel={closeModal}
        onOk={handleSubmit}
        confirmLoading={submitting}
        okText={editing ? '保存修改' : '创建设备'}
        cancelText="取消"
      >
        <Form layout="vertical" form={form}>
          <Form.Item label="设备编号" name="device_code" rules={[{ required: true, message: '请输入设备编号' }]}>
            <Input disabled={Boolean(editing)} />
          </Form.Item>
          <Form.Item label="设备名称" name="name" rules={[{ required: true, message: '请输入设备名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="安装位置" name="location" rules={[{ required: true, message: '请输入安装位置' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="设备类型" name="device_type" rules={[{ required: true, message: '请输入设备类型' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="设备状态" name="status" rules={[{ required: true, message: '请选择设备状态' }]}>
            <Select
              options={[
                { label: '在线', value: 'active' },
                { label: '停用', value: 'inactive' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </section>
  )
}

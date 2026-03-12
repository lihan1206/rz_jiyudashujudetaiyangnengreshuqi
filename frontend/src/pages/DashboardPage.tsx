import { Card, Col, Empty, Row, Skeleton, Statistic, Typography, notification } from 'antd'
import ReactECharts from 'echarts-for-react'
import { useEffect, useMemo, useState } from 'react'

import { fetchSummary, fetchTrend, fetchWeeklyReport, normalizeError } from '../api/client'
import { DashboardSummary, DeviceItem, ReportItem, TrendItem } from '../api/types'

interface DashboardPageProps {
  devices: DeviceItem[]
}

export function DashboardPage({ devices }: DashboardPageProps): JSX.Element {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [trend, setTrend] = useState<TrendItem[]>([])
  const [report, setReport] = useState<ReportItem[]>([])
  const [loading, setLoading] = useState(false)
  const [api, contextHolder] = notification.useNotification()

  useEffect(() => {
    const run = async (): Promise<void> => {
      try {
        setLoading(true)
        const [summaryData, reportData] = await Promise.all([fetchSummary(), fetchWeeklyReport()])
        setSummary(summaryData)
        setReport(reportData)

        if (devices.length > 0) {
          const trendData = await fetchTrend(devices[0].id)
          setTrend(trendData)
        }
      } catch (error) {
        api.error({ message: '大屏数据加载失败', description: normalizeError(error) })
      } finally {
        setLoading(false)
      }
    }
    void run()
  }, [api, devices])

  const trendOption = useMemo(() => {
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['出水温度', '健康评分'] },
      xAxis: {
        type: 'category',
        data: trend.map((item) => item.collected_at.slice(11, 16)),
      },
      yAxis: [
        { type: 'value', name: '温度(°C)' },
        { type: 'value', name: '评分', min: 0, max: 100 },
      ],
      series: [
        {
          name: '出水温度',
          type: 'line',
          smooth: true,
          data: trend.map((item) => item.temperature_out),
          areaStyle: { opacity: 0.15 },
        },
        {
          name: '健康评分',
          type: 'line',
          smooth: true,
          yAxisIndex: 1,
          data: trend.map((item) => item.health_score),
        },
      ],
    }
  }, [trend])

  const reportOption = useMemo(() => {
    return {
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: report.map((item) => item.date.slice(5)),
      },
      yAxis: [{ type: 'value', name: '评分' }, { type: 'value', name: '数量' }],
      legend: { data: ['平均健康评分', '高风险次数', '告警次数'] },
      series: [
        {
          name: '平均健康评分',
          type: 'bar',
          data: report.map((item) => item.avg_health_score),
        },
        {
          name: '高风险次数',
          type: 'line',
          yAxisIndex: 1,
          data: report.map((item) => item.high_risk_count),
        },
        {
          name: '告警次数',
          type: 'line',
          yAxisIndex: 1,
          data: report.map((item) => item.alarm_count),
        },
      ],
    }
  }, [report])

  return (
    <section>
      {contextHolder}
      <Typography.Title level={4}>监控大屏</Typography.Title>
      <Typography.Paragraph type="secondary">展示当前设备运行状态、健康评分趋势与近 7 日风险变化。</Typography.Paragraph>

      {loading || !summary ? (
        <Skeleton active paragraph={{ rows: 8 }} />
      ) : (
        <>
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12} lg={6}>
              <Card className="glass-card">
                <Statistic title="设备总数" value={summary.total_devices} />
              </Card>
            </Col>
            <Col xs={24} md={12} lg={6}>
              <Card className="glass-card">
                <Statistic title="在线设备" value={summary.active_devices} valueStyle={{ color: '#2f9e44' }} />
              </Card>
            </Col>
            <Col xs={24} md={12} lg={6}>
              <Card className="glass-card">
                <Statistic title="高风险设备" value={summary.high_risk_devices} valueStyle={{ color: '#d9480f' }} />
              </Card>
            </Col>
            <Col xs={24} md={12} lg={6}>
              <Card className="glass-card">
                <Statistic title="平均健康评分" value={summary.avg_health_score} suffix="分" precision={2} />
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginTop: 8 }}>
            <Col xs={24} lg={14}>
              <Card className="glass-card" title="实时趋势（默认首台设备）">
                {trend.length > 0 ? (
                  <ReactECharts option={trendOption} style={{ height: 320 }} />
                ) : (
                  <Empty description="暂无趋势数据" />
                )}
              </Card>
            </Col>
            <Col xs={24} lg={10}>
              <Card className="glass-card" title="近 7 日健康报告">
                {report.length > 0 ? (
                  <ReactECharts option={reportOption} style={{ height: 320 }} />
                ) : (
                  <Empty description="暂无报告数据" />
                )}
              </Card>
            </Col>
          </Row>
        </>
      )}
    </section>
  )
}

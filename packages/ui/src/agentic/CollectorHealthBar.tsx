'use client'

import * as React from 'react'
import { AlertTriangle, CheckCircle, RefreshCw, XCircle } from 'lucide-react'
import { Card, CardContent } from '../components/card'
import { Badge } from '../components/badge'
import { Button } from '../components/button'

export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy'

export interface CollectorHealthResult {
  collector_name: string
  status: HealthStatus
  checked_at: string
  sample_count: number
  error_message: string | null
  response_time_ms: number | null
}

export interface HealthCheckData {
  checked_at: string
  results: CollectorHealthResult[]
  summary: {
    total: number
    healthy: number
    degraded: number
    unhealthy: number
  }
}

export interface CollectorHealthBarProps {
  data: HealthCheckData | null
  isLoading?: boolean
  onRefresh?: () => void
  className?: string
}

const STATUS_CONFIG: Record<
  HealthStatus,
  {
    icon: React.ComponentType<{ className?: string }>
    color: string
    bgColor: string
    borderColor: string
    label: string
  }
> = {
  healthy: {
    icon: CheckCircle,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-l-green-500',
    label: '정상',
  },
  degraded: {
    icon: AlertTriangle,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-l-yellow-500',
    label: '저하',
  },
  unhealthy: {
    icon: XCircle,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-l-red-500',
    label: '오류',
  },
}

const COLLECTOR_LABELS: Record<string, string> = {
  onoffmix: 'OnOffMix',
  eventus: 'EventUs',
  festa: 'Festa',
  rss: 'RSS',
  eventbrite: 'Eventbrite',
  devevent: 'DevEvent',
}

function StatusIcon({ status, className }: { status: HealthStatus; className?: string }) {
  const config = STATUS_CONFIG[status]
  const Icon = config.icon
  return <Icon className={`${config.color} ${className || 'h-4 w-4'}`} />
}

function CollectorItem({ result }: { result: CollectorHealthResult }) {
  const config = STATUS_CONFIG[result.status]
  const label = COLLECTOR_LABELS[result.collector_name] || result.collector_name

  return (
    <div
      className={`flex items-center gap-2 rounded-md px-3 py-2 ${config.bgColor}`}
      title={result.error_message || undefined}
    >
      <StatusIcon status={result.status} />
      <span className="font-medium text-sm">{label}</span>
      <Badge variant="secondary" className="text-xs">
        {result.sample_count}건
      </Badge>
      {result.response_time_ms && (
        <span className="text-xs text-gray-500">{Math.round(result.response_time_ms)}ms</span>
      )}
    </div>
  )
}

export function CollectorHealthBar({
  data,
  isLoading,
  onRefresh,
  className,
}: CollectorHealthBarProps) {
  if (!data && !isLoading) {
    return null
  }

  // 전체 상태 결정
  const overallStatus: HealthStatus = React.useMemo(() => {
    if (!data) return 'healthy'
    if (data.summary.unhealthy > 0) return 'unhealthy'
    if (data.summary.degraded > 0) return 'degraded'
    return 'healthy'
  }, [data])

  const overallConfig = STATUS_CONFIG[overallStatus]

  return (
    <Card className={`border-l-4 ${overallConfig.borderColor} ${className || ''}`}>
      <CardContent className="py-3 px-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* 전체 상태 */}
            <div className="flex items-center gap-2">
              <StatusIcon status={overallStatus} className="h-5 w-5" />
              <span className="font-semibold">수집기 상태</span>
            </div>

            {/* 구분선 */}
            <div className="h-6 w-px bg-gray-200" />

            {/* 개별 수집기 상태 */}
            {isLoading ? (
              <div className="flex items-center gap-2 text-gray-500">
                <RefreshCw className="h-4 w-4 animate-spin" />
                <span className="text-sm">확인 중...</span>
              </div>
            ) : data ? (
              <div className="flex flex-wrap gap-2">
                {data.results.map(result => (
                  <CollectorItem key={result.collector_name} result={result} />
                ))}
              </div>
            ) : null}
          </div>

          {/* 새로고침 버튼 */}
          <div className="flex items-center gap-2">
            {data && (
              <span className="text-xs text-gray-500">
                마지막 확인: {new Date(data.checked_at).toLocaleTimeString('ko-KR')}
              </span>
            )}
            {onRefresh && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onRefresh}
                disabled={isLoading}
                className="h-8 w-8 p-0"
              >
                <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              </Button>
            )}
          </div>
        </div>

        {/* 경고/오류 메시지 */}
        {data && (data.summary.degraded > 0 || data.summary.unhealthy > 0) && (
          <div className="mt-2 pt-2 border-t border-gray-100">
            {data.results
              .filter(r => r.error_message)
              .map(r => (
                <div
                  key={r.collector_name}
                  className="flex items-start gap-2 text-sm text-gray-600"
                >
                  <StatusIcon status={r.status} className="h-4 w-4 mt-0.5" />
                  <span>
                    <strong>{COLLECTOR_LABELS[r.collector_name]}:</strong> {r.error_message}
                  </span>
                </div>
              ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

/**
 * ToolCallCard
 *
 * 도구 호출 상태 표시 카드
 * 에이전트가 외부 도구를 호출할 때 진행 상황 표시
 */

import * as React from 'react'
import { cn } from '@ax/utils'
import { Badge } from '../components/badge'
import { Loader2, CheckCircle, XCircle, Clock, ChevronDown, ChevronUp, Wrench } from 'lucide-react'

type ToolCallStatus = 'pending' | 'running' | 'completed' | 'error'

interface ToolCallCardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 도구 이름 */
  toolName: string
  /** 실행 상태 */
  status: ToolCallStatus
  /** 호출 인자 */
  args?: Record<string, unknown>
  /** 실행 결과 */
  result?: unknown
  /** 오류 메시지 */
  error?: string
  /** 실행 시간 (ms) */
  duration?: number
  /** 기본 접힘 상태 */
  defaultExpanded?: boolean
}

const statusConfig: Record<
  ToolCallStatus,
  { icon: React.ReactNode; label: string; className: string }
> = {
  pending: {
    icon: <Clock className="h-3.5 w-3.5" />,
    label: '대기 중',
    className: 'text-muted-foreground',
  },
  running: {
    icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
    label: '실행 중',
    className: 'text-blue-500',
  },
  completed: {
    icon: <CheckCircle className="h-3.5 w-3.5" />,
    label: '완료',
    className: 'text-green-500',
  },
  error: {
    icon: <XCircle className="h-3.5 w-3.5" />,
    label: '오류',
    className: 'text-red-500',
  },
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

function formatValue(value: unknown): string {
  if (value === null) return 'null'
  if (value === undefined) return 'undefined'
  if (typeof value === 'string') return value.length > 100 ? value.slice(0, 100) + '...' : value
  try {
    const str = JSON.stringify(value, null, 2)
    return str.length > 200 ? str.slice(0, 200) + '...' : str
  } catch {
    return String(value)
  }
}

const ToolCallCard = React.forwardRef<HTMLDivElement, ToolCallCardProps>(
  (
    {
      className,
      toolName,
      status,
      args,
      result,
      error,
      duration,
      defaultExpanded = false,
      ...props
    },
    ref
  ) => {
    const [expanded, setExpanded] = React.useState(defaultExpanded)
    const config = statusConfig[status]

    return (
      <div
        ref={ref}
        className={cn(
          'rounded-lg border bg-card text-card-foreground',
          status === 'running' && 'border-blue-200 dark:border-blue-800',
          status === 'error' && 'border-red-200 dark:border-red-800',
          className
        )}
        {...props}
      >
        {/* Header */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex w-full items-center justify-between p-3 text-left"
        >
          <div className="flex items-center gap-2">
            <Wrench className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium text-sm">{toolName}</span>
            <span className={cn('flex items-center gap-1', config.className)}>
              {config.icon}
              <span className="text-xs">{config.label}</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            {duration !== undefined && status === 'completed' && (
              <Badge variant="secondary" className="text-xs">
                {formatDuration(duration)}
              </Badge>
            )}
            {expanded ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
        </button>

        {/* Content */}
        {expanded && (
          <div className="border-t px-3 pb-3 pt-2 space-y-3">
            {/* Arguments */}
            {args && Object.keys(args).length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1">인자</p>
                <pre className="rounded bg-muted p-2 text-xs overflow-auto max-h-32">
                  {JSON.stringify(args, null, 2)}
                </pre>
              </div>
            )}

            {/* Result */}
            {status === 'completed' && result !== undefined && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1">결과</p>
                <pre className="rounded bg-green-50 dark:bg-green-950/30 p-2 text-xs overflow-auto max-h-32">
                  {formatValue(result)}
                </pre>
              </div>
            )}

            {/* Error */}
            {status === 'error' && error && (
              <div>
                <p className="text-xs font-medium text-red-600 dark:text-red-400 mb-1">오류</p>
                <pre className="rounded bg-red-50 dark:bg-red-950/30 p-2 text-xs text-red-700 dark:text-red-300 overflow-auto max-h-32">
                  {error}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    )
  }
)
ToolCallCard.displayName = 'ToolCallCard'

/**
 * ToolCallList
 *
 * 여러 도구 호출을 표시하는 리스트
 */
interface ToolCallListProps extends React.HTMLAttributes<HTMLDivElement> {
  calls: Array<{
    id: string
    toolName: string
    status: ToolCallStatus
    args?: Record<string, unknown>
    result?: unknown
    error?: string
    duration?: number
  }>
}

const ToolCallList = React.forwardRef<HTMLDivElement, ToolCallListProps>(
  ({ className, calls, ...props }, ref) => {
    if (calls.length === 0) return null

    return (
      <div ref={ref} className={cn('space-y-2', className)} {...props}>
        {calls.map(call => (
          <ToolCallCard
            key={call.id}
            toolName={call.toolName}
            status={call.status}
            args={call.args}
            result={call.result}
            error={call.error}
            duration={call.duration}
          />
        ))}
      </div>
    )
  }
)
ToolCallList.displayName = 'ToolCallList'

export { ToolCallCard, ToolCallList }
export type { ToolCallCardProps, ToolCallListProps, ToolCallStatus }

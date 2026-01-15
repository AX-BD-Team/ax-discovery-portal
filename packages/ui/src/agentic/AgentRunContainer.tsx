/**
 * AgentRunContainer
 *
 * 에이전트 워크플로 실행 컨테이너
 * 전체 실행 상태를 표시하고 하위 컴포넌트를 감싸는 레이아웃
 */

import * as React from 'react'
import { cn } from '@ax/utils'
import type { RunStatus } from '@ax/types'
import { Loader2, CheckCircle2, XCircle, PauseCircle, Circle } from 'lucide-react'

interface AgentRunContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 실행 ID */
  runId: string
  /** 세션 ID */
  sessionId?: string
  /** 워크플로 제목 */
  title: string
  /** 워크플로 설명 */
  description?: string
  /** 실행 상태 */
  status: RunStatus
  /** 취소 핸들러 */
  onCancel?: () => void
  /** 재시도 핸들러 */
  onRetry?: () => void
}

const statusConfig: Record<RunStatus, { icon: React.ReactNode; label: string; className: string }> =
  {
    idle: {
      icon: <Circle className="h-4 w-4" />,
      label: '대기 중',
      className: 'text-muted-foreground',
    },
    running: {
      icon: <Loader2 className="h-4 w-4 animate-spin" />,
      label: '실행 중',
      className: 'text-blue-500',
    },
    completed: {
      icon: <CheckCircle2 className="h-4 w-4" />,
      label: '완료',
      className: 'text-green-500',
    },
    error: {
      icon: <XCircle className="h-4 w-4" />,
      label: '오류',
      className: 'text-red-500',
    },
    paused: {
      icon: <PauseCircle className="h-4 w-4" />,
      label: '일시 중지',
      className: 'text-yellow-500',
    },
  }

const AgentRunContainer = React.forwardRef<HTMLDivElement, AgentRunContainerProps>(
  (
    {
      className,
      runId,
      sessionId,
      title,
      description,
      status,
      onCancel,
      onRetry,
      children,
      ...props
    },
    ref
  ) => {
    const config = statusConfig[status]

    return (
      <div
        ref={ref}
        className={cn(
          'rounded-xl border bg-card text-card-foreground shadow-sm',
          'transition-all duration-200',
          status === 'running' && 'border-blue-200 dark:border-blue-800',
          status === 'completed' && 'border-green-200 dark:border-green-800',
          status === 'error' && 'border-red-200 dark:border-red-800',
          className
        )}
        data-run-id={runId}
        data-session-id={sessionId}
        {...props}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-3">
          <div className="flex items-center gap-3">
            <span className={cn('flex items-center gap-1.5', config.className)}>
              {config.icon}
              <span className="text-xs font-medium">{config.label}</span>
            </span>
            <div>
              <h3 className="font-semibold leading-none">{title}</h3>
              {description && <p className="mt-1 text-xs text-muted-foreground">{description}</p>}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {status === 'running' && onCancel && (
              <button
                onClick={onCancel}
                className="rounded-md px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted transition-colors"
              >
                취소
              </button>
            )}
            {status === 'error' && onRetry && (
              <button
                onClick={onRetry}
                className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                재시도
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="p-4">{children}</div>
      </div>
    )
  }
)
AgentRunContainer.displayName = 'AgentRunContainer'

export { AgentRunContainer }
export type { AgentRunContainerProps }

/**
 * StepIndicator
 *
 * 워크플로 단계 진행률 표시기
 * 각 단계의 상태를 시각적으로 표현
 */

import * as React from 'react'
import { cn } from '@ax/utils'
import type { StepStatus } from '@ax/types'
import { Check, Loader2, X, Circle, SkipForward } from 'lucide-react'

interface Step {
  id: string
  label: string
  status: StepStatus
  duration?: number // ms
  message?: string
}

interface StepIndicatorProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 단계 목록 */
  steps: Step[]
  /** 현재 단계 인덱스 */
  currentStepIndex: number
  /** 표시 방향 */
  orientation?: 'horizontal' | 'vertical'
  /** 컴팩트 모드 */
  compact?: boolean
}

const statusConfig: Record<
  StepStatus,
  { icon: React.ReactNode; className: string; bgClassName: string }
> = {
  pending: {
    icon: <Circle className="h-3.5 w-3.5" />,
    className: 'text-muted-foreground',
    bgClassName: 'bg-muted',
  },
  running: {
    icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
    className: 'text-blue-500',
    bgClassName: 'bg-blue-100 dark:bg-blue-900',
  },
  completed: {
    icon: <Check className="h-3.5 w-3.5" />,
    className: 'text-green-500',
    bgClassName: 'bg-green-100 dark:bg-green-900',
  },
  error: {
    icon: <X className="h-3.5 w-3.5" />,
    className: 'text-red-500',
    bgClassName: 'bg-red-100 dark:bg-red-900',
  },
  skipped: {
    icon: <SkipForward className="h-3.5 w-3.5" />,
    className: 'text-muted-foreground',
    bgClassName: 'bg-muted',
  },
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

const StepIndicator = React.forwardRef<HTMLDivElement, StepIndicatorProps>(
  (
    { className, steps, currentStepIndex, orientation = 'vertical', compact = false, ...props },
    ref
  ) => {
    const isHorizontal = orientation === 'horizontal'

    return (
      <div
        ref={ref}
        className={cn(
          'flex',
          isHorizontal ? 'flex-row items-center gap-2' : 'flex-col gap-1',
          className
        )}
        role="list"
        aria-label="워크플로 단계"
        {...props}
      >
        {steps.map((step, index) => {
          const config = statusConfig[step.status]
          const isLast = index === steps.length - 1
          const isCurrent = index === currentStepIndex

          return (
            <div
              key={step.id}
              className={cn(
                'flex',
                isHorizontal ? 'flex-row items-center' : 'flex-row gap-3',
                !isLast && isHorizontal && 'flex-1'
              )}
              role="listitem"
              aria-current={isCurrent ? 'step' : undefined}
            >
              {/* Step indicator */}
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    'flex items-center justify-center rounded-full',
                    compact ? 'h-6 w-6' : 'h-8 w-8',
                    config.bgClassName,
                    isCurrent && 'ring-2 ring-primary ring-offset-2'
                  )}
                >
                  <span className={config.className}>{config.icon}</span>
                </div>

                {/* Vertical connector line */}
                {!isHorizontal && !isLast && (
                  <div
                    className={cn(
                      'w-0.5 flex-1 min-h-[1rem]',
                      step.status === 'completed' ? 'bg-green-300 dark:bg-green-700' : 'bg-muted'
                    )}
                  />
                )}
              </div>

              {/* Horizontal connector line */}
              {isHorizontal && !isLast && (
                <div
                  className={cn(
                    'h-0.5 flex-1 mx-2',
                    step.status === 'completed' ? 'bg-green-300 dark:bg-green-700' : 'bg-muted'
                  )}
                />
              )}

              {/* Label and info */}
              {!compact && !isHorizontal && (
                <div className="flex-1 pb-4">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        'text-sm font-medium',
                        isCurrent ? 'text-foreground' : 'text-muted-foreground'
                      )}
                    >
                      {step.label}
                    </span>
                    {step.duration && step.status === 'completed' && (
                      <span className="text-xs text-muted-foreground">
                        ({formatDuration(step.duration)})
                      </span>
                    )}
                  </div>
                  {step.message && (
                    <p className="mt-0.5 text-xs text-muted-foreground">{step.message}</p>
                  )}
                </div>
              )}

              {/* Horizontal label */}
              {!compact && isHorizontal && (
                <span
                  className={cn(
                    'text-xs font-medium ml-1',
                    isCurrent ? 'text-foreground' : 'text-muted-foreground'
                  )}
                >
                  {step.label}
                </span>
              )}
            </div>
          )
        })}
      </div>
    )
  }
)
StepIndicator.displayName = 'StepIndicator'

export { StepIndicator }
export type { StepIndicatorProps, Step }

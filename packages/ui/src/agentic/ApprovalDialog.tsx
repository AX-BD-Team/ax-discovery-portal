/**
 * ApprovalDialog
 *
 * Human-in-the-Loop 승인 다이얼로그
 * 고위험 액션에 대한 사용자 승인 요청
 */

import * as React from 'react'
import { cn } from '@ax/utils'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../components/dialog'
import { Button } from '../components/button'
import { Badge } from '../components/badge'
import type { ImpactLevel } from '@ax/types'
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  Info,
  Clock,
  ArrowRight,
  Plus,
  Minus,
  Edit,
} from 'lucide-react'

interface ChangeItem {
  label: string
  before?: string
  after: string
  type: 'create' | 'update' | 'delete'
}

interface ApprovalDialogProps {
  /** 다이얼로그 열림 상태 */
  open: boolean
  /** 열림 상태 변경 핸들러 */
  onOpenChange?: (open: boolean) => void
  /** 제목 */
  title: string
  /** 설명 */
  description: string
  /** 위험도 수준 */
  impact: ImpactLevel
  /** 변경 사항 목록 */
  changes?: ChangeItem[]
  /** 승인 핸들러 */
  onApprove: () => void
  /** 거부 핸들러 */
  onReject: (reason?: string) => void
  /** 추가 정보 요청 핸들러 */
  onRequestMoreInfo?: () => void
  /** 타임아웃 (ms) */
  timeout?: number
  /** 승인 중 상태 */
  isApproving?: boolean
}

const impactConfig: Record<
  ImpactLevel,
  { icon: React.ReactNode; label: string; className: string; bgClassName: string }
> = {
  low: {
    icon: <Info className="h-4 w-4" />,
    label: '낮음',
    className: 'text-blue-600 dark:text-blue-400',
    bgClassName: 'bg-blue-100 dark:bg-blue-900/30',
  },
  medium: {
    icon: <AlertTriangle className="h-4 w-4" />,
    label: '중간',
    className: 'text-yellow-600 dark:text-yellow-400',
    bgClassName: 'bg-yellow-100 dark:bg-yellow-900/30',
  },
  high: {
    icon: <AlertTriangle className="h-4 w-4" />,
    label: '높음',
    className: 'text-orange-600 dark:text-orange-400',
    bgClassName: 'bg-orange-100 dark:bg-orange-900/30',
  },
  critical: {
    icon: <AlertTriangle className="h-4 w-4" />,
    label: '심각',
    className: 'text-red-600 dark:text-red-400',
    bgClassName: 'bg-red-100 dark:bg-red-900/30',
  },
}

const changeTypeConfig: Record<
  ChangeItem['type'],
  { icon: React.ReactNode; label: string; className: string }
> = {
  create: {
    icon: <Plus className="h-3 w-3" />,
    label: '생성',
    className: 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30',
  },
  update: {
    icon: <Edit className="h-3 w-3" />,
    label: '수정',
    className: 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30',
  },
  delete: {
    icon: <Minus className="h-3 w-3" />,
    label: '삭제',
    className: 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30',
  },
}

function ApprovalDialog({
  open,
  onOpenChange,
  title,
  description,
  impact,
  changes,
  onApprove,
  onReject,
  onRequestMoreInfo,
  timeout,
  isApproving,
}: ApprovalDialogProps) {
  const [rejectReason, setRejectReason] = React.useState('')
  const [showRejectInput, setShowRejectInput] = React.useState(false)
  const [remainingTime, setRemainingTime] = React.useState(timeout)

  const config = impactConfig[impact]

  // 타임아웃 카운트다운
  React.useEffect(() => {
    if (!timeout || !open) return

    setRemainingTime(timeout)

    const interval = setInterval(() => {
      setRemainingTime(prev => {
        if (!prev || prev <= 1000) {
          clearInterval(interval)
          onReject('타임아웃으로 자동 거부되었습니다')
          return 0
        }
        return prev - 1000
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [timeout, open, onReject])

  const handleReject = () => {
    if (showRejectInput) {
      onReject(rejectReason || undefined)
      setShowRejectInput(false)
      setRejectReason('')
    } else {
      setShowRejectInput(true)
    }
  }

  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000)
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return minutes > 0
      ? `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
      : `${remainingSeconds}초`
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className={cn('rounded-full p-2', config.bgClassName)}>
              <span className={config.className}>{config.icon}</span>
            </div>
            <div>
              <DialogTitle>{title}</DialogTitle>
              <div className="mt-1 flex items-center gap-2">
                <Badge variant="outline" className={cn('text-xs', config.className)}>
                  위험도: {config.label}
                </Badge>
                {remainingTime && remainingTime > 0 && (
                  <span className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {formatTime(remainingTime)}
                  </span>
                )}
              </div>
            </div>
          </div>
        </DialogHeader>

        <DialogDescription className="mt-4">{description}</DialogDescription>

        {/* 변경 사항 목록 */}
        {changes && changes.length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="text-sm font-medium">변경 사항</p>
            <div className="space-y-2">
              {changes.map((change, index) => {
                const changeConfig = changeTypeConfig[change.type]
                return (
                  <div key={index} className="rounded-lg border bg-muted/50 p-3 text-sm">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          'inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs',
                          changeConfig.className
                        )}
                      >
                        {changeConfig.icon}
                        {changeConfig.label}
                      </span>
                      <span className="font-medium">{change.label}</span>
                    </div>
                    {(change.before || change.after) && (
                      <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                        {change.before && (
                          <>
                            <span className="line-through">{change.before}</span>
                            <ArrowRight className="h-3 w-3" />
                          </>
                        )}
                        <span className="text-foreground">{change.after}</span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* 거부 사유 입력 */}
        {showRejectInput && (
          <div className="mt-4">
            <label className="text-sm font-medium">거부 사유 (선택)</label>
            <textarea
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
              rows={2}
              placeholder="거부 사유를 입력하세요..."
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
            />
          </div>
        )}

        {/* 액션 버튼 */}
        <div className="mt-6 flex justify-end gap-2">
          {onRequestMoreInfo && !showRejectInput && (
            <Button variant="outline" size="sm" onClick={onRequestMoreInfo}>
              더 알아보기
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={handleReject} disabled={isApproving}>
            <XCircle className="mr-1.5 h-4 w-4" />
            {showRejectInput ? '거부 확인' : '거부'}
          </Button>
          {!showRejectInput && (
            <Button
              size="sm"
              onClick={onApprove}
              disabled={isApproving}
              className={cn(
                impact === 'critical' && 'bg-red-600 hover:bg-red-700',
                impact === 'high' && 'bg-orange-600 hover:bg-orange-700'
              )}
            >
              <CheckCircle className="mr-1.5 h-4 w-4" />
              {isApproving ? '처리 중...' : '승인'}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

export { ApprovalDialog }
export type { ApprovalDialogProps, ChangeItem }

'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { scorecardApi } from '@ax/api-client'
import type { Signal } from '@ax/types'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  Button,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Badge,
  toast,
} from '@ax/ui'
import { TrendingUp, Loader2 } from 'lucide-react'

interface EvaluateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  availableSignals: Signal[]
}

export function EvaluateDialog({ open, onOpenChange, availableSignals }: EvaluateDialogProps) {
  const [selectedSignalId, setSelectedSignalId] = useState<string>('')
  const [evaluationMode, setEvaluationMode] = useState<'auto' | 'manual'>('auto')
  const queryClient = useQueryClient()

  const evaluateMutation = useMutation({
    mutationFn: (signalId: string) =>
      scorecardApi.evaluateSignal(signalId, { mode: evaluationMode }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signals'] })
      queryClient.invalidateQueries({ queryKey: ['scorecard-distribution'] })
      onOpenChange(false)
      setSelectedSignalId('')
    },
  })

  const handleEvaluate = () => {
    if (!selectedSignalId) {
      toast.warning('Signal 선택 필요', {
        description: '평가할 Signal을 선택해주세요.',
      })
      return
    }
    evaluateMutation.mutate(selectedSignalId)
  }

  const selectedSignal = availableSignals.find(s => s.signal_id === selectedSignalId)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Evaluate Signal</DialogTitle>
          <DialogDescription>
            평가할 Signal을 선택하고 Scorecard를 생성합니다
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Signal Selection */}
          <div>
            <Label htmlFor="signal">Signal *</Label>
            <Select value={selectedSignalId} onValueChange={setSelectedSignalId}>
              <SelectTrigger id="signal" className="mt-2">
                <SelectValue placeholder="Select a signal to evaluate" />
              </SelectTrigger>
              <SelectContent>
                {availableSignals.length === 0 ? (
                  <div className="p-4 text-center text-sm text-gray-500">
                    No signals available for evaluation
                  </div>
                ) : (
                  availableSignals.map(signal => (
                    <SelectItem key={signal.signal_id} value={signal.signal_id}>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{signal.signal_id}</span>
                        <span>-</span>
                        <span className="text-gray-600">{signal.title}</span>
                        <Badge variant="outline" className="ml-2">
                          {signal.status}
                        </Badge>
                      </div>
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>

          {/* Selected Signal Preview */}
          {selectedSignal && (
            <div className="rounded-lg border bg-gray-50 p-4">
              <h4 className="mb-2 font-semibold text-gray-900">{selectedSignal.title}</h4>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium text-gray-700">Pain Point:</span>
                  <p className="mt-1 text-gray-600">{selectedSignal.pain}</p>
                </div>
                {selectedSignal.customer_segment && (
                  <div>
                    <span className="font-medium text-gray-700">Customer Segment:</span>
                    <p className="mt-1 text-gray-600">{selectedSignal.customer_segment}</p>
                  </div>
                )}
                <div className="flex gap-2">
                  <Badge variant="outline">{selectedSignal.source}</Badge>
                  <Badge variant="outline">{selectedSignal.channel}</Badge>
                </div>
              </div>
            </div>
          )}

          {/* Evaluation Mode */}
          <div>
            <Label htmlFor="mode">Evaluation Mode</Label>
            <Select
              value={evaluationMode}
              onValueChange={v => setEvaluationMode(v as 'auto' | 'manual')}
            >
              <SelectTrigger id="mode" className="mt-2">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="auto">
                  <div className="space-y-1">
                    <div className="font-medium">Auto (AI-powered)</div>
                    <div className="text-xs text-gray-500">
                      Claude Agent가 자동으로 평가합니다
                    </div>
                  </div>
                </SelectItem>
                <SelectItem value="manual">
                  <div className="space-y-1">
                    <div className="font-medium">Manual</div>
                    <div className="text-xs text-gray-500">수동으로 점수를 입력합니다</div>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Evaluation Info */}
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
            <h4 className="mb-2 font-semibold text-blue-900">Evaluation Criteria</h4>
            <ul className="space-y-1 text-sm text-blue-800">
              <li>• Problem Severity (20점): 문제의 심각도</li>
              <li>• Willingness to Pay (20점): 지불 의사</li>
              <li>• Data Availability (20점): 데이터 가용성</li>
              <li>• Feasibility (20점): 실현 가능성</li>
              <li>• Strategic Fit (20점): 전략 적합성</li>
            </ul>
            <p className="mt-3 text-sm font-medium text-blue-900">
              Total: 100점 만점 (70+ GO, 50-69 PIVOT, 30-49 HOLD, &lt;30 NO_GO)
            </p>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={evaluateMutation.isPending}
            >
              Cancel
            </Button>
            <Button onClick={handleEvaluate} disabled={evaluateMutation.isPending || !selectedSignalId}>
              {evaluateMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Evaluating...
                </>
              ) : (
                <>
                  <TrendingUp className="mr-2 h-4 w-4" />
                  Start Evaluation
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

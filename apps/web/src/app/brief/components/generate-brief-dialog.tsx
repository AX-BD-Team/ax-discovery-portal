'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { briefApi } from '@ax/api-client'
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
import { FileText, Loader2 } from 'lucide-react'

interface GenerateBriefDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  availableSignals: Signal[]
}

export function GenerateBriefDialog({
  open,
  onOpenChange,
  availableSignals,
}: GenerateBriefDialogProps) {
  const [selectedSignalId, setSelectedSignalId] = useState<string>('')
  const queryClient = useQueryClient()

  const generateMutation = useMutation({
    mutationFn: (signalId: string) => briefApi.generateBrief(signalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['briefs'] })
      queryClient.invalidateQueries({ queryKey: ['signals'] })
      onOpenChange(false)
      setSelectedSignalId('')
    },
  })

  const handleGenerate = () => {
    if (!selectedSignalId) {
      toast.warning('Signal 선택 필요', {
        description: 'Brief를 생성할 Signal을 선택해주세요.',
      })
      return
    }
    generateMutation.mutate(selectedSignalId)
  }

  const selectedSignal = availableSignals.find(s => s.signal_id === selectedSignalId)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Generate Brief</DialogTitle>
          <DialogDescription>
            평가된 Signal에서 1-Page Opportunity Brief를 생성합니다
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Signal Selection */}
          <div>
            <Label htmlFor="signal">Signal (SCORED) *</Label>
            <Select value={selectedSignalId} onValueChange={setSelectedSignalId}>
              <SelectTrigger id="signal" className="mt-2">
                <SelectValue placeholder="Select a scored signal" />
              </SelectTrigger>
              <SelectContent>
                {availableSignals.length === 0 ? (
                  <div className="p-4 text-center text-sm text-gray-500">
                    No scored signals available
                  </div>
                ) : (
                  availableSignals.map(signal => (
                    <SelectItem key={signal.signal_id} value={signal.signal_id}>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{signal.signal_id}</span>
                        <span>-</span>
                        <span className="text-gray-600">{signal.title}</span>
                        <Badge variant="outline" className="ml-2">
                          {signal.source}
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
              <h4 className="mb-3 font-semibold text-gray-900">{selectedSignal.title}</h4>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium text-gray-700">Pain Point:</span>
                  <p className="mt-1 text-gray-600">{selectedSignal.pain}</p>
                </div>
                {selectedSignal.proposed_value && (
                  <div>
                    <span className="font-medium text-gray-700">Proposed Value:</span>
                    <p className="mt-1 text-gray-600">{selectedSignal.proposed_value}</p>
                  </div>
                )}
                {selectedSignal.customer_segment && (
                  <div>
                    <span className="font-medium text-gray-700">Customer:</span>
                    <p className="mt-1 text-gray-600">{selectedSignal.customer_segment}</p>
                  </div>
                )}
                {selectedSignal.kpi_hypothesis && selectedSignal.kpi_hypothesis.length > 0 && (
                  <div>
                    <span className="font-medium text-gray-700">KPI Hypothesis:</span>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {selectedSignal.kpi_hypothesis.map((kpi, idx) => (
                        <Badge key={idx} variant="secondary" className="text-xs">
                          {kpi}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                <div className="flex gap-2 pt-2">
                  <Badge variant="outline">{selectedSignal.source}</Badge>
                  <Badge variant="outline">{selectedSignal.channel}</Badge>
                </div>
              </div>
            </div>
          )}

          {/* Brief Generation Info */}
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
            <h4 className="mb-2 font-semibold text-blue-900">Brief 생성 프로세스</h4>
            <ul className="space-y-1 text-sm text-blue-800">
              <li>• Claude Agent가 Signal과 Scorecard를 분석합니다</li>
              <li>• 고객, 문제, 솔루션을 구조화된 형식으로 정리합니다</li>
              <li>• 검증 계획 및 MVP Scope를 제안합니다</li>
              <li>• 1-Page Brief로 자동 생성됩니다</li>
            </ul>
            <p className="mt-3 text-sm font-medium text-blue-900">
              생성 후 검토 및 수정이 가능합니다
            </p>
          </div>

          {/* Brief Sections Preview */}
          <div className="rounded-lg border bg-gray-50 p-4">
            <h4 className="mb-2 font-semibold text-gray-900">Brief에 포함될 내용</h4>
            <div className="grid grid-cols-2 gap-2 text-sm text-gray-700">
              <div>✓ Customer (Segment, Buyer Role)</div>
              <div>✓ Problem (Pain, Why Now)</div>
              <div>✓ Solution Hypothesis</div>
              <div>✓ Integration Points</div>
              <div>✓ Target KPIs</div>
              <div>✓ Evidence Links</div>
              <div>✓ Validation Plan (5-Day Sprint)</div>
              <div>✓ MVP Scope</div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={generateMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={handleGenerate}
              disabled={generateMutation.isPending || !selectedSignalId}
            >
              {generateMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <FileText className="mr-2 h-4 w-4" />
                  Generate Brief
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

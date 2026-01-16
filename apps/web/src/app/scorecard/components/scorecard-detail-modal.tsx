'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { scorecardApi, inboxApi, briefApi } from '@ax/api-client'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  Button,
  Badge,
  Separator,
} from '@ax/ui'
import { formatRelativeTime } from '@ax/utils'
import { SCORECARD_DIMENSIONS } from '@ax/config'
import { FileText, AlertTriangle } from 'lucide-react'

interface ScorecardDetailModalProps {
  signalId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ScorecardDetailModal({ signalId, open, onOpenChange }: ScorecardDetailModalProps) {
  const queryClient = useQueryClient()

  const { data: scorecard, isLoading: isLoadingScorecard } = useQuery({
    queryKey: ['scorecard', signalId],
    queryFn: () => scorecardApi.getScorecard(signalId!),
    enabled: !!signalId && open,
  })

  const { data: signal, isLoading: isLoadingSignal } = useQuery({
    queryKey: ['signal', signalId],
    queryFn: () => inboxApi.getSignal(signalId!),
    enabled: !!signalId && open,
  })

  const generateBriefMutation = useMutation({
    mutationFn: () => briefApi.generateBrief(signalId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signal', signalId] })
      queryClient.invalidateQueries({ queryKey: ['signals'] })
      onOpenChange(false)
    },
  })

  if (!signalId) return null

  const isLoading = isLoadingScorecard || isLoadingSignal

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'GO':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'PIVOT':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'HOLD':
        return 'bg-orange-100 text-orange-800 border-orange-200'
      case 'NO_GO':
        return 'bg-red-100 text-red-800 border-red-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-green-600'
    if (score >= 50) return 'text-yellow-600'
    if (score >= 30) return 'text-orange-600'
    return 'text-red-600'
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-describedby={undefined} className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Scorecard Details</DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
              <p className="text-gray-600">Loading...</p>
            </div>
          </div>
        ) : !scorecard || !signal ? (
          <div className="py-12 text-center text-gray-600">Scorecard not found</div>
        ) : (
          <div className="space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="mb-3 flex items-center gap-3">
                  <Badge className={getDecisionColor(scorecard.recommendation.decision)}>
                    {scorecard.recommendation.decision}
                  </Badge>
                  <span className="text-sm text-gray-600">
                    Next Step: {scorecard.recommendation.next_step.replace(/_/g, ' ')}
                  </span>
                </div>
                <h2 className="text-2xl font-bold text-gray-900">{signal.title}</h2>
                <p className="mt-2 text-sm text-gray-500">
                  Scorecard ID: {scorecard.scorecard_id || 'N/A'} • Evaluated{' '}
                  {formatRelativeTime(scorecard.scored_at)}
                  {scorecard.scored_by && ` by ${scorecard.scored_by}`}
                </p>
              </div>
              <div className="text-center">
                <p className={`text-5xl font-bold ${getScoreColor(scorecard.total_score)}`}>
                  {scorecard.total_score}
                </p>
                <p className="text-sm text-gray-500">/ 100</p>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="h-3 w-full overflow-hidden rounded-full bg-gray-200">
              <div
                className={`h-full ${
                  scorecard.total_score >= 70
                    ? 'bg-green-500'
                    : scorecard.total_score >= 50
                      ? 'bg-yellow-500'
                      : scorecard.total_score >= 30
                        ? 'bg-orange-500'
                        : 'bg-red-500'
                }`}
                style={{ width: `${scorecard.total_score}%` }}
              />
            </div>

            {/* Rationale */}
            {scorecard.recommendation.rationale && (
              <div className="rounded-lg bg-gray-50 p-4">
                <p className="text-sm font-medium text-gray-900">Evaluation Rationale</p>
                <p className="mt-2 text-sm text-gray-700">{scorecard.recommendation.rationale}</p>
              </div>
            )}

            <Separator />

            {/* Dimension Breakdown */}
            <div>
              <h3 className="mb-4 font-semibold text-gray-900">Dimension Breakdown</h3>
              <div className="space-y-4">
                {Object.entries(scorecard.dimension_scores || {}).map(([key, value]) => (
                  <div key={key}>
                    <div className="mb-2 flex items-center justify-between">
                      <span className="font-medium text-gray-900">
                        {SCORECARD_DIMENSIONS[key as keyof typeof SCORECARD_DIMENSIONS]}
                      </span>
                      <span className="text-lg font-bold text-gray-900">{value} / 20</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
                      <div
                        className={`h-full ${
                          value >= 14
                            ? 'bg-green-500'
                            : value >= 10
                              ? 'bg-yellow-500'
                              : value >= 6
                                ? 'bg-orange-500'
                                : 'bg-red-500'
                        }`}
                        style={{ width: `${(value / 20) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Red Flags */}
            {scorecard.red_flags && scorecard.red_flags.length > 0 && (
              <>
                <Separator />
                <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <AlertTriangle className="h-5 w-5 text-red-600" />
                    <h3 className="font-semibold text-red-900">
                      Red Flags ({scorecard.red_flags.length})
                    </h3>
                  </div>
                  <ul className="space-y-2">
                    {scorecard.red_flags.map((flag, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-gray-700">
                        <span className="mt-1 text-red-500">•</span>
                        <span>{flag}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}

            <Separator />

            {/* Signal Information */}
            <div>
              <h3 className="mb-4 font-semibold text-gray-900">Signal Information</h3>
              <div className="space-y-4">
                <div>
                  <p className="mb-1 text-sm font-medium text-gray-700">Pain Point</p>
                  <p className="text-gray-900">{signal.pain}</p>
                </div>

                {signal.proposed_value && (
                  <div>
                    <p className="mb-1 text-sm font-medium text-gray-700">Proposed Value</p>
                    <p className="text-gray-900">{signal.proposed_value}</p>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-600">Source</p>
                    <p className="font-medium text-gray-900">{signal.source}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Channel</p>
                    <p className="font-medium text-gray-900">{signal.channel}</p>
                  </div>
                  {signal.customer_segment && (
                    <div>
                      <p className="text-gray-600">Customer Segment</p>
                      <p className="font-medium text-gray-900">{signal.customer_segment}</p>
                    </div>
                  )}
                  <div>
                    <p className="text-gray-600">Play ID</p>
                    <p className="font-medium text-gray-900">{signal.play_id}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-4">
              {scorecard.recommendation.decision === 'GO' &&
                scorecard.recommendation.next_step === 'BRIEF' && (
                  <Button
                    onClick={() => generateBriefMutation.mutate()}
                    disabled={generateBriefMutation.isPending}
                    className="flex-1"
                  >
                    <FileText className="mr-2 h-4 w-4" />
                    {generateBriefMutation.isPending ? 'Generating...' : 'Generate Brief'}
                  </Button>
                )}
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

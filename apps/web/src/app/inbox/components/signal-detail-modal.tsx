'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { inboxApi, scorecardApi, briefApi } from '@ax/api-client'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  Button,
  Badge,
  Separator,
} from '@ax/ui'
import { formatDate, formatRelativeTime, getStatusColor } from '@ax/utils'
import { STATUS_LABELS } from '@ax/config'
import { TrendingUp, FileText, ExternalLink, Calendar, User, Tag, X } from 'lucide-react'

interface SignalDetailModalProps {
  signalId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SignalDetailModal({ signalId, open, onOpenChange }: SignalDetailModalProps) {
  const queryClient = useQueryClient()

  const { data: signal, isLoading } = useQuery({
    queryKey: ['signal', signalId],
    queryFn: () => inboxApi.getSignal(signalId!),
    enabled: !!signalId && open,
  })

  const { data: scorecard } = useQuery({
    queryKey: ['scorecard', signalId],
    queryFn: () => scorecardApi.getScorecard(signalId!),
    enabled: !!signalId && open && signal?.status !== 'NEW',
  })

  const triageMutation = useMutation({
    mutationFn: () => inboxApi.triggerTriage(signalId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signal', signalId] })
      queryClient.invalidateQueries({ queryKey: ['scorecard', signalId] })
      queryClient.invalidateQueries({ queryKey: ['signals'] })
    },
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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-describedby={undefined} className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between">
            <span>Signal Details</span>
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
              <p className="text-gray-600">Loading...</p>
            </div>
          </div>
        ) : !signal ? (
          <div className="py-12 text-center text-gray-600">Signal not found</div>
        ) : (
          <div className="space-y-6">
            {/* Header */}
            <div>
              <div className="mb-3 flex items-center gap-2">
                <Badge variant={getStatusColor(signal.status) === 'gray' ? 'secondary' : 'default'}>
                  {STATUS_LABELS[signal.status]}
                </Badge>
                <Badge variant="outline">{signal.source}</Badge>
                <Badge variant="outline">{signal.channel}</Badge>
              </div>
              <h2 className="text-2xl font-bold text-gray-900">{signal.title}</h2>
              <p className="mt-2 text-sm text-gray-500">
                Signal ID: {signal.signal_id} • Created {formatRelativeTime(signal.created_at)}
              </p>
            </div>

            <Separator />

            {/* Pain Point */}
            <div>
              <h3 className="mb-2 font-semibold text-gray-900">Pain Point</h3>
              <p className="text-gray-700">{signal.pain}</p>
            </div>

            {/* Proposed Value */}
            {signal.proposed_value && (
              <div>
                <h3 className="mb-2 font-semibold text-gray-900">Proposed Value</h3>
                <p className="text-gray-700">{signal.proposed_value}</p>
              </div>
            )}

            {/* Customer Segment */}
            {signal.customer_segment && (
              <div>
                <h3 className="mb-2 font-semibold text-gray-900">Customer Segment</h3>
                <p className="text-gray-700">{signal.customer_segment}</p>
              </div>
            )}

            {/* KPI Hypothesis */}
            {signal.kpi_hypothesis && signal.kpi_hypothesis.length > 0 && (
              <div>
                <h3 className="mb-2 font-semibold text-gray-900">KPI Hypothesis</h3>
                <ul className="list-inside list-disc space-y-1 text-gray-700">
                  {signal.kpi_hypothesis.map((kpi, idx) => (
                    <li key={idx}>{kpi}</li>
                  ))}
                </ul>
              </div>
            )}

            <Separator />

            {/* Evidence */}
            {signal.evidence && signal.evidence.length > 0 && (
              <div>
                <h3 className="mb-3 font-semibold text-gray-900">
                  Evidence ({signal.evidence.length})
                </h3>
                <div className="space-y-2">
                  {signal.evidence.map((ev, idx) => (
                    <div key={idx} className="flex items-center gap-2 rounded-lg border p-3">
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{ev.title}</p>
                        <p className="text-sm text-gray-500">Type: {ev.type}</p>
                        {ev.note && <p className="mt-1 text-sm text-gray-600">{ev.note}</p>}
                      </div>
                      <a href={ev.url} target="_blank" rel="noopener noreferrer">
                        <Button variant="ghost" size="sm">
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tags */}
            {signal.tags && signal.tags.length > 0 && (
              <div>
                <h3 className="mb-2 font-semibold text-gray-900">Tags</h3>
                <div className="flex flex-wrap gap-2">
                  {signal.tags.map((tag, idx) => (
                    <Badge key={idx} variant="outline">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <Separator />

            {/* Metadata */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="flex items-center gap-2 text-gray-600">
                <User className="h-4 w-4" />
                <span>Owner: {signal.owner || 'Unassigned'}</span>
              </div>
              <div className="flex items-center gap-2 text-gray-600">
                <Tag className="h-4 w-4" />
                <span>Play: {signal.play_id}</span>
              </div>
              <div className="flex items-center gap-2 text-gray-600">
                <Calendar className="h-4 w-4" />
                <span>Created: {formatDate(signal.created_at)}</span>
              </div>
              {signal.confidence && (
                <div className="flex items-center gap-2 text-gray-600">
                  <span>Confidence: {Math.round(signal.confidence * 100)}%</span>
                </div>
              )}
            </div>

            {/* Scorecard (if exists) */}
            {scorecard && (
              <>
                <Separator />
                <div className="rounded-lg border bg-gray-50 p-4">
                  <h3 className="mb-4 font-semibold text-gray-900">Scorecard</h3>
                  <div className="mb-4 text-center">
                    <p className="text-sm text-gray-600">Total Score</p>
                    <p className="text-4xl font-bold text-blue-600">{scorecard.total_score}/100</p>
                  </div>
                  <div className="grid gap-2">
                    {Object.entries(scorecard.dimension_scores || {}).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between text-sm">
                        <span className="capitalize text-gray-600">{key.replace(/_/g, ' ')}</span>
                        <span className="font-medium">{value}/20</span>
                      </div>
                    ))}
                  </div>
                  {scorecard.recommendation && (
                    <div className="mt-4 pt-4 border-t">
                      <p className="text-sm">
                        <span className="font-medium">Decision:</span>{' '}
                        <Badge>{scorecard.recommendation.decision}</Badge>
                      </p>
                    </div>
                  )}
                </div>
              </>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-4">
              {signal.status === 'NEW' && (
                <Button
                  onClick={() => triageMutation.mutate()}
                  disabled={triageMutation.isPending}
                  className="flex-1"
                >
                  <TrendingUp className="mr-2 h-4 w-4" />
                  {triageMutation.isPending ? 'Triaging...' : 'Run Triage'}
                </Button>
              )}

              {signal.status === 'SCORED' && (
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

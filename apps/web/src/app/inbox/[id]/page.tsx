'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { inboxApi, scorecardApi, briefApi } from '@ax/api-client'
import { Button, Card, CardContent, CardHeader, CardTitle, Badge, Separator } from '@ax/ui'
import { formatDate, formatRelativeTime, getStatusColor } from '@ax/utils'
import { STATUS_LABELS } from '@ax/config'
import { ArrowLeft, TrendingUp, FileText, ExternalLink, Calendar, User, Tag } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

export default function SignalDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const queryClient = useQueryClient()
  const signalId = params.id

  // Fetch signal
  const { data: signal, isLoading } = useQuery({
    queryKey: ['signal', signalId],
    queryFn: () => inboxApi.getSignal(signalId),
  })

  // Fetch scorecard (if exists)
  const { data: scorecard } = useQuery({
    queryKey: ['scorecard', signalId],
    queryFn: () => scorecardApi.getScorecard(signalId),
    enabled: signal?.status !== 'NEW',
  })

  // Triage mutation
  const triageMutation = useMutation({
    mutationFn: () => inboxApi.triggerTriage(signalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signal', signalId] })
      queryClient.invalidateQueries({ queryKey: ['scorecard', signalId] })
    },
  })

  // Generate brief mutation
  const generateBriefMutation = useMutation({
    mutationFn: () => briefApi.generateBrief(signalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signal', signalId] })
      router.push('/brief')
    },
  })

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
          <p className="text-gray-600">Loading signal...</p>
        </div>
      </div>
    )
  }

  if (!signal) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">Signal not found</p>
          <Link href="/inbox">
            <Button variant="outline" className="mt-4">
              Back to Inbox
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  const statusColor = getStatusColor(signal.status)

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-6">
          <Link href="/inbox">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Inbox
            </Button>
          </Link>
        </div>

        {/* Signal Info */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="mb-3 flex items-center gap-2">
                  <Badge variant={statusColor === 'gray' ? 'secondary' : 'default'}>
                    {STATUS_LABELS[signal.status]}
                  </Badge>
                  <Badge variant="outline">{signal.source}</Badge>
                  <Badge variant="outline">{signal.channel}</Badge>
                </div>
                <CardTitle className="text-2xl">{signal.title}</CardTitle>
                <p className="mt-2 text-sm text-gray-500">
                  Signal ID: {signal.signal_id} • Created {formatRelativeTime(signal.created_at)}
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
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

            <Separator />

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
                  <span>⭐ Confidence: {Math.round(signal.confidence * 100)}%</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Scorecard (if exists) */}
        {scorecard && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Scorecard</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-center">
                <p className="text-sm text-gray-600">Total Score</p>
                <p className="text-4xl font-bold text-blue-600">{scorecard.total_score}/100</p>
              </div>

              <Separator />

              <div className="grid gap-3">
                {Object.entries(scorecard.dimension_scores).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-sm capitalize">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <span className="font-medium">{value}/20</span>
                  </div>
                ))}
              </div>

              {scorecard.red_flags && scorecard.red_flags.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <h4 className="mb-2 font-semibold text-red-600">Red Flags</h4>
                    <ul className="list-inside list-disc space-y-1 text-sm text-gray-700">
                      {scorecard.red_flags.map((flag, idx) => (
                        <li key={idx}>{flag}</li>
                      ))}
                    </ul>
                  </div>
                </>
              )}

              <Separator />

              <div>
                <h4 className="mb-2 font-semibold">Recommendation</h4>
                <div className="space-y-2">
                  <p className="text-sm">
                    <span className="font-medium">Decision:</span>{' '}
                    <Badge>{scorecard.recommendation.decision}</Badge>
                  </p>
                  <p className="text-sm">
                    <span className="font-medium">Next Step:</span>{' '}
                    {scorecard.recommendation.next_step}
                  </p>
                  {scorecard.recommendation.rationale && (
                    <p className="text-sm text-gray-600">{scorecard.recommendation.rationale}</p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Actions */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex gap-3">
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

              {signal.status === 'BRIEF_CREATED' && (
                <Link href="/brief" className="flex-1">
                  <Button className="w-full">
                    <FileText className="mr-2 h-4 w-4" />
                    View Brief
                  </Button>
                </Link>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

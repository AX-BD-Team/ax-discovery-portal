'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { scorecardApi, inboxApi, briefApi } from '@ax/api-client'
import { Button, Card, CardContent, CardHeader, CardTitle, Badge, Separator } from '@ax/ui'
import { formatDate, formatRelativeTime } from '@ax/utils'
import { SCORECARD_DIMENSIONS } from '@ax/config'
import { ArrowLeft, FileText, AlertTriangle, TrendingUp } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

export default function ScorecardDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const queryClient = useQueryClient()
  const signalId = params.id

  // Fetch scorecard
  const { data: scorecard, isLoading: isLoadingScorecard } = useQuery({
    queryKey: ['scorecard', signalId],
    queryFn: () => scorecardApi.getScorecard(signalId),
  })

  // Fetch signal info
  const { data: signal, isLoading: isLoadingSignal } = useQuery({
    queryKey: ['signal', signalId],
    queryFn: () => inboxApi.getSignal(signalId),
  })

  // Generate brief mutation
  const generateBriefMutation = useMutation({
    mutationFn: () => briefApi.generateBrief(signalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signal', signalId] })
      router.push('/brief')
    },
  })

  if (isLoadingScorecard || isLoadingSignal) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
          <p className="text-gray-600">Loading scorecard...</p>
        </div>
      </div>
    )
  }

  if (!scorecard || !signal) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">Scorecard not found</p>
          <Link href="/scorecard">
            <Button variant="outline" className="mt-4">
              Back to Scorecards
            </Button>
          </Link>
        </div>
      </div>
    )
  }

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
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-6">
          <Link href="/scorecard">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Scorecards
            </Button>
          </Link>
        </div>

        {/* Score Overview */}
        <Card className="mb-6">
          <CardHeader>
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
                <CardTitle className="text-2xl">{signal.title}</CardTitle>
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
          </CardHeader>
          <CardContent>
            {/* Progress Bar */}
            <div className="mb-4 h-3 w-full overflow-hidden rounded-full bg-gray-200">
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
          </CardContent>
        </Card>

        {/* Dimension Scores */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Dimension Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {Object.entries(scorecard.dimension_scores).map(([key, value]) => (
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
          </CardContent>
        </Card>

        {/* Red Flags */}
        {scorecard.red_flags && scorecard.red_flags.length > 0 && (
          <Card className="mb-6 border-red-200">
            <CardHeader className="bg-red-50">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-red-600" />
                <CardTitle className="text-red-900">
                  Red Flags ({scorecard.red_flags.length})
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <ul className="space-y-2">
                {scorecard.red_flags.map((flag, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-gray-700">
                    <span className="mt-1 text-red-500">•</span>
                    <span>{flag}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* Signal Information */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Signal Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
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

            <Separator />

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

            {signal.kpi_hypothesis && signal.kpi_hypothesis.length > 0 && (
              <>
                <Separator />
                <div>
                  <p className="mb-2 text-sm font-medium text-gray-700">KPI Hypothesis</p>
                  <ul className="list-inside list-disc space-y-1 text-sm text-gray-700">
                    {signal.kpi_hypothesis.map((kpi, idx) => (
                      <li key={idx}>{kpi}</li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Actions */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex gap-3">
              <Link href={`/inbox/${signalId}`} className="flex-1">
                <Button variant="outline" className="w-full">
                  View Signal Details
                </Button>
              </Link>

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
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

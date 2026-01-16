'use client'

import type { Scorecard } from '@ax/types'
import { Card, CardContent, CardHeader, Badge, Button } from '@ax/ui'
import { formatRelativeTime } from '@ax/utils'
import { SCORECARD_DIMENSIONS } from '@ax/config'
import { ExternalLink, AlertTriangle, TrendingUp } from 'lucide-react'
import Link from 'next/link'

interface ScorecardCardProps {
  scorecard: Scorecard
  onViewDetail?: (signalId: string) => void
}

export function ScorecardCard({ scorecard, onViewDetail }: ScorecardCardProps) {
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
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <div className="text-center">
                <p className={`text-3xl font-bold ${getScoreColor(scorecard.total_score)}`}>
                  {scorecard.total_score}
                </p>
                <p className="text-xs text-gray-500">/ 100</p>
              </div>
              <div className="flex-1">
                <Badge className={getDecisionColor(scorecard.recommendation.decision)}>
                  {scorecard.recommendation.decision}
                </Badge>
                <p className="mt-1 text-sm text-gray-600">
                  Next: {scorecard.recommendation.next_step.replace(/_/g, ' ')}
                </p>
              </div>
            </div>
            <h3 className="text-lg font-semibold text-gray-900">
              Signal: {scorecard.signal_id}
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Evaluated {formatRelativeTime(scorecard.scored_at)}
              {scorecard.scored_by && ` by ${scorecard.scored_by}`}
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={() => onViewDetail?.(scorecard.signal_id)}>
              <ExternalLink className="h-4 w-4" />
            </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Dimension Scores */}
          <div>
            <p className="mb-3 text-sm font-medium text-gray-700">Dimension Scores</p>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
              {Object.entries(scorecard.dimension_scores || {}).map(([key, value]) => (
                <div key={key} className="rounded-lg border bg-gray-50 p-3 text-center">
                  <p className="text-lg font-bold text-gray-900">{value}</p>
                  <p className="text-xs text-gray-600">
                    {SCORECARD_DIMENSIONS[key as keyof typeof SCORECARD_DIMENSIONS]}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Red Flags */}
          {scorecard.red_flags && scorecard.red_flags.length > 0 && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3">
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 text-red-600" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-red-900">
                    Red Flags ({scorecard.red_flags.length})
                  </p>
                  <ul className="mt-1 space-y-1 text-sm text-red-700">
                    {scorecard.red_flags.slice(0, 3).map((flag, idx) => (
                      <li key={idx}>• {flag}</li>
                    ))}
                    {scorecard.red_flags.length > 3 && (
                      <li className="text-red-600">+ {scorecard.red_flags.length - 3} more</li>
                    )}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Rationale */}
          {scorecard.recommendation.rationale && (
            <div>
              <p className="mb-1 text-sm font-medium text-gray-700">Rationale</p>
              <p className="text-sm text-gray-600">{scorecard.recommendation.rationale}</p>
            </div>
          )}

          {/* Progress Bar */}
          <div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
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
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

'use client'

import type { Signal } from '@ax/types'
import { Card, CardContent, CardHeader, Badge, Button } from '@ax/ui'
import { formatRelativeTime, getStatusColor } from '@ax/utils'
import { STATUS_LABELS } from '@ax/config'
import { TrendingUp, ExternalLink, Clock, Tag } from 'lucide-react'
import Link from 'next/link'

interface SignalCardProps {
  signal: Signal
  onTriage: (signalId: string) => void
  isTriaging: boolean
  onViewDetail?: (signalId: string) => void
}

export function SignalCard({ signal, onTriage, isTriaging, onViewDetail }: SignalCardProps) {
  const statusColor = getStatusColor(signal.status)

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant={statusColor === 'gray' ? 'secondary' : 'default'}>
                {STATUS_LABELS[signal.status]}
              </Badge>
              <Badge variant="outline">{signal.source}</Badge>
              <Badge variant="outline">{signal.channel}</Badge>
            </div>
            <h3 className="text-xl font-semibold text-gray-900">{signal.title}</h3>
            <p className="mt-1 text-sm text-gray-500 flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatRelativeTime(signal.created_at)}
            </p>
          </div>
          <div className="flex gap-2">
            {signal.status === 'NEW' && (
              <Button
                size="sm"
                onClick={() => onTriage(signal.signal_id)}
                disabled={isTriaging}
              >
                <TrendingUp className="mr-1 h-4 w-4" />
                Triage
              </Button>
            )}
            <Button size="sm" variant="outline" onClick={() => onViewDetail?.(signal.signal_id)}>
              <ExternalLink className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {/* Pain Point */}
          <div>
            <p className="text-sm font-medium text-gray-700">Pain Point</p>
            <p className="mt-1 text-sm text-gray-600">{signal.pain}</p>
          </div>

          {/* Proposed Value */}
          {signal.proposed_value && (
            <div>
              <p className="text-sm font-medium text-gray-700">Proposed Value</p>
              <p className="mt-1 text-sm text-gray-600">{signal.proposed_value}</p>
            </div>
          )}

          {/* Customer Segment */}
          {signal.customer_segment && (
            <div>
              <p className="text-sm font-medium text-gray-700">Customer Segment</p>
              <p className="mt-1 text-sm text-gray-600">{signal.customer_segment}</p>
            </div>
          )}

          {/* KPI Hypothesis */}
          {signal.kpi_hypothesis && signal.kpi_hypothesis.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700">KPI Hypothesis</p>
              <div className="mt-1 flex flex-wrap gap-2">
                {signal.kpi_hypothesis.map((kpi, idx) => (
                  <Badge key={idx} variant="secondary">
                    {kpi}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Tags */}
          {signal.tags && signal.tags.length > 0 && (
            <div className="flex items-center gap-2">
              <Tag className="h-4 w-4 text-gray-400" />
              <div className="flex flex-wrap gap-1">
                {signal.tags.map((tag, idx) => (
                  <Badge key={idx} variant="outline" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Evidence Count */}
          {signal.evidence && signal.evidence.length > 0 && (
            <div className="text-sm text-gray-500">
              📎 {signal.evidence.length} evidence file(s)
            </div>
          )}

          {/* Owner and Play */}
          <div className="flex items-center gap-4 text-sm text-gray-500">
            {signal.owner && <span>👤 {signal.owner}</span>}
            <span>🎯 Play: {signal.play_id}</span>
            {signal.confidence && (
              <span>
                ⭐ Confidence: {Math.round(signal.confidence * 100)}%
              </span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

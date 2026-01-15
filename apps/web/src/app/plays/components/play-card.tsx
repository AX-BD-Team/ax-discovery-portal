'use client'

import type { PlayRecord } from '@ax/types'
import { Card, CardContent, CardHeader, Badge, Button } from '@ax/ui'
import { formatRelativeTime } from '@ax/utils'
import {
  ExternalLink,
  User,
  Calendar,
  Activity,
  FileText,
  Target,
  CheckCircle,
  AlertCircle,
  Clock,
} from 'lucide-react'
import Link from 'next/link'

interface PlayCardProps {
  play: PlayRecord
  onViewDetail?: (playId: string) => void
}

export function PlayCard({ play, onViewDetail }: PlayCardProps) {
  const getStatusColor = (status: 'G' | 'Y' | 'R') => {
    switch (status) {
      case 'G':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'Y':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'R':
        return 'bg-red-100 text-red-800 border-red-200'
    }
  }

  const getStatusLabel = (status: 'G' | 'Y' | 'R') => {
    switch (status) {
      case 'G':
        return 'Green'
      case 'Y':
        return 'Yellow'
      case 'R':
        return 'Red'
    }
  }

  const getStatusIcon = (status: 'G' | 'Y' | 'R') => {
    switch (status) {
      case 'G':
        return <CheckCircle className="h-4 w-4" />
      case 'Y':
        return <Clock className="h-4 w-4" />
      case 'R':
        return <AlertCircle className="h-4 w-4" />
    }
  }

  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="mb-2 flex items-center gap-2">
              <Badge className={getStatusColor(play.status)}>
                {getStatusIcon(play.status)}
                <span className="ml-1">{getStatusLabel(play.status)}</span>
              </Badge>
              {play.confluence_live_doc_url && (
                <Badge variant="outline">
                  <ExternalLink className="mr-1 h-3 w-3" />
                  Live Doc
                </Badge>
              )}
            </div>
            <h3 className="text-xl font-semibold text-gray-900">{play.play_name}</h3>
            <p className="mt-1 flex items-center gap-1 text-sm text-gray-500">
              <span>Play ID: {play.play_id}</span>
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={() => onViewDetail?.(play.play_id)}>
              <ExternalLink className="h-4 w-4" />
            </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Owner & Last Activity */}
          <div className="flex items-center gap-4 text-sm text-gray-600">
            {play.owner && (
              <span className="flex items-center gap-1">
                <User className="h-4 w-4" />
                {play.owner}
              </span>
            )}
            {play.last_activity_date && (
              <span className="flex items-center gap-1">
                <Activity className="h-4 w-4" />
                Last Activity: {formatRelativeTime(play.last_activity_date)}
              </span>
            )}
          </div>

          {/* Quarterly Metrics */}
          <div className="rounded-lg border bg-gray-50 p-4">
            <p className="mb-3 text-sm font-medium text-gray-700">Quarterly Metrics</p>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-900">{play.activity_qtd}</p>
                <p className="text-xs text-gray-600">Activities</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-blue-600">{play.signal_qtd}</p>
                <p className="text-xs text-gray-600">Signals</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-purple-600">{play.brief_qtd}</p>
                <p className="text-xs text-gray-600">Briefs</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-green-600">{play.s2_qtd}</p>
                <p className="text-xs text-gray-600">S2 (Validated)</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-indigo-600">{play.s3_qtd}</p>
                <p className="text-xs text-gray-600">S3 (Pilot)</p>
              </div>
            </div>
          </div>

          {/* Next Action */}
          {play.next_action && (
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
              <p className="flex items-center gap-1 text-sm font-medium text-blue-900">
                <Target className="h-4 w-4" />
                Next Action
              </p>
              <p className="mt-1 text-sm text-blue-800">{play.next_action}</p>
              {play.due_date && (
                <p className="mt-1 flex items-center gap-1 text-xs text-blue-700">
                  <Calendar className="h-3 w-3" />
                  Due: {new Date(play.due_date).toLocaleDateString()}
                </p>
              )}
            </div>
          )}

          {/* Notes */}
          {play.notes && (
            <div>
              <p className="text-sm font-medium text-gray-700">Notes</p>
              <p className="mt-1 text-sm text-gray-600">{play.notes}</p>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between border-t pt-3">
            <span className="text-xs text-gray-500">
              Updated {formatRelativeTime(play.last_updated)}
            </span>
            {play.confluence_live_doc_url && (
              <a
                href={play.confluence_live_doc_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-sm text-blue-600 hover:underline"
              >
                View Live Doc
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

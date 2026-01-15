'use client'

import { use } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { playsApi } from '@ax/api-client'
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
  Separator,
} from '@ax/ui'
import { formatDate, formatRelativeTime } from '@ax/utils'
import {
  ArrowLeft,
  ExternalLink,
  User,
  Activity,
  Target,
  Calendar,
  CheckCircle,
  Clock,
  AlertCircle,
  RefreshCw,
  FileText,
  TrendingUp,
} from 'lucide-react'
import Link from 'next/link'

export default function PlayDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const queryClient = useQueryClient()
  const playId = id

  // Fetch play
  const { data: play, isLoading: isLoadingPlay } = useQuery({
    queryKey: ['play', playId],
    queryFn: () => playsApi.getPlay(playId),
  })

  // Fetch timeline
  const { data: timeline, isLoading: isLoadingTimeline } = useQuery({
    queryKey: ['play-timeline', playId],
    queryFn: () => playsApi.getPlayTimeline(playId, 20),
  })

  // Sync mutation
  const syncMutation = useMutation({
    mutationFn: () => playsApi.syncPlay(playId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['play', playId] })
      queryClient.invalidateQueries({ queryKey: ['play-timeline', playId] })
    },
  })

  if (isLoadingPlay) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
          <p className="text-gray-600">Loading play...</p>
        </div>
      </div>
    )
  }

  if (!play) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">Play not found</p>
          <Link href="/plays">
            <Button variant="outline" className="mt-4">
              Back to Plays
            </Button>
          </Link>
        </div>
      </div>
    )
  }

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
        return 'Green (On Track)'
      case 'Y':
        return 'Yellow (At Risk)'
      case 'R':
        return 'Red (Critical)'
    }
  }

  const getStatusIcon = (status: 'G' | 'Y' | 'R') => {
    switch (status) {
      case 'G':
        return <CheckCircle className="h-5 w-5" />
      case 'Y':
        return <Clock className="h-5 w-5" />
      case 'R':
        return <AlertCircle className="h-5 w-5" />
    }
  }

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'ACTIVITY':
        return <Activity className="h-4 w-4 text-blue-600" />
      case 'SIGNAL':
        return <Target className="h-4 w-4 text-purple-600" />
      case 'BRIEF':
        return <FileText className="h-4 w-4 text-green-600" />
      case 'VALIDATION':
        return <CheckCircle className="h-4 w-4 text-indigo-600" />
      default:
        return <Activity className="h-4 w-4 text-gray-600" />
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-6">
          <Link href="/plays">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Plays
            </Button>
          </Link>
        </div>

        {/* Play Header */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="mb-3 flex items-center gap-2">
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
                <CardTitle className="text-2xl">{play.play_name}</CardTitle>
                <p className="mt-2 text-sm text-gray-500">
                  Play ID: {play.play_id} • Updated {formatRelativeTime(play.last_updated)}
                </p>
                <div className="mt-2 flex items-center gap-4 text-sm text-gray-600">
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
              </div>
            </div>
          </CardHeader>
        </Card>

        {/* Quarterly Metrics */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Quarterly Metrics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-5">
              <div className="rounded-lg border bg-gray-50 p-4 text-center">
                <p className="text-3xl font-bold text-gray-900">{play.activity_qtd}</p>
                <p className="mt-1 text-sm text-gray-600">Activities</p>
              </div>
              <div className="rounded-lg border bg-blue-50 p-4 text-center">
                <p className="text-3xl font-bold text-blue-600">{play.signal_qtd}</p>
                <p className="mt-1 text-sm text-blue-700">Signals</p>
              </div>
              <div className="rounded-lg border bg-purple-50 p-4 text-center">
                <p className="text-3xl font-bold text-purple-600">{play.brief_qtd}</p>
                <p className="mt-1 text-sm text-purple-700">Briefs</p>
              </div>
              <div className="rounded-lg border bg-green-50 p-4 text-center">
                <p className="text-3xl font-bold text-green-600">{play.s2_qtd}</p>
                <p className="mt-1 text-sm text-green-700">S2 (Validated)</p>
              </div>
              <div className="rounded-lg border bg-indigo-50 p-4 text-center">
                <p className="text-3xl font-bold text-indigo-600">{play.s3_qtd}</p>
                <p className="mt-1 text-sm text-indigo-700">S3 (Pilot)</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Next Action */}
        {play.next_action && (
          <Card className="mb-6 border-blue-200 bg-blue-50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-blue-900">
                <Target className="h-5 w-5" />
                Next Action
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-blue-900">{play.next_action}</p>
              {play.due_date && (
                <p className="mt-2 flex items-center gap-1 text-sm text-blue-700">
                  <Calendar className="h-4 w-4" />
                  Due Date: {formatDate(play.due_date)}
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Notes */}
        {play.notes && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Notes</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-700">{play.notes}</p>
            </CardContent>
          </Card>
        )}

        {/* Timeline */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Activity Timeline</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoadingTimeline ? (
              <p className="py-8 text-center text-gray-500">Loading timeline...</p>
            ) : timeline && timeline.events.length > 0 ? (
              <div className="space-y-4">
                {timeline.events.map(event => (
                  <div key={event.event_id} className="flex gap-3">
                    <div className="mt-1">{getEventIcon(event.type)}</div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-gray-900">{event.title}</p>
                        <span className="text-sm text-gray-500">
                          {formatRelativeTime(event.date)}
                        </span>
                      </div>
                      {event.description && (
                        <p className="mt-1 text-sm text-gray-600">{event.description}</p>
                      )}
                      <Badge variant="outline" className="mt-2">
                        {event.type}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="py-8 text-center text-gray-500">No timeline events yet</p>
            )}
          </CardContent>
        </Card>

        {/* Actions */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex gap-3">
              {play.confluence_live_doc_url && (
                <a
                  href={play.confluence_live_doc_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1"
                >
                  <Button variant="outline" className="w-full">
                    <ExternalLink className="mr-2 h-4 w-4" />
                    View Live Doc
                  </Button>
                </a>
              )}
              <Button
                onClick={() => syncMutation.mutate()}
                disabled={syncMutation.isPending}
                variant="outline"
                className="flex-1"
              >
                <RefreshCw
                  className={`mr-2 h-4 w-4 ${syncMutation.isPending ? 'animate-spin' : ''}`}
                />
                {syncMutation.isPending ? 'Syncing...' : 'Sync from Confluence'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { playsApi } from '@ax/api-client'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  Button,
  Badge,
  Separator,
} from '@ax/ui'
import { formatDate, formatRelativeTime } from '@ax/utils'
import {
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

interface PlayDetailModalProps {
  playId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function PlayDetailModal({ playId, open, onOpenChange }: PlayDetailModalProps) {
  const queryClient = useQueryClient()

  const { data: play, isLoading: isLoadingPlay } = useQuery({
    queryKey: ['play', playId],
    queryFn: () => playsApi.getPlay(playId!),
    enabled: !!playId && open,
  })

  const { data: timeline, isLoading: isLoadingTimeline } = useQuery({
    queryKey: ['play-timeline', playId],
    queryFn: () => playsApi.getPlayTimeline(playId!, 10),
    enabled: !!playId && open,
  })

  const syncMutation = useMutation({
    mutationFn: () => playsApi.syncPlay(playId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['play', playId] })
      queryClient.invalidateQueries({ queryKey: ['play-timeline', playId] })
      queryClient.invalidateQueries({ queryKey: ['plays'] })
    },
  })

  if (!playId) return null

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
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-describedby={undefined} className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Play Details</DialogTitle>
        </DialogHeader>

        {isLoadingPlay ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
              <p className="text-gray-600">Loading...</p>
            </div>
          </div>
        ) : !play ? (
          <div className="py-12 text-center text-gray-600">Play not found</div>
        ) : (
          <div className="space-y-6">
            {/* Header */}
            <div>
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
              <h2 className="text-2xl font-bold text-gray-900">{play.play_name}</h2>
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

            <Separator />

            {/* Quarterly Metrics */}
            <div>
              <h3 className="flex items-center gap-2 mb-4 font-semibold text-gray-900">
                <TrendingUp className="h-5 w-5" />
                Quarterly Metrics
              </h3>
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
                  <p className="mt-1 text-sm text-green-700">S2</p>
                </div>
                <div className="rounded-lg border bg-indigo-50 p-4 text-center">
                  <p className="text-3xl font-bold text-indigo-600">{play.s3_qtd}</p>
                  <p className="mt-1 text-sm text-indigo-700">S3</p>
                </div>
              </div>
            </div>

            {/* Next Action */}
            {play.next_action && (
              <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                <h3 className="flex items-center gap-2 mb-2 font-semibold text-blue-900">
                  <Target className="h-5 w-5" />
                  Next Action
                </h3>
                <p className="text-blue-900">{play.next_action}</p>
                {play.due_date && (
                  <p className="mt-2 flex items-center gap-1 text-sm text-blue-700">
                    <Calendar className="h-4 w-4" />
                    Due Date: {formatDate(play.due_date)}
                  </p>
                )}
              </div>
            )}

            {/* Notes */}
            {play.notes && (
              <div>
                <h3 className="mb-2 font-semibold text-gray-900">Notes</h3>
                <p className="text-gray-700">{play.notes}</p>
              </div>
            )}

            {/* Timeline */}
            <div>
              <h3 className="mb-4 font-semibold text-gray-900">Recent Activity</h3>
              {isLoadingTimeline ? (
                <p className="py-4 text-center text-gray-500">Loading timeline...</p>
              ) : timeline && timeline.events.length > 0 ? (
                <div className="space-y-3 max-h-60 overflow-y-auto">
                  {timeline.events.map(event => (
                    <div key={event.event_id} className="flex gap-3 p-2 rounded-lg hover:bg-gray-50">
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
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="py-4 text-center text-gray-500">No timeline events yet</p>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-4">
              {play.confluence_live_doc_url && (
                <a href={play.confluence_live_doc_url} target="_blank" rel="noopener noreferrer">
                  <Button variant="outline">
                    <ExternalLink className="mr-2 h-4 w-4" />
                    View Live Doc
                  </Button>
                </a>
              )}
              <Button
                onClick={() => syncMutation.mutate()}
                disabled={syncMutation.isPending}
                variant="outline"
              >
                <RefreshCw className={`mr-2 h-4 w-4 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
                {syncMutation.isPending ? 'Syncing...' : 'Sync from Confluence'}
              </Button>
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

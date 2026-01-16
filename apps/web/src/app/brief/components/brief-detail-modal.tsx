'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { briefApi, inboxApi } from '@ax/api-client'
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
import {
  CheckCircle,
  ExternalLink,
  User,
  Target,
  AlertTriangle,
  Calendar,
  Rocket,
  Upload,
} from 'lucide-react'

interface BriefDetailModalProps {
  briefId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function BriefDetailModal({ briefId, open, onOpenChange }: BriefDetailModalProps) {
  const queryClient = useQueryClient()

  const { data: brief, isLoading } = useQuery({
    queryKey: ['brief', briefId],
    queryFn: () => briefApi.getBrief(briefId!),
    enabled: !!briefId && open,
  })

  const approveMutation = useMutation({
    mutationFn: () => briefApi.approveBrief(briefId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brief', briefId] })
      queryClient.invalidateQueries({ queryKey: ['briefs'] })
    },
  })

  const startValidationMutation = useMutation({
    mutationFn: () => briefApi.startValidation(briefId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brief', briefId] })
      queryClient.invalidateQueries({ queryKey: ['briefs'] })
    },
  })

  if (!briefId) return null

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'DRAFT':
        return 'bg-gray-100 text-gray-800'
      case 'REVIEW':
        return 'bg-yellow-100 text-yellow-800'
      case 'APPROVED':
        return 'bg-green-100 text-green-800'
      case 'VALIDATED':
        return 'bg-blue-100 text-blue-800'
      case 'PILOT_READY':
        return 'bg-purple-100 text-purple-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-describedby={undefined} className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Brief Details</DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
              <p className="text-gray-600">Loading...</p>
            </div>
          </div>
        ) : !brief ? (
          <div className="py-12 text-center text-gray-600">Brief not found</div>
        ) : (
          <div className="space-y-6">
            {/* Header */}
            <div>
              <div className="mb-3 flex items-center gap-2">
                <Badge className={getStatusColor(brief.status)}>{brief.status}</Badge>
                {brief.confluence_url && (
                  <Badge variant="outline">
                    <CheckCircle className="mr-1 h-3 w-3" />
                    Published to Confluence
                  </Badge>
                )}
              </div>
              <h2 className="text-2xl font-bold text-gray-900">{brief.title}</h2>
              <p className="mt-2 text-sm text-gray-500">
                Brief ID: {brief.brief_id} • Created {formatRelativeTime(brief.created_at)}
              </p>
              <div className="mt-2 flex items-center gap-4 text-sm text-gray-600">
                <span className="flex items-center gap-1">
                  <User className="h-4 w-4" />
                  {brief.owner}
                </span>
                <span>Signal: {brief.signal_id}</span>
              </div>
            </div>

            <Separator />

            {/* Customer */}
            <div>
              <h3 className="flex items-center gap-2 mb-3 font-semibold text-gray-900">
                <Target className="h-5 w-5" />
                Customer
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-700">Segment</p>
                  <p className="mt-1 text-gray-900">{brief.customer.segment}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-700">Buyer Role</p>
                  <p className="mt-1 text-gray-900">{brief.customer.buyer_role}</p>
                </div>
              </div>
            </div>

            {/* Problem */}
            <div>
              <h3 className="mb-3 font-semibold text-gray-900">Problem</h3>
              <div className="space-y-3">
                <div>
                  <p className="text-sm font-medium text-gray-700">Core Pain Point</p>
                  <p className="mt-1 text-gray-900">{brief.problem.pain}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-700">Why Now?</p>
                  <p className="mt-1 text-gray-900">{brief.problem.why_now}</p>
                </div>
              </div>
            </div>

            {/* Solution */}
            <div>
              <h3 className="mb-3 font-semibold text-gray-900">Solution Hypothesis</h3>
              <div>
                <p className="text-sm font-medium text-gray-700">Approach</p>
                <p className="mt-1 text-gray-900">{brief.solution_hypothesis.approach}</p>
              </div>
            </div>

            {/* KPIs */}
            {brief.kpis && brief.kpis.length > 0 && (
              <div>
                <h3 className="mb-3 font-semibold text-gray-900">Target KPIs</h3>
                <div className="grid gap-2 md:grid-cols-2">
                  {brief.kpis.map((kpi, idx) => (
                    <div key={idx} className="rounded-lg border bg-blue-50 p-3">
                      <p className="font-medium text-blue-900">{kpi}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Validation Plan */}
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
              <h3 className="flex items-center gap-2 mb-3 font-semibold text-blue-900">
                <Calendar className="h-5 w-5" />
                Validation Plan
              </h3>
              <div className="grid grid-cols-2 gap-4 mb-3">
                <div>
                  <p className="text-sm font-medium text-blue-900">Method</p>
                  <p className="mt-1 text-blue-800">{brief.validation_plan.method}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-blue-900">Timebox</p>
                  <p className="mt-1 text-blue-800">{brief.validation_plan.timebox_days} days</p>
                </div>
              </div>
              <div>
                <p className="text-sm font-medium text-blue-900">Validation Questions</p>
                <ul className="mt-2 list-inside list-disc space-y-1 text-blue-800">
                  {brief.validation_plan.questions.map((q, idx) => (
                    <li key={idx}>{q}</li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Risks */}
            {brief.risks && brief.risks.length > 0 && (
              <div className="rounded-lg border border-orange-200 bg-orange-50 p-4">
                <h3 className="flex items-center gap-2 mb-3 font-semibold text-orange-900">
                  <AlertTriangle className="h-5 w-5" />
                  Risks ({brief.risks.length})
                </h3>
                <ul className="space-y-2">
                  {brief.risks.map((risk, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-gray-700">
                      <span className="mt-1 text-orange-500">•</span>
                      <span>{risk}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Actions */}
            <div className="flex flex-wrap gap-3 pt-4">
              {brief.confluence_url && (
                <a href={brief.confluence_url} target="_blank" rel="noopener noreferrer">
                  <Button variant="outline">
                    <ExternalLink className="mr-2 h-4 w-4" />
                    View in Confluence
                  </Button>
                </a>
              )}

              {(brief.status === 'DRAFT' || brief.status === 'REVIEW') && (
                <Button
                  onClick={() => approveMutation.mutate()}
                  disabled={approveMutation.isPending}
                >
                  <Upload className="mr-2 h-4 w-4" />
                  {approveMutation.isPending ? 'Approving...' : 'Approve & Publish'}
                </Button>
              )}

              {brief.status === 'APPROVED' && (
                <Button
                  onClick={() => startValidationMutation.mutate()}
                  disabled={startValidationMutation.isPending}
                >
                  <Rocket className="mr-2 h-4 w-4" />
                  {startValidationMutation.isPending ? 'Starting...' : 'Start Validation'}
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

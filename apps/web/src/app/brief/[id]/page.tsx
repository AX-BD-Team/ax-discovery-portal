'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { briefApi, inboxApi } from '@ax/api-client'
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
  CheckCircle,
  ExternalLink,
  User,
  Target,
  AlertTriangle,
  Calendar,
  Rocket,
  Upload,
} from 'lucide-react'
import Link from 'next/link'

export default function BriefDetailPage({ params }: { params: { id: string } }) {
  const queryClient = useQueryClient()
  const briefId = params.id

  // Fetch brief
  const { data: brief, isLoading } = useQuery({
    queryKey: ['brief', briefId],
    queryFn: () => briefApi.getBrief(briefId),
  })

  // Fetch signal info
  const { data: signal } = useQuery({
    queryKey: ['signal', brief?.signal_id],
    queryFn: () => inboxApi.getSignal(brief!.signal_id),
    enabled: !!brief,
  })

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: () => briefApi.approveBrief(briefId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brief', briefId] })
      queryClient.invalidateQueries({ queryKey: ['briefs'] })
    },
  })

  // Start validation mutation
  const startValidationMutation = useMutation({
    mutationFn: () => briefApi.startValidation(briefId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brief', briefId] })
      queryClient.invalidateQueries({ queryKey: ['briefs'] })
    },
  })

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
          <p className="text-gray-600">Loading brief...</p>
        </div>
      </div>
    )
  }

  if (!brief) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">Brief not found</p>
          <Link href="/brief">
            <Button variant="outline" className="mt-4">
              Back to Briefs
            </Button>
          </Link>
        </div>
      </div>
    )
  }

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
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-6">
          <Link href="/brief">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Briefs
            </Button>
          </Link>
        </div>

        {/* Brief Header */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="mb-3 flex items-center gap-2">
                  <Badge className={getStatusColor(brief.status)}>{brief.status}</Badge>
                  {brief.confluence_url && (
                    <Badge variant="outline">
                      <CheckCircle className="mr-1 h-3 w-3" />
                      Published to Confluence
                    </Badge>
                  )}
                </div>
                <CardTitle className="text-2xl">{brief.title}</CardTitle>
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
            </div>
          </CardHeader>
        </Card>

        {/* Customer */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              Customer
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-gray-700">Segment</p>
                <p className="mt-1 text-gray-900">{brief.customer.segment}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-700">Buyer Role</p>
                <p className="mt-1 text-gray-900">{brief.customer.buyer_role}</p>
              </div>
              {brief.customer.users && (
                <div>
                  <p className="text-sm font-medium text-gray-700">End Users</p>
                  <p className="mt-1 text-gray-900">{brief.customer.users}</p>
                </div>
              )}
              {brief.customer.account && (
                <div>
                  <p className="text-sm font-medium text-gray-700">Account</p>
                  <p className="mt-1 text-gray-900">{brief.customer.account}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Problem */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Problem</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-medium text-gray-700">Core Pain Point</p>
              <p className="mt-2 text-gray-900">{brief.problem.pain}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-700">Why Now?</p>
              <p className="mt-2 text-gray-900">{brief.problem.why_now}</p>
            </div>
            {brief.problem.current_process && (
              <div>
                <p className="text-sm font-medium text-gray-700">Current Process</p>
                <p className="mt-2 text-gray-900">{brief.problem.current_process}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Solution Hypothesis */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Solution Hypothesis</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-medium text-gray-700">Approach</p>
              <p className="mt-2 text-gray-900">{brief.solution_hypothesis.approach}</p>
            </div>

            {brief.solution_hypothesis.integration_points.length > 0 && (
              <div>
                <p className="text-sm font-medium text-gray-700">Integration Points</p>
                <ul className="mt-2 list-inside list-disc space-y-1 text-gray-900">
                  {brief.solution_hypothesis.integration_points.map((point, idx) => (
                    <li key={idx}>{point}</li>
                  ))}
                </ul>
              </div>
            )}

            {brief.solution_hypothesis.data_needed &&
              brief.solution_hypothesis.data_needed.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-gray-700">Data Needed</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {brief.solution_hypothesis.data_needed.map((data, idx) => (
                      <Badge key={idx} variant="secondary">
                        {data}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
          </CardContent>
        </Card>

        {/* KPIs */}
        {brief.kpis && brief.kpis.length > 0 && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Target KPIs</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-2">
                {brief.kpis.map((kpi, idx) => (
                  <div key={idx} className="rounded-lg border bg-blue-50 p-3">
                    <p className="font-medium text-blue-900">{kpi}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Evidence */}
        {brief.evidence && brief.evidence.length > 0 && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Evidence ({brief.evidence.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {brief.evidence.map((link, idx) => (
                  <a
                    key={idx}
                    href={link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 rounded-lg border p-3 hover:bg-gray-50"
                  >
                    <ExternalLink className="h-4 w-4 text-gray-400" />
                    <span className="text-sm text-blue-600 hover:underline">{link}</span>
                  </a>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Validation Plan */}
        <Card className="mb-6 border-blue-200 bg-blue-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-blue-900">
              <Calendar className="h-5 w-5" />
              Validation Plan
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
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

            <div>
              <p className="text-sm font-medium text-blue-900">Success Criteria</p>
              <ul className="mt-2 list-inside list-disc space-y-1 text-blue-800">
                {brief.validation_plan.success_criteria.map((c, idx) => (
                  <li key={idx}>{c}</li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* MVP Scope */}
        {brief.mvp_scope && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>MVP Scope</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {brief.mvp_scope.in_scope && brief.mvp_scope.in_scope.length > 0 && (
                <div>
                  <p className="mb-2 text-sm font-medium text-green-700">✓ In Scope</p>
                  <ul className="list-inside list-disc space-y-1 text-gray-900">
                    {brief.mvp_scope.in_scope.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
              {brief.mvp_scope.out_of_scope && brief.mvp_scope.out_of_scope.length > 0 && (
                <div>
                  <p className="mb-2 text-sm font-medium text-red-700">✗ Out of Scope</p>
                  <ul className="list-inside list-disc space-y-1 text-gray-600">
                    {brief.mvp_scope.out_of_scope.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Risks */}
        {brief.risks && brief.risks.length > 0 && (
          <Card className="mb-6 border-orange-200">
            <CardHeader className="bg-orange-50">
              <CardTitle className="flex items-center gap-2 text-orange-900">
                <AlertTriangle className="h-5 w-5" />
                Risks ({brief.risks.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <ul className="space-y-2">
                {brief.risks.map((risk, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-gray-700">
                    <span className="mt-1 text-orange-500">•</span>
                    <span>{risk}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* Actions */}
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-3">
              {/* View Signal */}
              <div className="flex gap-3">
                <Link href={`/inbox/${brief.signal_id}`} className="flex-1">
                  <Button variant="outline" className="w-full">
                    View Source Signal
                  </Button>
                </Link>
                {brief.confluence_url && (
                  <a
                    href={brief.confluence_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1"
                  >
                    <Button variant="outline" className="w-full">
                      <ExternalLink className="mr-2 h-4 w-4" />
                      View in Confluence
                    </Button>
                  </a>
                )}
              </div>

              {/* Approve */}
              {(brief.status === 'DRAFT' || brief.status === 'REVIEW') && (
                <Button
                  onClick={() => approveMutation.mutate()}
                  disabled={approveMutation.isPending}
                  className="w-full"
                >
                  <Upload className="mr-2 h-4 w-4" />
                  {approveMutation.isPending ? 'Approving...' : 'Approve & Publish to Confluence'}
                </Button>
              )}

              {/* Start Validation */}
              {brief.status === 'APPROVED' && (
                <Button
                  onClick={() => startValidationMutation.mutate()}
                  disabled={startValidationMutation.isPending}
                  className="w-full"
                >
                  <Rocket className="mr-2 h-4 w-4" />
                  {startValidationMutation.isPending ? 'Starting...' : 'Start Validation Sprint'}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

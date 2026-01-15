'use client'

import type { Brief } from '@ax/types'
import { Card, CardContent, CardHeader, Badge, Button } from '@ax/ui'
import { formatRelativeTime } from '@ax/utils'
import { ExternalLink, User, Target, Calendar, CheckCircle, Clock } from 'lucide-react'
import Link from 'next/link'

interface BriefCardProps {
  brief: Brief
  onViewDetail?: (briefId: string) => void
}

export function BriefCard({ brief, onViewDetail }: BriefCardProps) {
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

  const getValidationMethodLabel = (method: string) => {
    const labels: Record<string, string> = {
      '5DAY_SPRINT': '5-Day Sprint',
      'INTERVIEW': 'Customer Interview',
      'DATA_ANALYSIS': 'Data Analysis',
      'BUYER_REVIEW': 'Buyer Review',
      'POC': 'Proof of Concept',
    }
    return labels[method] || method
  }

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Badge className={getStatusColor(brief.status)}>
                {brief.status}
              </Badge>
              {brief.confluence_url && (
                <Badge variant="outline">
                  <CheckCircle className="mr-1 h-3 w-3" />
                  Published
                </Badge>
              )}
            </div>
            <h3 className="text-xl font-semibold text-gray-900">{brief.title}</h3>
            <p className="mt-1 text-sm text-gray-500 flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatRelativeTime(brief.created_at)}
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={() => onViewDetail?.(brief.brief_id)}>
              <ExternalLink className="h-4 w-4" />
            </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Customer */}
          <div>
            <p className="text-sm font-medium text-gray-700 flex items-center gap-1">
              <Target className="h-4 w-4" />
              Customer
            </p>
            <div className="mt-1 flex flex-wrap gap-2">
              <Badge variant="secondary">{brief.customer.segment}</Badge>
              <Badge variant="outline">Buyer: {brief.customer.buyer_role}</Badge>
              {brief.customer.account && (
                <Badge variant="outline">Account: {brief.customer.account}</Badge>
              )}
            </div>
          </div>

          {/* Problem */}
          <div>
            <p className="text-sm font-medium text-gray-700">Pain Point</p>
            <p className="mt-1 text-sm text-gray-600 line-clamp-2">{brief.problem.pain}</p>
          </div>

          {/* Solution */}
          <div>
            <p className="text-sm font-medium text-gray-700">Solution Approach</p>
            <p className="mt-1 text-sm text-gray-600 line-clamp-2">
              {brief.solution_hypothesis.approach}
            </p>
          </div>

          {/* KPIs */}
          {brief.kpis && brief.kpis.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700">Target KPIs</p>
              <div className="mt-1 flex flex-wrap gap-2">
                {brief.kpis.slice(0, 3).map((kpi, idx) => (
                  <Badge key={idx} variant="secondary">
                    {kpi}
                  </Badge>
                ))}
                {brief.kpis.length > 3 && (
                  <Badge variant="outline">+{brief.kpis.length - 3} more</Badge>
                )}
              </div>
            </div>
          )}

          {/* Validation Plan */}
          <div className="rounded-lg border bg-blue-50 p-3">
            <p className="text-sm font-medium text-blue-900 flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              Validation Plan
            </p>
            <div className="mt-2 flex items-center justify-between text-sm">
              <span className="text-blue-800">
                {getValidationMethodLabel(brief.validation_plan.method)}
              </span>
              <span className="font-medium text-blue-900">
                {brief.validation_plan.timebox_days} days
              </span>
            </div>
            <p className="mt-1 text-xs text-blue-700">
              {brief.validation_plan.questions.length} validation question(s)
            </p>
          </div>

          {/* Risks */}
          {brief.risks && brief.risks.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700">Key Risks</p>
              <p className="mt-1 text-sm text-gray-600">
                {brief.risks.slice(0, 2).join(', ')}
                {brief.risks.length > 2 && ` (+${brief.risks.length - 2} more)`}
              </p>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center gap-4 text-sm text-gray-500 pt-2 border-t">
            <span className="flex items-center gap-1">
              <User className="h-4 w-4" />
              {brief.owner}
            </span>
            <span>Signal: {brief.signal_id}</span>
            {brief.confluence_url && (
              <a
                href={brief.confluence_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline flex items-center gap-1"
              >
                View in Confluence
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

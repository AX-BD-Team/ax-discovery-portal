'use client'

import type { KPIDigest } from '@ax/types'
import { Card, CardContent, CardHeader, CardTitle, Badge } from '@ax/ui'
import { TrendingUp, TrendingDown, Target, Clock } from 'lucide-react'

interface KPIDigestCardProps {
  digest: KPIDigest
}

export function KPIDigestCard({ digest }: KPIDigestCardProps) {
  const getProgressColor = (actual: number, target: number) => {
    const percentage = (actual / target) * 100
    if (percentage >= 100) return 'text-green-600'
    if (percentage >= 80) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getProgressIcon = (actual: number, target: number) => {
    const percentage = (actual / target) * 100
    if (percentage >= 80) {
      return <TrendingUp className="h-4 w-4 text-green-600" />
    }
    return <TrendingDown className="h-4 w-4 text-red-600" />
  }

  const metrics = [
    {
      label: 'Activities',
      actual: digest.activity_actual,
      target: digest.activity_target,
      icon: '📋',
    },
    {
      label: 'Signals',
      actual: digest.signal_actual,
      target: digest.signal_target,
      icon: '📡',
    },
    {
      label: 'Briefs',
      actual: digest.brief_actual,
      target: digest.brief_target,
      icon: '📝',
    },
    {
      label: 'S2 (Validated)',
      actual: digest.s2_actual,
      target: digest.s2_target,
      icon: '✅',
      isRange: true,
    },
  ]

  return (
    <Card className="border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-blue-900">
          <Target className="h-5 w-5" />
          KPI Digest ({digest.period.charAt(0).toUpperCase() + digest.period.slice(1)})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-4">
          {metrics.map((metric, idx) => {
            const isRange = metric.isRange
            const targetDisplay = isRange ? metric.target : metric.target
            const percentage = isRange
              ? 0
              : Math.round((metric.actual / (metric.target as number)) * 100)

            return (
              <div
                key={idx}
                className="rounded-lg border border-blue-200 bg-white p-4 shadow-sm"
              >
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-2xl">{metric.icon}</span>
                  {!isRange && getProgressIcon(metric.actual, metric.target as number)}
                </div>
                <p className="text-sm font-medium text-gray-700">{metric.label}</p>
                <div className="mt-2 flex items-baseline gap-2">
                  <span
                    className={`text-2xl font-bold ${isRange ? 'text-gray-900' : getProgressColor(metric.actual, metric.target as number)}`}
                  >
                    {metric.actual}
                  </span>
                  <span className="text-sm text-gray-500">/ {targetDisplay}</span>
                </div>
                {!isRange && (
                  <div className="mt-2">
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-200">
                      <div
                        className={`h-full ${
                          percentage >= 100
                            ? 'bg-green-500'
                            : percentage >= 80
                              ? 'bg-yellow-500'
                              : 'bg-red-500'
                        }`}
                        style={{ width: `${Math.min(percentage, 100)}%` }}
                      />
                    </div>
                    <p className="mt-1 text-xs text-gray-600">{percentage}% achieved</p>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Cycle Time Metrics */}
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-purple-600" />
              <p className="text-sm font-medium text-purple-900">Avg. Signal → Brief</p>
            </div>
            <p className="mt-2 text-2xl font-bold text-purple-900">
              {digest.avg_signal_to_brief_days.toFixed(1)} days
            </p>
          </div>
          <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-indigo-600" />
              <p className="text-sm font-medium text-indigo-900">Avg. Brief → S2</p>
            </div>
            <p className="mt-2 text-2xl font-bold text-indigo-900">
              {digest.avg_brief_to_s2_days.toFixed(1)} days
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

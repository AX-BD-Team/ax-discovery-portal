'use client'

import { useQuery } from '@tanstack/react-query'
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ax/ui'
import { inboxApi, scorecardApi, briefApi, playsApi } from '@ax/api-client'
import Link from 'next/link'
import { TrendingUp, TrendingDown, AlertCircle, Loader2, Target, Clock } from 'lucide-react'

export default function Home() {
  // KPI Digest 데이터
  const { data: kpiDigest, isLoading: kpiLoading } = useQuery({
    queryKey: ['kpi-digest'],
    queryFn: () => playsApi.getKPIDigest('week'),
  })

  // Inbox 통계
  const { data: inboxStats, isLoading: inboxLoading } = useQuery({
    queryKey: ['inbox-stats'],
    queryFn: () => inboxApi.getStats(),
  })

  // Scorecard 분포
  const { data: scorecardDist, isLoading: scorecardLoading } = useQuery({
    queryKey: ['scorecard-distribution'],
    queryFn: () => scorecardApi.getDistribution(),
  })

  // Brief 목록 (개수만)
  const { data: briefs, isLoading: briefLoading } = useQuery({
    queryKey: ['briefs'],
    queryFn: () => briefApi.getBriefs({ page_size: 1 }),
  })

  // KPI 알림
  const { data: kpiAlerts } = useQuery({
    queryKey: ['kpi-alerts'],
    queryFn: () => playsApi.getKPIAlerts(),
  })

  const getProgressColor = (actual: number, target: number) => {
    const percentage = (actual / target) * 100
    if (percentage >= 100) return 'text-green-600'
    if (percentage >= 80) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getProgressBgColor = (actual: number, target: number) => {
    const percentage = (actual / target) * 100
    if (percentage >= 100) return 'bg-green-500'
    if (percentage >= 80) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const alertCount = kpiAlerts
    ? kpiAlerts.alerts.length + kpiAlerts.red_plays.length + kpiAlerts.overdue_briefs.length
    : 0

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4 md:p-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-6 text-center md:mb-8">
          <h1 className="mb-2 text-3xl font-bold text-gray-900 md:mb-4 md:text-5xl">AX Discovery Portal</h1>
          <p className="text-base text-gray-600 md:text-xl">
            멀티에이전트 기반 사업기회 포착 엔진
          </p>
        </header>

        {/* KPI Summary Section */}
        <Card className="mb-8 border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-blue-900">
              <Target className="h-5 w-5" />
              주간 KPI 현황
              {alertCount > 0 && (
                <span className="ml-2 flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                  <AlertCircle className="h-3 w-3" />
                  {alertCount}개 알림
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {kpiLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                <span className="ml-2 text-gray-600">KPI 데이터 로딩 중...</span>
              </div>
            ) : kpiDigest ? (
              <>
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
                  {[
                    { label: 'Activity', actual: kpiDigest.activity_actual ?? 0, target: kpiDigest.activity_target ?? 20, icon: '📋' },
                    { label: 'Signal', actual: kpiDigest.signal_actual ?? 0, target: kpiDigest.signal_target ?? 30, icon: '📡' },
                    { label: 'Brief', actual: kpiDigest.brief_actual ?? 0, target: kpiDigest.brief_target ?? 6, icon: '📝' },
                    { label: 'S2', actual: kpiDigest.s2_actual ?? 0, target: kpiDigest.s2_target ?? '2~4', icon: '✅', isRange: true },
                  ].map((metric, idx) => {
                    const isRange = metric.isRange
                    const targetNum = isRange ? 3 : (metric.target as number)
                    const percentage = Math.round(((metric.actual || 0) / targetNum) * 100)

                    return (
                      <div key={idx} className="rounded-lg border border-blue-200 bg-white p-3 shadow-sm">
                        <div className="flex items-center justify-between">
                          <span className="text-lg">{metric.icon}</span>
                          {percentage >= 80 ? (
                            <TrendingUp className="h-4 w-4 text-green-600" />
                          ) : (
                            <TrendingDown className="h-4 w-4 text-red-600" />
                          )}
                        </div>
                        <p className="text-xs font-medium text-gray-600">{metric.label}</p>
                        <div className="flex items-baseline gap-1">
                          <span className={`text-xl font-bold ${isRange ? 'text-gray-900' : getProgressColor(metric.actual, targetNum)}`}>
                            {metric.actual}
                          </span>
                          <span className="text-xs text-gray-500">/ {metric.target}</span>
                        </div>
                        {!isRange && (
                          <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-gray-200">
                            <div
                              className={`h-full ${getProgressBgColor(metric.actual, targetNum)}`}
                              style={{ width: `${Math.min(percentage, 100)}%` }}
                            />
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>

                {/* Cycle Time */}
                <div className="mt-4 grid gap-3 md:grid-cols-2 md:gap-4">
                  <div className="flex flex-wrap items-center gap-2 rounded-lg border border-purple-200 bg-purple-50 px-3 py-2 md:gap-3 md:px-4">
                    <Clock className="h-4 w-4 text-purple-600" />
                    <span className="text-xs text-purple-900 md:text-sm">Signal → Brief:</span>
                    <span className="font-bold text-purple-900">{(kpiDigest.avg_signal_to_brief_days ?? 0).toFixed(1)}일</span>
                    <span className="text-xs text-purple-600">(≤7일)</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 md:gap-3 md:px-4">
                    <Clock className="h-4 w-4 text-indigo-600" />
                    <span className="text-xs text-indigo-900 md:text-sm">Brief → S2:</span>
                    <span className="font-bold text-indigo-900">{(kpiDigest.avg_brief_to_s2_days ?? 0).toFixed(1)}일</span>
                    <span className="text-xs text-indigo-600">(≤14일)</span>
                  </div>
                </div>
              </>
            ) : (
              <p className="py-4 text-center text-gray-500">KPI 데이터를 불러올 수 없습니다</p>
            )}
          </CardContent>
        </Card>

        {/* Navigation Cards */}
        <div className="grid gap-4 sm:grid-cols-2 md:gap-6 lg:grid-cols-3">
          <Card className="transition-shadow hover:shadow-lg">
            <CardHeader>
              <CardTitle>📥 Inbox</CardTitle>
              <CardDescription>신규 Signal 관리 및 Triage</CardDescription>
            </CardHeader>
            <CardContent>
              {inboxLoading ? (
                <div className="mb-4 flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm text-gray-500">로딩 중...</span>
                </div>
              ) : inboxStats ? (
                <div className="mb-4 space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">총 Signal</span>
                    <span className="font-semibold">{inboxStats.total}개</span>
                  </div>
                  <div className="flex gap-2">
                    {Object.entries(inboxStats.by_status).slice(0, 3).map(([status, count]) => (
                      <span key={status} className="rounded-full bg-gray-100 px-2 py-0.5 text-xs">
                        {status}: {count}
                      </span>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="mb-4 text-sm text-gray-600">
                  고객 Pain Point를 수집하고, 사업기회 신호를 등록합니다.
                </p>
              )}
              <Link href="/inbox">
                <Button className="w-full">Inbox 보기</Button>
              </Link>
            </CardContent>
          </Card>

          <Card className="transition-shadow hover:shadow-lg">
            <CardHeader>
              <CardTitle>📊 Scorecard</CardTitle>
              <CardDescription>Signal 평가 및 우선순위 결정</CardDescription>
            </CardHeader>
            <CardContent>
              {scorecardLoading ? (
                <div className="mb-4 flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm text-gray-500">로딩 중...</span>
                </div>
              ) : scorecardDist ? (
                <div className="mb-4 space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">평균 점수</span>
                    <span className="font-semibold">{(scorecardDist.avg_score ?? 0).toFixed(1)}점</span>
                  </div>
                  {scorecardDist.ranges && scorecardDist.ranges.length > 0 && (
                    <div className="flex gap-1">
                      {scorecardDist.ranges.map((r) => (
                        <div
                          key={r.range}
                          className="flex-1 rounded bg-blue-100 px-1 py-0.5 text-center text-xs"
                          title={r.range}
                        >
                          {r.count}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <p className="mb-4 text-sm text-gray-600">
                  100점 만점 스코어카드로 기회를 평가합니다.
                </p>
              )}
              <Link href="/scorecard">
                <Button className="w-full">Scorecard 보기</Button>
              </Link>
            </CardContent>
          </Card>

          <Card className="transition-shadow hover:shadow-lg">
            <CardHeader>
              <CardTitle>📝 Brief</CardTitle>
              <CardDescription>1-Page Opportunity Brief</CardDescription>
            </CardHeader>
            <CardContent>
              {briefLoading ? (
                <div className="mb-4 flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm text-gray-500">로딩 중...</span>
                </div>
              ) : briefs ? (
                <div className="mb-4 space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">등록된 Brief</span>
                    <span className="font-semibold">{Array.isArray(briefs) ? briefs.length : 0}개</span>
                  </div>
                  <p className="text-xs text-gray-500">
                    검증된 기회를 Brief로 정리하여 Confluence에 발행합니다.
                  </p>
                </div>
              ) : (
                <p className="mb-4 text-sm text-gray-600">
                  검증된 기회를 Brief로 정리하여 Confluence에 발행합니다.
                </p>
              )}
              <Link href="/brief">
                <Button className="w-full">Brief 보기</Button>
              </Link>
            </CardContent>
          </Card>

          <Card className="transition-shadow hover:shadow-lg">
            <CardHeader>
              <CardTitle>🎯 Play Dashboard</CardTitle>
              <CardDescription>비즈니스 케이스 추적</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-gray-600">
                Play별 진행 상황을 대시보드에서 한눈에 파악합니다.
              </p>
              <Link href="/plays">
                <Button className="w-full">Dashboard 보기</Button>
              </Link>
            </CardContent>
          </Card>

          <Card className="transition-shadow hover:shadow-lg">
            <CardHeader>
              <CardTitle>📅 외부 세미나</CardTitle>
              <CardDescription>세미나/이벤트 수집</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-gray-600">
                외부 세미나, 컨퍼런스, 이벤트 정보를 수집합니다.
              </p>
              <Link href="/activities">
                <Button className="w-full">세미나 보기</Button>
              </Link>
            </CardContent>
          </Card>

          <Card className="transition-shadow hover:shadow-lg">
            <CardHeader>
              <CardTitle>⚙️ Settings</CardTitle>
              <CardDescription>시스템 설정</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-gray-600">
                Confluence, Teams 연동 및 에이전트 설정을 관리합니다.
              </p>
              <Button className="w-full" variant="outline" disabled>
                Coming Soon
              </Button>
            </CardContent>
          </Card>
        </div>

        <footer className="mt-8 text-center text-sm text-gray-500 md:mt-16">
          <p>Powered by Claude Agent SDK & Next.js 15</p>
          <p className="mt-1 md:mt-2">Version 0.5.0 - PoC Complete</p>
        </footer>
      </div>
    </div>
  )
}

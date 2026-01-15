'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { scorecardApi, inboxApi } from '@ax/api-client'
import type { Scorecard, ScorecardDecision } from '@ax/types'
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Badge,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@ax/ui'
import { formatRelativeTime } from '@ax/utils'
import { Search, TrendingUp, AlertCircle, BarChart3, CheckCircle } from 'lucide-react'
import { ScorecardCard } from './components/scorecard-card'
import { ScoreDistributionChart } from './components/score-distribution-chart'
import { EvaluateDialog } from './components/evaluate-dialog'
import { ScorecardDetailModal } from './components/scorecard-detail-modal'

export default function ScorecardPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [filterDecision, setFilterDecision] = useState<ScorecardDecision | 'ALL'>('ALL')
  const [filterScoreRange, setFilterScoreRange] = useState<'ALL' | 'HIGH' | 'MEDIUM' | 'LOW'>('ALL')
  const [isEvaluateDialogOpen, setIsEvaluateDialogOpen] = useState(false)
  const [selectedSignalId, setSelectedSignalId] = useState<string | null>(null)

  // Fetch signals for evaluation (NEW and SCORING status)
  const { data: signals = [] } = useQuery({
    queryKey: ['signals'],
    queryFn: inboxApi.getSignals,
  })

  // Fetch score distribution stats
  const { data: distribution } = useQuery({
    queryKey: ['scorecard-distribution'],
    queryFn: scorecardApi.getDistribution,
  })

  // Fetch scorecards from API
  const { data: scorecardsData, isLoading: isLoadingScorecards } = useQuery({
    queryKey: ['scorecards', filterDecision, filterScoreRange],
    queryFn: () => scorecardApi.getScorecards({
      decision: filterDecision !== 'ALL' ? filterDecision : undefined,
      min_score: filterScoreRange === 'HIGH' ? 70 : filterScoreRange === 'MEDIUM' ? 50 : filterScoreRange === 'LOW' ? 0 : undefined,
      max_score: filterScoreRange === 'HIGH' ? 100 : filterScoreRange === 'MEDIUM' ? 69 : filterScoreRange === 'LOW' ? 49 : undefined,
      page_size: 100,
    }),
  })

  const scorecards = scorecardsData?.items ?? []

  // Filter scorecards
  const filteredScorecards = scorecards.filter(scorecard => {
    const matchesDecision =
      filterDecision === 'ALL' || scorecard.recommendation.decision === filterDecision

    const matchesScoreRange =
      filterScoreRange === 'ALL' ||
      (filterScoreRange === 'HIGH' && scorecard.total_score >= 70) ||
      (filterScoreRange === 'MEDIUM' &&
        scorecard.total_score >= 50 &&
        scorecard.total_score < 70) ||
      (filterScoreRange === 'LOW' && scorecard.total_score < 50)

    return matchesDecision && matchesScoreRange
  })

  // Group by decision
  const scorecardsByDecision = filteredScorecards.reduce(
    (acc, scorecard) => {
      const decision = scorecard.recommendation.decision
      if (!acc[decision]) {
        acc[decision] = []
      }
      acc[decision].push(scorecard)
      return acc
    },
    {} as Record<ScorecardDecision, Scorecard[]>
  )

  // Count signals available for evaluation
  const availableSignals = signals.filter(
    s => s.status === 'NEW' || s.status === 'SCORING'
  ).length

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-gray-900">📊 Scorecard</h1>
              <p className="mt-2 text-gray-600">Signal 평가 및 우선순위 결정</p>
            </div>
            <Button onClick={() => setIsEvaluateDialogOpen(true)} size="lg">
              <TrendingUp className="mr-2 h-5 w-5" />
              Evaluate Signal
            </Button>
          </div>

          {/* Stats */}
          <div className="mt-6 grid gap-4 md:grid-cols-5">
            <Card>
              <CardHeader className="pb-3">
                <CardDescription>Total Evaluated</CardDescription>
                <CardTitle className="text-3xl">{scorecards.length}</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-3">
                <CardDescription>Available to Evaluate</CardDescription>
                <CardTitle className="text-3xl text-blue-600">{availableSignals}</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-3">
                <CardDescription>GO Decision</CardDescription>
                <CardTitle className="text-3xl text-green-600">
                  {scorecardsByDecision.GO?.length || 0}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-3">
                <CardDescription>PIVOT</CardDescription>
                <CardTitle className="text-3xl text-yellow-600">
                  {scorecardsByDecision.PIVOT?.length || 0}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-3">
                <CardDescription>Average Score</CardDescription>
                <CardTitle className="text-3xl text-purple-600">
                  {distribution?.avg_score?.toFixed(1) || '0.0'}
                </CardTitle>
              </CardHeader>
            </Card>
          </div>
        </div>

        {/* Score Distribution Chart */}
        {distribution && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Score Distribution</CardTitle>
              <CardDescription>점수 분포 현황</CardDescription>
            </CardHeader>
            <CardContent>
              <ScoreDistributionChart data={distribution} />
            </CardContent>
          </Card>
        )}

        {/* Filters */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="grid gap-4 md:grid-cols-2">
              {/* Decision filter */}
              <Select
                value={filterDecision}
                onValueChange={v => setFilterDecision(v as any)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Filter by decision" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Decisions</SelectItem>
                  <SelectItem value="GO">GO (70+)</SelectItem>
                  <SelectItem value="PIVOT">PIVOT (50-69)</SelectItem>
                  <SelectItem value="HOLD">HOLD (30-49)</SelectItem>
                  <SelectItem value="NO_GO">NO_GO (&lt;30)</SelectItem>
                </SelectContent>
              </Select>

              {/* Score range filter */}
              <Select
                value={filterScoreRange}
                onValueChange={v => setFilterScoreRange(v as any)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Filter by score range" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Scores</SelectItem>
                  <SelectItem value="HIGH">High (70-100)</SelectItem>
                  <SelectItem value="MEDIUM">Medium (50-69)</SelectItem>
                  <SelectItem value="LOW">Low (0-49)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Scorecard List */}
        {isLoadingScorecards ? (
          <Card>
            <CardContent className="py-12 text-center">
              <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600" />
              <p className="text-lg font-medium text-gray-900">Loading Scorecards...</p>
            </CardContent>
          </Card>
        ) : scorecards.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <BarChart3 className="mx-auto mb-4 h-12 w-12 text-gray-400" />
              <p className="mb-2 text-lg font-medium text-gray-900">No Scorecards Yet</p>
              <p className="mb-4 text-gray-600">
                {availableSignals > 0
                  ? `${availableSignals} signal(s) available for evaluation`
                  : 'No signals available for evaluation'}
              </p>
              <Button onClick={() => setIsEvaluateDialogOpen(true)}>
                <TrendingUp className="mr-2 h-4 w-4" />
                Start Evaluation
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Tabs defaultValue="all" className="space-y-4">
            <TabsList>
              <TabsTrigger value="all">All ({filteredScorecards.length})</TabsTrigger>
              <TabsTrigger value="go">
                GO ({scorecardsByDecision.GO?.length || 0})
              </TabsTrigger>
              <TabsTrigger value="pivot">
                PIVOT ({scorecardsByDecision.PIVOT?.length || 0})
              </TabsTrigger>
              <TabsTrigger value="hold">
                HOLD ({scorecardsByDecision.HOLD?.length || 0})
              </TabsTrigger>
              <TabsTrigger value="no-go">
                NO_GO ({scorecardsByDecision.NO_GO?.length || 0})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="all" className="space-y-4">
              {filteredScorecards.map(scorecard => (
                <ScorecardCard key={scorecard.scorecard_id || scorecard.signal_id} scorecard={scorecard} onViewDetail={setSelectedSignalId} />
              ))}
            </TabsContent>

            <TabsContent value="go" className="space-y-4">
              {scorecardsByDecision.GO?.map(scorecard => (
                <ScorecardCard key={scorecard.scorecard_id || scorecard.signal_id} scorecard={scorecard} onViewDetail={setSelectedSignalId} />
              ))}
            </TabsContent>

            <TabsContent value="pivot" className="space-y-4">
              {scorecardsByDecision.PIVOT?.map(scorecard => (
                <ScorecardCard key={scorecard.scorecard_id || scorecard.signal_id} scorecard={scorecard} onViewDetail={setSelectedSignalId} />
              ))}
            </TabsContent>

            <TabsContent value="hold" className="space-y-4">
              {scorecardsByDecision.HOLD?.map(scorecard => (
                <ScorecardCard key={scorecard.scorecard_id || scorecard.signal_id} scorecard={scorecard} onViewDetail={setSelectedSignalId} />
              ))}
            </TabsContent>

            <TabsContent value="no-go" className="space-y-4">
              {scorecardsByDecision.NO_GO?.map(scorecard => (
                <ScorecardCard key={scorecard.scorecard_id || scorecard.signal_id} scorecard={scorecard} onViewDetail={setSelectedSignalId} />
              ))}
            </TabsContent>
          </Tabs>
        )}
      </div>

      {/* Evaluate Dialog */}
      <EvaluateDialog
        open={isEvaluateDialogOpen}
        onOpenChange={setIsEvaluateDialogOpen}
        availableSignals={signals.filter(s => s.status === 'NEW' || s.status === 'SCORING')}
      />

      {/* Detail Modal */}
      <ScorecardDetailModal
        signalId={selectedSignalId}
        open={!!selectedSignalId}
        onOpenChange={(open) => !open && setSelectedSignalId(null)}
      />
    </div>
  )
}

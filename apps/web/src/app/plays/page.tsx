'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { playsApi } from '@ax/api-client'
import type { PlayRecord } from '@ax/types'
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
} from '@ax/ui'
import { Search, TrendingUp, Activity, Target, Award } from 'lucide-react'
import { PlayCard } from './components/play-card'
import { KPIDigestCard } from './components/kpi-digest-card'
import { PlayDetailModal } from './components/play-detail-modal'

export default function PlaysPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<'G' | 'Y' | 'R' | 'ALL'>('ALL')
  const [selectedPlayId, setSelectedPlayId] = useState<string | null>(null)

  // Fetch plays
  const { data: playsResponse, isLoading } = useQuery({
    queryKey: ['plays', filterStatus],
    queryFn: () =>
      playsApi.getPlays({
        status: filterStatus === 'ALL' ? undefined : filterStatus,
      }),
  })

  const plays = playsResponse?.items || []

  // Fetch KPI digest
  const { data: kpiDigest } = useQuery({
    queryKey: ['kpi-digest', 'week'],
    queryFn: () => playsApi.getKPIDigest('week'),
  })

  // Fetch KPI alerts
  const { data: kpiAlerts } = useQuery({
    queryKey: ['kpi-alerts'],
    queryFn: playsApi.getKPIAlerts,
  })

  // Filter plays
  const filteredPlays = plays.filter(play => {
    const matchesSearch =
      searchQuery === '' ||
      play.play_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      play.play_id.toLowerCase().includes(searchQuery.toLowerCase())

    return matchesSearch
  })

  // Group by status
  const playsByStatus = filteredPlays.reduce(
    (acc, play) => {
      if (!acc[play.status]) {
        acc[play.status] = []
      }
      acc[play.status].push(play)
      return acc
    },
    {} as Record<'G' | 'Y' | 'R', PlayRecord[]>
  )

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

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-gray-900">🎯 Play Dashboard</h1>
              <p className="mt-2 text-gray-600">Business Case Tracking & KPI Monitoring</p>
            </div>
          </div>

          {/* KPI Digest */}
          {kpiDigest && (
            <div className="mt-6">
              <KPIDigestCard digest={kpiDigest} />
            </div>
          )}

          {/* Stats */}
          <div className="mt-6 grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="pb-3">
                <CardDescription>Total Plays</CardDescription>
                <CardTitle className="text-3xl">{plays.length}</CardTitle>
              </CardHeader>
            </Card>
            <Card className="border-green-200 bg-green-50">
              <CardHeader className="pb-3">
                <CardDescription className="text-green-700">Green (On Track)</CardDescription>
                <CardTitle className="text-3xl text-green-600">
                  {playsByStatus.G?.length || 0}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card className="border-yellow-200 bg-yellow-50">
              <CardHeader className="pb-3">
                <CardDescription className="text-yellow-700">Yellow (At Risk)</CardDescription>
                <CardTitle className="text-3xl text-yellow-600">
                  {playsByStatus.Y?.length || 0}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card className="border-red-200 bg-red-50">
              <CardHeader className="pb-3">
                <CardDescription className="text-red-700">Red (Critical)</CardDescription>
                <CardTitle className="text-3xl text-red-600">
                  {playsByStatus.R?.length || 0}
                </CardTitle>
              </CardHeader>
            </Card>
          </div>

          {/* Alerts */}
          {kpiAlerts && (kpiAlerts.alerts.length > 0 || kpiAlerts.red_plays.length > 0) && (
            <Card className="mt-6 border-orange-200 bg-orange-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-orange-900">
                  <Activity className="h-5 w-5" />
                  Active Alerts
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {kpiAlerts.alerts.map((alert, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-sm text-orange-800">
                      <span className="mt-0.5">•</span>
                      <span>{alert}</span>
                    </div>
                  ))}
                  {kpiAlerts.red_plays.length > 0 && (
                    <div className="text-sm text-orange-800">
                      <strong>Red Plays:</strong> {kpiAlerts.red_plays.join(', ')}
                    </div>
                  )}
                  {kpiAlerts.overdue_briefs.length > 0 && (
                    <div className="text-sm text-orange-800">
                      <strong>Overdue Briefs:</strong> {kpiAlerts.overdue_briefs.join(', ')}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Filters */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="grid gap-4 md:grid-cols-2">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <Input
                  placeholder="Search plays..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>

              {/* Status filter */}
              <Select value={filterStatus} onValueChange={v => setFilterStatus(v as any)}>
                <SelectTrigger>
                  <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Statuses</SelectItem>
                  <SelectItem value="G">Green (On Track)</SelectItem>
                  <SelectItem value="Y">Yellow (At Risk)</SelectItem>
                  <SelectItem value="R">Red (Critical)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Play List */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
              <p className="text-gray-600">Loading plays...</p>
            </div>
          </div>
        ) : plays.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Target className="mx-auto mb-4 h-12 w-12 text-gray-400" />
              <p className="mb-2 text-lg font-medium text-gray-900">No Plays Yet</p>
              <p className="text-gray-600">Play data will be synced from Confluence Live Doc</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {filteredPlays.map(play => (
              <PlayCard key={play.play_id} play={play} onViewDetail={setSelectedPlayId} />
            ))}
          </div>
        )}
      </div>

      {/* Detail Modal */}
      <PlayDetailModal
        playId={selectedPlayId}
        open={!!selectedPlayId}
        onOpenChange={(open) => !open && setSelectedPlayId(null)}
      />
    </div>
  )
}

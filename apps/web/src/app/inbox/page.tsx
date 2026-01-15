'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { inboxApi } from '@ax/api-client'
import type { Signal, SignalStatus, SignalSource, SignalChannel } from '@ax/types'
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
import { formatDate, formatRelativeTime, getStatusColor } from '@ax/utils'
import { SIGNAL_SOURCES, SIGNAL_CHANNELS, STATUS_LABELS } from '@ax/config'
import { Plus, Search, Filter, TrendingUp, AlertCircle } from 'lucide-react'
import { CreateSignalDialog } from './components/create-signal-dialog'
import { SignalCard } from './components/signal-card'
import { SignalDetailModal } from './components/signal-detail-modal'

export default function InboxPage() {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<SignalStatus | 'ALL'>('ALL')
  const [filterSource, setFilterSource] = useState<SignalSource | 'ALL'>('ALL')
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [selectedSignalId, setSelectedSignalId] = useState<string | null>(null)

  // Fetch signals
  const { data: signals = [], isLoading } = useQuery({
    queryKey: ['signals'],
    queryFn: inboxApi.getSignals,
  })

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['inbox-stats'],
    queryFn: inboxApi.getStats,
  })

  // Triage mutation
  const triageMutation = useMutation({
    mutationFn: (signalId: string) => inboxApi.triggerTriage(signalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signals'] })
      queryClient.invalidateQueries({ queryKey: ['inbox-stats'] })
    },
  })

  // Filter signals
  const filteredSignals = signals.filter(signal => {
    const matchesSearch =
      searchQuery === '' ||
      signal.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      signal.pain.toLowerCase().includes(searchQuery.toLowerCase())

    const matchesStatus = filterStatus === 'ALL' || signal.status === filterStatus
    const matchesSource = filterSource === 'ALL' || signal.source === filterSource

    return matchesSearch && matchesStatus && matchesSource
  })

  // Group by status
  const signalsByStatus = filteredSignals.reduce(
    (acc, signal) => {
      if (!acc[signal.status]) {
        acc[signal.status] = []
      }
      acc[signal.status].push(signal)
      return acc
    },
    {} as Record<SignalStatus, Signal[]>
  )

  const handleTriage = async (signalId: string) => {
    try {
      await triageMutation.mutateAsync(signalId)
    } catch (error) {
      console.error('Triage failed:', error)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-gray-900">📥 Inbox</h1>
              <p className="mt-2 text-gray-600">Signal 수집 및 Triage</p>
            </div>
            <Button onClick={() => setIsCreateDialogOpen(true)} size="lg">
              <Plus className="mr-2 h-5 w-5" />
              New Signal
            </Button>
          </div>

          {/* Stats */}
          {stats && (
            <div className="mt-6 grid gap-4 md:grid-cols-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardDescription>Total Signals</CardDescription>
                  <CardTitle className="text-3xl">{stats.total}</CardTitle>
                </CardHeader>
              </Card>
              <Card>
                <CardHeader className="pb-3">
                  <CardDescription>New</CardDescription>
                  <CardTitle className="text-3xl text-gray-600">
                    {stats.by_status?.NEW || 0}
                  </CardTitle>
                </CardHeader>
              </Card>
              <Card>
                <CardHeader className="pb-3">
                  <CardDescription>Scored</CardDescription>
                  <CardTitle className="text-3xl text-blue-600">
                    {stats.by_status?.SCORED || 0}
                  </CardTitle>
                </CardHeader>
              </Card>
              <Card>
                <CardHeader className="pb-3">
                  <CardDescription>Brief Created</CardDescription>
                  <CardTitle className="text-3xl text-green-600">
                    {stats.by_status?.BRIEF_CREATED || 0}
                  </CardTitle>
                </CardHeader>
              </Card>
            </div>
          )}
        </div>

        {/* Filters */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="grid gap-4 md:grid-cols-3">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <Input
                  placeholder="Search signals..."
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
                  <SelectItem value="NEW">New</SelectItem>
                  <SelectItem value="SCORING">Scoring</SelectItem>
                  <SelectItem value="SCORED">Scored</SelectItem>
                  <SelectItem value="BRIEF_CREATED">Brief Created</SelectItem>
                  <SelectItem value="VALIDATED">Validated</SelectItem>
                  <SelectItem value="PILOT_READY">Pilot Ready</SelectItem>
                </SelectContent>
              </Select>

              {/* Source filter */}
              <Select value={filterSource} onValueChange={v => setFilterSource(v as any)}>
                <SelectTrigger>
                  <SelectValue placeholder="Filter by source" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Sources</SelectItem>
                  {SIGNAL_SOURCES.map(source => (
                    <SelectItem key={source} value={source}>
                      {source}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Signal List */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent motion-reduce:animate-[spin_1.5s_linear_infinite]" />
              <p className="text-gray-600">Loading signals...</p>
            </div>
          </div>
        ) : filteredSignals.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <AlertCircle className="mx-auto mb-4 h-12 w-12 text-gray-400" />
              <p className="text-gray-600">No signals found</p>
              <Button
                onClick={() => setIsCreateDialogOpen(true)}
                variant="outline"
                className="mt-4"
              >
                Create your first signal
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Tabs defaultValue="all" className="space-y-4">
            <TabsList>
              <TabsTrigger value="all">
                All ({filteredSignals.length})
              </TabsTrigger>
              <TabsTrigger value="new">
                New ({signalsByStatus.NEW?.length || 0})
              </TabsTrigger>
              <TabsTrigger value="scored">
                Scored ({signalsByStatus.SCORED?.length || 0})
              </TabsTrigger>
              <TabsTrigger value="brief">
                Brief ({signalsByStatus.BRIEF_CREATED?.length || 0})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="all" className="space-y-4">
              {filteredSignals.map(signal => (
                <SignalCard
                  key={signal.signal_id}
                  signal={signal}
                  onTriage={handleTriage}
                  isTriaging={triageMutation.isPending}
                  onViewDetail={setSelectedSignalId}
                />
              ))}
            </TabsContent>

            <TabsContent value="new" className="space-y-4">
              {signalsByStatus.NEW?.map(signal => (
                <SignalCard
                  key={signal.signal_id}
                  signal={signal}
                  onTriage={handleTriage}
                  isTriaging={triageMutation.isPending}
                  onViewDetail={setSelectedSignalId}
                />
              ))}
            </TabsContent>

            <TabsContent value="scored" className="space-y-4">
              {signalsByStatus.SCORED?.map(signal => (
                <SignalCard
                  key={signal.signal_id}
                  signal={signal}
                  onTriage={handleTriage}
                  isTriaging={triageMutation.isPending}
                  onViewDetail={setSelectedSignalId}
                />
              ))}
            </TabsContent>

            <TabsContent value="brief" className="space-y-4">
              {signalsByStatus.BRIEF_CREATED?.map(signal => (
                <SignalCard
                  key={signal.signal_id}
                  signal={signal}
                  onTriage={handleTriage}
                  isTriaging={triageMutation.isPending}
                  onViewDetail={setSelectedSignalId}
                />
              ))}
            </TabsContent>
          </Tabs>
        )}
      </div>

      {/* Create Dialog */}
      <CreateSignalDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['signals'] })
          queryClient.invalidateQueries({ queryKey: ['inbox-stats'] })
        }}
      />

      {/* Detail Modal */}
      <SignalDetailModal
        signalId={selectedSignalId}
        open={!!selectedSignalId}
        onOpenChange={(open) => !open && setSelectedSignalId(null)}
      />
    </div>
  )
}

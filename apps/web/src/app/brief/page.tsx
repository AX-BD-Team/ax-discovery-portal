'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { briefApi, inboxApi } from '@ax/api-client'
import type { Brief, BriefStatus } from '@ax/types'
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
import { Search, FileText, CheckCircle, Clock, AlertCircle } from 'lucide-react'
import { BriefCard } from './components/brief-card'
import { GenerateBriefDialog } from './components/generate-brief-dialog'
import { BriefDetailModal } from './components/brief-detail-modal'

const STATUS_LABELS: Record<BriefStatus, string> = {
  DRAFT: '초안',
  REVIEW: '검토 중',
  APPROVED: '승인됨',
  VALIDATED: '검증 완료',
  PILOT_READY: 'Pilot 준비',
  ARCHIVED: '보관',
}

export default function BriefPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<BriefStatus | 'ALL'>('ALL')
  const [isGenerateDialogOpen, setIsGenerateDialogOpen] = useState(false)
  const [selectedBriefId, setSelectedBriefId] = useState<string | null>(null)

  // Fetch briefs
  const { data: briefs = [], isLoading } = useQuery({
    queryKey: ['briefs'],
    queryFn: () => briefApi.getBriefs(),
  })

  // Fetch signals for brief generation (SCORED status)
  const { data: signals = [] } = useQuery({
    queryKey: ['signals'],
    queryFn: inboxApi.getSignals,
  })

  // Filter briefs
  const filteredBriefs = briefs.filter(brief => {
    const matchesSearch =
      searchQuery === '' ||
      brief.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      brief.customer.segment.toLowerCase().includes(searchQuery.toLowerCase())

    const matchesStatus = filterStatus === 'ALL' || brief.status === filterStatus

    return matchesSearch && matchesStatus
  })

  // Group by status
  const briefsByStatus = filteredBriefs.reduce(
    (acc, brief) => {
      if (!acc[brief.status]) {
        acc[brief.status] = []
      }
      acc[brief.status].push(brief)
      return acc
    },
    {} as Record<BriefStatus, Brief[]>
  )

  // Count signals available for brief generation
  const availableSignals = signals.filter(s => s.status === 'SCORED').length

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-gray-900">📝 Brief</h1>
              <p className="mt-2 text-gray-600">1-Page Opportunity Brief</p>
            </div>
            <Button onClick={() => setIsGenerateDialogOpen(true)} size="lg">
              <FileText className="mr-2 h-5 w-5" />
              Generate Brief
            </Button>
          </div>

          {/* Stats */}
          <div className="mt-6 grid gap-4 md:grid-cols-5">
            <Card>
              <CardHeader className="pb-3">
                <CardDescription>Total Briefs</CardDescription>
                <CardTitle className="text-3xl">{briefs.length}</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-3">
                <CardDescription>Available to Generate</CardDescription>
                <CardTitle className="text-3xl text-blue-600">{availableSignals}</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-3">
                <CardDescription>Draft</CardDescription>
                <CardTitle className="text-3xl text-gray-600">
                  {briefsByStatus.DRAFT?.length || 0}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-3">
                <CardDescription>Approved</CardDescription>
                <CardTitle className="text-3xl text-green-600">
                  {briefsByStatus.APPROVED?.length || 0}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-3">
                <CardDescription>Validated</CardDescription>
                <CardTitle className="text-3xl text-purple-600">
                  {briefsByStatus.VALIDATED?.length || 0}
                </CardTitle>
              </CardHeader>
            </Card>
          </div>
        </div>

        {/* Filters */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="grid gap-4 md:grid-cols-2">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <Input
                  placeholder="Search briefs..."
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
                  <SelectItem value="DRAFT">Draft</SelectItem>
                  <SelectItem value="REVIEW">Review</SelectItem>
                  <SelectItem value="APPROVED">Approved</SelectItem>
                  <SelectItem value="VALIDATED">Validated</SelectItem>
                  <SelectItem value="PILOT_READY">Pilot Ready</SelectItem>
                  <SelectItem value="ARCHIVED">Archived</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Brief List */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
              <p className="text-gray-600">Loading briefs...</p>
            </div>
          </div>
        ) : briefs.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <FileText className="mx-auto mb-4 h-12 w-12 text-gray-400" />
              <p className="mb-2 text-lg font-medium text-gray-900">No Briefs Yet</p>
              <p className="mb-4 text-gray-600">
                {availableSignals > 0
                  ? `${availableSignals} signal(s) available for brief generation`
                  : 'No signals available for brief generation'}
              </p>
              <Button onClick={() => setIsGenerateDialogOpen(true)}>
                <FileText className="mr-2 h-4 w-4" />
                Generate First Brief
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Tabs defaultValue="all" className="space-y-4">
            <TabsList>
              <TabsTrigger value="all">All ({filteredBriefs.length})</TabsTrigger>
              <TabsTrigger value="draft">
                Draft ({briefsByStatus.DRAFT?.length || 0})
              </TabsTrigger>
              <TabsTrigger value="review">
                Review ({briefsByStatus.REVIEW?.length || 0})
              </TabsTrigger>
              <TabsTrigger value="approved">
                Approved ({briefsByStatus.APPROVED?.length || 0})
              </TabsTrigger>
              <TabsTrigger value="validated">
                Validated ({briefsByStatus.VALIDATED?.length || 0})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="all" className="space-y-4">
              {filteredBriefs.map(brief => (
                <BriefCard key={brief.brief_id} brief={brief} onViewDetail={setSelectedBriefId} />
              ))}
            </TabsContent>

            <TabsContent value="draft" className="space-y-4">
              {briefsByStatus.DRAFT?.map(brief => (
                <BriefCard key={brief.brief_id} brief={brief} onViewDetail={setSelectedBriefId} />
              ))}
            </TabsContent>

            <TabsContent value="review" className="space-y-4">
              {briefsByStatus.REVIEW?.map(brief => (
                <BriefCard key={brief.brief_id} brief={brief} onViewDetail={setSelectedBriefId} />
              ))}
            </TabsContent>

            <TabsContent value="approved" className="space-y-4">
              {briefsByStatus.APPROVED?.map(brief => (
                <BriefCard key={brief.brief_id} brief={brief} onViewDetail={setSelectedBriefId} />
              ))}
            </TabsContent>

            <TabsContent value="validated" className="space-y-4">
              {briefsByStatus.VALIDATED?.map(brief => (
                <BriefCard key={brief.brief_id} brief={brief} onViewDetail={setSelectedBriefId} />
              ))}
            </TabsContent>
          </Tabs>
        )}
      </div>

      {/* Generate Dialog */}
      <GenerateBriefDialog
        open={isGenerateDialogOpen}
        onOpenChange={setIsGenerateDialogOpen}
        availableSignals={signals.filter(s => s.status === 'SCORED')}
      />

      {/* Detail Modal */}
      <BriefDetailModal
        briefId={selectedBriefId}
        open={!!selectedBriefId}
        onOpenChange={(open) => !open && setSelectedBriefId(null)}
      />
    </div>
  )
}

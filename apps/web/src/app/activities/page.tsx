'use client'

import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  activitiesApi,
  type Activity,
  type SeminarExtractResult,
  type HealthCheckResponse,
} from '@ax/api-client'
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
  CollectorHealthBar,
  SeminarChatPanel,
} from '@ax/ui'
import { Search, Calendar, ExternalLink, Building2, Tag, Loader2, ArrowLeft, Plus } from 'lucide-react'
import Link from 'next/link'

const SOURCE_TYPE_LABELS: Record<string, string> = {
  rss: 'RSS',
  festa: 'Festa',
  eventbrite: 'Eventbrite',
  manual: '수동 등록',
}

const SOURCE_TYPE_COLORS: Record<string, string> = {
  rss: 'bg-blue-100 text-blue-800',
  festa: 'bg-purple-100 text-purple-800',
  eventbrite: 'bg-orange-100 text-orange-800',
  manual: 'bg-gray-100 text-gray-800',
}

function ActivityCard({ activity }: { activity: Activity }) {
  const sourceTypeColor = SOURCE_TYPE_COLORS[activity.source_type || 'manual'] || SOURCE_TYPE_COLORS.manual

  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <CardTitle className="text-lg leading-tight">{activity.name}</CardTitle>
            <CardDescription className="mt-1 line-clamp-2">
              {activity.description || '설명 없음'}
            </CardDescription>
          </div>
          {activity.url && (
            <a
              href={activity.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-shrink-0 rounded-md p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary" className={sourceTypeColor}>
              {SOURCE_TYPE_LABELS[activity.source_type || 'manual']}
            </Badge>
            {activity.categories?.map((cat) => (
              <Badge key={cat} variant="outline" className="text-xs">
                <Tag className="mr-1 h-3 w-3" />
                {cat}
              </Badge>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
            {activity.date && (
              <div className="flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                <span>{activity.date}</span>
              </div>
            )}
            {activity.organizer && (
              <div className="flex items-center gap-1">
                <Building2 className="h-4 w-4" />
                <span className="truncate">{activity.organizer}</span>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between border-t pt-2 text-xs text-gray-500">
            <span>ID: {activity.entity_id}</span>
            <span>Play: {activity.play_id || 'N/A'}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function ActivitiesPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [filterSourceType, setFilterSourceType] = useState<string>('ALL')
  const [page, setPage] = useState(1)
  const [isChatOpen, setIsChatOpen] = useState(false)
  const pageSize = 12
  const queryClient = useQueryClient()

  // Fetch activities
  const { data: activitiesData, isLoading } = useQuery({
    queryKey: ['activities', page, filterSourceType],
    queryFn: () =>
      activitiesApi.getActivities({
        page,
        page_size: pageSize,
        source_type: filterSourceType === 'ALL' ? undefined : filterSourceType,
      }),
  })

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['activities-stats'],
    queryFn: activitiesApi.getStats,
  })

  // Fetch health check
  const {
    data: healthData,
    isLoading: isHealthLoading,
    refetch: refetchHealth,
  } = useQuery({
    queryKey: ['collector-health'],
    queryFn: activitiesApi.getHealthCheck,
    refetchInterval: 300000, // 5분마다 자동 새로고침
    staleTime: 60000, // 1분간 캐시
  })

  // 세미나 추가 완료 핸들러
  const handleSeminarAdded = () => {
    // 활동 목록 새로고침
    queryClient.invalidateQueries({ queryKey: ['activities'] })
    queryClient.invalidateQueries({ queryKey: ['activities-stats'] })
  }

  // 채팅 제출 핸들러
  const handleChatSubmit = async (message: string, files?: File[]) => {
    return activitiesApi.chatAddSeminar(message, files)
  }

  // 세미나 확인 핸들러
  const handleConfirmSeminars = async (
    seminars: SeminarExtractResult[],
    playId?: string
  ) => {
    await activitiesApi.confirmSeminars(seminars, playId)
    handleSeminarAdded()
  }

  // 파일 업로드 핸들러
  const handleUploadFiles = async (files: File[], playId?: string) => {
    return activitiesApi.uploadSeminars(files, playId, false)
  }

  const activities = activitiesData?.items || []
  const total = activitiesData?.total || 0
  const totalPages = Math.ceil(total / pageSize)

  // Filter by search query (client-side)
  const filteredActivities = activities.filter((activity) => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      activity.name.toLowerCase().includes(query) ||
      activity.description?.toLowerCase().includes(query) ||
      activity.organizer?.toLowerCase().includes(query) ||
      activity.categories?.some((cat) => cat.toLowerCase().includes(query))
    )
  })

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-6">
          <Link href="/" className="mb-4 inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900">
            <ArrowLeft className="h-4 w-4" />
            홈으로
          </Link>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 md:text-3xl">외부 세미나</h1>
              <p className="mt-1 text-gray-600">수집된 외부 세미나 및 이벤트 목록</p>
            </div>
            <Button onClick={() => setIsChatOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              세미나 추가
            </Button>
          </div>
        </div>

        {/* 수집기 헬스체크 */}
        <CollectorHealthBar
          data={healthData || null}
          isLoading={isHealthLoading}
          onRefresh={() => refetchHealth()}
          className="mb-6"
        />

        {/* Stats Cards */}
        <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-5">
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-gray-600">전체</p>
              <p className="text-2xl font-bold">{stats?.total ?? 0}</p>
            </CardContent>
          </Card>
          {Object.entries(stats?.by_source_type || {}).map(([type, count]) => (
            <Card key={type}>
              <CardContent className="p-4">
                <p className="text-sm text-gray-600">{SOURCE_TYPE_LABELS[type] || type}</p>
                <p className="text-2xl font-bold">{count}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Filters */}
        <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              placeholder="세미나 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select value={filterSourceType} onValueChange={setFilterSourceType}>
            <SelectTrigger className="w-full md:w-48">
              <SelectValue placeholder="소스 타입" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">전체 소스</SelectItem>
              <SelectItem value="rss">RSS</SelectItem>
              <SelectItem value="festa">Festa</SelectItem>
              <SelectItem value="eventbrite">Eventbrite</SelectItem>
              <SelectItem value="manual">수동 등록</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Activity List */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            <span className="ml-2 text-gray-600">로딩 중...</span>
          </div>
        ) : filteredActivities.length > 0 ? (
          <>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredActivities.map((activity) => (
                <ActivityCard key={activity.entity_id} activity={activity} />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-6 flex items-center justify-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  이전
                </Button>
                <span className="px-4 text-sm text-gray-600">
                  {page} / {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  다음
                </Button>
              </div>
            )}
          </>
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-gray-500">
                {searchQuery ? '검색 결과가 없습니다.' : '등록된 세미나가 없습니다.'}
              </p>
            </CardContent>
          </Card>
        )}

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>총 {total}개의 세미나가 등록되어 있습니다.</p>
        </div>
      </div>

      {/* 세미나 추가 채팅 패널 */}
      <SeminarChatPanel
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        onSeminarAdded={handleSeminarAdded}
        onChatSubmit={handleChatSubmit}
        onConfirmSeminars={handleConfirmSeminars}
        onUploadFiles={handleUploadFiles}
      />
    </div>
  )
}

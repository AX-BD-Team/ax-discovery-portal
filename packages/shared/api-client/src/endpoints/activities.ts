import { apiClient } from '../client'

export interface Activity {
  entity_id: string
  entity_type: string
  name: string
  description: string | null
  url: string | null
  date: string | null
  organizer: string | null
  play_id: string | null
  source: string | null
  channel: string | null
  source_type: string | null
  categories: string[] | null
  status: string | null
  created_at: string | null
  updated_at: string | null
}

interface ActivityListResponse {
  items: Activity[]
  total: number
  page: number
  page_size: number
}

interface ActivityStatsResponse {
  total: number
  by_source_type: Record<string, number>
  today_count: number
}

interface ActivityFilters {
  play_id?: string
  source_type?: string
  status?: string
  page?: number
  page_size?: number
}

// 헬스체크 타입
export interface CollectorHealthResult {
  collector_name: string
  status: 'healthy' | 'degraded' | 'unhealthy'
  checked_at: string
  sample_count: number
  error_message: string | null
  response_time_ms: number | null
}

export interface HealthCheckResponse {
  checked_at: string
  results: CollectorHealthResult[]
  summary: {
    total: number
    healthy: number
    degraded: number
    unhealthy: number
  }
}

// 세미나 추출 타입
export interface SeminarExtractResult {
  title: string
  description: string | null
  date: string | null
  organizer: string | null
  url: string | null
  categories: string[]
  confidence: number
}

// 채팅 SSE 이벤트 타입
export interface ChatSSEEvent {
  type: 'start' | 'progress' | 'info' | 'extracted' | 'complete' | 'error'
  message?: string
  seminars?: SeminarExtractResult[]
  count?: number
  timestamp?: string
}

// 업로드 결과 타입
export interface UploadResult {
  filename: string
  extracted_count: number
  seminars: SeminarExtractResult[]
  error: string | null
}

export interface UploadResponse {
  total_files: number
  total_extracted: number
  results: UploadResult[]
}

// 확인 응답 타입
export interface ConfirmResponse {
  registered: Activity[]
  count: number
  play_id: string
}

/**
 * Activities API endpoints
 */
export const activitiesApi = {
  /**
   * Get activities list
   */
  async getActivities(filters?: ActivityFilters): Promise<ActivityListResponse> {
    const searchParams = new URLSearchParams()
    if (filters?.play_id) searchParams.set('play_id', filters.play_id)
    if (filters?.source_type) searchParams.set('source_type', filters.source_type)
    if (filters?.status) searchParams.set('status', filters.status)
    if (filters?.page) searchParams.set('page', String(filters.page))
    if (filters?.page_size) searchParams.set('page_size', String(filters.page_size))

    const query = searchParams.toString()
    const url = query ? `api/activities?${query}` : 'api/activities'
    return apiClient.get(url).json<ActivityListResponse>()
  },

  /**
   * Get activity by ID
   */
  async getActivity(activityId: string): Promise<Activity> {
    return apiClient.get(`api/activities/${activityId}`).json<Activity>()
  },

  /**
   * Get activities stats
   */
  async getStats(): Promise<ActivityStatsResponse> {
    return apiClient.get('api/activities/stats').json<ActivityStatsResponse>()
  },

  /**
   * Check duplicate activity
   */
  async checkDuplicate(params: {
    url?: string
    title?: string
    date?: string
    external_id?: string
  }): Promise<{ is_duplicate: boolean; existing_activity: Activity | null }> {
    const searchParams = new URLSearchParams()
    if (params.url) searchParams.set('url', params.url)
    if (params.title) searchParams.set('title', params.title)
    if (params.date) searchParams.set('date', params.date)
    if (params.external_id) searchParams.set('external_id', params.external_id)

    return apiClient.post(`api/activities/check-duplicate?${searchParams}`).json()
  },

  /**
   * 수집기 헬스체크 조회
   */
  async getHealthCheck(): Promise<HealthCheckResponse> {
    return apiClient.get('api/activities/health-check').json<HealthCheckResponse>()
  },

  /**
   * 채팅으로 세미나 추가 (SSE 스트리밍)
   *
   * @param message 사용자 메시지
   * @param files 첨부 파일 (선택)
   * @returns EventSource 스트림
   */
  chatAddSeminar(
    message: string,
    files?: File[]
  ): {
    stream: ReadableStream<ChatSSEEvent>
    abort: () => void
  } {
    const formData = new FormData()
    formData.append('message', message)
    if (files) {
      files.forEach(file => formData.append('files', file))
    }

    const abortController = new AbortController()

    const stream = new ReadableStream<ChatSSEEvent>({
      async start(controller) {
        try {
          const response = await fetch('/api/activities/chat', {
            method: 'POST',
            body: formData,
            signal: abortController.signal,
          })

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
          }

          const reader = response.body?.getReader()
          if (!reader) {
            throw new Error('No response body')
          }

          const decoder = new TextDecoder()

          while (true) {
            const { done, value } = await reader.read()
            if (done) break

            const text = decoder.decode(value)
            const lines = text.split('\n')

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const event = JSON.parse(line.slice(6)) as ChatSSEEvent
                  controller.enqueue(event)
                } catch {
                  // 파싱 오류 무시
                }
              }
            }
          }

          controller.close()
        } catch (error) {
          if ((error as Error).name !== 'AbortError') {
            controller.error(error)
          }
        }
      },
    })

    return {
      stream,
      abort: () => abortController.abort(),
    }
  },

  /**
   * 추출된 세미나 확인 및 등록
   */
  async confirmSeminars(
    seminars: SeminarExtractResult[],
    playId: string = 'EXT_Desk_D01_Seminar'
  ): Promise<ConfirmResponse> {
    const response = await fetch('/api/activities/chat/confirm', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        seminars,
        play_id: playId,
      }),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return response.json()
  },

  /**
   * 파일 업로드로 세미나 일괄 추출
   */
  async uploadSeminars(
    files: File[],
    playId: string = 'EXT_Desk_D01_Seminar',
    autoRegister: boolean = false
  ): Promise<UploadResponse> {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    formData.append('play_id', playId)
    formData.append('auto_register', String(autoRegister))

    const response = await fetch('/api/activities/upload', {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return response.json()
  },
}

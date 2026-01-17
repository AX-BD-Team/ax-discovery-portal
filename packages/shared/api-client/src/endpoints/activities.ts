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
}

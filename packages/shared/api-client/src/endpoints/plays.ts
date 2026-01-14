import type {
  PlayRecord,
  PlayListResponse,
  KPIDigest,
  KPIAlerts,
  PlayTimelineEvent,
} from '@ax/types'
import { apiClient } from '../client'

/**
 * Play Dashboard API endpoints
 */
export const playsApi = {
  /**
   * Get all plays
   */
  async getPlays(params?: {
    status?: 'G' | 'Y' | 'R'
    owner?: string
    page?: number
    page_size?: number
  }): Promise<PlayListResponse> {
    const searchParams = new URLSearchParams()
    if (params?.status) searchParams.append('status', params.status)
    if (params?.owner) searchParams.append('owner', params.owner)
    if (params?.page) searchParams.append('page', params.page.toString())
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString())

    const query = searchParams.toString()
    return apiClient.get(`api/plays${query ? `?${query}` : ''}`).json<PlayListResponse>()
  },

  /**
   * Get play by ID
   */
  async getPlay(playId: string): Promise<PlayRecord> {
    return apiClient.get(`api/plays/${playId}`).json<PlayRecord>()
  },

  /**
   * Get play timeline
   */
  async getPlayTimeline(
    playId: string,
    limit?: number
  ): Promise<{ play_id: string; events: PlayTimelineEvent[] }> {
    const query = limit ? `?limit=${limit}` : ''
    return apiClient.get(`api/plays/${playId}/timeline${query}`).json()
  },

  /**
   * Get KPI digest
   */
  async getKPIDigest(period: 'week' | 'month' = 'week'): Promise<KPIDigest> {
    return apiClient.get(`api/plays/kpi/digest?period=${period}`).json<KPIDigest>()
  },

  /**
   * Get KPI alerts
   */
  async getKPIAlerts(): Promise<KPIAlerts> {
    return apiClient.get('api/plays/kpi/alerts').json<KPIAlerts>()
  },

  /**
   * Get leaderboard
   */
  async getLeaderboard(period: 'week' | 'month' = 'week'): Promise<{
    period: string
    top_plays: Array<{ play_id: string; score: number }>
    top_contributors: Array<{ name: string; score: number }>
  }> {
    return apiClient.get(`api/plays/leaderboard?period=${period}`).json()
  },

  /**
   * Sync play from Confluence
   */
  async syncPlay(playId: string): Promise<{ status: string; play_id: string; message: string }> {
    return apiClient.post(`api/plays/${playId}/sync`).json()
  },
}

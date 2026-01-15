import type { Scorecard } from '@ax/types'
import { apiClient } from '../client'

/**
 * Scorecard 목록 응답 타입
 */
export interface ScorecardListResponse {
  items: Scorecard[]
  total: number
  page: number
  page_size: number
}

/**
 * Scorecard API endpoints
 */
export const scorecardApi = {
  /**
   * Get all scorecards with filtering
   */
  async getScorecards(params?: {
    decision?: 'GO' | 'PIVOT' | 'HOLD' | 'NO_GO'
    min_score?: number
    max_score?: number
    page?: number
    page_size?: number
  }): Promise<ScorecardListResponse> {
    const searchParams = new URLSearchParams()
    if (params?.decision) searchParams.append('decision', params.decision)
    if (params?.min_score !== undefined)
      searchParams.append('min_score', params.min_score.toString())
    if (params?.max_score !== undefined)
      searchParams.append('max_score', params.max_score.toString())
    if (params?.page) searchParams.append('page', params.page.toString())
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString())

    const query = searchParams.toString()
    return apiClient.get(`api/scorecard${query ? `?${query}` : ''}`).json<ScorecardListResponse>()
  },

  /**
   * Get scorecard by signal ID
   */
  async getScorecard(signalId: string): Promise<Scorecard> {
    return apiClient.get(`api/scorecard/${signalId}`).json<Scorecard>()
  },

  /**
   * Evaluate signal and create scorecard
   */
  async evaluateSignal(
    signalId: string,
    options?: { mode?: 'auto' | 'manual' }
  ): Promise<Scorecard> {
    return apiClient.post(`api/scorecard/evaluate/${signalId}`, { json: options }).json()
  },

  /**
   * Get score distribution stats
   */
  async getDistribution(): Promise<{
    ranges: Array<{ range: string; count: number }>
    avg_score: number
  }> {
    return apiClient.get('api/scorecard/stats/distribution').json()
  },
}

import type { Scorecard } from '@ax/types'
import { apiClient } from '../client'

/**
 * Scorecard API endpoints
 */
export const scorecardApi = {
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

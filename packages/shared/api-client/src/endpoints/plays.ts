import type { PlayRecord } from '@ax/types'
import { apiClient } from '../client'

/**
 * Play Dashboard API endpoints
 */
export const playsApi = {
  /**
   * Get all plays
   */
  async getPlays(): Promise<PlayRecord[]> {
    return apiClient.get('api/plays').json<PlayRecord[]>()
  },

  /**
   * Get play by ID
   */
  async getPlay(playId: string): Promise<PlayRecord> {
    return apiClient.get(`api/plays/${playId}`).json<PlayRecord>()
  },

  /**
   * Create new play
   */
  async createPlay(data: Partial<PlayRecord>): Promise<PlayRecord> {
    return apiClient.post('api/plays', { json: data }).json()
  },
}

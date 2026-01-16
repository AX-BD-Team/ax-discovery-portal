import type { Signal, CreateSignalRequest } from '@ax/types'
import { apiClient } from '../client'

interface SignalListResponse {
  items: Signal[]
  total: number
  page: number
  page_size: number
}

/**
 * Inbox API endpoints
 */
export const inboxApi = {
  /**
   * Get all signals
   */
  async getSignals(): Promise<Signal[]> {
    const response = await apiClient.get('api/inbox').json<SignalListResponse>()
    return response.items
  },

  /**
   * Get signal by ID
   */
  async getSignal(signalId: string): Promise<Signal> {
    return apiClient.get(`api/inbox/${signalId}`).json<Signal>()
  },

  /**
   * Create new signal
   */
  async createSignal(data: CreateSignalRequest): Promise<Signal> {
    return apiClient.post('api/inbox', { json: data }).json<Signal>()
  },

  /**
   * Trigger triage (scorecard evaluation)
   */
  async triggerTriage(signalId: string): Promise<{ message: string }> {
    return apiClient.post(`api/inbox/${signalId}/triage`).json()
  },

  /**
   * Get inbox stats
   */
  async getStats(): Promise<{
    total: number
    by_status: Record<string, number>
    by_channel: Record<string, number>
  }> {
    return apiClient.get('api/inbox/stats/summary').json()
  },
}

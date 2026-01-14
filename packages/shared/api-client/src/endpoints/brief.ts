import type { Brief } from '@ax/types'
import { apiClient } from '../client'

/**
 * Brief API endpoints
 */
export const briefApi = {
  /**
   * Get all briefs
   */
  async getBriefs(): Promise<Brief[]> {
    return apiClient.get('api/brief').json<Brief[]>()
  },

  /**
   * Get brief by ID
   */
  async getBrief(briefId: string): Promise<Brief> {
    return apiClient.get(`api/brief/${briefId}`).json<Brief>()
  },

  /**
   * Generate brief from signal
   */
  async generateBrief(signalId: string): Promise<Brief> {
    return apiClient.post(`api/brief/generate/${signalId}`).json()
  },

  /**
   * Approve and publish brief to Confluence
   */
  async approveBrief(briefId: string): Promise<{ message: string; confluence_url?: string }> {
    return apiClient.post(`api/brief/${briefId}/approve`).json()
  },

  /**
   * Start validation sprint
   */
  async startValidation(briefId: string): Promise<{ message: string }> {
    return apiClient.post(`api/brief/${briefId}/start-validation`).json()
  },
}

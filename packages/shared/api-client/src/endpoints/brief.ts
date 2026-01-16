import type { Brief } from '@ax/types'
import { apiClient } from '../client'

/**
 * Brief 목록 응답 타입
 */
export interface BriefListResponse {
  items: Brief[]
  total: number
  page: number
  page_size: number
}

/**
 * Brief API endpoints
 */
export const briefApi = {
  /**
   * Get all briefs with filtering
   */
  async getBriefs(params?: {
    status?: string
    owner?: string
    page?: number
    page_size?: number
  }): Promise<Brief[]> {
    const searchParams = new URLSearchParams()
    if (params?.status) searchParams.append('status', params.status)
    if (params?.owner) searchParams.append('owner', params.owner)
    if (params?.page) searchParams.append('page', params.page.toString())
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString())

    const query = searchParams.toString()
    return apiClient.get(`api/brief${query ? `?${query}` : ''}`).json<Brief[]>()
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

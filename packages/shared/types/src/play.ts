/**
 * Play Record - Business Case / Play Tracking
 */
export interface PlayRecord {
  play_id: string
  play_name: string
  description?: string
  owner?: string
  status?: 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'ARCHIVED'
  created_at: string
  updated_at?: string
}

/**
 * Create Play Request
 */
export type CreatePlayRequest = Omit<PlayRecord, 'play_id' | 'created_at' | 'updated_at'>

import type { Evidence, SignalChannel, SignalSource, SignalStatus } from './common'

/**
 * Signal - 사업기회 신호
 */
export interface Signal {
  signal_id: string
  title: string
  source: SignalSource
  channel: SignalChannel
  play_id: string
  customer_segment?: string
  pain: string
  proposed_value?: string
  kpi_hypothesis?: string[]
  evidence?: Evidence[]
  tags?: string[]
  status: SignalStatus
  owner?: string
  confidence?: number
  created_at: string
  updated_at?: string
}

/**
 * Create Signal Request
 */
export interface CreateSignalRequest {
  title: string
  source: SignalSource
  channel: SignalChannel
  play_id: string
  customer_segment?: string
  pain: string
  proposed_value?: string
  kpi_hypothesis?: string[]
  evidence?: Evidence[]
  tags?: string[]
  owner?: string
}

/**
 * Update Signal Request
 */
export type UpdateSignalRequest = Partial<Omit<Signal, 'signal_id' | 'created_at' | 'updated_at'>>

/**
 * Play Record - Business Case / Play Tracking
 */
export interface PlayRecord {
  play_id: string
  play_name: string
  owner?: string
  status: 'G' | 'Y' | 'R' // Green/Yellow/Red
  activity_qtd: number
  signal_qtd: number
  brief_qtd: number
  s2_qtd: number // Validated
  s3_qtd: number // Pilot-ready
  next_action?: string
  due_date?: string
  last_activity_date?: string
  notes?: string
  confluence_live_doc_url?: string
  last_updated: string
}

/**
 * KPI Digest
 */
export interface KPIDigest {
  period: string
  activity_actual: number
  activity_target: number
  signal_actual: number
  signal_target: number
  brief_actual: number
  brief_target: number
  s2_actual: number
  s2_target: string // "2~4" format
  avg_signal_to_brief_days: number
  avg_brief_to_s2_days: number
}

/**
 * KPI Alerts
 */
export interface KPIAlerts {
  alerts: string[]
  yellow_plays: string[]
  red_plays: string[]
  overdue_briefs: string[]
  stale_signals: string[]
}

/**
 * Play Timeline Event
 */
export interface PlayTimelineEvent {
  event_id: string
  type: 'ACTIVITY' | 'SIGNAL' | 'BRIEF' | 'VALIDATION'
  title: string
  date: string
  description?: string
}

/**
 * Play List Response
 */
export interface PlayListResponse {
  items: PlayRecord[]
  total: number
  page: number
  page_size: number
}

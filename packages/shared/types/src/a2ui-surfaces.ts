/**
 * A2UI (Agent-to-UI) Surface Types
 *
 * A2UI 프로토콜 기반 UI Surface 타입 정의
 * 에이전트가 UI를 선언적 데이터로 전송하고, 클라이언트가 네이티브 컴포넌트로 렌더링
 */

// Surface 타입 열거형
export type SurfaceType =
  | 'form'
  | 'card'
  | 'table'
  | 'summary'
  | 'action_buttons'
  | 'progress'
  | 'message'
  | 'activity_preview'
  | 'aar_template'
  | 'approval_request'

// Surface 액션
export interface SurfaceAction {
  id: string
  label: string
  type: 'primary' | 'secondary' | 'destructive' | 'ghost'
  icon?: string
  disabled?: boolean
  loading?: boolean
}

// 기본 Surface 인터페이스
export interface BaseSurface {
  id: string
  type: SurfaceType
  title?: string
  description?: string
  actions?: SurfaceAction[]
  metadata?: Record<string, unknown>
}

// 폼 필드 타입
export type FormFieldType =
  | 'text'
  | 'textarea'
  | 'number'
  | 'date'
  | 'select'
  | 'multiselect'
  | 'checkbox'
  | 'radio'
  | 'url'
  | 'email'

// 폼 필드 정의
export interface FormField {
  id: string
  type: FormFieldType
  label: string
  placeholder?: string
  defaultValue?: unknown
  required?: boolean
  disabled?: boolean
  options?: Array<{
    value: string
    label: string
  }>
  validation?: {
    min?: number
    max?: number
    pattern?: string
    message?: string
  }
}

// 폼 Surface
export interface FormSurface extends BaseSurface {
  type: 'form'
  fields: FormField[]
  submitLabel?: string
  cancelLabel?: string
}

// 카드 Surface
export interface CardSurface extends BaseSurface {
  type: 'card'
  content: string // Markdown 지원
  image?: string
  badges?: Array<{
    label: string
    variant: 'default' | 'secondary' | 'destructive' | 'outline'
  }>
  footer?: string
}

// 테이블 컬럼 정의
export interface TableColumn {
  id: string
  header: string
  accessor: string
  type?: 'text' | 'number' | 'date' | 'badge' | 'link' | 'actions'
  sortable?: boolean
  width?: string
}

// 테이블 Surface
export interface TableSurface extends BaseSurface {
  type: 'table'
  columns: TableColumn[]
  rows: Array<Record<string, unknown>>
  pagination?: {
    page: number
    pageSize: number
    total: number
  }
  selectable?: boolean
}

// 요약 항목
export interface SummaryItem {
  label: string
  value: string | number
  change?: {
    value: number
    direction: 'up' | 'down' | 'neutral'
  }
  icon?: string
}

// 요약 Surface
export interface SummarySurface extends BaseSurface {
  type: 'summary'
  items: SummaryItem[]
  layout?: 'grid' | 'list'
}

// 액션 버튼 Surface
export interface ActionButtonsSurface extends BaseSurface {
  type: 'action_buttons'
  buttons: SurfaceAction[]
  layout?: 'horizontal' | 'vertical'
}

// 진행률 Surface
export interface ProgressSurface extends BaseSurface {
  type: 'progress'
  current: number
  total: number
  percentage: number
  status?: 'active' | 'success' | 'error' | 'paused'
  message?: string
}

// 메시지 Surface
export interface MessageSurface extends BaseSurface {
  type: 'message'
  content: string
  variant: 'info' | 'success' | 'warning' | 'error'
  dismissible?: boolean
}

// Activity 미리보기 Surface (WF-01 전용)
export interface ActivityPreviewSurface extends BaseSurface {
  type: 'activity_preview'
  activity: {
    activity_id: string
    title: string
    date?: string
    organizer?: string
    url: string
    play_id: string
    themes: string[]
    source: string
    channel: string
    status: string
  }
}

// AAR 템플릿 Surface (WF-01 전용)
export interface AARTemplateSurface extends BaseSurface {
  type: 'aar_template'
  activityId: string
  content: string // Markdown
  confluenceUrl?: string
}

// 승인 요청 Surface
export interface ApprovalRequestSurface extends BaseSurface {
  type: 'approval_request'
  approvalId: string
  impact: 'low' | 'medium' | 'high' | 'critical'
  changes: Array<{
    label: string
    before?: string
    after: string
    type: 'create' | 'update' | 'delete'
  }>
  timeout?: number // ms
}

// 모든 Surface 타입 유니온
export type A2UISurface =
  | FormSurface
  | CardSurface
  | TableSurface
  | SummarySurface
  | ActionButtonsSurface
  | ProgressSurface
  | MessageSurface
  | ActivityPreviewSurface
  | AARTemplateSurface
  | ApprovalRequestSurface

// Surface 렌더러 컨텍스트
export interface SurfaceRendererContext {
  onAction?: (surfaceId: string, actionId: string, payload?: unknown) => void
  onFormSubmit?: (surfaceId: string, values: Record<string, unknown>) => void
  onApproval?: (approvalId: string, approved: boolean, reason?: string) => void
}

// Surface 카탈로그 (허용된 Surface 타입 목록)
export const SURFACE_CATALOG: SurfaceType[] = [
  'form',
  'card',
  'table',
  'summary',
  'action_buttons',
  'progress',
  'message',
  'activity_preview',
  'aar_template',
  'approval_request',
]

// Surface 타입 가드
export function isFormSurface(surface: A2UISurface): surface is FormSurface {
  return surface.type === 'form'
}

export function isCardSurface(surface: A2UISurface): surface is CardSurface {
  return surface.type === 'card'
}

export function isTableSurface(surface: A2UISurface): surface is TableSurface {
  return surface.type === 'table'
}

export function isActivityPreviewSurface(surface: A2UISurface): surface is ActivityPreviewSurface {
  return surface.type === 'activity_preview'
}

export function isAARTemplateSurface(surface: A2UISurface): surface is AARTemplateSurface {
  return surface.type === 'aar_template'
}

export function isApprovalRequestSurface(surface: A2UISurface): surface is ApprovalRequestSurface {
  return surface.type === 'approval_request'
}

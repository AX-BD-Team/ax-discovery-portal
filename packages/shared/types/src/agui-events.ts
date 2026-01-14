/**
 * AG-UI (Agent-User Interaction) Event Types
 *
 * AG-UI 프로토콜 기반 이벤트 타입 정의
 * 에이전트 실행 상태, 단계 진행, 메시지 스트리밍, 승인 요청 등을 표준화
 */

// 이벤트 타입 열거형
export type AgentEventType =
  // 실행 제어
  | 'RUN_STARTED'
  | 'RUN_FINISHED'
  | 'RUN_ERROR'
  // 단계 진행
  | 'STEP_STARTED'
  | 'STEP_FINISHED'
  | 'STEP_ERROR'
  // 메시지 스트리밍
  | 'TEXT_MESSAGE_START'
  | 'TEXT_MESSAGE_CONTENT'
  | 'TEXT_MESSAGE_END'
  // 도구 호출
  | 'TOOL_CALL_START'
  | 'TOOL_CALL_ARGS'
  | 'TOOL_CALL_END'
  // 상태 동기화
  | 'STATE_SNAPSHOT'
  | 'STATE_DELTA'
  // 사용자 개입
  | 'ACTION_REQUIRED'
  | 'APPROVAL_REQUESTED'
  // A2UI Surface
  | 'RENDER_SURFACE'

// 실행 상태
export type RunStatus = 'idle' | 'running' | 'completed' | 'error' | 'paused'

// 단계 상태
export type StepStatus = 'pending' | 'running' | 'completed' | 'error' | 'skipped'

// 위험도 수준
export type ImpactLevel = 'low' | 'medium' | 'high' | 'critical'

// 워크플로 단계 정의 (WF-01 세미나 파이프라인)
export type SeminarPipelineStep =
  | 'METADATA_EXTRACTION'
  | 'ACTIVITY_CREATION'
  | 'AAR_TEMPLATE_GENERATION'
  | 'CONFLUENCE_UPDATE'
  | 'SIGNAL_INITIALIZATION'

// 기본 이벤트 인터페이스
export interface BaseAgentEvent {
  type: AgentEventType
  runId: string
  sessionId: string
  timestamp: string // ISO 8601
}

// 실행 시작 이벤트
export interface RunStartedEvent extends BaseAgentEvent {
  type: 'RUN_STARTED'
  workflowId: string
  input: Record<string, unknown>
  totalSteps: number
  steps: Array<{
    id: string
    label: string
  }>
}

// 실행 완료 이벤트
export interface RunFinishedEvent extends BaseAgentEvent {
  type: 'RUN_FINISHED'
  result: Record<string, unknown>
  durationMs: number
}

// 실행 오류 이벤트
export interface RunErrorEvent extends BaseAgentEvent {
  type: 'RUN_ERROR'
  error: string
  errorCode?: string
  recoverable: boolean
}

// 단계 시작 이벤트
export interface StepStartedEvent extends BaseAgentEvent {
  type: 'STEP_STARTED'
  stepId: string
  stepIndex: number
  stepLabel: string
  message?: string
}

// 단계 완료 이벤트
export interface StepFinishedEvent extends BaseAgentEvent {
  type: 'STEP_FINISHED'
  stepId: string
  stepIndex: number
  durationMs: number
  result?: Record<string, unknown>
}

// 단계 오류 이벤트
export interface StepErrorEvent extends BaseAgentEvent {
  type: 'STEP_ERROR'
  stepId: string
  stepIndex: number
  error: string
  recoverable: boolean
}

// 텍스트 메시지 시작 이벤트
export interface TextMessageStartEvent extends BaseAgentEvent {
  type: 'TEXT_MESSAGE_START'
  messageId: string
}

// 텍스트 메시지 내용 이벤트 (스트리밍)
export interface TextMessageContentEvent extends BaseAgentEvent {
  type: 'TEXT_MESSAGE_CONTENT'
  messageId: string
  content: string
  isComplete: boolean
}

// 텍스트 메시지 종료 이벤트
export interface TextMessageEndEvent extends BaseAgentEvent {
  type: 'TEXT_MESSAGE_END'
  messageId: string
  fullContent: string
}

// 도구 호출 시작 이벤트
export interface ToolCallStartEvent extends BaseAgentEvent {
  type: 'TOOL_CALL_START'
  toolCallId: string
  toolName: string
}

// 도구 호출 인자 이벤트
export interface ToolCallArgsEvent extends BaseAgentEvent {
  type: 'TOOL_CALL_ARGS'
  toolCallId: string
  args: Record<string, unknown>
}

// 도구 호출 완료 이벤트
export interface ToolCallEndEvent extends BaseAgentEvent {
  type: 'TOOL_CALL_END'
  toolCallId: string
  result?: unknown
  error?: string
  durationMs: number
}

// 상태 스냅샷 이벤트
export interface StateSnapshotEvent extends BaseAgentEvent {
  type: 'STATE_SNAPSHOT'
  state: Record<string, unknown>
}

// 상태 델타 이벤트 (JSON Patch RFC 6902 기반)
export interface StateDeltaEvent extends BaseAgentEvent {
  type: 'STATE_DELTA'
  patches: Array<{
    op: 'add' | 'remove' | 'replace' | 'move' | 'copy' | 'test'
    path: string
    value?: unknown
    from?: string
  }>
}

// 액션 요청 이벤트
export interface ActionRequiredEvent extends BaseAgentEvent {
  type: 'ACTION_REQUIRED'
  actionId: string
  actionType: string
  message: string
  options?: Array<{
    id: string
    label: string
    description?: string
  }>
  timeout?: number // ms
}

// 승인 요청 이벤트
export interface ApprovalRequestedEvent extends BaseAgentEvent {
  type: 'APPROVAL_REQUESTED'
  approvalId: string
  title: string
  description: string
  impact: ImpactLevel
  changes?: Array<{
    label: string
    before?: string
    after: string
    type: 'create' | 'update' | 'delete'
  }>
  timeout?: number // ms
}

// Surface 렌더링 이벤트 (A2UI 연동)
export interface RenderSurfaceEvent extends BaseAgentEvent {
  type: 'RENDER_SURFACE'
  surfaceId: string
  surface: import('./a2ui-surfaces').A2UISurface
}

// 모든 이벤트 타입 유니온
export type AgentEvent =
  | RunStartedEvent
  | RunFinishedEvent
  | RunErrorEvent
  | StepStartedEvent
  | StepFinishedEvent
  | StepErrorEvent
  | TextMessageStartEvent
  | TextMessageContentEvent
  | TextMessageEndEvent
  | ToolCallStartEvent
  | ToolCallArgsEvent
  | ToolCallEndEvent
  | StateSnapshotEvent
  | StateDeltaEvent
  | ActionRequiredEvent
  | ApprovalRequestedEvent
  | RenderSurfaceEvent

// 단계 정보 인터페이스
export interface StepInfo {
  id: string
  label: string
  status: StepStatus
  startedAt?: string
  finishedAt?: string
  durationMs?: number
  error?: string
}

// 에이전트 실행 상태 인터페이스
export interface AgentRunState {
  runId: string
  sessionId: string
  workflowId: string
  status: RunStatus
  currentStepIndex: number
  steps: StepInfo[]
  messages: string[]
  surfaces: Array<import('./a2ui-surfaces').A2UISurface>
  pendingApproval?: ApprovalRequestedEvent
  result?: Record<string, unknown>
  error?: string
  startedAt: string
  finishedAt?: string
}

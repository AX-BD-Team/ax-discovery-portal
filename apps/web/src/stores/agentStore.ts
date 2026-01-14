/**
 * Agent Store
 *
 * Zustand 기반 에이전트 실행 상태 관리
 * AG-UI 이벤트를 기반으로 상태 업데이트
 */

import { create } from 'zustand'
import { immer } from 'zustand/middleware/immer'
import type {
  AgentEvent,
  RunStatus,
  StepStatus,
  A2UISurface,
  ApprovalRequestedEvent,
} from '@ax/types'

// 단계 정보
interface StepInfo {
  id: string
  label: string
  status: StepStatus
  message?: string
  durationMs?: number
}

// 에이전트 실행 정보
interface AgentRun {
  runId: string
  sessionId: string
  workflowId: string
  status: RunStatus
  currentStepIndex: number
  steps: StepInfo[]
  events: AgentEvent[]
  surfaces: A2UISurface[]
  messages: string[]
  pendingApproval?: ApprovalRequestedEvent
  result?: Record<string, unknown>
  error?: string
  startedAt: string
  finishedAt?: string
}

// 스토어 상태
interface AgentStoreState {
  /** 모든 실행 목록 */
  runs: Record<string, AgentRun>
  /** 현재 활성화된 실행 ID */
  activeRunId: string | null
}

// 스토어 액션
interface AgentStoreActions {
  /** 새 실행 시작 */
  startRun: (runId: string, sessionId: string, workflowId: string) => void
  /** 이벤트로 실행 상태 업데이트 */
  updateFromEvent: (runId: string, event: AgentEvent) => void
  /** 활성 실행 설정 */
  setActiveRun: (runId: string | null) => void
  /** 승인 응답 */
  respondToApproval: (runId: string, approved: boolean, reason?: string) => void
  /** 실행 취소 */
  cancelRun: (runId: string) => void
  /** 실행 삭제 */
  removeRun: (runId: string) => void
  /** 모든 실행 초기화 */
  clearAllRuns: () => void
  /** 현재 활성 실행 가져오기 */
  getActiveRun: () => AgentRun | null
}

type AgentStore = AgentStoreState & AgentStoreActions

export const useAgentStore = create<AgentStore>()(
  immer((set, get) => ({
    // 초기 상태
    runs: {},
    activeRunId: null,

    // 액션
    startRun: (runId, sessionId, workflowId) => {
      set((state) => {
        state.runs[runId] = {
          runId,
          sessionId,
          workflowId,
          status: 'running',
          currentStepIndex: -1,
          steps: [],
          events: [],
          surfaces: [],
          messages: [],
          startedAt: new Date().toISOString(),
        }
        state.activeRunId = runId
      })
    },

    updateFromEvent: (runId, event) => {
      set((state) => {
        const run = state.runs[runId]
        if (!run) return

        // 이벤트 기록
        run.events.push(event)

        // 이벤트 타입별 처리
        switch (event.type) {
          case 'RUN_STARTED': {
            run.status = 'running'
            run.steps = (event as any).steps?.map((s: any) => ({
              id: s.id,
              label: s.label,
              status: 'pending' as StepStatus,
            })) || []
            break
          }

          case 'RUN_FINISHED': {
            run.status = 'completed'
            run.result = (event as any).result
            run.finishedAt = event.timestamp
            break
          }

          case 'RUN_ERROR': {
            run.status = 'error'
            run.error = (event as any).error
            run.finishedAt = event.timestamp
            break
          }

          case 'STEP_STARTED': {
            const stepEvent = event as any
            const stepIndex = run.steps.findIndex((s) => s.id === stepEvent.stepId)
            if (stepIndex >= 0) {
              run.steps[stepIndex].status = 'running'
              run.steps[stepIndex].message = stepEvent.message
            }
            run.currentStepIndex = stepEvent.stepIndex
            break
          }

          case 'STEP_FINISHED': {
            const stepEvent = event as any
            const stepIndex = run.steps.findIndex((s) => s.id === stepEvent.stepId)
            if (stepIndex >= 0) {
              run.steps[stepIndex].status = 'completed'
              run.steps[stepIndex].durationMs = stepEvent.durationMs
            }
            break
          }

          case 'STEP_ERROR': {
            const stepEvent = event as any
            const stepIndex = run.steps.findIndex((s) => s.id === stepEvent.stepId)
            if (stepIndex >= 0) {
              run.steps[stepIndex].status = 'error'
              run.steps[stepIndex].message = stepEvent.error
            }
            break
          }

          case 'TEXT_MESSAGE_CONTENT': {
            const msgEvent = event as any
            if (msgEvent.content) {
              run.messages.push(msgEvent.content)
            }
            break
          }

          case 'RENDER_SURFACE': {
            const surfaceEvent = event as any
            if (surfaceEvent.surface) {
              run.surfaces.push(surfaceEvent.surface)
            }
            break
          }

          case 'APPROVAL_REQUESTED': {
            run.status = 'paused'
            run.pendingApproval = event as ApprovalRequestedEvent
            break
          }
        }
      })
    },

    setActiveRun: (runId) => {
      set((state) => {
        state.activeRunId = runId
      })
    },

    respondToApproval: (runId, approved, reason) => {
      set((state) => {
        const run = state.runs[runId]
        if (run) {
          run.pendingApproval = undefined
          if (approved) {
            run.status = 'running'
          } else {
            run.status = 'error'
            run.error = reason || '사용자가 승인을 거부했습니다'
          }
        }
      })
    },

    cancelRun: (runId) => {
      set((state) => {
        const run = state.runs[runId]
        if (run) {
          run.status = 'error'
          run.error = '사용자가 실행을 취소했습니다'
          run.finishedAt = new Date().toISOString()
        }
      })
    },

    removeRun: (runId) => {
      set((state) => {
        delete state.runs[runId]
        if (state.activeRunId === runId) {
          state.activeRunId = null
        }
      })
    },

    clearAllRuns: () => {
      set((state) => {
        state.runs = {}
        state.activeRunId = null
      })
    },

    getActiveRun: () => {
      const { runs, activeRunId } = get()
      return activeRunId ? runs[activeRunId] : null
    },
  }))
)

// 셀렉터
export const selectActiveRun = (state: AgentStore) =>
  state.activeRunId ? state.runs[state.activeRunId] : null

export const selectRunById = (runId: string) => (state: AgentStore) =>
  state.runs[runId]

export const selectAllRuns = (state: AgentStore) => Object.values(state.runs)

export type { AgentRun, StepInfo, AgentStore }

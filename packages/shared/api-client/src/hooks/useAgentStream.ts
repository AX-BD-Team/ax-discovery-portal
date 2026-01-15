/**
 * useAgentStream Hook
 *
 * AG-UI 이벤트 스트림(SSE) 구독 훅
 * 에이전트 워크플로 실행 상태를 실시간으로 수신
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import type { AgentEvent, AgentEventType, RunStatus } from '@ax/types'

interface UseAgentStreamOptions {
  /** 워크플로 ID (예: WF-01) */
  workflowId: string
  /** API 베이스 URL */
  baseUrl?: string
  /** 이벤트 수신 콜백 */
  onEvent?: (event: AgentEvent) => void
  /** 오류 콜백 */
  onError?: (error: Error) => void
  /** 연결 상태 변경 콜백 */
  onStatusChange?: (status: ConnectionStatus) => void
  /** 자동 재연결 여부 */
  autoReconnect?: boolean
  /** 재연결 최대 시도 횟수 */
  maxReconnectAttempts?: number
}

type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'error' | 'closed'

interface UseAgentStreamReturn {
  /** 현재 연결 상태 */
  status: ConnectionStatus
  /** 수신된 이벤트 목록 */
  events: AgentEvent[]
  /** 현재 실행 상태 */
  runStatus: RunStatus
  /** 스트림 연결 시작 */
  connect: (params?: Record<string, string>) => void
  /** 스트림 연결 종료 */
  disconnect: () => void
  /** 이벤트 목록 초기화 */
  clearEvents: () => void
  /** 마지막 오류 */
  error: Error | null
}

const DEFAULT_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function useAgentStream(options: UseAgentStreamOptions): UseAgentStreamReturn {
  const {
    workflowId,
    baseUrl = DEFAULT_BASE_URL,
    onEvent,
    onError,
    onStatusChange,
    autoReconnect = false,
    maxReconnectAttempts = 3,
  } = options

  const [status, setStatus] = useState<ConnectionStatus>('idle')
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [runStatus, setRunStatus] = useState<RunStatus>('idle')
  const [error, setError] = useState<Error | null>(null)

  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectAttemptsRef = useRef(0)

  // 상태 업데이트 헬퍼
  const updateStatus = useCallback(
    (newStatus: ConnectionStatus) => {
      setStatus(newStatus)
      onStatusChange?.(newStatus)
    },
    [onStatusChange]
  )

  // 이벤트 처리
  const handleEvent = useCallback(
    (event: AgentEvent) => {
      setEvents(prev => [...prev, event])
      onEvent?.(event)

      // 실행 상태 업데이트
      switch (event.type) {
        case 'RUN_STARTED':
          setRunStatus('running')
          break
        case 'RUN_FINISHED':
          setRunStatus('completed')
          break
        case 'RUN_ERROR':
          setRunStatus('error')
          break
        case 'APPROVAL_REQUESTED':
          setRunStatus('paused')
          break
      }
    },
    [onEvent]
  )

  // 연결 시작
  const connect = useCallback(
    (params?: Record<string, string>) => {
      // 기존 연결 종료
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }

      // URL 생성
      const url = new URL(`${baseUrl}/api/stream/workflow/${workflowId}`)
      if (params) {
        Object.entries(params).forEach(([key, value]) => {
          url.searchParams.set(key, value)
        })
      }

      updateStatus('connecting')
      setEvents([])
      setRunStatus('idle')
      setError(null)

      try {
        const es = new EventSource(url.toString())

        es.onopen = () => {
          updateStatus('connected')
          reconnectAttemptsRef.current = 0
        }

        es.onerror = e => {
          const err = new Error('SSE 연결 오류')
          setError(err)
          onError?.(err)

          if (es.readyState === EventSource.CLOSED) {
            updateStatus('closed')

            // 자동 재연결
            if (autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
              reconnectAttemptsRef.current++
              setTimeout(() => connect(params), 1000 * reconnectAttemptsRef.current)
            } else {
              updateStatus('error')
            }
          }
        }

        // 각 이벤트 타입별 핸들러 등록
        const eventTypes: AgentEventType[] = [
          'RUN_STARTED',
          'RUN_FINISHED',
          'RUN_ERROR',
          'STEP_STARTED',
          'STEP_FINISHED',
          'STEP_ERROR',
          'TEXT_MESSAGE_START',
          'TEXT_MESSAGE_CONTENT',
          'TEXT_MESSAGE_END',
          'TOOL_CALL_START',
          'TOOL_CALL_ARGS',
          'TOOL_CALL_END',
          'STATE_SNAPSHOT',
          'STATE_DELTA',
          'ACTION_REQUIRED',
          'APPROVAL_REQUESTED',
          'RENDER_SURFACE',
        ]

        eventTypes.forEach(eventType => {
          es.addEventListener(eventType, (e: MessageEvent) => {
            try {
              const event = JSON.parse(e.data) as AgentEvent
              handleEvent(event)
            } catch (parseError) {
              console.error('이벤트 파싱 오류:', parseError)
            }
          })
        })

        // Keep-alive 이벤트 처리
        es.addEventListener('KEEP_ALIVE', () => {
          // 연결 유지 확인
        })

        eventSourceRef.current = es
      } catch (e) {
        const err = e instanceof Error ? e : new Error('SSE 연결 실패')
        setError(err)
        onError?.(err)
        updateStatus('error')
      }
    },
    [workflowId, baseUrl, updateStatus, handleEvent, onError, autoReconnect, maxReconnectAttempts]
  )

  // 연결 종료
  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    updateStatus('closed')
  }, [updateStatus])

  // 이벤트 초기화
  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  // 컴포넌트 언마운트 시 정리
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  return {
    status,
    events,
    runStatus,
    connect,
    disconnect,
    clearEvents,
    error,
  }
}

export type { UseAgentStreamOptions, UseAgentStreamReturn, ConnectionStatus }

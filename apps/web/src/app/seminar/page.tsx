'use client'

/**
 * 세미나 등록 페이지
 *
 * WF-01 세미나 파이프라인을 실행하고 결과를 표시
 * AG-UI/A2UI 패턴을 활용한 Agentic UI 예시
 */

import { useState, useCallback } from 'react'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Button,
  Input,
  Label,
  Badge,
  AgentRunContainer,
  StepIndicator,
  StreamingText,
  SurfaceRenderer,
} from '@ax/ui'
import type { A2UISurface, StepStatus } from '@ax/types'
import { useAgentStream } from '@ax/api-client'
import { useAgentStore, selectActiveRun } from '@/stores/agentStore'
import { ExternalLink, Play, RotateCcw } from 'lucide-react'

export default function SeminarPage() {
  // 폼 상태
  const [url, setUrl] = useState('')
  const [themes, setThemes] = useState('')
  const [playId, setPlayId] = useState('EXT_Desk_D01_Seminar')

  // 스토어
  const { startRun, updateFromEvent, getActiveRun } = useAgentStore()
  const activeRun = useAgentStore(selectActiveRun)

  // SSE 훅
  const { status, connect, disconnect, events, runStatus } = useAgentStream({
    workflowId: 'WF-01',
    onEvent: (event) => {
      if (activeRun) {
        updateFromEvent(activeRun.runId, event)
      }
    },
    onError: (error) => {
      console.error('SSE 오류:', error)
    },
  })

  // 실행 시작
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()

      if (!url) return

      // 새 실행 시작
      const runId = `run-${Date.now()}`
      const sessionId = `sess-WF-01-${Date.now()}`
      startRun(runId, sessionId, 'WF-01')

      // SSE 연결
      connect({
        url,
        themes: themes || undefined,
        play_id: playId,
      } as Record<string, string>)
    },
    [url, themes, playId, startRun, connect]
  )

  // 재시도
  const handleRetry = useCallback(() => {
    handleSubmit({ preventDefault: () => {} } as React.FormEvent)
  }, [handleSubmit])

  // 취소
  const handleCancel = useCallback(() => {
    disconnect()
  }, [disconnect])

  // 초기화
  const handleReset = useCallback(() => {
    setUrl('')
    setThemes('')
    disconnect()
  }, [disconnect])

  // 단계 데이터 변환
  const steps =
    activeRun?.steps.map((step) => ({
      id: step.id,
      label: step.label,
      status: step.status as StepStatus,
      message: step.message,
      duration: step.durationMs,
    })) || []

  // Surface 데이터
  const surfaces = activeRun?.surfaces || []

  // 마지막 메시지
  const lastMessage = activeRun?.messages[activeRun.messages.length - 1] || ''

  return (
    <div className="container mx-auto max-w-4xl py-8 px-4">
      {/* 헤더 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold">세미나 등록</h1>
        <p className="mt-1 text-muted-foreground">
          세미나/컨퍼런스 URL을 입력하면 자동으로 Activity와 AAR 템플릿을 생성합니다.
        </p>
      </div>

      {/* 입력 폼 */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg">세미나 정보 입력</CardTitle>
          <CardDescription>등록할 세미나의 URL과 관련 정보를 입력하세요</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="url">세미나 URL *</Label>
              <Input
                id="url"
                type="url"
                placeholder="https://example.com/seminar"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
                disabled={status === 'connecting' || status === 'connected'}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="themes">테마 (쉼표로 구분)</Label>
              <Input
                id="themes"
                type="text"
                placeholder="AI, 클라우드, 데이터"
                value={themes}
                onChange={(e) => setThemes(e.target.value)}
                disabled={status === 'connecting' || status === 'connected'}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="playId">Play ID</Label>
              <Input
                id="playId"
                type="text"
                placeholder="EXT_Desk_D01_Seminar"
                value={playId}
                onChange={(e) => setPlayId(e.target.value)}
                disabled={status === 'connecting' || status === 'connected'}
              />
            </div>

            <div className="flex gap-2 pt-2">
              <Button
                type="submit"
                disabled={!url || status === 'connecting' || status === 'connected'}
              >
                <Play className="mr-2 h-4 w-4" />
                등록 시작
              </Button>
              {(status === 'connected' || status === 'connecting') && (
                <Button type="button" variant="outline" onClick={handleCancel}>
                  취소
                </Button>
              )}
              {(activeRun?.status === 'completed' || activeRun?.status === 'error') && (
                <Button type="button" variant="outline" onClick={handleReset}>
                  <RotateCcw className="mr-2 h-4 w-4" />
                  새로 시작
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      {/* 실행 상태 */}
      {activeRun && (
        <AgentRunContainer
          runId={activeRun.runId}
          sessionId={activeRun.sessionId}
          title="세미나 등록 파이프라인"
          description={`WF-01 | ${activeRun.workflowId}`}
          status={activeRun.status}
          onCancel={handleCancel}
          onRetry={handleRetry}
          className="mb-6"
        >
          {/* 단계 표시 */}
          {steps.length > 0 && (
            <div className="mb-4">
              <StepIndicator
                steps={steps}
                currentStepIndex={activeRun.currentStepIndex}
                orientation="vertical"
              />
            </div>
          )}

          {/* 메시지 */}
          {lastMessage && (
            <div className="mb-4">
              <StreamingText
                content={lastMessage}
                isStreaming={activeRun.status === 'running'}
              />
            </div>
          )}

          {/* 오류 표시 */}
          {activeRun.error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
              <strong>오류:</strong> {activeRun.error}
            </div>
          )}
        </AgentRunContainer>
      )}

      {/* Surface 렌더링 */}
      {surfaces.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">결과</h2>
          {surfaces.map((surface, index) => (
            <SurfaceRenderer key={surface.id || index} surface={surface} />
          ))}
        </div>
      )}

      {/* 완료 상태 */}
      {activeRun?.status === 'completed' && activeRun.result && (
        <Card className="mt-6 border-green-200 dark:border-green-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-green-600">
              <Badge variant="outline" className="border-green-300 text-green-600">
                완료
              </Badge>
              등록 완료
            </CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Activity ID</dt>
                <dd className="font-mono">{String(activeRun.result.activity_id || '-')}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Confluence 업데이트</dt>
                <dd>{activeRun.result.confluence_updated ? '완료' : '미완료'}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

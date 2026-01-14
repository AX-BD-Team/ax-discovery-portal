import type { SignalChannel, SignalSource, SignalStatus } from '@ax/types'

/**
 * Application constants
 */

export const SIGNAL_SOURCES: SignalSource[] = ['KT', '그룹사', '대외']

export const SIGNAL_CHANNELS: SignalChannel[] = [
  '데스크리서치',
  '자사활동',
  '영업PM',
  '인바운드',
  '아웃바운드',
]

export const SIGNAL_STATUSES: SignalStatus[] = [
  'NEW',
  'SCORING',
  'SCORED',
  'BRIEF_CREATED',
  'VALIDATED',
  'PILOT_READY',
  'ARCHIVED',
]

export const STATUS_LABELS: Record<SignalStatus, string> = {
  NEW: '신규',
  SCORING: '평가 중',
  SCORED: '평가 완료',
  BRIEF_CREATED: 'Brief 작성',
  VALIDATED: '검증 완료',
  PILOT_READY: 'Pilot 준비',
  ARCHIVED: '보관',
}

export const SCORECARD_DIMENSIONS = {
  problem_severity: '문제 심각도',
  willingness_to_pay: '지불 의사',
  data_availability: '데이터 가용성',
  feasibility: '실현 가능성',
  strategic_fit: '전략 적합성',
} as const

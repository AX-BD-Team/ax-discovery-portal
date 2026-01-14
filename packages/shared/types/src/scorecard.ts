import type { NextStep, ScorecardDecision } from './common'

/**
 * Dimension Scores (5 dimensions × 20 points)
 */
export interface DimensionScores {
  problem_severity: number // 문제 심각도 (20점)
  willingness_to_pay: number // 지불 의사 (20점)
  data_availability: number // 데이터 가용성 (20점)
  feasibility: number // 실현 가능성 (20점)
  strategic_fit: number // 전략 적합성 (20점)
}

/**
 * Recommendation
 */
export interface Recommendation {
  decision: ScorecardDecision
  next_step: NextStep
  rationale?: string
}

/**
 * Scorecard - Signal 평가 스코어카드
 */
export interface Scorecard {
  scorecard_id?: string
  signal_id: string
  total_score: number // 100점 만점
  dimension_scores: DimensionScores
  red_flags: string[]
  recommendation: Recommendation
  scored_by?: string
  scored_at: string
}

/**
 * Evaluate Signal Options
 */
export interface EvaluateSignalOptions {
  mode?: 'auto' | 'manual'
}

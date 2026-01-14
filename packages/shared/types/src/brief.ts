import type { BriefStatus, ValidationMethod } from './common'

/**
 * Customer Information
 */
export interface Customer {
  segment: string
  buyer_role: string
  users?: string
  account?: string
}

/**
 * Problem Definition
 */
export interface Problem {
  pain: string
  why_now: string
  current_process?: string
}

/**
 * Solution Hypothesis
 */
export interface SolutionHypothesis {
  approach: string
  integration_points: string[]
  data_needed?: string[]
}

/**
 * Validation Plan
 */
export interface ValidationPlan {
  questions: string[]
  method: ValidationMethod
  success_criteria: string[]
  timebox_days: number
}

/**
 * MVP Scope
 */
export interface MvpScope {
  in_scope?: string[]
  out_of_scope?: string[]
}

/**
 * Brief - 1-Page Opportunity Brief
 */
export interface Brief {
  brief_id: string
  signal_id: string
  title: string
  customer: Customer
  problem: Problem
  solution_hypothesis: SolutionHypothesis
  kpis: string[]
  evidence: string[]
  validation_plan: ValidationPlan
  mvp_scope?: MvpScope
  risks?: string[]
  status: BriefStatus
  owner: string
  confluence_url?: string
  created_at: string
  updated_at?: string
}

/**
 * Create Brief Request
 */
export type CreateBriefRequest = Omit<Brief, 'brief_id' | 'created_at' | 'updated_at'>

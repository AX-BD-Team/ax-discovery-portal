/**
 * Common types used across the application
 */

export type SignalSource = 'KT' | '그룹사' | '대외'

export type SignalChannel = '데스크리서치' | '자사활동' | '영업PM' | '인바운드' | '아웃바운드'

export type SignalStatus =
  | 'NEW'
  | 'SCORING'
  | 'SCORED'
  | 'BRIEF_CREATED'
  | 'VALIDATED'
  | 'PILOT_READY'
  | 'ARCHIVED'

export type EvidenceType = 'link' | 'doc' | 'ticket' | 'meeting_note' | 'dataset' | 'image'

export interface Evidence {
  type: EvidenceType
  title: string
  url: string
  note?: string
}

export type ScorecardDecision = 'GO' | 'PIVOT' | 'HOLD' | 'NO_GO'

export type NextStep = 'BRIEF' | 'VALIDATION' | 'PILOT_READY' | 'DROP' | 'NEED_MORE_EVIDENCE'

export type BriefStatus = 'DRAFT' | 'REVIEW' | 'APPROVED' | 'VALIDATED' | 'PILOT_READY' | 'ARCHIVED'

export type ValidationMethod =
  | '5DAY_SPRINT'
  | 'INTERVIEW'
  | 'DATA_ANALYSIS'
  | 'BUYER_REVIEW'
  | 'POC'

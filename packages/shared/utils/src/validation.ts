/**
 * Validation utilities
 */

/**
 * Validate Signal ID format (SIG-YYYY-XXX)
 */
export function isValidSignalId(id: string): boolean {
  return /^SIG-\d{4}-\d{3,}$/.test(id)
}

/**
 * Validate Scorecard ID format (SCR-YYYY-XXX)
 */
export function isValidScorecardId(id: string): boolean {
  return /^SCR-\d{4}-\d{3,}$/.test(id)
}

/**
 * Validate Brief ID format (BRF-YYYY-XXX)
 */
export function isValidBriefId(id: string): boolean {
  return /^BRF-\d{4}-\d{3,}$/.test(id)
}

/**
 * Validate score range (0-100)
 */
export function isValidScore(score: number): boolean {
  return score >= 0 && score <= 100
}

/**
 * Validate dimension score (0-20)
 */
export function isValidDimensionScore(score: number): boolean {
  return score >= 0 && score <= 20
}

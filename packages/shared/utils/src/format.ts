import { format as dateFnsFormat } from 'date-fns'
import { ko } from 'date-fns/locale'

/**
 * Format date to Korean locale
 */
export function formatDate(date: string | Date, formatStr: string = 'yyyy-MM-dd'): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date
  return dateFnsFormat(dateObj, formatStr, { locale: ko })
}

/**
 * Format date to relative time (e.g., "2시간 전")
 */
export function formatRelativeTime(date: string | Date): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date
  const now = new Date()
  const diff = now.getTime() - dateObj.getTime()

  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) return `${days}일 전`
  if (hours > 0) return `${hours}시간 전`
  if (minutes > 0) return `${minutes}분 전`
  return '방금 전'
}

/**
 * Format score to percentage
 */
export function formatScore(score: number): string {
  return `${score}점`
}

/**
 * Get status badge color
 */
export function getStatusColor(
  status: string
): 'gray' | 'blue' | 'green' | 'yellow' | 'red' | 'purple' {
  const statusColors: Record<string, 'gray' | 'blue' | 'green' | 'yellow' | 'red' | 'purple'> = {
    NEW: 'gray',
    SCORING: 'blue',
    SCORED: 'blue',
    BRIEF_CREATED: 'yellow',
    VALIDATED: 'green',
    PILOT_READY: 'purple',
    ARCHIVED: 'gray',
    DRAFT: 'gray',
    REVIEW: 'yellow',
    APPROVED: 'green',
  }
  return statusColors[status] || 'gray'
}

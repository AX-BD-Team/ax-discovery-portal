/**
 * ActivityPreviewCard
 *
 * Activity 미리보기 카드 컴포넌트
 * WF-01 세미나 파이프라인 결과 표시용
 */

import * as React from 'react'
import { cn } from '@ax/utils'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '../components/card'
import { Badge } from '../components/badge'
import { ExternalLink, Calendar, MapPin, User, Tag, Edit } from 'lucide-react'

interface ActivityData {
  activity_id: string
  title: string
  date?: string | null
  organizer?: string | null
  url: string
  play_id: string
  themes?: string[]
  source: string
  channel: string
  status: string
}

interface ActivityPreviewCardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Activity 데이터 */
  activity: ActivityData
  /** 수정 버튼 클릭 핸들러 */
  onEdit?: () => void
  /** 카드 변형 */
  variant?: 'default' | 'compact'
}

const ActivityPreviewCard = React.forwardRef<HTMLDivElement, ActivityPreviewCardProps>(
  ({ className, activity, onEdit, variant = 'default', ...props }, ref) => {
    const isCompact = variant === 'compact'

    return (
      <Card
        ref={ref}
        className={cn(
          'border-green-200 dark:border-green-800',
          isCompact && 'shadow-sm',
          className
        )}
        {...props}
      >
        <CardHeader className={cn(isCompact && 'pb-2')}>
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <CardTitle className={cn('truncate', isCompact ? 'text-base' : 'text-lg')}>
                {activity.title}
              </CardTitle>
              <CardDescription className="mt-1 font-mono text-xs">
                {activity.activity_id}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge
                variant="outline"
                className="shrink-0 border-green-300 text-green-600 dark:border-green-700 dark:text-green-400"
              >
                {activity.status}
              </Badge>
              {onEdit && (
                <button
                  onClick={onEdit}
                  className="rounded-md p-1 text-muted-foreground hover:bg-muted transition-colors"
                  aria-label="수정"
                >
                  <Edit className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>
        </CardHeader>

        <CardContent className={cn('space-y-3', isCompact && 'pt-0')}>
          {/* 메타 정보 */}
          <div className="grid gap-2 text-sm">
            {activity.date && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Calendar className="h-4 w-4 shrink-0" />
                <span>{activity.date}</span>
              </div>
            )}
            {activity.organizer && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <User className="h-4 w-4 shrink-0" />
                <span className="truncate">{activity.organizer}</span>
              </div>
            )}
            <div className="flex items-center gap-2 text-muted-foreground">
              <MapPin className="h-4 w-4 shrink-0" />
              <span>
                {activity.source} / {activity.channel}
              </span>
            </div>
          </div>

          {/* 테마 태그 */}
          {activity.themes && activity.themes.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {activity.themes.map((theme, i) => (
                <Badge key={i} variant="secondary" className="text-xs">
                  <Tag className="mr-1 h-3 w-3" />
                  {theme}
                </Badge>
              ))}
            </div>
          )}

          {/* Play ID */}
          <div className="text-xs text-muted-foreground">
            Play: <span className="font-mono">{activity.play_id}</span>
          </div>
        </CardContent>

        <CardFooter className="pt-0">
          <a
            href={activity.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
          >
            <ExternalLink className="h-4 w-4" />
            원본 링크 열기
          </a>
        </CardFooter>
      </Card>
    )
  }
)
ActivityPreviewCard.displayName = 'ActivityPreviewCard'

export { ActivityPreviewCard }
export type { ActivityPreviewCardProps, ActivityData }

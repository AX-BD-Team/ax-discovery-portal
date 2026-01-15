/**
 * SurfaceRenderer
 *
 * A2UI Surface를 React 컴포넌트로 렌더링
 * 허용된 카탈로그 컴포넌트만 렌더링 (보안)
 */

import * as React from 'react'
import { cn } from '@ax/utils'
import type { A2UISurface, SurfaceRendererContext, SurfaceType, SURFACE_CATALOG } from '@ax/types'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '../components/card'
import { Badge } from '../components/badge'
import { Button } from '../components/button'
import { ExternalLink, Calendar, MapPin, User, Tag, FileText, AlertTriangle } from 'lucide-react'

interface SurfaceRendererProps extends React.HTMLAttributes<HTMLDivElement> {
  /** A2UI Surface 데이터 */
  surface: A2UISurface
  /** 액션 콜백 컨텍스트 */
  context?: SurfaceRendererContext
}

/**
 * 허용된 Surface 타입 목록
 */
const ALLOWED_SURFACE_TYPES: SurfaceType[] = [
  'form',
  'card',
  'table',
  'summary',
  'action_buttons',
  'progress',
  'message',
  'activity_preview',
  'aar_template',
  'approval_request',
]

/**
 * Activity Preview Surface 렌더러
 */
function ActivityPreviewRenderer({
  surface,
  context,
}: {
  surface: Extract<A2UISurface, { type: 'activity_preview' }>
  context?: SurfaceRendererContext
}) {
  const { activity } = surface

  return (
    <Card className="border-green-200 dark:border-green-800">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg">{activity.title}</CardTitle>
            <CardDescription className="mt-1">{activity.activity_id}</CardDescription>
          </div>
          <Badge variant="outline" className="text-green-600 border-green-300">
            {activity.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-2 text-sm">
          {activity.date && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Calendar className="h-4 w-4" />
              <span>{activity.date}</span>
            </div>
          )}
          {activity.organizer && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <User className="h-4 w-4" />
              <span>{activity.organizer}</span>
            </div>
          )}
          <div className="flex items-center gap-2 text-muted-foreground">
            <MapPin className="h-4 w-4" />
            <span>
              {activity.source} / {activity.channel}
            </span>
          </div>
        </div>

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

/**
 * AAR Template Surface 렌더러
 */
function AARTemplateRenderer({
  surface,
  context,
}: {
  surface: Extract<A2UISurface, { type: 'aar_template' }>
  context?: SurfaceRendererContext
}) {
  const [copied, setCopied] = React.useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(surface.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="h-4 w-4" />
            AAR 템플릿
          </CardTitle>
          <Button variant="outline" size="sm" onClick={handleCopy} className="h-7 text-xs">
            {copied ? '복사됨!' : '복사'}
          </Button>
        </div>
        <CardDescription>Activity: {surface.activityId}</CardDescription>
      </CardHeader>
      <CardContent>
        <pre className="max-h-[300px] overflow-auto rounded-lg bg-muted p-3 text-xs whitespace-pre-wrap">
          {surface.content}
        </pre>
      </CardContent>
      {surface.confluenceUrl && (
        <CardFooter className="pt-0">
          <a
            href={surface.confluenceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
          >
            <ExternalLink className="h-4 w-4" />
            Confluence에서 보기
          </a>
        </CardFooter>
      )}
    </Card>
  )
}

/**
 * Message Surface 렌더러
 */
function MessageRenderer({ surface }: { surface: Extract<A2UISurface, { type: 'message' }> }) {
  const variantStyles = {
    info: 'bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-950 dark:border-blue-800 dark:text-blue-200',
    success:
      'bg-green-50 border-green-200 text-green-800 dark:bg-green-950 dark:border-green-800 dark:text-green-200',
    warning:
      'bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-950 dark:border-yellow-800 dark:text-yellow-200',
    error:
      'bg-red-50 border-red-200 text-red-800 dark:bg-red-950 dark:border-red-800 dark:text-red-200',
  }

  return (
    <div className={cn('rounded-lg border p-3 text-sm', variantStyles[surface.variant])}>
      {surface.variant === 'warning' && <AlertTriangle className="mb-1 h-4 w-4" />}
      <p>{surface.content}</p>
    </div>
  )
}

/**
 * Generic Card Surface 렌더러
 */
function CardRenderer({
  surface,
  context,
}: {
  surface: Extract<A2UISurface, { type: 'card' }>
  context?: SurfaceRendererContext
}) {
  return (
    <Card>
      {surface.title && (
        <CardHeader>
          <CardTitle>{surface.title}</CardTitle>
          {surface.description && <CardDescription>{surface.description}</CardDescription>}
        </CardHeader>
      )}
      <CardContent>
        <div className="prose prose-sm dark:prose-invert max-w-none">{surface.content}</div>
        {surface.badges && surface.badges.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {surface.badges.map((badge, i) => (
              <Badge key={i} variant={badge.variant}>
                {badge.label}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
      {surface.footer && (
        <CardFooter>
          <p className="text-sm text-muted-foreground">{surface.footer}</p>
        </CardFooter>
      )}
      {surface.actions && surface.actions.length > 0 && (
        <CardFooter className="gap-2">
          {surface.actions.map(action => (
            <Button
              key={action.id}
              variant={
                action.type === 'destructive'
                  ? 'destructive'
                  : action.type === 'primary'
                    ? 'default'
                    : 'outline'
              }
              size="sm"
              disabled={action.disabled}
              onClick={() => context?.onAction?.(surface.id, action.id)}
            >
              {action.label}
            </Button>
          ))}
        </CardFooter>
      )}
    </Card>
  )
}

/**
 * Progress Surface 렌더러
 */
function ProgressRenderer({ surface }: { surface: Extract<A2UISurface, { type: 'progress' }> }) {
  const statusColors = {
    active: 'bg-blue-500',
    success: 'bg-green-500',
    error: 'bg-red-500',
    paused: 'bg-yellow-500',
  }

  return (
    <div className="space-y-2">
      {surface.title && (
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium">{surface.title}</span>
          <span className="text-muted-foreground">
            {surface.current} / {surface.total}
          </span>
        </div>
      )}
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={cn(
            'h-full transition-all duration-300',
            statusColors[surface.status || 'active']
          )}
          style={{ width: `${surface.percentage}%` }}
        />
      </div>
      {surface.message && <p className="text-xs text-muted-foreground">{surface.message}</p>}
    </div>
  )
}

/**
 * Fallback 렌더러 (알 수 없는 타입)
 */
function FallbackRenderer({ surface }: { surface: A2UISurface }) {
  return (
    <div className="rounded-lg border border-dashed border-muted-foreground/25 p-4 text-center text-sm text-muted-foreground">
      <p>지원하지 않는 Surface 타입: {surface.type}</p>
    </div>
  )
}

/**
 * Main SurfaceRenderer 컴포넌트
 */
const SurfaceRenderer = React.forwardRef<HTMLDivElement, SurfaceRendererProps>(
  ({ className, surface, context, ...props }, ref) => {
    // 보안: 허용된 타입만 렌더링
    if (!ALLOWED_SURFACE_TYPES.includes(surface.type)) {
      console.warn(`Surface type "${surface.type}" is not in the allowed catalog`)
      return <FallbackRenderer surface={surface} />
    }

    return (
      <div ref={ref} className={cn('w-full', className)} data-surface-id={surface.id} {...props}>
        {surface.type === 'activity_preview' && (
          <ActivityPreviewRenderer
            surface={surface as Extract<A2UISurface, { type: 'activity_preview' }>}
            context={context}
          />
        )}
        {surface.type === 'aar_template' && (
          <AARTemplateRenderer
            surface={surface as Extract<A2UISurface, { type: 'aar_template' }>}
            context={context}
          />
        )}
        {surface.type === 'message' && (
          <MessageRenderer surface={surface as Extract<A2UISurface, { type: 'message' }>} />
        )}
        {surface.type === 'card' && (
          <CardRenderer
            surface={surface as Extract<A2UISurface, { type: 'card' }>}
            context={context}
          />
        )}
        {surface.type === 'progress' && (
          <ProgressRenderer surface={surface as Extract<A2UISurface, { type: 'progress' }>} />
        )}
        {!['activity_preview', 'aar_template', 'message', 'card', 'progress'].includes(
          surface.type
        ) && <FallbackRenderer surface={surface} />}
      </div>
    )
  }
)
SurfaceRenderer.displayName = 'SurfaceRenderer'

export { SurfaceRenderer }
export type { SurfaceRendererProps }

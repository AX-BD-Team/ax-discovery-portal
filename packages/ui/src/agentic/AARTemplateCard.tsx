/**
 * AARTemplateCard
 *
 * AAR(After Action Review) 템플릿 표시 카드
 * WF-01 세미나 파이프라인 결과물
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
import { Button } from '../components/button'
import { FileText, Copy, Check, ExternalLink, Download, Edit2 } from 'lucide-react'

interface AARTemplateCardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Activity ID */
  activityId: string
  /** 템플릿 내용 (Markdown) */
  content: string
  /** Confluence 페이지 URL */
  confluenceUrl?: string | null
  /** 작성 시작 핸들러 */
  onStartFilling?: () => void
  /** 다운로드 핸들러 */
  onDownload?: () => void
  /** 최대 표시 높이 */
  maxHeight?: number | string
  /** 접힌 상태로 시작 */
  defaultCollapsed?: boolean
}

const AARTemplateCard = React.forwardRef<HTMLDivElement, AARTemplateCardProps>(
  (
    {
      className,
      activityId,
      content,
      confluenceUrl,
      onStartFilling,
      onDownload,
      maxHeight = 300,
      defaultCollapsed = false,
      ...props
    },
    ref
  ) => {
    const [copied, setCopied] = React.useState(false)
    const [collapsed, setCollapsed] = React.useState(defaultCollapsed)

    // 클립보드 복사
    const handleCopy = async () => {
      try {
        await navigator.clipboard.writeText(content)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      } catch (err) {
        console.error('복사 실패:', err)
      }
    }

    // 다운로드
    const handleDownload = () => {
      if (onDownload) {
        onDownload()
        return
      }

      // 기본 다운로드 로직
      const blob = new Blob([content], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `AAR-${activityId}.md`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }

    return (
      <Card ref={ref} className={cn(className)} {...props}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4 text-muted-foreground" />
              AAR 템플릿
            </CardTitle>

            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" onClick={handleCopy} className="h-7 px-2 text-xs">
                {copied ? (
                  <>
                    <Check className="mr-1 h-3 w-3" />
                    복사됨
                  </>
                ) : (
                  <>
                    <Copy className="mr-1 h-3 w-3" />
                    복사
                  </>
                )}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleDownload}
                className="h-7 px-2 text-xs"
              >
                <Download className="mr-1 h-3 w-3" />
                저장
              </Button>
            </div>
          </div>
          <CardDescription className="font-mono text-xs">Activity: {activityId}</CardDescription>
        </CardHeader>

        <CardContent>
          {/* 토글 버튼 */}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="mb-2 text-xs text-muted-foreground hover:text-foreground"
          >
            {collapsed ? '▶ 템플릿 펼치기' : '▼ 템플릿 접기'}
          </button>

          {/* 템플릿 내용 */}
          {!collapsed && (
            <pre
              className={cn(
                'overflow-auto rounded-lg bg-muted p-3 text-xs whitespace-pre-wrap font-mono',
                'leading-relaxed'
              )}
              style={{ maxHeight: typeof maxHeight === 'number' ? `${maxHeight}px` : maxHeight }}
            >
              {content}
            </pre>
          )}
        </CardContent>

        <CardFooter className="flex flex-wrap gap-2 pt-0">
          {confluenceUrl && (
            <a
              href={confluenceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
            >
              <ExternalLink className="h-4 w-4" />
              Confluence에서 보기
            </a>
          )}
          {onStartFilling && (
            <Button variant="outline" size="sm" onClick={onStartFilling} className="ml-auto">
              <Edit2 className="mr-1.5 h-4 w-4" />
              작성 시작
            </Button>
          )}
        </CardFooter>
      </Card>
    )
  }
)
AARTemplateCard.displayName = 'AARTemplateCard'

export { AARTemplateCard }
export type { AARTemplateCardProps }

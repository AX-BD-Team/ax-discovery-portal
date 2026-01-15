/**
 * StreamingText
 *
 * 실시간 텍스트 스트리밍 표시 컴포넌트
 * 타이핑 효과와 스트리밍 상태 표시
 */

import * as React from 'react'
import { cn } from '@ax/utils'

interface StreamingTextProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 표시할 텍스트 내용 */
  content: string
  /** 스트리밍 중 여부 */
  isStreaming: boolean
  /** 타이핑 속도 (ms per character) - 스트리밍 종료 후 애니메이션용 */
  typingSpeed?: number
  /** 커서 표시 여부 */
  showCursor?: boolean
  /** 메시지 ID (여러 메시지 구분용) */
  messageId?: string
}

const StreamingText = React.forwardRef<HTMLDivElement, StreamingTextProps>(
  (
    { className, content, isStreaming, typingSpeed = 0, showCursor = true, messageId, ...props },
    ref
  ) => {
    const [displayedContent, setDisplayedContent] = React.useState(content)

    // 컨텐츠가 변경될 때 업데이트
    React.useEffect(() => {
      setDisplayedContent(content)
    }, [content])

    return (
      <div
        ref={ref}
        className={cn(
          'relative rounded-lg bg-muted/50 p-3 text-sm',
          isStreaming && 'animate-pulse-subtle',
          className
        )}
        data-message-id={messageId}
        {...props}
      >
        {/* Text content */}
        <p className="whitespace-pre-wrap break-words leading-relaxed">
          {displayedContent}
          {/* Cursor */}
          {showCursor && isStreaming && (
            <span className="ml-0.5 inline-block h-4 w-0.5 animate-blink bg-foreground" />
          )}
        </p>

        {/* Streaming indicator */}
        {isStreaming && (
          <div className="mt-2 flex items-center gap-1.5">
            <span className="flex gap-1">
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.3s]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.15s]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary" />
            </span>
            <span className="text-xs text-muted-foreground">처리 중...</span>
          </div>
        )}
      </div>
    )
  }
)
StreamingText.displayName = 'StreamingText'

/**
 * StreamingTextList
 *
 * 여러 스트리밍 메시지를 표시하는 컨테이너
 */
interface StreamingTextListProps extends React.HTMLAttributes<HTMLDivElement> {
  messages: Array<{
    id: string
    content: string
    isStreaming: boolean
  }>
}

const StreamingTextList = React.forwardRef<HTMLDivElement, StreamingTextListProps>(
  ({ className, messages, ...props }, ref) => {
    return (
      <div ref={ref} className={cn('flex flex-col gap-2', className)} {...props}>
        {messages.map(message => (
          <StreamingText
            key={message.id}
            content={message.content}
            isStreaming={message.isStreaming}
            messageId={message.id}
          />
        ))}
      </div>
    )
  }
)
StreamingTextList.displayName = 'StreamingTextList'

export { StreamingText, StreamingTextList }
export type { StreamingTextProps, StreamingTextListProps }

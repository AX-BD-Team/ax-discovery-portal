'use client'

import * as React from 'react'
import { Bot, Calendar, Check, ExternalLink, Loader2, Paperclip, Send, User, X } from 'lucide-react'
import { Button } from '../components/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/card'
import { Input } from '../components/input'
import { Badge } from '../components/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/tabs'
import { FileUploadZone } from './FileUploadZone'

export interface SeminarExtractResult {
  title: string
  description: string | null
  date: string | null
  organizer: string | null
  url: string | null
  categories: string[]
  confidence: number
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  files?: File[]
  extractedSeminars?: SeminarExtractResult[]
}

export interface SeminarChatPanelProps {
  isOpen: boolean
  onClose: () => void
  onSeminarAdded?: (seminars: SeminarExtractResult[]) => void
  onChatSubmit: (
    message: string,
    files?: File[]
  ) => Promise<{
    stream: ReadableStream<ChatSSEEvent>
    abort: () => void
  }>
  onConfirmSeminars: (seminars: SeminarExtractResult[], playId?: string) => Promise<void>
  onUploadFiles: (
    files: File[],
    playId?: string
  ) => Promise<{
    total_extracted: number
    results: Array<{
      filename: string
      extracted_count: number
      seminars: SeminarExtractResult[]
      error: string | null
    }>
  }>
}

interface ChatSSEEvent {
  type: 'start' | 'progress' | 'info' | 'extracted' | 'complete' | 'error'
  message?: string
  seminars?: SeminarExtractResult[]
  count?: number
  timestamp?: string
}

function SeminarPreviewCard({
  seminar,
  selected,
  onToggle,
}: {
  seminar: SeminarExtractResult
  selected: boolean
  onToggle: () => void
}) {
  return (
    <Card
      className={`cursor-pointer transition-all ${
        selected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
      }`}
      onClick={onToggle}
    >
      <CardContent className="p-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h4 className="font-medium text-sm truncate">{seminar.title}</h4>
            {seminar.description && (
              <p className="text-xs text-gray-600 line-clamp-2 mt-1">{seminar.description}</p>
            )}
            <div className="flex flex-wrap gap-1 mt-2">
              {seminar.date && (
                <Badge variant="secondary" className="text-xs">
                  <Calendar className="h-3 w-3 mr-1" />
                  {seminar.date}
                </Badge>
              )}
              {seminar.organizer && (
                <Badge variant="outline" className="text-xs">
                  {seminar.organizer}
                </Badge>
              )}
              {seminar.url && (
                <a
                  href={seminar.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={e => e.stopPropagation()}
                  className="text-xs text-blue-600 hover:underline flex items-center gap-0.5"
                >
                  <ExternalLink className="h-3 w-3" />
                  링크
                </a>
              )}
            </div>
          </div>
          <div
            className={`flex-shrink-0 h-5 w-5 rounded-full border-2 flex items-center justify-center ${
              selected ? 'border-blue-500 bg-blue-500 text-white' : 'border-gray-300'
            }`}
          >
            {selected && <Check className="h-3 w-3" />}
          </div>
        </div>
        <div className="mt-2 flex items-center gap-1">
          <div className="h-1 flex-1 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500"
              style={{ width: `${seminar.confidence * 100}%` }}
            />
          </div>
          <span className="text-xs text-gray-500">{Math.round(seminar.confidence * 100)}%</span>
        </div>
      </CardContent>
    </Card>
  )
}

function ChatMessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-2 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-blue-100' : 'bg-gray-100'
        }`}
      >
        {isUser ? (
          <User className="h-4 w-4 text-blue-600" />
        ) : (
          <Bot className="h-4 w-4 text-gray-600" />
        )}
      </div>
      <div className={`flex-1 max-w-[80%] ${isUser ? 'text-right' : ''}`}>
        <div
          className={`inline-block rounded-lg px-3 py-2 text-sm ${
            isUser ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-800'
          }`}
        >
          {message.content}
          {message.files && message.files.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {message.files.map((file, i) => (
                <Badge key={i} variant="secondary" className="text-xs">
                  <Paperclip className="h-3 w-3 mr-1" />
                  {file.name}
                </Badge>
              ))}
            </div>
          )}
        </div>
        {message.extractedSeminars && message.extractedSeminars.length > 0 && (
          <div className="mt-2 text-left">
            <p className="text-xs text-gray-500 mb-1">
              {message.extractedSeminars.length}개의 세미나 발견
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export function SeminarChatPanel({
  isOpen,
  onClose,
  onSeminarAdded,
  onChatSubmit,
  onConfirmSeminars,
  onUploadFiles,
}: SeminarChatPanelProps) {
  const [messages, setMessages] = React.useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = React.useState('')
  const [attachedFiles, setAttachedFiles] = React.useState<File[]>([])
  const [isLoading, setIsLoading] = React.useState(false)
  const [extractedSeminars, setExtractedSeminars] = React.useState<SeminarExtractResult[]>([])
  const [selectedSeminars, setSelectedSeminars] = React.useState<Set<number>>(new Set())
  const [activeTab, setActiveTab] = React.useState<string>('chat')
  const messagesEndRef = React.useRef<HTMLDivElement>(null)
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  // 메시지 목록 스크롤
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 초기 메시지
  React.useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content:
            '안녕하세요! 세미나 정보를 추가해드릴게요. URL을 붙여넣거나, 세미나 정보를 입력해주세요. 이미지나 파일을 첨부하면 OCR로 정보를 추출할 수도 있어요.',
          timestamp: new Date(),
        },
      ])
    }
  }, [isOpen, messages.length])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() && attachedFiles.length === 0) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue || '(파일 첨부)',
      timestamp: new Date(),
      files: attachedFiles.length > 0 ? [...attachedFiles] : undefined,
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setAttachedFiles([])
    setIsLoading(true)

    try {
      const { stream } = await onChatSubmit(inputValue, attachedFiles)
      const reader = stream.getReader()

      let assistantContent = ''
      const newSeminars: SeminarExtractResult[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        if (value.type === 'progress' || value.type === 'info') {
          assistantContent = value.message || ''
        } else if (value.type === 'extracted' && value.seminars) {
          newSeminars.push(...value.seminars)
        } else if (value.type === 'complete') {
          assistantContent = value.message || `${newSeminars.length}개의 세미나를 찾았습니다.`
        } else if (value.type === 'error') {
          assistantContent = value.message || '처리 중 오류가 발생했습니다.'
        }
      }

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: assistantContent,
        timestamp: new Date(),
        extractedSeminars: newSeminars.length > 0 ? newSeminars : undefined,
      }

      setMessages(prev => [...prev, assistantMessage])

      if (newSeminars.length > 0) {
        setExtractedSeminars(prev => [...prev, ...newSeminars])
        // 새로 추출된 세미나 모두 선택
        setSelectedSeminars(prev => {
          const newSet = new Set(prev)
          const currentLength = extractedSeminars.length
          newSeminars.forEach((_, i) => newSet.add(currentLength + i))
          return newSet
        })
      }
    } catch (error) {
      setMessages(prev => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `오류가 발생했습니다: ${(error as Error).message}`,
          timestamp: new Date(),
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    setAttachedFiles(prev => [...prev, ...files])
  }

  const handleRemoveFile = (index: number) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleToggleSeminar = (index: number) => {
    setSelectedSeminars(prev => {
      const newSet = new Set(prev)
      if (newSet.has(index)) {
        newSet.delete(index)
      } else {
        newSet.add(index)
      }
      return newSet
    })
  }

  const handleConfirm = async () => {
    const selectedList = extractedSeminars.filter((_, i) => selectedSeminars.has(i))
    if (selectedList.length === 0) return

    setIsLoading(true)
    try {
      await onConfirmSeminars(selectedList)

      setMessages(prev => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: `${selectedList.length}개의 세미나가 등록되었습니다!`,
          timestamp: new Date(),
        },
      ])

      // 등록된 세미나 제거
      const remainingIndices = [...selectedSeminars]
      remainingIndices.sort((a, b) => b - a)
      let newSeminars = [...extractedSeminars]
      remainingIndices.forEach(i => newSeminars.splice(i, 1))
      setExtractedSeminars(newSeminars)
      setSelectedSeminars(new Set())

      onSeminarAdded?.(selectedList)
    } catch (error) {
      setMessages(prev => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: `등록 중 오류가 발생했습니다: ${(error as Error).message}`,
          timestamp: new Date(),
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleUploadComplete = (seminars: SeminarExtractResult[]) => {
    if (seminars.length > 0) {
      const currentLength = extractedSeminars.length
      setExtractedSeminars(prev => [...prev, ...seminars])
      setSelectedSeminars(prev => {
        const newSet = new Set(prev)
        seminars.forEach((_, i) => newSet.add(currentLength + i))
        return newSet
      })

      setMessages(prev => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: `파일에서 ${seminars.length}개의 세미나를 추출했습니다.`,
          timestamp: new Date(),
        },
      ])
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-lg bg-white shadow-xl z-50 flex flex-col">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h2 className="font-semibold">세미나 추가</h2>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* 탭 */}
      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="flex-1 flex flex-col overflow-hidden"
      >
        <TabsList className="mx-4 mt-2">
          <TabsTrigger value="chat">채팅으로 추가</TabsTrigger>
          <TabsTrigger value="upload">파일 업로드</TabsTrigger>
        </TabsList>

        <TabsContent value="chat" className="flex-1 flex flex-col overflow-hidden m-0 p-0">
          {/* 메시지 목록 */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map(message => (
              <ChatMessageBubble key={message.id} message={message} />
            ))}
            {isLoading && (
              <div className="flex gap-2">
                <div className="h-8 w-8 rounded-full bg-gray-100 flex items-center justify-center">
                  <Bot className="h-4 w-4 text-gray-600" />
                </div>
                <div className="flex items-center gap-1 text-gray-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm">처리 중...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 첨부 파일 미리보기 */}
          {attachedFiles.length > 0 && (
            <div className="px-4 py-2 border-t bg-gray-50">
              <div className="flex flex-wrap gap-2">
                {attachedFiles.map((file, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-1 bg-white rounded px-2 py-1 text-sm border"
                  >
                    <Paperclip className="h-3 w-3" />
                    <span className="truncate max-w-[100px]">{file.name}</span>
                    <button
                      onClick={() => handleRemoveFile(i)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 입력창 */}
          <form onSubmit={handleSubmit} className="p-4 border-t">
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={() => fileInputRef.current?.click()}
              >
                <Paperclip className="h-4 w-4" />
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/*,.pdf,.docx,.xlsx,.txt,.csv,.json,.md"
                onChange={handleFileSelect}
                className="hidden"
              />
              <Input
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                placeholder="URL 또는 세미나 정보 입력..."
                disabled={isLoading}
                className="flex-1"
              />
              <Button type="submit" disabled={isLoading}>
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </form>
        </TabsContent>

        <TabsContent value="upload" className="flex-1 overflow-y-auto m-0 p-4">
          <FileUploadZone onUpload={onUploadFiles} onComplete={handleUploadComplete} />
        </TabsContent>
      </Tabs>

      {/* 추출된 세미나 목록 */}
      {extractedSeminars.length > 0 && (
        <div className="border-t p-4 max-h-[40%] overflow-y-auto">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium text-sm">
              추출된 세미나 ({selectedSeminars.size}/{extractedSeminars.length})
            </h3>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (selectedSeminars.size === extractedSeminars.length) {
                    setSelectedSeminars(new Set())
                  } else {
                    setSelectedSeminars(new Set(extractedSeminars.map((_, i) => i)))
                  }
                }}
              >
                {selectedSeminars.size === extractedSeminars.length ? '전체 해제' : '전체 선택'}
              </Button>
              <Button
                size="sm"
                disabled={selectedSeminars.size === 0 || isLoading}
                onClick={handleConfirm}
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                ) : (
                  <Check className="h-4 w-4 mr-1" />
                )}
                선택 등록 ({selectedSeminars.size})
              </Button>
            </div>
          </div>
          <div className="space-y-2">
            {extractedSeminars.map((seminar, i) => (
              <SeminarPreviewCard
                key={i}
                seminar={seminar}
                selected={selectedSeminars.has(i)}
                onToggle={() => handleToggleSeminar(i)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

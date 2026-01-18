'use client'

import * as React from 'react'
import {
  FileImage,
  FileText,
  FileSpreadsheet,
  File,
  Loader2,
  Upload,
  X,
  CheckCircle,
  AlertCircle,
} from 'lucide-react'
import { Button } from '../components/button'
import { Card, CardContent } from '../components/card'
import { Badge } from '../components/badge'

export interface SeminarExtractResult {
  title: string
  description: string | null
  date: string | null
  organizer: string | null
  url: string | null
  categories: string[]
  confidence: number
}

interface UploadResult {
  filename: string
  extracted_count: number
  seminars: SeminarExtractResult[]
  error: string | null
}

export interface FileUploadZoneProps {
  onUpload: (
    files: File[],
    playId?: string
  ) => Promise<{
    total_extracted: number
    results: UploadResult[]
  }>
  onComplete?: (seminars: SeminarExtractResult[]) => void
  className?: string
}

interface FileItem {
  file: File
  status: 'pending' | 'uploading' | 'success' | 'error'
  result?: UploadResult
}

const FILE_TYPE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  image: FileImage,
  pdf: FileText,
  spreadsheet: FileSpreadsheet,
  default: File,
}

const SUPPORTED_EXTENSIONS = [
  '.jpg',
  '.jpeg',
  '.png',
  '.webp',
  '.gif',
  '.pdf',
  '.docx',
  '.xlsx',
  '.xls',
  '.txt',
  '.csv',
  '.json',
  '.md',
]

function getFileType(filename: string): string {
  const ext = filename.toLowerCase().split('.').pop() || ''
  if (['jpg', 'jpeg', 'png', 'webp', 'gif'].includes(ext)) return 'image'
  if (ext === 'pdf') return 'pdf'
  if (['xlsx', 'xls', 'csv'].includes(ext)) return 'spreadsheet'
  return 'default'
}

function getFileIcon(filename: string) {
  const type = getFileType(filename)
  return FILE_TYPE_ICONS[type] || FILE_TYPE_ICONS.default
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function FileItemRow({ item, onRemove }: { item: FileItem; onRemove: () => void }) {
  const FileIcon = getFileIcon(item.file.name)

  return (
    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
      <div className="flex-shrink-0">
        <FileIcon className="h-8 w-8 text-gray-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{item.file.name}</p>
        <p className="text-xs text-gray-500">{formatFileSize(item.file.size)}</p>
        {item.status === 'success' && item.result && (
          <p className="text-xs text-green-600">{item.result.extracted_count}개 세미나 추출</p>
        )}
        {item.status === 'error' && item.result?.error && (
          <p className="text-xs text-red-600">{item.result.error}</p>
        )}
      </div>
      <div className="flex-shrink-0">
        {item.status === 'pending' && (
          <Button variant="ghost" size="sm" onClick={onRemove} className="h-8 w-8 p-0">
            <X className="h-4 w-4" />
          </Button>
        )}
        {item.status === 'uploading' && <Loader2 className="h-5 w-5 animate-spin text-blue-500" />}
        {item.status === 'success' && <CheckCircle className="h-5 w-5 text-green-500" />}
        {item.status === 'error' && <AlertCircle className="h-5 w-5 text-red-500" />}
      </div>
    </div>
  )
}

export function FileUploadZone({ onUpload, onComplete, className }: FileUploadZoneProps) {
  const [files, setFiles] = React.useState<FileItem[]>([])
  const [isDragging, setIsDragging] = React.useState(false)
  const [isUploading, setIsUploading] = React.useState(false)
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const droppedFiles = Array.from(e.dataTransfer.files)
    addFiles(droppedFiles)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || [])
    addFiles(selectedFiles)
    e.target.value = '' // Reset input
  }

  const addFiles = (newFiles: File[]) => {
    // 지원 확장자 필터링
    const validFiles = newFiles.filter(file => {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase()
      return SUPPORTED_EXTENSIONS.includes(ext)
    })

    const newItems: FileItem[] = validFiles.map(file => ({
      file,
      status: 'pending',
    }))

    setFiles(prev => [...prev, ...newItems])
  }

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleUpload = async () => {
    if (files.length === 0) return

    const pendingFiles = files.filter(f => f.status === 'pending')
    if (pendingFiles.length === 0) return

    setIsUploading(true)

    // 상태 업데이트: uploading
    setFiles(prev => prev.map(f => (f.status === 'pending' ? { ...f, status: 'uploading' } : f)))

    try {
      const response = await onUpload(pendingFiles.map(f => f.file))

      // 결과 매핑
      const allSeminars: SeminarExtractResult[] = []
      setFiles(prev =>
        prev.map(f => {
          if (f.status === 'uploading') {
            const result = response.results.find(r => r.filename === f.file.name)
            if (result) {
              allSeminars.push(...result.seminars)
              return {
                ...f,
                status: result.error ? 'error' : 'success',
                result,
              }
            }
          }
          return f
        })
      )

      // 완료 콜백
      if (allSeminars.length > 0) {
        onComplete?.(allSeminars)
      }
    } catch (error) {
      // 오류 시 모든 업로드 중인 파일을 에러로 표시
      setFiles(prev =>
        prev.map(f =>
          f.status === 'uploading'
            ? {
                ...f,
                status: 'error',
                result: {
                  filename: f.file.name,
                  extracted_count: 0,
                  seminars: [],
                  error: (error as Error).message,
                },
              }
            : f
        )
      )
    } finally {
      setIsUploading(false)
    }
  }

  const handleClearAll = () => {
    setFiles([])
  }

  const pendingCount = files.filter(f => f.status === 'pending').length
  const successCount = files.filter(f => f.status === 'success').length
  const totalExtracted = files
    .filter(f => f.status === 'success' && f.result)
    .reduce((sum, f) => sum + (f.result?.extracted_count || 0), 0)

  return (
    <div className={className}>
      {/* 드롭존 */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
          transition-colors
          ${
            isDragging
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={SUPPORTED_EXTENSIONS.join(',')}
          onChange={handleFileSelect}
          className="hidden"
        />
        <Upload className="h-10 w-10 mx-auto text-gray-400 mb-3" />
        <p className="text-gray-600 mb-1">파일을 드래그하거나 클릭하여 선택하세요</p>
        <p className="text-xs text-gray-400">
          지원 형식: 이미지(JPG, PNG), PDF, 문서(DOCX, XLSX), 텍스트(TXT, CSV, JSON, MD)
        </p>
      </div>

      {/* 파일 목록 */}
      {files.length > 0 && (
        <Card className="mt-4">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">파일 목록 ({files.length})</span>
                {successCount > 0 && (
                  <Badge variant="secondary" className="text-xs">
                    {totalExtracted}개 세미나 추출
                  </Badge>
                )}
              </div>
              <Button variant="ghost" size="sm" onClick={handleClearAll}>
                전체 삭제
              </Button>
            </div>

            <div className="space-y-2 max-h-[300px] overflow-y-auto">
              {files.map((item, index) => (
                <FileItemRow
                  key={`${item.file.name}-${index}`}
                  item={item}
                  onRemove={() => removeFile(index)}
                />
              ))}
            </div>

            {pendingCount > 0 && (
              <Button className="w-full mt-4" onClick={handleUpload} disabled={isUploading}>
                {isUploading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    처리 중...
                  </>
                ) : (
                  <>
                    <Upload className="h-4 w-4 mr-2" />
                    {pendingCount}개 파일 업로드
                  </>
                )}
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

'use client'

import { useEffect } from 'react'
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ax/ui'
import { AlertTriangle, RefreshCw, Home } from 'lucide-react'
import Link from 'next/link'

interface ErrorPageProps {
  error: Error & { digest?: string }
  reset: () => void
}

export default function Error({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    // 에러 로깅 (Sentry 등 연동 시 사용)
    console.error('Application error:', error)
  }, [error])

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 p-8">
      <Card className="w-full max-w-lg border-red-200 shadow-lg">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
            <AlertTriangle className="h-8 w-8 text-red-600" />
          </div>
          <CardTitle className="text-2xl text-gray-900">오류가 발생했습니다</CardTitle>
          <CardDescription className="text-gray-600">
            예기치 않은 오류가 발생했습니다. 문제가 지속되면 관리자에게 문의해주세요.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 에러 메시지 (개발 모드에서만 표시) */}
          {process.env.NODE_ENV === 'development' && (
            <div className="rounded-lg bg-gray-100 p-4">
              <p className="mb-1 text-xs font-medium text-gray-500">Error Details</p>
              <p className="break-all font-mono text-sm text-gray-700">{error.message}</p>
              {error.digest && (
                <p className="mt-2 text-xs text-gray-500">Digest: {error.digest}</p>
              )}
            </div>
          )}

          <div className="flex flex-col gap-3 sm:flex-row">
            <Button onClick={reset} className="flex-1 gap-2">
              <RefreshCw className="h-4 w-4" />
              다시 시도
            </Button>
            <Link href="/" className="flex-1">
              <Button variant="outline" className="w-full gap-2">
                <Home className="h-4 w-4" />
                홈으로 이동
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

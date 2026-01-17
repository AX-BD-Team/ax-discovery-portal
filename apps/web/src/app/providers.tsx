'use client'

import { QueryClient, QueryClientProvider, MutationCache, QueryCache } from '@tanstack/react-query'
import { Toaster, toast } from '@ax/ui'
import { useState, useCallback } from 'react'

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    // Ky HTTPError
    if ('response' in error && error.response) {
      const response = error.response as Response
      if (response.status === 401) return '인증이 만료되었습니다. 다시 로그인해주세요.'
      if (response.status === 403) return '접근 권한이 없습니다.'
      if (response.status === 404) return '요청한 리소스를 찾을 수 없습니다.'
      if (response.status >= 500) return '서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
    }
    return error.message
  }
  return '알 수 없는 오류가 발생했습니다.'
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1분
            refetchOnWindowFocus: false,
            retry: (failureCount, error) => {
              // 401, 403, 404는 재시도하지 않음
              if (error instanceof Error && 'response' in error) {
                const response = error.response as Response | undefined
                if (response && [401, 403, 404].includes(response.status)) {
                  return false
                }
              }
              return failureCount < 2
            },
          },
          mutations: {
            retry: false,
          },
        },
        queryCache: new QueryCache({
          onError: (error, query) => {
            // 백그라운드 refetch 에러는 무시 (이미 데이터가 있는 경우)
            if (query.state.data !== undefined) {
              console.warn('Background refetch failed:', error)
              return
            }
            // 첫 로드 에러만 toast 표시
            toast.error('데이터 로딩 실패', {
              description: getErrorMessage(error),
            })
          },
        }),
        mutationCache: new MutationCache({
          onError: (error) => {
            toast.error('작업 실패', {
              description: getErrorMessage(error),
            })
          },
        }),
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster position="top-right" richColors closeButton />
    </QueryClientProvider>
  )
}

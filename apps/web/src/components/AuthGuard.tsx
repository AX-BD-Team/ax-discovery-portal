'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuthStore } from '@/stores'

interface AuthGuardProps {
  children: React.ReactNode
  requireAdmin?: boolean
}

// 인증이 필요 없는 경로
const PUBLIC_PATHS = ['/login']

export function AuthGuard({ children, requireAdmin = false }: AuthGuardProps) {
  const router = useRouter()
  const pathname = usePathname()
  const { token, user, checkAuth, isLoading } = useAuthStore()
  const [isChecking, setIsChecking] = useState(true)

  useEffect(() => {
    const verifyAuth = async () => {
      // 공개 경로는 인증 체크 생략
      if (PUBLIC_PATHS.includes(pathname)) {
        setIsChecking(false)
        return
      }

      // 토큰이 있으면 인증 상태 확인
      if (token) {
        const isValid = await checkAuth()
        if (!isValid) {
          router.push('/login')
        } else if (requireAdmin && user?.role !== 'admin') {
          // 관리자 권한 필요하지만 일반 사용자인 경우
          router.push('/')
        }
      } else {
        // 토큰이 없으면 로그인 페이지로
        router.push('/login')
      }

      setIsChecking(false)
    }

    verifyAuth()
  }, [token, pathname, checkAuth, router, requireAdmin, user?.role])

  // 공개 경로는 바로 렌더링
  if (PUBLIC_PATHS.includes(pathname)) {
    return <>{children}</>
  }

  // 인증 체크 중 로딩 표시
  if (isChecking || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent mx-auto"></div>
          <p className="text-gray-500">인증 확인 중...</p>
        </div>
      </div>
    )
  }

  // 인증되지 않은 경우 아무것도 렌더링하지 않음 (리다이렉트 중)
  if (!token || !user) {
    return null
  }

  // 관리자 권한 체크
  if (requireAdmin && user.role !== 'admin') {
    return null
  }

  return <>{children}</>
}

export default AuthGuard

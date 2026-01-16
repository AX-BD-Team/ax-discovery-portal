/**
 * Auth Store
 *
 * Zustand 기반 인증 상태 관리
 * JWT 토큰 및 사용자 정보 관리
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'

// 사용자 정보 타입
export interface User {
  user_id: string
  email: string
  name: string
  role: 'admin' | 'user'
  is_active: boolean
  last_login_at: string | null
}

// 로그인 응답 타입
interface LoginResponse {
  access_token: string
  token_type: string
}

// 인증 상태
interface AuthState {
  /** 인증 토큰 */
  token: string | null
  /** 현재 사용자 정보 */
  user: User | null
  /** 로딩 상태 */
  isLoading: boolean
  /** 에러 메시지 */
  error: string | null
}

// 인증 액션
interface AuthActions {
  /** 로그인 */
  login: (email: string, password: string) => Promise<boolean>
  /** 로그아웃 */
  logout: () => void
  /** 현재 사용자 정보 조회 (토큰 검증) */
  checkAuth: () => Promise<boolean>
  /** 에러 초기화 */
  clearError: () => void
  /** 인증 여부 */
  isAuthenticated: () => boolean
  /** 관리자 여부 */
  isAdmin: () => boolean
}

type AuthStore = AuthState & AuthActions

// API Base URL
const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  }
  return 'http://localhost:8000'
}

export const useAuthStore = create<AuthStore>()(
  persist(
    immer((set, get) => ({
      // 초기 상태
      token: null,
      user: null,
      isLoading: false,
      error: null,

      // 로그인
      login: async (email: string, password: string) => {
        set((state) => {
          state.isLoading = true
          state.error = null
        })

        try {
          const response = await fetch(`${getApiUrl()}/api/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password }),
          })

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}))
            throw new Error(errorData.detail || '로그인에 실패했습니다')
          }

          const data: LoginResponse = await response.json()

          // 토큰 저장 (localStorage에도 저장 - API Client 호환)
          localStorage.setItem('auth_token', data.access_token)

          set((state) => {
            state.token = data.access_token
            state.isLoading = false
          })

          // 사용자 정보 조회
          await get().checkAuth()

          return true
        } catch (error) {
          set((state) => {
            state.isLoading = false
            state.error = error instanceof Error ? error.message : '로그인에 실패했습니다'
          })
          return false
        }
      },

      // 로그아웃
      logout: () => {
        localStorage.removeItem('auth_token')
        set((state) => {
          state.token = null
          state.user = null
          state.error = null
        })
      },

      // 인증 상태 확인 (토큰 검증 + 사용자 정보 조회)
      checkAuth: async () => {
        const token = get().token || localStorage.getItem('auth_token')

        if (!token) {
          set((state) => {
            state.user = null
          })
          return false
        }

        set((state) => {
          state.isLoading = true
        })

        try {
          const response = await fetch(`${getApiUrl()}/api/auth/me`, {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          })

          if (!response.ok) {
            // 토큰이 유효하지 않으면 로그아웃
            get().logout()
            return false
          }

          const data = await response.json()

          set((state) => {
            state.token = token
            state.user = data.user
            state.isLoading = false
          })

          // localStorage 동기화
          if (!localStorage.getItem('auth_token')) {
            localStorage.setItem('auth_token', token)
          }

          return true
        } catch {
          set((state) => {
            state.isLoading = false
          })
          get().logout()
          return false
        }
      },

      // 에러 초기화
      clearError: () => {
        set((state) => {
          state.error = null
        })
      },

      // 인증 여부 확인
      isAuthenticated: () => {
        return !!get().token && !!get().user
      },

      // 관리자 여부 확인
      isAdmin: () => {
        return get().user?.role === 'admin'
      },
    })),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
      }),
    }
  )
)

// 셀렉터
export const selectUser = (state: AuthStore) => state.user
export const selectIsAuthenticated = (state: AuthStore) => !!state.token && !!state.user
export const selectIsAdmin = (state: AuthStore) => state.user?.role === 'admin'
export const selectIsLoading = (state: AuthStore) => state.isLoading
export const selectError = (state: AuthStore) => state.error

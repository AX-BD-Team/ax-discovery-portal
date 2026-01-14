import ky from 'ky'

/**
 * API Client Configuration
 */
export interface ApiClientConfig {
  baseUrl: string
  timeout?: number
  headers?: Record<string, string>
}

/**
 * Create API client instance
 */
export function createApiClient(config: ApiClientConfig) {
  const { baseUrl, timeout = 30000, headers = {} } = config

  const client = ky.create({
    prefixUrl: baseUrl,
    timeout,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    hooks: {
      beforeRequest: [
        request => {
          // Add auth token if available
          const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
          if (token) {
            request.headers.set('Authorization', `Bearer ${token}`)
          }
        },
      ],
    },
  })

  return client
}

/**
 * Default API client (can be overridden)
 */
export const apiClient = createApiClient({
  baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
})

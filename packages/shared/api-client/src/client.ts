import ky from 'ky'

/**
 * API Client Configuration
 */
export interface ApiClientConfig {
  baseUrl: string
  timeout?: number
  headers?: Record<string, string>
  onUnauthorized?: () => void
}

/**
 * Create API client instance
 */
export function createApiClient(config: ApiClientConfig) {
  const { baseUrl, timeout = 30000, headers = {}, onUnauthorized } = config

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
      afterResponse: [
        async (_request, _options, response) => {
          // Handle 401 Unauthorized - auto logout
          if (response.status === 401 && typeof window !== 'undefined') {
            localStorage.removeItem('auth_token')

            // Call custom handler if provided
            if (onUnauthorized) {
              onUnauthorized()
            } else {
              // Default: redirect to login
              window.location.href = '/login'
            }
          }
          return response
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

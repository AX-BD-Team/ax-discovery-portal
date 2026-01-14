declare module 'next-pwa' {
  import type { NextConfig } from 'next'

  interface PWAConfig {
    dest?: string
    disable?: boolean
    register?: boolean
    skipWaiting?: boolean
    scope?: string
    sw?: string
    runtimeCaching?: unknown[]
    publicExcludes?: string[]
    buildExcludes?: (string | RegExp)[]
  }

  function withPWA(config?: PWAConfig): (nextConfig: NextConfig) => NextConfig
  export default withPWA
}

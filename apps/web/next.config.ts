import type { NextConfig } from 'next'
import withPWA from 'next-pwa'

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@ax/api-client', '@ax/types', '@ax/utils', '@ax/config', '@ax/ui'],
  experimental: {
    optimizePackageImports: ['@ax/ui'],
  },
}

const pwaConfig = withPWA({
  dest: 'public',
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === 'development',
})

export default pwaConfig(nextConfig)

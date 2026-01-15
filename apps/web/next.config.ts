import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  reactStrictMode: true,
  transpilePackages: ['@ax/api-client', '@ax/types', '@ax/utils', '@ax/config', '@ax/ui'],
  experimental: {
    optimizePackageImports: ['@ax/ui'],
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig

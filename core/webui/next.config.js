/**
 * @type {import('next').NextConfig}
 */
const { i18n } = require('./next-i18next.config.js')
const fs = require('fs')
const path = require('path')
const JSON5 = require('json5')

const isStaticExport = process.env.EXPORT_STATIC === 'true'

/**
 * Read the engine base URL from config/settings.json5 (services.engine).
 * Priority: NEXT_PUBLIC_CODES_API env var → settings.json5 → hardcoded default.
 */
function readEngineBaseUrl() {
  if (process.env.NEXT_PUBLIC_CODES_API) {
    return process.env.NEXT_PUBLIC_CODES_API.replace(/\/$/, '')
  }
  try {
    const settingsPath = path.resolve(__dirname, '../../config/settings.json5')
    const data = JSON5.parse(fs.readFileSync(settingsPath, 'utf-8'))
    const engine = (data && data.services && data.services.engine) || {}
    const host = engine.host || '127.0.0.1'
    const port = engine.port || 3001
    return `http://${host}:${port}`
  } catch (_) {
    return 'http://127.0.0.1:3001'
  }
}

const engineBaseUrl = readEngineBaseUrl()

const nextConfig = {
  env: {
    CODES_API_SSR: engineBaseUrl,
  },
  reactStrictMode: true,
  ...(isStaticExport ? { output: 'export', distDir: 'www'} : {}),
  ...(isStaticExport ? {} : { i18n }),
  allowedDevOrigins: [
    'localhost',
    '*.localhost',
    '127.0.0.1',
  ],
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'private, no-store, max-age=0',
          },
        ],
      },
    ]
  },
  async rewrites() {
    if (isStaticExport) return []
    return [
      {
        source: '/api/:path*',
        destination: `${engineBaseUrl}/api/:path*`,
      },
    ]
  },
  trailingSlash: isStaticExport ? true : false,
}


module.exports = nextConfig

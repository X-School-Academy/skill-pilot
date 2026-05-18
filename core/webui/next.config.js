/**
 * @type {import('next').NextConfig}
 */
const { PHASE_DEVELOPMENT_SERVER } = require('next/constants')
const fs = require('fs')
const os = require('os')
const path = require('path')
const JSON5 = require('json5')

const isStaticExport = process.env.EXPORT_STATIC === 'true'

function normalizeRuntimeMode(value, defaultMode = 'production') {
  const normalized = String(value || '').trim().toLowerCase()
  if (normalized === 'dev' || normalized === 'development') return 'development'
  if (normalized === 'prod' || normalized === 'production' || normalized === 'release') return 'production'
  return defaultMode
}

/**
 * Read the engine base URL from config/settings.json5 (services.engine).
 * Priority: NEXT_PUBLIC_CODES_API env var → settings.json5 → hardcoded default.
 */
function readEngineBaseUrl(mode) {
  if (process.env.NEXT_PUBLIC_CODES_API) {
    return process.env.NEXT_PUBLIC_CODES_API.replace(/\/$/, '')
  }
  try {
    const settingsPath = path.resolve(__dirname, '../../config/settings.json5')
    const data = JSON5.parse(fs.readFileSync(settingsPath, 'utf-8'))
    const engine = (data && data.services && data.services.engine) || {}
    const modeConfig = (engine && engine[mode]) || {}
    const host = modeConfig.host || engine.host || '127.0.0.1'
    const port = modeConfig.port || (mode === 'development' ? 3002 : 3001)
    return `http://${host}:${port}`
  } catch (_) {
    return mode === 'development' ? 'http://127.0.0.1:3002' : 'http://127.0.0.1:3001'
  }
}

function getLocalDevOrigins() {
  const origins = new Set([
    'localhost',
    '*.localhost',
    '127.0.0.1',
  ])

  try {
    const interfaces = os.networkInterfaces()
    for (const entries of Object.values(interfaces)) {
      for (const entry of entries || []) {
        if (entry && entry.family === 'IPv4' && !entry.internal) {
          origins.add(entry.address)
        }
      }
    }
  } catch (_) {
    // Keep the static loopback defaults if local interface detection fails.
  }

  return Array.from(origins)
}

module.exports = (phase) => {
  const runtimeMode = normalizeRuntimeMode(
    process.env.SKILL_PILOT_RUNTIME_MODE,
    phase === PHASE_DEVELOPMENT_SERVER ? 'development' : 'production',
  )
  const engineBaseUrl = readEngineBaseUrl(runtimeMode)

  return {
    env: {
      CODES_API_SSR: engineBaseUrl,
      NEXT_PUBLIC_FILE_EVENTS_API: engineBaseUrl,
    },
    devIndicators: false,
    reactStrictMode: true,
    outputFileTracingRoot: path.resolve(__dirname, '../..'),
    ...(isStaticExport ? { output: 'export', distDir: 'www' } : {}),
    // Temporarily disable locale-prefixed routing until the WebUI i18n paths are fully supported.
    allowedDevOrigins: getLocalDevOrigins(),
    ...(!isStaticExport
      ? {
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
            return [
              {
                source: '/api/:path*',
                destination: `${engineBaseUrl}/api/:path*`,
              },
            ]
          },
        }
      : {}),
    trailingSlash: isStaticExport ? true : false,
  }
}

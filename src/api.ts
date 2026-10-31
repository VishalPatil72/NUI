const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim().replace(/\/+$/, '') ?? ''

export function apiUrl(path: string): string {
  if (!path.startsWith('/api/')) {
    throw new Error('API paths must start with /api/.')
  }
  if (import.meta.env.DEV) return path
  if (!configuredApiBaseUrl) {
    throw new Error('VITE_API_BASE_URL is required for production API requests.')
  }
  return `${configuredApiBaseUrl}${path}`
}

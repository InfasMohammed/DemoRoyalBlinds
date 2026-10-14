import { accessToken } from './auth/client'

const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const token = await accessToken()
  const headers = new Headers(options?.headers)
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${baseUrl}/api${path}`, {
    ...options,
    headers,
  })
  const result = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = result?.detail
    throw new Error(
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail
              .map(
                (item: { loc: string[]; msg: string }) =>
                  `${item.loc.slice(1).join('.')}: ${item.msg}`,
              )
              .join('; ')
          : `Request failed (${response.status}). Check the backend connection.`,
    )
  }
  return result as T
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...options?.headers } })
  const result = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = result?.detail
    throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail)
      ? detail.map((item: { loc: string[]; msg: string }) => `${item.loc.slice(1).join('.')}: ${item.msg}`).join('; ')
      : `Request failed (${response.status}). Check the backend connection.`)
  }
  return result as T
}

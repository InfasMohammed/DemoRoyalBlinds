import { createClient } from '@supabase/supabase-js'

export const authRequired = import.meta.env.VITE_REQUIRE_AUTH === 'true'

function configuredClient() {
  const url = import.meta.env.VITE_SUPABASE_URL
  const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY
  if (!url || !key) throw new Error('Configure the public Supabase URL and publishable key.')
  if (key.startsWith('sb_secret_'))
    throw new Error('A server secret must never be used in the frontend.')
  if (!key.startsWith('sb_publishable_')) {
    try {
      const claims = JSON.parse(atob(key.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
      if (claims.role !== 'anon') throw new Error('Use a publishable key or legacy anon key.')
    } catch {
      throw new Error('Use a publishable key or legacy anon key in the frontend.')
    }
  }
  return createClient(url, key)
}

export const authClient = authRequired ? configuredClient() : null

export async function accessToken() {
  if (!authClient) return null
  const { data, error } = await authClient.auth.getSession()
  if (error || !data.session) throw new Error('Session expired. Sign in again.')
  return data.session.access_token
}

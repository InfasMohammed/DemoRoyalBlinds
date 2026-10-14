import { loadEnv } from 'vite'

const env = { ...loadEnv('production', process.cwd(), 'VITE_'), ...process.env }
const required = env.VITE_REQUIRE_AUTH === 'true'
if (env.VERCEL === '1' && !required) {
  throw new Error('Set VITE_REQUIRE_AUTH=true before deploying the shared demo on Vercel.')
}
if (required) {
  for (const name of ['VITE_API_BASE_URL', 'VITE_SUPABASE_URL']) {
    let url
    try {
      url = new URL(env[name])
    } catch {
      throw new Error(`Set ${name} to the HTTPS service origin.`)
    }
    if (
      url.protocol !== 'https:' ||
      url.username ||
      url.password ||
      url.search ||
      url.hash ||
      url.pathname !== '/'
    ) {
      throw new Error(`${name} must be an HTTPS origin without a path, credentials or query.`)
    }
  }
  const key = env.VITE_SUPABASE_PUBLISHABLE_KEY || ''
  if (!key.startsWith('sb_publishable_')) {
    let claims
    try {
      claims = JSON.parse(Buffer.from(key.split('.')[1], 'base64url').toString())
    } catch {
      /* invalid key */
    }
    if (claims?.role !== 'anon')
      throw new Error(
        'Use a Supabase publishable or legacy anon key in the frontend; never a server key.',
      )
  }
}

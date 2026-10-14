import { createContext, useContext, useEffect, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'
import { LogOut, LoaderCircle } from 'lucide-react'
import { authClient } from './client'
import '../styles/auth.css'

const SessionContext = createContext<Session | null>(null)

export function SessionControls() {
  const session = useContext(SessionContext)
  if (!session) return null
  return (
    <button
      className="text-link"
      onClick={() => void authClient?.auth.signOut()}
      title={session.user.email}
    >
      <LogOut size={15} /> Sign out
    </button>
  )
}

export default function AuthGate({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(!!authClient)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!authClient) return
    const { data } = authClient.auth.onAuthStateChange((_event, next) => {
      setSession(next)
      setLoading(false)
    })
    return () => data.subscription.unsubscribe()
  }, [])

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!authClient || busy) return
    const form = new FormData(event.currentTarget)
    setBusy(true)
    setError('')
    try {
      const { error: failure } = await authClient.auth.signInWithPassword({
        email: String(form.get('email')).trim(),
        password: String(form.get('password')),
      })
      if (failure)
        setError('Sign-in failed. Check your email and password, or contact the demo owner.')
    } catch {
      setError('Could not reach sign-in. Check your connection and try again.')
    } finally {
      setBusy(false)
    }
  }

  if (!authClient) return children
  if (session) return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>
  return (
    <main className="auth-page">
      <section className="card auth-card">
        <img src="/brand/royal-blinds-logo.png" alt="Royal Blinds" width="260" />
        <span className="eyebrow">OPERATIONS STUDIO · INTERVIEW DEMO</span>
        <h1>Sign in to explore the demo.</h1>
        <p className="muted">Use the reviewer account provided by the demo owner.</p>
        {loading ? (
          <p role="status">
            <LoaderCircle className="spin" size={18} /> Checking your session…
          </p>
        ) : (
          <form onSubmit={(event) => void signIn(event)}>
            <label>
              Email
              <input name="email" type="email" autoComplete="username" required disabled={busy} />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                autoComplete="current-password"
                required
                disabled={busy}
              />
            </label>
            {error && (
              <p role="alert" className="warning-text">
                {error}
              </p>
            )}
            <button className="button primary" disabled={busy}>
              {busy ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        )}
        <p className="fine-print">Independent prototype with sample manufacturing data.</p>
      </section>
    </main>
  )
}

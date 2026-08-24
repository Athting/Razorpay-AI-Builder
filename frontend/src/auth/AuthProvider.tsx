import React, { createContext, useContext, useState, useEffect } from 'react'
import { useAuthStore } from '../store/authStore'
import { apiClient } from '../api/client'
import { supabase, isSupabaseConfigured } from '../supabase'
import type { AuthUser } from '../api/types'

interface AuthContextValue {
  user: AuthUser | null
  loading: boolean
  signInWithGoogle: () => Promise<void>
  signInWithEmail: (email: string, password: string) => Promise<void>
  signUpWithEmail: (name: string, email: string, password: string) => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { user, setUser, logout } = useAuthStore()
  const [loading, setLoading] = useState(false)

  // Listen to Supabase auth state changes (when configured)
  useEffect(() => {
    if (!supabase) return
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (event === 'SIGNED_IN' && session) {
          // Exchange Supabase session token for our app user info
          try {
            const res = await apiClient.post<AuthUser>('/auth/supabase', {
              access_token: session.access_token,
            })
            setUser(res.data)
          } catch {
            // If backend exchange fails, create a minimal user from session
            const sbUser = session.user
            setUser({
              user_id: sbUser.id,
              email: sbUser.email || '',
              name: sbUser.user_metadata?.full_name || sbUser.email || 'User',
              role: 'admin',
              access_token: session.access_token,
            })
          }
        } else if (event === 'SIGNED_OUT') {
          logout()
        }
      }
    )
    return () => subscription.unsubscribe()
  }, [])

  const signInWithGoogle = async () => {
    setLoading(true)
    try {
      if (isSupabaseConfigured && supabase) {
        // Supabase Google OAuth — opens popup/redirect
        const { error } = await supabase.auth.signInWithOAuth({
          provider: 'google',
          options: { redirectTo: window.location.origin },
        })
        if (error) throw error
        // auth state change listener handles the rest
        return
      }
      // Fallback: demo login
      await signInWithEmail('admin@demo.com', 'demo1234')
    } finally {
      setLoading(false)
    }
  }

  const signInWithEmail = async (email: string, password: string) => {
    setLoading(true)
    try {
      // Email/password accounts belong to RevRec's backend.  This keeps the
      // demo account and accounts created from the Register form independent
      // of optional Supabase configuration.
      const response = await apiClient.post<AuthUser>('/auth/login', { email, password })
      setUser(response.data)
    } finally {
      setLoading(false)
    }
  }

  const signUpWithEmail = async (name: string, email: string, password: string) => {
    setLoading(true)
    try {
      const response = await apiClient.post<AuthUser>('/auth/register', { name, email, password })
      setUser(response.data)
    } finally { setLoading(false) }
  }

  const signOut = async () => {
    if (supabase) {
      await supabase.auth.signOut()
    }
    logout()
  }

  return (
    <AuthContext.Provider value={{ user, loading, signInWithGoogle, signInWithEmail, signUpWithEmail, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

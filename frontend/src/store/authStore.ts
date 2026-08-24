import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AuthUser } from '../api/types'

interface AuthState {
  user: AuthUser | null
  setUser: (user: AuthUser | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      setUser: (user) => {
        if (user) {
          localStorage.setItem('access_token', user.access_token)
        } else {
          localStorage.removeItem('access_token')
        }
        set({ user })
      },
      logout: () => {
        localStorage.removeItem('access_token')
        set({ user: null })
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ user: state.user }),
    }
  )
)

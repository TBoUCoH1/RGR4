import { create } from 'zustand'
import type { User } from './types'

interface AuthState {
  token: string | null
  user: User | null
  bootstrapped: boolean
  setSession: (token: string, user: User) => void
  setUser: (user: User) => void
  clear: () => void
  setBootstrapped: (value: boolean) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  bootstrapped: false,
  setSession: (token, user) => set({ token, user }),
  setUser: (user) => set({ user }),
  clear: () => set({ token: null, user: null }),
  setBootstrapped: (bootstrapped) => set({ bootstrapped })
}))

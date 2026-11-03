import { create } from 'zustand'
import type { UserInfo } from '../types'

interface AuthState {
  token: string | null
  user: UserInfo | null
  isAuthenticated: boolean
  setAuth: (token: string, user: UserInfo) => void
  logout: () => void
  loadFromStorage: () => void
}

function loadFromLocalStorage() {
  const token = localStorage.getItem('token')
  const userStr = localStorage.getItem('user')
  let user: UserInfo | null = null
  if (userStr) {
    try {
      user = JSON.parse(userStr) as UserInfo
    } catch {
      localStorage.removeItem('user')
    }
  }
  return { token, user, isAuthenticated: !!(token && user) }
}

const initial = loadFromLocalStorage()

export const useAuthStore = create<AuthState>((set) => ({
  token: initial.token,
  user: initial.user,
  isAuthenticated: initial.isAuthenticated,

  setAuth: (token: string, user: UserInfo) => {
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(user))
    set({ token, user, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    set({ token: null, user: null, isAuthenticated: false })
  },

  loadFromStorage: () => {
    const { token, user, isAuthenticated } = loadFromLocalStorage()
    set({ token, user, isAuthenticated })
  },
}))

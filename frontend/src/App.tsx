import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuthStore } from './stores/authStore'
import { authAPI } from './api/client'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import KnowledgeBase from './pages/KnowledgeBase'
import Chat from './pages/Chat'

function App() {
  const { isAuthenticated, setAuth, logout, loadFromStorage } = useAuthStore()

  useEffect(() => {
    loadFromStorage()
  }, [])

  // Verify token on mount
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      authAPI.getMe()
        .then(user => {
          setAuth(token, user)
        })
        .catch(() => {
          logout()
        })
    }
  }, [])

  return (
    <Routes>
      <Route path="/login" element={
        isAuthenticated ? <Navigate to="/" replace /> : <Login />
      } />
      <Route element={<Layout />}>
        <Route path="/" element={
          isAuthenticated ? <Dashboard /> : <Navigate to="/login" replace />
        } />
        <Route path="/kb/:kbId" element={
          isAuthenticated ? <KnowledgeBase /> : <Navigate to="/login" replace />
        } />
        <Route path="/kb/:kbId/chat" element={
          isAuthenticated ? <Chat /> : <Navigate to="/login" replace />
        } />
        <Route path="/chat" element={
          isAuthenticated ? <Chat /> : <Navigate to="/login" replace />
        } />
      </Route>
    </Routes>
  )
}

export default App

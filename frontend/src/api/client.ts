import axios from 'axios'
import type { LoginResponse, UserInfo, KnowledgeBase, DocumentInfo } from '../types'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ------- Auth -------
export const authAPI = {
  register: (data: { email: string; username: string; password: string; tenant_name?: string }) =>
    api.post<LoginResponse>('/auth/register', data).then(r => r.data),

  login: (data: { email: string; password: string }) =>
    api.post<LoginResponse>('/auth/login', data).then(r => r.data),

  getMe: () => api.get<UserInfo>('/auth/me').then(r => r.data),
}

// ------- Knowledge Bases -------
export const kbAPI = {
  list: () => api.get<KnowledgeBase[]>('/knowledge-bases').then(r => r.data),

  create: (data: { name: string; description: string }) =>
    api.post<KnowledgeBase>('/knowledge-bases', data).then(r => r.data),

  delete: (kbId: string) =>
    api.delete(`/knowledge-bases/${kbId}`).then(r => r.data),

  listMembers: (kbId: string) =>
    api.get(`/knowledge-bases/${kbId}/members`).then(r => r.data),

  addMember: (kbId: string, data: { user_email: string; access_level: string }) =>
    api.put(`/knowledge-bases/${kbId}/members`, data).then(r => r.data),
}

// ------- Documents -------
export const docAPI = {
  list: (kbId: string) =>
    api.get<DocumentInfo[]>(`/knowledge-bases/${kbId}/documents`).then(r => r.data),

  upload: (kbId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<DocumentInfo>(`/knowledge-bases/${kbId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },

  delete: (kbId: string, docId: string) =>
    api.delete(`/knowledge-bases/${kbId}/documents/${docId}`).then(r => r.data),
}

// ------- Conversations -------
export const convAPI = {
  list: (kbId?: string) => {
    const params = kbId ? `?kb_id=${encodeURIComponent(kbId)}` : ''
    return api.get('/conversations' + params).then(r => r.data)
  },
  create: (kbId?: string, title?: string) => {
    const params = new URLSearchParams()
    if (kbId) params.append('kb_id', kbId)
    if (title) params.append('title', title)
    return api.post('/conversations?' + params.toString()).then(r => r.data)
  },
  getMessages: (convId: string) =>
    api.get(`/conversations/${convId}/messages`).then(r => r.data),
  delete: (convId: string) =>
    api.delete(`/conversations/${convId}`).then(r => r.data),
}

// ------- Chat -------
export function chatWithKB(kbId: string, question: string, history: { role: string; content: string }[] = [], convId?: string) {
  const token = localStorage.getItem('token')
  const url = `/api/knowledge-bases/${kbId}/chat` + (convId ? `?conversation_id=${convId}` : '')
  return fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ question, history }),
  })
}

// ------- Agent Chat -------
export function chatWithAgent(question: string, history: { role: string; content: string }[] = []) {
  const token = localStorage.getItem('token')
  return fetch('/api/agent/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ question, history }),
  })
}

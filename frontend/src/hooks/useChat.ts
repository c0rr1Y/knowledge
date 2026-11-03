import { useState, useCallback, useRef } from 'react'
import type { ChatMessage, SourceInfo } from '../types'

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const loadMessages = useCallback((msgs: ChatMessage[]) => {
    setMessages(msgs)
  }, [])

  const sendMessage = useCallback(async (
    question: string,
    mode: 'kb' | 'agent',
    kbId?: string,
    history?: { role: string; content: string }[],
    convId?: string,
  ) => {
    const userMsg: ChatMessage = { role: 'user', content: question }
    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)

    const assistantMsg: ChatMessage = { role: 'assistant', content: '', isStreaming: true }
    setMessages(prev => [...prev, assistantMsg])

    const abortController = new AbortController()
    abortRef.current = abortController

    let resultConvId: string | null = convId || null

    try {
      const baseUrl = mode === 'kb'
        ? `/api/knowledge-bases/${kbId}/chat`
        : '/api/agent/chat'

      const url = convId ? `${baseUrl}?conversation_id=${convId}` : baseUrl

      const token = localStorage.getItem('token')
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ question, history }),
        signal: abortController.signal,
      })

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No reader')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            try {
              const event = JSON.parse(data)
              if (event.type === 'chunk') {
                setMessages(prev => {
                  const u = [...prev]
                  const last = u[u.length - 1]
                  if (last && last.role === 'assistant') {
                    u[u.length - 1] = { ...last, content: last.content + event.content }
                  }
                  return u
                })
              } else if (event.type === 'sources') {
                setMessages(prev => {
                  const u = [...prev]
                  const last = u[u.length - 1]
                  if (last && last.role === 'assistant') {
                    u[u.length - 1] = { ...last, sources: event.content as SourceInfo[] }
                  }
                  return u
                })
              } else if (event.type === 'done') {
                resultConvId = event.content?.conv_id ?? resultConvId
                setMessages(prev => {
                  const u = [...prev]
                  const last = u[u.length - 1]
                  if (last && last.role === 'assistant') {
                    u[u.length - 1] = { ...last, isStreaming: false }
                  }
                  return u
                })
              } else if (event.type === 'error') {
                setMessages(prev => {
                  const u = [...prev]
                  const last = u[u.length - 1]
                  if (last && last.role === 'assistant') {
                    u[u.length - 1] = { ...last, content: `错误: ${event.content}`, isStreaming: false }
                  }
                  return u
                })
              }
            } catch {}
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') return resultConvId
      setMessages(prev => {
        const u = [...prev]
        const last = u[u.length - 1]
        if (last && last.role === 'assistant') {
          u[u.length - 1] = { ...last, content: `请求失败: ${err.message}`, isStreaming: false }
        }
        return u
      })
    } finally {
      setIsLoading(false)
    }

    return resultConvId
  }, [])

  const stop = useCallback(() => {
    abortRef.current?.abort()
    setIsLoading(false)
    setMessages(prev => {
      const u = [...prev]
      const last = u[u.length - 1]
      if (last?.role === 'assistant' && last.isStreaming) {
        u[u.length - 1] = { ...last, isStreaming: false }
      }
      return u
    })
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  return { messages, isLoading, sendMessage, stop, clearMessages, loadMessages }
}

import { useState, useRef, useEffect, useCallback } from 'react'
import { useParams, Link, useSearchParams } from 'react-router-dom'
import { useChat } from '../hooks/useChat'
import { convAPI } from '../api/client'
import ChatBubble from '../components/ChatBubble'
import type { ChatMessage } from '../types'
import {
  Send,
  ArrowLeft,
  Sparkles,
  StopCircle,
  Trash2,
  Globe,
  BookOpen,
  MessageSquare,
  Plus,
} from 'lucide-react'

interface ConvInfo {
  id: string
  title: string
  knowledge_base_id: string | null
  message_count: number
  updated_at: string
}

export default function Chat() {
  const { kbId } = useParams<{ kbId: string }>()
  const { messages, isLoading, sendMessage, stop, clearMessages, loadMessages } = useChat()
  const [searchParams, setSearchParams] = useSearchParams()
  const [input, setInput] = useState('')
  const [convs, setConvs] = useState<ConvInfo[]>([])
  const [showSidebar, setShowSidebar] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const mode = kbId ? 'kb' : 'agent'
  const activeConvId = searchParams.get('conv')

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (!isLoading && inputRef.current) inputRef.current.focus()
  }, [isLoading])

  const loadConvs = useCallback(async () => {
    try {
      const data = await convAPI.list(kbId ?? 'agent')
      setConvs(data)
    } catch {}
  }, [kbId])

  useEffect(() => { loadConvs() }, [loadConvs])

  useEffect(() => {
    if (activeConvId) {
      convAPI.getMessages(activeConvId).then(msgs => {
        const formatted: ChatMessage[] = msgs.map((m: any) => ({
          role: m.role,
          content: m.content,
          sources: m.sources_json && m.sources_json !== '[]' ? JSON.parse(m.sources_json) : undefined,
        }))
        loadMessages(formatted)
      }).catch(() => {})
    } else {
      clearMessages()
    }
  }, [activeConvId, loadMessages, clearMessages])

  const handleNewConv = () => {
    setSearchParams({})
    inputRef.current?.focus()
  }

  const handleSelectConv = (convId: string) => {
    setSearchParams({ conv: convId })
  }

  const handleDeleteConv = async (convId: string) => {
    await convAPI.delete(convId)
    if (activeConvId === convId) {
      setSearchParams({})
    }
    loadConvs()
  }

  const handleSend = async () => {
    if (!input.trim() || isLoading) return
    const question = input.trim()
    setInput('')
    const newConvId = await sendMessage(question, mode, kbId, undefined, activeConvId || undefined)
    if (newConvId && newConvId !== activeConvId) {
      setSearchParams({ conv: newConvId })
    }
    setTimeout(() => loadConvs(), 500)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] max-w-5xl mx-auto gap-4">
      {/* Sidebar */}
      {showSidebar && (
        <div className="w-64 flex-shrink-0 bg-white/80 rounded-2xl border border-nature-200/50 flex flex-col overflow-hidden">
          <div className="p-3 border-b border-nature-100">
            <button onClick={handleNewConv} className="w-full flex items-center gap-2 px-3 py-2 bg-leaf-500 hover:bg-leaf-600 text-white rounded-xl text-sm font-medium transition-all">
              <Plus className="w-4 h-4" /> 新对话
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
            {convs.map(c => (
              <div
                key={c.id}
                onClick={() => handleSelectConv(c.id)}
                className={`group flex items-center gap-2 px-3 py-2.5 rounded-xl cursor-pointer text-sm transition-all ${
                  c.id === activeConvId ? 'bg-leaf-50 text-leaf-700 font-medium' : 'hover:bg-nature-100 text-wood-600'
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
                <span className="truncate flex-1">{c.title}</span>
                <button
                  onClick={e => { e.stopPropagation(); handleDeleteConv(c.id) }}
                  className="opacity-0 group-hover:opacity-100 p-1 text-wood-300 hover:text-red-500 rounded transition-all"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Chat */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex items-center gap-3 mb-3 flex-shrink-0">
          <button onClick={() => setShowSidebar(!showSidebar)} className="p-2 hover:bg-nature-100 rounded-xl transition-all">
            <MessageSquare className="w-4 h-4 text-wood-400" />
          </button>
          {kbId ? (
            <Link to={`/kb/${kbId}`} className="p-2 hover:bg-nature-100 rounded-xl"><ArrowLeft className="w-5 h-5 text-wood-400" /></Link>
          ) : (
            <Link to="/" className="p-2 hover:bg-nature-100 rounded-xl"><ArrowLeft className="w-5 h-5 text-wood-400" /></Link>
          )}
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-leaf-400 to-sky-500 flex items-center justify-center shadow-sm">
            {mode === 'agent' ? <Globe className="w-4 h-4 text-white" /> : <BookOpen className="w-4 h-4 text-white" />}
          </div>
          <h1 className="text-sm font-bold text-nature-800">{mode === 'agent' ? 'AI Agent' : '知识库问答'}</h1>
        </div>

        <div className="flex-1 overflow-y-auto space-y-4 p-4 bg-white/50 rounded-2xl border border-nature-200/50 mb-3">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-8">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-leaf-100 to-sky-100 flex items-center justify-center mb-5">
                <Sparkles className="w-8 h-8 text-leaf-500" />
              </div>
              <h2 className="text-lg font-bold text-nature-800 mb-2">
                {mode === 'agent' ? '你好！我是 AI Agent' : '开始提问'}
              </h2>
              <p className="text-wood-400 text-sm max-w-md mb-6">
                向我提出任何问题，我会结合知识库文档为你解答。
              </p>
              <div className="grid grid-cols-2 gap-2 w-full max-w-lg">
                {['总结文档的主要内容', '列出关键要点', '有哪些重要规定？', '对比分析差异'].map(q => (
                  <button key={q} onClick={() => { setInput(q); inputRef.current?.focus() }}
                    className="text-left px-3 py-2.5 bg-nature-100 hover:bg-leaf-50 hover:text-leaf-700 rounded-xl text-sm text-wood-500 transition-all">{q}</button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, i) => <ChatBubble key={i} message={msg} />)
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="flex-shrink-0">
          <div className="flex items-end gap-2 bg-white rounded-2xl border border-nature-200 shadow-sm p-2.5 focus-within:border-leaf-400 focus-within:ring-2 focus-within:ring-leaf-500/10 transition-all">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入问题，按 Enter 发送..."
              rows={1}
              className="flex-1 resize-none bg-transparent text-nature-800 placeholder-wood-300 outline-none text-sm py-1.5 max-h-32"
              disabled={isLoading}
            />
            {isLoading ? (
              <button onClick={stop} className="flex items-center gap-1 px-3 py-1.5 bg-red-50 hover:bg-red-100 text-red-600 rounded-xl text-xs font-medium transition-all">
                <StopCircle className="w-3.5 h-3.5" /> 停止
              </button>
            ) : (
              <button onClick={handleSend} disabled={!input.trim()}
                className="flex items-center gap-1 px-4 py-1.5 bg-leaf-500 hover:bg-leaf-600 disabled:bg-nature-200 disabled:text-wood-400 text-white rounded-xl text-sm font-medium transition-all shadow-sm">
                <Send className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { kbAPI } from '../api/client'
import type { KnowledgeBase } from '../types'
import {
  BookOpen,
  Plus,
  FileText,
  MessageSquare,
  Trash2,
  Users,
  Sparkles,
  TrendingUp,
  FileArchive,
} from 'lucide-react'

export default function Dashboard() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const loadKBs = () => {
    kbAPI.list().then(setKbs).catch(console.error)
  }

  useEffect(() => { loadKBs() }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newName.trim()) return
    setLoading(true)
    try {
      await kbAPI.create({ name: newName, description: newDesc })
      setNewName('')
      setNewDesc('')
      setShowCreate(false)
      loadKBs()
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (kbId: string, name: string) => {
    if (!confirm(`确定要删除知识库 "${name}" 吗？所有文档和问答数据将被永久删除。`)) return
    try {
      await kbAPI.delete(kbId)
      loadKBs()
    } catch (err) {
      console.error(err)
    }
  }

  const totalDocs = kbs.reduce((sum, kb) => sum + kb.document_count, 0)

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-nature-800 mb-2">仪表盘</h1>
        <p className="text-wood-400">管理你的知识库，上传文档，智能问答</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-nature-200/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-leaf-100 flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-leaf-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-nature-800">{kbs.length}</div>
              <div className="text-xs text-wood-400">知识库</div>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-nature-200/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-100 flex items-center justify-center">
              <FileText className="w-5 h-5 text-sky-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-nature-800">{totalDocs}</div>
              <div className="text-xs text-wood-400">文档总数</div>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-nature-200/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sunset-100 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-sunset-500" />
            </div>
            <div>
              <div className="text-sm font-medium text-nature-800">AI Agent</div>
              <div className="text-xs text-wood-400">多知识库路由</div>
            </div>
          </div>
        </div>
      </div>

      {/* Knowledge Bases Grid */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-nature-800 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-leaf-600" />
          我的知识库
        </h2>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-leaf-500 hover:bg-leaf-600 text-white rounded-xl text-sm font-medium transition-all shadow-sm"
        >
          <Plus className="w-4 h-4" />
          新建知识库
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="mb-6 p-6 bg-white rounded-2xl shadow-sm border border-leaf-200">
          <h3 className="font-semibold text-nature-800 mb-4">创建新知识库</h3>
          <form onSubmit={handleCreate} className="space-y-4">
            <input
              type="text"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              placeholder="知识库名称"
              className="w-full px-4 py-2.5 border border-nature-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-leaf-500/20 focus:border-leaf-500"
              required
            />
            <input
              type="text"
              value={newDesc}
              onChange={e => setNewDesc(e.target.value)}
              placeholder="描述（可选）"
              className="w-full px-4 py-2.5 border border-nature-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-leaf-500/20 focus:border-leaf-500"
            />
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2.5 bg-leaf-500 hover:bg-leaf-600 disabled:bg-leaf-300 text-white rounded-xl text-sm font-medium transition-all"
              >
                {loading ? '创建中...' : '创建'}
              </button>
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className="px-6 py-2.5 bg-nature-100 hover:bg-nature-200 text-nature-700 rounded-xl text-sm font-medium transition-all"
              >
                取消
              </button>
            </div>
          </form>
        </div>
      )}

      {/* KB Cards */}
      {kbs.length === 0 ? (
        <div className="text-center py-20">
          <FileArchive className="w-16 h-16 mx-auto mb-4 text-wood-300" />
          <h3 className="text-lg font-semibold text-nature-700 mb-2">还没有知识库</h3>
          <p className="text-wood-400 mb-6">创建你的第一个知识库，开始上传文档进行智能问答</p>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 px-6 py-3 bg-leaf-500 hover:bg-leaf-600 text-white rounded-xl font-medium transition-all shadow-lg shadow-leaf-500/25"
          >
            <Plus className="w-4 h-4" />
            创建知识库
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {kbs.map(kb => (
            <div
              key={kb.id}
              className="bg-white rounded-2xl p-5 shadow-sm border border-nature-200/50 hover:shadow-md hover:border-leaf-200 transition-all group"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-leaf-400 to-leaf-600 flex items-center justify-center shadow-sm">
                  <BookOpen className="w-5 h-5 text-white" />
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => handleDelete(kb.id, kb.name)}
                    className="p-1.5 text-wood-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                    title="删除"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <h3 className="font-semibold text-nature-800 mb-1 truncate">{kb.name}</h3>
              <p className="text-sm text-wood-400 mb-4 line-clamp-2">{kb.description || '暂无描述'}</p>

              <div className="flex items-center gap-4 text-xs text-wood-400 mb-4">
                <span className="flex items-center gap-1">
                  <FileText className="w-3.5 h-3.5" />
                  {kb.document_count} 个文档
                </span>
                <span className="px-1.5 py-0.5 rounded-md bg-nature-100 text-wood-500 text-xs">
                  {kb.access_level === 'admin' ? '管理员' : kb.access_level === 'write' ? '可编辑' : '只读'}
                </span>
              </div>

              <div className="flex gap-2">
                <Link
                  to={`/kb/${kb.id}`}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-nature-100 hover:bg-nature-200 text-nature-700 rounded-xl text-sm font-medium transition-all"
                >
                  <FileText className="w-3.5 h-3.5" />
                  管理文档
                </Link>
                <Link
                  to={`/kb/${kb.id}/chat`}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-leaf-500 hover:bg-leaf-600 text-white rounded-xl text-sm font-medium transition-all shadow-sm"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  问答
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

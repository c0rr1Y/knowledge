import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { docAPI, kbAPI } from '../api/client'
import type { DocumentInfo, KnowledgeBase, KBMember } from '../types'
import {
  Upload,
  FileText,
  Trash2,
  ArrowLeft,
  MessageSquare,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  FileArchive,
  HardDrive,
  RefreshCw,
  Users,
} from 'lucide-react'

export default function KnowledgeBase() {
  const { kbId } = useParams<{ kbId: string }>()
  const [kb, setKb] = useState<KnowledgeBase | null>(null)
  const [docs, setDocs] = useState<DocumentInfo[]>([])
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [loading, setLoading] = useState(true)
  const [showMembers, setShowMembers] = useState(false)
  const [members, setMembers] = useState<KBMember[]>([])
  const [newEmail, setNewEmail] = useState('')
  const [newAccess, setNewAccess] = useState('read')
  const [addingMember, setAddingMember] = useState(false)

  const loadData = useCallback(async () => {
    if (!kbId) return
    try {
      const [kbs, documents] = await Promise.all([
        kbAPI.list(),
        docAPI.list(kbId),
      ])
      const currentKb = kbs.find(k => k.id === kbId)
      setKb(currentKb || null)
      setDocs(documents)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [kbId])

  useEffect(() => { loadData() }, [loadData])

  const loadMembers = useCallback(async () => {
    if (!kbId) return
    try {
      const data = await kbAPI.listMembers(kbId)
      setMembers(data)
    } catch (err) {
      console.error(err)
    }
  }, [kbId])

  useEffect(() => {
    if (showMembers) loadMembers()
  }, [showMembers, loadMembers])

  const handleAddMember = async () => {
    if (!kbId || !newEmail.trim()) return
    setAddingMember(true)
    try {
      await kbAPI.addMember(kbId, { user_email: newEmail.trim(), access_level: newAccess })
      setNewEmail('')
      loadMembers()
    } catch (err) {
      console.error(err)
      alert('添加失败：请确认该同事已注册且与你同一租户')
    } finally {
      setAddingMember(false)
    }
  }

  // Auto-refresh when there are processing documents
  useEffect(() => {
    const hasProcessing = docs.some(d => d.status === 'uploaded' || d.status === 'processing')
    if (!hasProcessing) return
    const timer = setInterval(loadData, 3000)
    return () => clearInterval(timer)
  }, [docs, loadData])

  const handleUpload = async (files: FileList | File[]) => {
    if (!kbId) return
    setUploading(true)
    const allowedExtensions = ['.pdf', '.docx', '.doc', '.txt', '.md', '.markdown', '.xlsx', '.xls', '.csv', '.pptx', '.ppt', '.html', '.htm', '.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff', '.tif']
    const fileArray = Array.from(files).filter(f => {
      const ext = '.' + f.name.split('.').pop()?.toLowerCase()
      return allowedExtensions.includes(ext)
    })

    for (const file of fileArray) {
      try {
        await docAPI.upload(kbId, file)
      } catch (err) {
        console.error(`Failed to upload ${file.name}:`, err)
      }
    }
    setUploading(false)
    loadData()
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleUpload(e.dataTransfer.files)
  }

  const handleDelete = async (docId: string, name: string) => {
    if (!kbId || !confirm(`删除文档 "${name}"？`)) return
    try {
      await docAPI.delete(kbId, docId)
      loadData()
    } catch (err) {
      console.error(err)
    }
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const statusIcon = (status: string) => {
    switch (status) {
      case 'done': return <CheckCircle2 className="w-4 h-4 text-leaf-500" />
      case 'error': return <XCircle className="w-4 h-4 text-red-500" />
      case 'processing': return <Loader2 className="w-4 h-4 text-sky-500 animate-spin" />
      default: return <Clock className="w-4 h-4 text-wood-400" />
    }
  }

  const statusText = (status: string) => {
    switch (status) {
      case 'done': return '已完成'
      case 'error': return '失败'
      case 'processing': return '处理中'
      case 'uploaded': return '等待处理'
      default: return status
    }
  }

  const accessLabel = (level: string) => level === 'admin' ? '管理员' : level === 'write' ? '可编辑' : '只读'

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-leaf-500 animate-spin" />
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link to="/" className="p-2 hover:bg-nature-100 rounded-xl transition-all">
          <ArrowLeft className="w-5 h-5 text-wood-400" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-nature-800">{kb?.name || '知识库'}</h1>
          <p className="text-sm text-wood-400">{kb?.description}</p>
        </div>
        {kb?.access_level === 'admin' && (
          <button
            onClick={() => setShowMembers(!showMembers)}
            className="flex items-center gap-2 px-4 py-2.5 bg-nature-100 hover:bg-nature-200 text-nature-700 rounded-xl text-sm font-medium transition-all"
          >
            <Users className="w-4 h-4" />
            成员
          </button>
        )}
        <Link
          to={`/kb/${kbId}/chat`}
          className="flex items-center gap-2 px-5 py-2.5 bg-leaf-500 hover:bg-leaf-600 text-white rounded-xl text-sm font-medium transition-all shadow-sm"
        >
          <MessageSquare className="w-4 h-4" />
          开始问答
        </Link>
      </div>

      {/* Member Management */}
      {showMembers && (
        <div className="mb-6 p-6 bg-white rounded-2xl border border-nature-200/50">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-nature-800 flex items-center gap-2">
              <Users className="w-4 h-4 text-leaf-600" />
              成员管理
            </h3>
            <button onClick={() => setShowMembers(false)} className="text-sm text-wood-400 hover:text-wood-600">关闭</button>
          </div>

          <div className="space-y-2 mb-4">
            {members.length === 0 ? (
              <p className="text-sm text-wood-400">暂无成员</p>
            ) : (
              members.map(m => (
                <div key={m.user_id} className="flex items-center gap-3 p-3 bg-nature-100/50 rounded-lg">
                  <span className="flex-1 text-sm text-nature-700 font-medium">{m.username}</span>
                  <span className="text-xs text-wood-400">{m.email}</span>
                  <span className="px-2 py-0.5 rounded-md bg-leaf-100 text-leaf-700 text-xs font-medium">
                    {accessLabel(m.access_level)}
                  </span>
                </div>
              ))
            )}
          </div>

          <div className="flex gap-2">
            <input
              type="email"
              value={newEmail}
              onChange={e => setNewEmail(e.target.value)}
              placeholder="输入同事邮箱（需已注册）"
              className="flex-1 px-3 py-2 border border-nature-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-leaf-500/20 focus:border-leaf-500 text-sm"
            />
            <select
              value={newAccess}
              onChange={e => setNewAccess(e.target.value)}
              className="px-3 py-2 border border-nature-200 rounded-xl text-sm bg-white"
            >
              <option value="read">只读</option>
              <option value="write">可编辑</option>
              <option value="admin">管理员</option>
            </select>
            <button
              onClick={handleAddMember}
              disabled={addingMember || !newEmail.trim()}
              className="px-4 py-2 bg-leaf-500 hover:bg-leaf-600 disabled:bg-nature-200 disabled:text-wood-400 text-white rounded-xl text-sm font-medium transition-all"
            >
              {addingMember ? '添加中...' : '添加'}
            </button>
          </div>
        </div>
      )}

      {/* Upload Zone */}
      <div
        className={`upload-zone p-10 mb-8 text-center cursor-pointer bg-white ${
          dragOver ? 'drag-over' : ''
        }`}
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => document.getElementById('file-input')?.click()}
      >
        <input
          id="file-input"
          type="file"
          accept=".pdf,.docx,.doc,.txt,.md,.xlsx,.xls,.csv,.pptx,.ppt,.html,.htm,.png,.jpg,.jpeg,.bmp,.gif,.webp,.tiff,.tif"
          multiple
          className="hidden"
          onChange={e => e.target.files && handleUpload(e.target.files)}
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-12 h-12 text-leaf-500 animate-spin" />
            <p className="text-nature-700 font-medium">正在上传...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-16 h-16 rounded-2xl bg-leaf-100 flex items-center justify-center">
              <Upload className="w-8 h-8 text-leaf-600" />
            </div>
            <div>
              <p className="text-nature-700 font-medium">拖拽文件到这里，或点击上传</p>
              <p className="text-sm text-wood-400 mt-1">支持批量上传，每个文件最大 50MB</p>
            </div>
          </div>
        )}
      </div>

      {/* Document List */}
      <h2 className="text-lg font-semibold text-nature-800 mb-4 flex items-center gap-2">
        <FileText className="w-5 h-5 text-leaf-600" />
        文档列表
        <span className="text-sm font-normal text-wood-400">({docs.length})</span>
      </h2>

      {docs.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-nature-200/50">
          <FileArchive className="w-12 h-12 mx-auto mb-3 text-wood-300" />
          <p className="text-wood-500">还没有上传任何文档</p>
          <p className="text-sm text-wood-400 mt-1">支持 PDF、Word、Excel、PPT、Markdown、HTML、图片等格式</p>
        </div>
      ) : (
        <div className="space-y-2">
          {docs.map(doc => (
            <div
              key={doc.id}
              className="bg-white rounded-xl p-4 border border-nature-200/50 hover:border-nature-200 flex items-center gap-4 transition-all"
            >
              <div className="w-10 h-10 rounded-lg bg-nature-100 flex items-center justify-center flex-shrink-0">
                <FileText className="w-5 h-5 text-wood-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-nature-800 truncate">{doc.original_filename}</span>
                  <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-nature-100">
                    {statusIcon(doc.status)}
                    <span className="text-wood-500">{statusText(doc.status)}</span>
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-wood-400">
                  <span className="flex items-center gap-1">
                    <HardDrive className="w-3 h-3" />
                    {formatSize(doc.file_size)}
                  </span>
                  {doc.chunk_count > 0 && (
                    <span>分块数: {doc.chunk_count}</span>
                  )}
                  {doc.error_message && (
                    <span className="text-red-500 truncate">{doc.error_message}</span>
                  )}
                </div>
              </div>
              <button
                onClick={() => handleDelete(doc.id, doc.original_filename)}
                className="p-2 text-wood-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all flex-shrink-0"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

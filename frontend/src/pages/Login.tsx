import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Leaf, Mail, Lock, User, Building2, Eye, EyeOff, Sparkles } from 'lucide-react'
import { authAPI } from '../api/client'
import { useAuthStore } from '../stores/authStore'

export default function Login() {
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [tenantName, setTenantName] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (isRegister) {
        const result = await authAPI.register({
          email,
          username,
          password,
          tenant_name: tenantName || undefined,
        })
        setAuth(result.access_token, {
          user_id: result.user_id,
          tenant_id: result.tenant_id,
          tenant_name: result.tenant_name,
          username: result.username,
          email: result.email,
          role: result.role,
        })
      } else {
        const result = await authAPI.login({ email, password })
        setAuth(result.access_token, {
          user_id: result.user_id,
          tenant_id: result.tenant_id,
          tenant_name: result.tenant_name,
          username: result.username,
          email: result.email,
          role: result.role,
        })
      }
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || '操作失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left: Decorative */}
      <div className="hidden lg:flex lg:w-1/2 bg-login-gradient relative overflow-hidden items-center justify-center">
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-20 left-20 w-72 h-72 bg-green-400 rounded-full blur-3xl" />
          <div className="absolute bottom-20 right-20 w-96 h-96 bg-blue-400 rounded-full blur-3xl" />
          <div className="absolute top-1/2 left-1/2 w-64 h-64 bg-yellow-300 rounded-full blur-3xl" />
        </div>
        <div className="relative z-10 text-center text-white px-12">
          <div className="w-20 h-20 mx-auto mb-8 rounded-3xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
            <Leaf className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl font-bold mb-4 tracking-tight">企业知识库</h1>
          <p className="text-lg text-white/80 leading-relaxed">
            上传文档，智能问答，让知识触手可及
          </p>
          <div className="mt-12 grid grid-cols-3 gap-6 text-sm text-white/70">
            <div className="bg-white/10 rounded-2xl p-4 backdrop-blur-sm">
              <Sparkles className="w-6 h-6 mx-auto mb-2 text-green-300" />
              <div>AI 驱动</div>
            </div>
            <div className="bg-white/10 rounded-2xl p-4 backdrop-blur-sm">
              <Building2 className="w-6 h-6 mx-auto mb-2 text-blue-300" />
              <div>多租户</div>
            </div>
            <div className="bg-white/10 rounded-2xl p-4 backdrop-blur-sm">
              <Lock className="w-6 h-6 mx-auto mb-2 text-yellow-300" />
              <div>权限管控</div>
            </div>
          </div>
        </div>
      </div>

      {/* Right: Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center bg-nature-50 p-8">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 mb-10 justify-center">
            <div className="w-10 h-10 rounded-xl bg-leaf-500 flex items-center justify-center">
              <Leaf className="w-5 h-5 text-white" />
            </div>
            <span className="font-semibold text-xl text-nature-800">知识库</span>
          </div>

          <h2 className="text-2xl font-bold text-nature-800 mb-1">
            {isRegister ? '创建账号' : '欢迎回来'}
          </h2>
          <p className="text-wood-400 mb-8">
            {isRegister ? '注册一个新的工作空间' : '登录到你的知识库'}
          </p>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <>
                <div>
                  <label className="block text-sm font-medium text-nature-700 mb-1.5">用户名</label>
                  <div className="relative">
                    <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-wood-300" />
                    <input
                      type="text"
                      value={username}
                      onChange={e => setUsername(e.target.value)}
                      className="w-full pl-10 pr-4 py-3 bg-white border border-nature-200 rounded-xl text-nature-800 placeholder-wood-300 focus:outline-none focus:ring-2 focus:ring-leaf-500/20 focus:border-leaf-500 transition-all"
                      placeholder="你的名字"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-nature-700 mb-1.5">
                    工作空间名称 <span className="text-wood-300 font-normal">(可选)</span>
                  </label>
                  <div className="relative">
                    <Building2 className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-wood-300" />
                    <input
                      type="text"
                      value={tenantName}
                      onChange={e => setTenantName(e.target.value)}
                      className="w-full pl-10 pr-4 py-3 bg-white border border-nature-200 rounded-xl text-nature-800 placeholder-wood-300 focus:outline-none focus:ring-2 focus:ring-leaf-500/20 focus:border-leaf-500 transition-all"
                      placeholder="与同事填同一个名字即可加入同一工作空间"
                    />
                  </div>
                </div>
              </>
            )}

            <div>
              <label className="block text-sm font-medium text-nature-700 mb-1.5">邮箱</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-wood-300" />
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-white border border-nature-200 rounded-xl text-nature-800 placeholder-wood-300 focus:outline-none focus:ring-2 focus:ring-leaf-500/20 focus:border-leaf-500 transition-all"
                  placeholder="your@email.com"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-nature-700 mb-1.5">密码</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-wood-300" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full pl-10 pr-12 py-3 bg-white border border-nature-200 rounded-xl text-nature-800 placeholder-wood-300 focus:outline-none focus:ring-2 focus:ring-leaf-500/20 focus:border-leaf-500 transition-all"
                  placeholder="••••••••"
                  required
                  minLength={6}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-wood-300 hover:text-wood-500"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-leaf-500 hover:bg-leaf-600 disabled:bg-leaf-300 text-white font-medium rounded-xl transition-all shadow-lg shadow-leaf-500/25 hover:shadow-leaf-600/30 disabled:shadow-none"
            >
              {loading ? '处理中...' : isRegister ? '创建账号' : '登录'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => { setIsRegister(!isRegister); setError('') }}
              className="text-sm text-leaf-600 hover:text-leaf-700 font-medium"
            >
              {isRegister ? '已有账号？点击登录' : '没有账号？点击注册'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

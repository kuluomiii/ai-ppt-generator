import { type FormEvent, type InputHTMLAttributes, useId, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'
import { BrandMark } from '@/components/BrandMark'
import { login, register } from '@/features/auth/api'
import { useAuthStore } from '@/features/auth/store'
import { errorMessage } from '@/lib/errors'

type Mode = 'login' | 'register'

const COPY: Record<Mode, { title: string; submit: string; switchHint: string; switchTo: string }> =
  {
    login: {
      title: '欢迎回来',
      submit: '登录',
      switchHint: '还没有账号？',
      switchTo: '注册一个',
    },
    register: {
      title: '创建账号',
      submit: '注册并开始',
      switchHint: '已经有账号了？',
      switchTo: '去登录',
    },
  }

export default function AuthPage() {
  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const user = useAuthStore((state) => state.user)
  const restoring = useAuthStore((state) => state.restoring)
  const applySession = useAuthStore((state) => state.applySession)
  const navigate = useNavigate()
  const location = useLocation()

  // 有本地 token 时先等 restore，避免已登录用户闪一下登录表单
  if (restoring) {
    return (
      <div className="images-module grid min-h-screen place-items-center text-sm text-[var(--img-text-secondary)]">
        正在恢复登录状态…
      </div>
    )
  }

  if (user) {
    return <Navigate to="/images" replace />
  }

  const copy = COPY[mode]

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const session = await (mode === 'login' ? login : register)({ email, password })
      applySession(session)
      const from = (location.state as { from?: string } | null)?.from ?? '/images'
      navigate(from, { replace: true })
    } catch (cause) {
      setError(errorMessage(cause instanceof Error ? cause : null, '网络异常，请稍后重试'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="images-module flex min-h-screen items-center justify-center px-5 py-10 sm:px-6 sm:py-16">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <BrandMark className="mx-auto mb-5 size-11 shadow-[0_8px_24px_var(--img-shadow)]" />
          <h1 className="text-2xl font-bold tracking-tight text-[var(--img-text-primary)]">
            {copy.title}
          </h1>
          <p className="mt-2 text-sm text-[var(--img-text-secondary)]">
            描述你的想法，让 AI 为你绘制插画
          </p>
        </div>

        <div className="rounded-[var(--img-radius-lg)] border border-[var(--img-border)] bg-white/85 p-6 shadow-[0_8px_24px_var(--img-shadow)]">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
            <CreamField
              label="邮箱"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              required
            />
            <CreamField
              label="密码"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="至少 8 位"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              minLength={8}
              required
            />

            {error && (
              <p
                role="alert"
                className="rounded-[var(--img-radius-md)] bg-[rgba(255,230,230,0.6)] px-3.5 py-2.5 text-[13px] text-[#E07070]"
              >
                {error}
              </p>
            )}

            <button type="submit" disabled={submitting} className="img-btn-primary mt-1 w-full">
              {submitting ? '处理中…' : copy.submit}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-[var(--img-text-secondary)]">
          {copy.switchHint}
          <button
            type="button"
            onClick={() => {
              setMode(mode === 'login' ? 'register' : 'login')
              setError(null)
            }}
            className="ml-1 font-medium text-[var(--img-pink-deep)] underline-offset-4 transition-colors hover:underline"
          >
            {copy.switchTo}
          </button>
        </p>
      </div>
    </div>
  )
}

/** 奶油风输入框：16px 字号防 iOS 聚焦缩放，粉色 focus ring。 */
function CreamField({
  label,
  ...props
}: { label: string } & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId()
  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor={id}
        className="text-[13px] font-semibold text-[var(--img-text-primary)]"
      >
        {label}
      </label>
      <input
        {...props}
        id={id}
        className="h-11 rounded-[var(--img-radius-md)] border border-[var(--img-border)] bg-[#FFFDFB] px-3.5 text-[16px] text-[var(--img-text-primary)] transition-shadow placeholder:text-[var(--img-text-muted)] focus:border-[var(--img-pink-deep)] focus:shadow-[0_0_0_3px_rgba(255,143,174,0.15)] focus:outline-none"
      />
    </div>
  )
}

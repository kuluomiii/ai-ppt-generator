import { Image as ImageIcon, LogOut, Plus } from 'lucide-react'
import { type ReactNode, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { BrandMark } from '@/components/BrandMark'
import { Button } from '@/components/ui/Button'
import { useAuthStore } from '@/features/auth/store'
import { cn } from '@/lib/utils'

/** 工作区外壳：仅用于列表与创作页；编辑工作台自带全屏 chrome，不套这层。 */
export function AppShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()
  const isImages = location.pathname.startsWith('/images')
  const onCreate = location.pathname === '/create' || location.pathname === '/images/create'

  return (
    <div className="flex min-h-screen flex-col">
      <header
        className={cn(
          'sticky top-0 z-30 border-b backdrop-blur-md',
          isImages
            ? 'border-[#F0E4DA] bg-[#FFF9F3]/92'
            : 'border-line bg-surface/80',
        )}
      >
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-8">
          <div className="flex items-center gap-6">
            <Link to="/projects" className="flex items-center gap-2.5">
              <BrandMark className="size-7" />
              <span
                className={cn(
                  'text-[15px] font-semibold tracking-tight',
                  isImages ? 'font-[Quicksand] text-[#FF8FAE]' : '',
                )}
              >
                AI<span className={isImages ? 'text-[#FFBE4D]' : ''}>PPT</span>
              </span>
            </Link>
            <nav
              className={cn(
                'hidden items-center gap-1 rounded-[20px] p-[3px] sm:flex',
                isImages ? 'bg-[#FFE4EC]' : '',
              )}
            >
              <NavLink active={!isImages} to="/projects" creamMode={isImages}>
                PPT
              </NavLink>
              <NavLink active={isImages} to="/images" creamMode={isImages}>
                AI 生图
              </NavLink>
            </nav>
          </div>

          <div className="flex items-center gap-3">
            {!onCreate && !isImages && (
              <Button size="sm" onClick={() => navigate('/create')}>
                <Plus className="size-4" />
                新建 PPT
              </Button>
            )}
            {!onCreate && isImages && (
              <button
                type="button"
                onClick={() => navigate('/images/create')}
                className="inline-flex items-center gap-2 rounded-[20px] bg-gradient-to-br from-[#FFB0C8] to-[#FF8FAE] px-5 py-2 text-[13px] font-semibold text-white shadow-[0_4px_12px_rgba(255,143,174,0.3)] transition-all hover:-translate-y-px hover:shadow-[0_6px_16px_rgba(255,143,174,0.4)]"
              >
                <ImageIcon className="size-4" />
                新建图片
              </button>
            )}
            <UserMenu creamMode={isImages} />
          </div>
        </div>
      </header>

      <main className="flex-1">{children}</main>
    </div>
  )
}

function NavLink({
  active,
  to,
  children,
  creamMode,
}: {
  active: boolean
  to: string
  children: ReactNode
  creamMode?: boolean
}) {
  return (
    <Link
      to={to}
      className={cn(
        'rounded-[17px] px-[18px] py-[6px] text-[13px] font-medium transition-all',
        creamMode
          ? active
            ? 'bg-white text-[#FF8FAE] shadow-[0_2px_8px_rgba(180,140,120,0.08)]'
            : 'text-[#9B8578] hover:text-[#5C4033]'
          : active
            ? 'bg-accent/10 text-accent'
            : 'text-ink-muted hover:text-ink',
      )}
    >
      {children}
    </Link>
  )
}

function UserMenu({ creamMode }: { creamMode?: boolean }) {
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onPointer = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onPointer)
    return () => document.removeEventListener('mousedown', onPointer)
  }, [open])

  const initial = user?.email?.[0]?.toUpperCase() ?? '?'

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="账号菜单"
        onClick={() => setOpen((value) => !value)}
        onKeyDown={(event) => {
          if (event.key === 'Escape') setOpen(false)
        }}
        className={cn(
          'grid size-8 place-items-center rounded-full text-[13px] font-semibold ring-1 transition-colors',
          creamMode
            ? 'bg-[#FFF3D6] text-[#FFBE4D] ring-[#F0E4DA] hover:ring-[#FFD98E]'
            : 'bg-surface-soft text-ink-soft ring-line hover:ring-line-strong',
        )}
      >
        {initial}
      </button>

      {open && (
        <div
          role="menu"
          className={cn(
            'absolute top-full right-0 z-40 mt-2 w-56 overflow-hidden rounded-2xl border shadow-pop',
            creamMode
              ? 'border-[#F0E4DA] bg-[#FFF9F3]'
              : 'border-line bg-surface',
          )}
        >
          <p
            className={cn(
              'truncate border-b px-4 py-3 text-xs',
              creamMode
                ? 'border-[#F0E4DA] text-[#9B8578]'
                : 'border-line text-ink-muted',
            )}
          >
            {user?.email}
          </p>
          <button
            type="button"
            role="menuitem"
            onClick={logout}
            className={cn(
              'flex w-full items-center gap-2 px-4 py-3 text-sm transition-colors',
              creamMode
                ? 'text-[#9B8578] hover:bg-[#FFE4EC] hover:text-[#5C4033]'
                : 'text-ink-soft hover:bg-surface-soft hover:text-ink',
            )}
          >
            <LogOut className="size-4" />
            退出登录
          </button>
        </div>
      )}
    </div>
  )
}

import { Image as ImageIcon, LogOut } from 'lucide-react'
import { type ReactNode, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { BrandMark } from '@/components/BrandMark'
import { useAuthStore } from '@/features/auth/store'

/** 工作区外壳：奶油甜品风；PPT 入口已隐藏（路由保留，可直接访问 URL）。 */
export function AppShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()
  const onCreate = location.pathname === '/create' || location.pathname === '/images/create'

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-30 border-b border-[#F0E4DA] bg-[#FFF9F3]/92 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-4 sm:h-16 sm:px-8">
          <Link to="/images" className="flex items-center gap-2.5">
            <BrandMark className="size-7" />
            <span className="font-[Quicksand] text-[15px] font-semibold tracking-tight text-[#FF8FAE]">
              AI<span className="text-[#FFBE4D]">插画</span>
            </span>
          </Link>

          <div className="flex items-center gap-2 sm:gap-3">
            {!onCreate && (
              <button
                type="button"
                onClick={() => navigate('/images/create')}
                className="inline-flex items-center gap-1.5 rounded-[20px] bg-gradient-to-br from-[#FFB0C8] to-[#FF8FAE] px-3.5 py-1.5 text-[12px] font-semibold text-white shadow-[0_4px_12px_rgba(255,143,174,0.3)] transition-all hover:-translate-y-px hover:shadow-[0_6px_16px_rgba(255,143,174,0.4)] sm:gap-2 sm:px-5 sm:py-2 sm:text-[13px]"
              >
                <ImageIcon className="size-3.5 sm:size-4" />
                新建图片
              </button>
            )}
            <UserMenu />
          </div>
        </div>
      </header>

      <main className="flex-1">{children}</main>
    </div>
  )
}

function UserMenu() {
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
        className="grid size-8 place-items-center rounded-full bg-[#FFF3D6] text-[13px] font-semibold text-[#FFBE4D] ring-1 ring-[#F0E4DA] transition-colors hover:ring-[#FFD98E]"
      >
        {initial}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute top-full right-0 z-40 mt-2 w-56 overflow-hidden rounded-2xl border border-[#F0E4DA] bg-[#FFF9F3] shadow-pop"
        >
          <p className="truncate border-b border-[#F0E4DA] px-4 py-3 text-xs text-[#9B8578]">
            {user?.email}
          </p>
          <button
            type="button"
            role="menuitem"
            onClick={logout}
            className="flex w-full items-center gap-2 px-4 py-3 text-sm text-[#9B8578] transition-colors hover:bg-[#FFE4EC] hover:text-[#5C4033]"
          >
            <LogOut className="size-4" />
            退出登录
          </button>
        </div>
      )}
    </div>
  )
}

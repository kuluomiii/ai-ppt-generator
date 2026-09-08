import { cn } from '@/lib/utils'

/**
 * 应用品牌标识：奶油甜品风（粉色渐变底 + 白色画笔与星星）。
 * 自带底色与圆角，调用方只需给尺寸（size-7 之类）。
 */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      role="img"
      aria-label="AI 插画"
      className={cn('shrink-0', className)}
    >
      <defs>
        <linearGradient id="brandmark-bg" x1="0" y1="0" x2="32" y2="32">
          <stop offset="0" stopColor="#FFB0C8" />
          <stop offset="1" stopColor="#FF8FAE" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill="url(#brandmark-bg)" />
      {/* 画笔 */}
      <path
        d="M11 21.5l1-3.6 7.4-7.4a1.6 1.6 0 0 1 2.3 0l.9.9a1.6 1.6 0 0 1 0 2.3L15.2 21l-3.6 1a.4.4 0 0 1-.6-.5z"
        fill="#FFF9F3"
      />
      <path d="M12.4 17.2l2.9 2.9-1.6.4a.4.4 0 0 1-.5-.2l-.9-2.7a.3.3 0 0 1 .1-.4z" fill="#FFD98E" />
      {/* 星星 */}
      <path
        d="M9.2 7.6l.62 1.74 1.74.62-1.74.62-.62 1.74-.62-1.74-1.74-.62 1.74-.62z"
        fill="#FFF3D6"
      />
      <path
        d="M24.6 22.4l.4.1.1.4.1-.4.4-.1-.4-.1-.1-.4-.1.4z"
        fill="#FFF3D6"
      />
    </svg>
  )
}

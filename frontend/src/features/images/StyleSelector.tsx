import { cn } from '@/lib/utils'
import type { ImageStyle } from './types'
import { STYLE_OPTIONS } from './types'

export function StyleSelector({
  value,
  onChange,
}: {
  value: ImageStyle | null
  onChange: (style: ImageStyle) => void
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {STYLE_OPTIONS.map((option) => {
        const selected = value === option.value
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={cn(
              'flex flex-col items-start gap-1 rounded-[var(--img-radius-md)] border-[1.5px] p-4 text-left transition-all',
              selected
                ? 'border-[var(--img-pink-deep)] bg-[var(--img-pink-light)] shadow-[0_0_0_3px_rgba(255,143,174,0.15)]'
                : 'border-[var(--img-border)] bg-[var(--img-surface)] hover:border-[var(--img-pink)] hover:bg-[var(--img-pink-light)]',
            )}
          >
            <span className="text-[13px] font-semibold text-[var(--img-text-primary)]">
              {option.label}
            </span>
            <span className="text-[11px] leading-relaxed text-[var(--img-text-secondary)]">
              {option.description}
            </span>
          </button>
        )
      })}
    </div>
  )
}

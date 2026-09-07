import { cn } from '@/lib/utils'
import type { ImageAspectRatio } from './types'
import { RATIO_OPTIONS } from './types'

/** 可视化比例框的宽高像素 */
const RATIO_BOX: Record<ImageAspectRatio, { w: number; h: number }> = {
  '1:1': { w: 24, h: 24 },
  '16:9': { w: 32, h: 18 },
  '9:16': { w: 18, h: 32 },
}

export function RatioSelector({
  value,
  onChange,
}: {
  value: ImageAspectRatio | null
  onChange: (ratio: ImageAspectRatio) => void
}) {
  return (
    <div className="flex gap-3">
      {RATIO_OPTIONS.map((option) => {
        const selected = value === option.value
        const box = RATIO_BOX[option.value]
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={cn(
              'flex flex-1 items-center gap-2.5 rounded-[var(--img-radius-md)] border-[1.5px] px-4 py-3 transition-all',
              selected
                ? 'border-[var(--img-yellow-deep)] bg-[var(--img-yellow-light)] shadow-[0_0_0_3px_rgba(255,190,77,0.12)]'
                : 'border-[var(--img-border)] bg-[var(--img-surface)] hover:border-[var(--img-yellow)]',
            )}
          >
            <span
              className={cn(
                'rounded-sm border-2 border-current opacity-50',
                selected ? 'text-[var(--img-yellow-deep)]' : 'text-[var(--img-text-muted)]',
              )}
              style={{ width: box.w, height: box.h }}
            />
            <span className="text-[13px]">
              <span className="block font-semibold text-[var(--img-text-primary)]">
                {option.value}
              </span>
              <span className="text-[11px] text-[var(--img-text-secondary)]">
                {option.label}
              </span>
            </span>
          </button>
        )
      })}
    </div>
  )
}

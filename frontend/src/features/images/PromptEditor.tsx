import { Loader2, RefreshCw } from 'lucide-react'

export function PromptEditor({
  value,
  onChange,
  onRegenerate,
  saving,
  regenerating,
}: {
  value: string
  onChange: (value: string) => void
  onRegenerate: () => void
  saving: boolean
  regenerating: boolean
}) {
  const busy = saving || regenerating

  return (
    <div className="flex flex-col">
      <label className="mb-2.5 block text-sm font-semibold text-[var(--img-text-primary)]">
        优化提示词
      </label>
      <div className="rounded-[var(--img-radius-md)] border-[1.5px] border-[var(--img-border)] bg-[var(--img-surface)] p-4">
        <textarea
          className="min-h-[160px] w-full resize-y border-none bg-transparent text-[13px] leading-relaxed text-[var(--img-text-primary)] outline-none placeholder:text-[var(--img-text-muted)]"
          maxLength={5000}
          placeholder="提示词将在此显示…"
          value={value}
          disabled={busy}
          onChange={(e) => onChange(e.target.value)}
        />
        <div className="mt-3 flex items-center justify-between border-t border-dashed border-[var(--img-border)] pt-3">
          <span className="text-[11px] text-[var(--img-text-muted)]">{value.length}/5000</span>
          <button
            type="button"
            disabled={busy}
            onClick={onRegenerate}
            className="flex items-center gap-1 border-none bg-none text-xs font-medium text-[var(--img-pink-deep)] hover:underline disabled:opacity-50"
          >
            {regenerating ? (
              <>
                <Loader2 className="size-3.5 animate-spin" />
                生成中…
              </>
            ) : (
              <>
                <RefreshCw className="size-3.5" />
                重新生成
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

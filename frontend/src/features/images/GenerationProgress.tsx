import { AlertCircle, Download, RefreshCw } from 'lucide-react'
import type { ProgressResponse } from './types'

export function GenerationProgress({
  progress,
  onRetry,
  onDownload,
  retrying,
}: {
  progress: ProgressResponse | undefined
  onRetry: () => void
  onDownload: () => void
  retrying: boolean
}) {
  if (!progress) return null

  const { status, progress: pct, error_message, image_url } = progress

  if (status === 'completed') {
    return (
      <div className="flex flex-col items-center gap-5">
        {image_url && (
          <img
            src={image_url}
            alt="生成结果"
            className="max-h-[500px] w-full rounded-[var(--img-radius-lg)] border border-[var(--img-border)] object-contain shadow-[0_8px_24px_var(--img-shadow)]"
          />
        )}
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 text-sm font-medium text-[#6DBE72]">
            ✦ 生成完成
          </span>
          <button type="button" className="img-btn-download" onClick={onDownload}>
            <Download className="size-4" />
            下载图片
          </button>
        </div>
      </div>
    )
  }

  if (status === 'failed') {
    return (
      <div className="flex flex-col items-center gap-4 rounded-[var(--img-radius-lg)] border border-[rgba(224,112,112,0.25)] bg-[rgba(255,230,230,0.5)] p-10">
        <AlertCircle className="size-10 text-[#E07070]" />
        <p className="text-center text-sm text-[#E07070]">
          {error_message ?? '生成失败，请重试'}
        </p>
        <button
          type="button"
          className="img-btn-ghost"
          disabled={retrying}
          onClick={onRetry}
        >
          <RefreshCw className="size-3.5" />
          {retrying ? '提交中…' : '重新生成'}
        </button>
      </div>
    )
  }

  // pending / generating
  const label = status === 'pending' ? '排队中，马上就好…' : 'AI 正在为你绘制插画…'
  return (
    <div className="flex flex-col items-center py-12 text-center">
      <div className="img-spinner mb-4" />
      <p className="mb-3 text-sm font-medium text-[var(--img-text-primary)]">{label}</p>
      <div className="img-progress-track">
        <div className="img-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="mt-2 text-xs text-[var(--img-text-muted)]">{pct}%</span>
    </div>
  )
}

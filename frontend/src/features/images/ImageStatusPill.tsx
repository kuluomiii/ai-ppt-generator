import { cn } from '@/lib/utils'
import type { ImageProjectStatus } from './types'

const STATUS_LABEL: Record<ImageProjectStatus, string> = {
  pending: '等待中',
  generating: '生成中',
  completed: '已完成',
  failed: '失败',
}

const STATUS_TONE: Record<ImageProjectStatus, string> = {
  pending: 'img-status-pending',
  generating: 'img-status-generating',
  completed: 'img-status-completed',
  failed: 'img-status-failed',
}

export function ImageStatusPill({
  status,
  className,
}: {
  status: ImageProjectStatus
  className?: string
}) {
  return (
    <span className={cn('img-status-pill', STATUS_TONE[status], className)}>
      {status === 'generating' && (
        <span className="size-1.5 animate-pulse rounded-full bg-current" />
      )}
      {STATUS_LABEL[status]}
    </span>
  )
}

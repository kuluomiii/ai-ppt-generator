export type ImageStyle = 'chiikawa_science' | 'minimal_doodle' | 'shinchan_education'
export type ImageAspectRatio = '1:1' | '16:9' | '9:16'
export type ImageProjectStatus = 'pending' | 'generating' | 'completed' | 'failed'

export interface ImageProject {
  id: string
  raw_prompt: string
  style: ImageStyle
  aspect_ratio: ImageAspectRatio
  optimized_prompt: string | null
  status: ImageProjectStatus
  progress: number
  error_message: string | null
  image_url: string | null
  created_at: string
  updated_at: string
}

export interface ImageProjectListResponse {
  items: ImageProject[]
  total: number
}

export interface ProgressResponse {
  status: ImageProjectStatus
  progress: number
  error_message: string | null
  image_url: string | null
}

export interface OptimizedPromptResponse {
  optimized_prompt: string
}

export const STYLE_OPTIONS: readonly { value: ImageStyle; label: string; description: string }[] = [
  {
    value: 'chiikawa_science',
    label: '吉伊卡哇科普',
    description: '可爱圆润角色，柔和粉彩配色，适合科普教育类插画',
  },
  {
    value: 'minimal_doodle',
    label: '简约手绘涂鸦',
    description: '简洁线条黑白为主，留白充足，极简视觉语言',
  },
  {
    value: 'shinchan_education',
    label: '蜡笔小新教育',
    description: '幽默夸张风格，粗犷手绘线条，趣味教育插画',
  },
] as const

export const RATIO_OPTIONS: readonly { value: ImageAspectRatio; label: string }[] = [
  { value: '1:1', label: '正方形' },
  { value: '16:9', label: '横版' },
  { value: '9:16', label: '竖版' },
] as const

/** @deprecated 使用 ImageStatusPill 组件内的奶油甜品风样式 */
export const STATUS_CONFIG: Record<
  ImageProjectStatus,
  { label: string; className: string; pulse?: boolean }
> = {
  pending: { label: '等待中', className: 'bg-surface-soft text-ink-muted' },
  generating: { label: '生成中', className: 'bg-accent-soft text-accent', pulse: true },
  completed: { label: '已完成', className: 'bg-positive/10 text-positive' },
  failed: { label: '失败', className: 'bg-negative/8 text-negative' },
}

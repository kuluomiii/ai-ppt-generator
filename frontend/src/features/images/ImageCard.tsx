import { Download, MoreHorizontal, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { MenuPopover, MenuItem } from '@/components/ui/MenuPopover'
import { Dialog } from '@/components/ui/Dialog'
import { Button } from '@/components/ui/Button'
import { relativeTime } from '@/lib/datetime'
import { ImageStatusPill } from './ImageStatusPill'
import type { ImageProject } from './types'
import { STYLE_OPTIONS } from './types'

export function ImageCard({
  project,
  onDeleteRequest,
}: {
  project: ImageProject
  onDeleteRequest: () => void
}) {
  const [previewOpen, setPreviewOpen] = useState(false)
  const styleLabel = STYLE_OPTIONS.find((o) => o.value === project.style)?.label ?? project.style
  const isComplete = project.status === 'completed' && !!project.image_url

  return (
    <>
      <li className="img-card group relative flex flex-col">
        {/* 缩略图区域 */}
        <div
          className="relative aspect-square w-full cursor-pointer overflow-hidden"
          onClick={() => isComplete && setPreviewOpen(true)}
        >
          {isComplete ? (
            <img
              src={project.image_url!}
              alt={project.raw_prompt}
              className="h-full w-full object-cover transition-transform group-hover:scale-105"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-[var(--img-pink-light)] to-[var(--img-yellow-light)] text-[13px] text-[var(--img-text-muted)]">
              {project.status === 'generating'
                ? '生成中…'
                : project.status === 'failed'
                  ? '失败'
                  : '等待中'}
            </div>
          )}
          <div className="absolute top-3 right-3">
            <ImageStatusPill status={project.status} />
          </div>
        </div>

        {/* 信息区 */}
        <div className="flex flex-1 flex-col p-3 sm:p-4">
          <p className="mb-2.5 line-clamp-2 text-[12px] leading-normal text-[var(--img-text-primary)] sm:text-[13px]">
            {project.raw_prompt}
          </p>
          <div className="mt-auto flex items-center justify-between gap-1 text-[11px] text-[var(--img-text-muted)]">
            <span className="truncate rounded-lg bg-[var(--img-yellow-light)] px-2 py-0.5 font-medium text-[var(--img-yellow-deep)] sm:px-2.5">
              {styleLabel}
            </span>
            <span className="shrink-0">{relativeTime(project.created_at)}</span>
          </div>
        </div>

        {/* 操作菜单：触屏无 hover，移动端常显 */}
        <div className="absolute top-3 left-3 opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100">
          <MenuPopover
            align="left"
            trigger={({ open, toggle }) => (
              <button
                type="button"
                aria-label="更多操作"
                onClick={toggle}
                className={`grid size-8 place-items-center rounded-full bg-white/90 backdrop-blur-sm transition-colors hover:bg-white ${open ? 'ring-2 ring-[var(--img-pink)]' : ''}`}
              >
                <MoreHorizontal className="size-4 text-[var(--img-text-secondary)]" />
              </button>
            )}
          >
            {({ close }) => (
              <>
                {isComplete && (
                  <MenuItem icon={Download} onSelect={() => { close(); setPreviewOpen(true) }}>
                    预览大图
                  </MenuItem>
                )}
                <MenuItem icon={Trash2} danger onSelect={() => { close(); onDeleteRequest() }}>
                  删除
                </MenuItem>
              </>
            )}
          </MenuPopover>
        </div>
      </li>

      {/* 大图预览弹窗 */}
      {previewOpen && project.image_url && (
        <Dialog
          title="图片预览"
          onClose={() => setPreviewOpen(false)}
          className="max-w-3xl"
          footer={
            <Button
              size="sm"
              onClick={() => {
                const a = document.createElement('a')
                a.href = project.image_url!
                a.download = `image-${project.id.slice(0, 8)}.png`
                a.click()
              }}
            >
              <Download className="size-4" />
              下载
            </Button>
          }
        >
          <img
            src={project.image_url}
            alt={project.raw_prompt}
            className="w-full rounded-xl"
          />
        </Dialog>
      )}
    </>
  )
}

import { Plus } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/Button'
import { Dialog } from '@/components/ui/Dialog'
import { errorMessage } from '@/lib/errors'
import { useImageProjects, useDeleteImageProject } from '@/features/images/api'
import { ImageCard } from '@/features/images/ImageCard'

export default function ImagesPage() {
  const navigate = useNavigate()
  const projects = useImageProjects()
  const remove = useDeleteImageProject()
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const handleConfirmDelete = () => {
    if (!deletingId) return
    remove.mutate(deletingId, { onSuccess: () => setDeletingId(null) })
  }

  // Loading skeleton
  if (projects.isLoading) {
    return (
      <div className="images-module">
        <div className="mx-auto max-w-[1200px] px-8 py-10">
          <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <li
                key={i}
                className="aspect-[4/5] animate-pulse rounded-[var(--img-radius-lg)] bg-[var(--img-pink-light)]/50"
              />
            ))}
          </ul>
        </div>
      </div>
    )
  }

  // Error
  if (projects.isError) {
    return (
      <div className="images-module">
        <div className="mx-auto max-w-[1200px] px-8 py-10">
          <p
            role="alert"
            className="rounded-[var(--img-radius-md)] bg-[rgba(255,230,230,0.6)] px-4 py-3 text-sm text-[#E07070]"
          >
            {errorMessage(projects.error, '图片列表加载失败，请稍后重试')}
          </p>
        </div>
      </div>
    )
  }

  const items = projects.data?.items ?? []

  return (
    <div className="images-module">
      <div className="mx-auto max-w-[1200px] px-8 py-10">
        {/* Header */}
        <div className="mb-8">
          <h1 className="mb-2 text-[28px] font-bold text-[var(--img-text-primary)]">
            我的插画集
          </h1>
          <p className="text-sm text-[var(--img-text-secondary)]">
            最近生成的 AI 插画，点击可预览大图
          </p>
        </div>

        {/* Empty state */}
        {items.length === 0 && (
          <div className="flex flex-col items-center py-20 text-center">
            <div className="mb-5 grid size-20 place-items-center rounded-full bg-gradient-to-br from-[var(--img-pink-light)] to-[var(--img-yellow-light)] text-[32px]">
              🎨
            </div>
            <p className="mb-2 text-lg font-semibold text-[var(--img-text-primary)]">
              还没有生成过图片
            </p>
            <p className="mb-6 text-sm text-[var(--img-text-secondary)]">
              选择风格和需求，让 AI 为你创作插画
            </p>
            <button
              type="button"
              className="img-btn-primary"
              onClick={() => navigate('/images/create')}
            >
              <Plus className="size-4" />
              开始创作
            </button>
          </div>
        )}

        {/* Card grid */}
        {items.length > 0 && (
          <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {items.map((project) => (
              <ImageCard
                key={project.id}
                project={project}
                onDeleteRequest={() => setDeletingId(project.id)}
              />
            ))}
          </ul>
        )}

        {/* Delete error feedback */}
        {remove.isError && (
          <p className="mt-4 text-sm text-[#E07070]">
            {errorMessage(remove.error, '删除失败，请重试')}
          </p>
        )}

        {/* 删除确认弹窗 */}
        {deletingId && (
          <Dialog
            title="删除这张图片？"
            description="删除后无法恢复。"
            className="max-w-sm"
            onClose={() => setDeletingId(null)}
            footer={
              <>
                <Button variant="ghost" size="sm" onClick={() => setDeletingId(null)}>
                  取消
                </Button>
                <Button
                  size="sm"
                  className="bg-negative hover:bg-negative/90 disabled:hover:bg-negative"
                  disabled={remove.isPending}
                  onClick={handleConfirmDelete}
                >
                  {remove.isPending ? '删除中…' : '删除'}
                </Button>
              </>
            }
          >
            <p className="text-sm text-ink-muted">确定要删除这张图片吗？此操作不可撤销。</p>
          </Dialog>
        )}
      </div>
    </div>
  )
}

import { Button } from '@/components/ui/Button'
import { Dialog } from '@/components/ui/Dialog'
import type { Project } from '@/features/projects/types'

export function DeleteProjectDialog({
  project,
  pending,
  onClose,
  onConfirm,
}: {
  project: Project
  pending: boolean
  onClose: () => void
  onConfirm: () => void
}) {
  return (
    <Dialog
      title="删除这个 PPT？"
      description={`「${project.title}」及其所有内容会一并删除，且无法撤销。`}
      className="max-w-sm"
      onClose={onClose}
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose}>
            取消
          </Button>
          <Button
            size="sm"
            className="bg-negative hover:bg-negative/90 disabled:hover:bg-negative"
            disabled={pending}
            onClick={onConfirm}
          >
            {pending ? '删除中…' : '删除'}
          </Button>
        </>
      }
    >
      <p className="text-sm text-ink-muted">此操作不可撤销。</p>
    </Dialog>
  )
}

import { ArrowLeft, Loader2, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import { errorMessage } from '@/lib/errors'
import {
  useCreateImageProject,
  useGenerateImage,
  useImageProgress,
  useImageProject,
  useOptimizePrompt,
  useUpdatePrompt,
} from '@/features/images/api'
import { GenerationProgress } from '@/features/images/GenerationProgress'
import { PromptEditor } from '@/features/images/PromptEditor'
import { RatioSelector } from '@/features/images/RatioSelector'
import { StyleSelector } from '@/features/images/StyleSelector'
import type { ImageAspectRatio, ImageStyle } from '@/features/images/types'

type Phase = 'form' | 'optimizing' | 'editing' | 'generating'

export default function ImageCreatePage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const resumeId = searchParams.get('id')

  // Form state
  const [rawPrompt, setRawPrompt] = useState('')
  const [style, setStyle] = useState<ImageStyle | null>(null)
  const [ratio, setRatio] = useState<ImageAspectRatio | null>(null)
  const [optimizedPrompt, setOptimizedPrompt] = useState('')
  const [projectId, setProjectId] = useState<string | null>(null)
  const [phase, setPhase] = useState<Phase>('form')

  // Hooks
  const create = useCreateImageProject()
  const optimize = useOptimizePrompt(projectId ?? '')
  const updatePrompt = useUpdatePrompt(projectId ?? '')
  const generate = useGenerateImage(projectId ?? '')
  const progress = useImageProgress(projectId ?? '')

  // Resume existing project
  const existing = useImageProject(resumeId ?? '')
  useEffect(() => {
    if (existing.data && resumeId) {
      setProjectId(resumeId)
      setRawPrompt(existing.data.raw_prompt)
      setStyle(existing.data.style)
      setRatio(existing.data.aspect_ratio)
      if (existing.data.optimized_prompt) {
        setOptimizedPrompt(existing.data.optimized_prompt)
        setPhase(
          existing.data.status === 'completed' || existing.data.status === 'failed'
            ? 'generating'
            : 'editing',
        )
      } else {
        setPhase('form')
      }
    }
  }, [existing.data, resumeId])

  // After creation → auto optimize
  useEffect(() => {
    if (create.isSuccess && !projectId) {
      setProjectId(create.data.id)
      setPhase('optimizing')
    }
  }, [create.isSuccess, create.data, projectId])

  // Trigger optimize after projectId is set
  useEffect(() => {
    if (phase === 'optimizing' && projectId && !optimize.data) {
      void optimize.mutateAsync(undefined).then((res) => {
        setOptimizedPrompt(res.optimized_prompt)
        setPhase('editing')
      })
    }
  }, [phase, projectId, optimize.data]) // eslint-disable-line react-hooks/exhaustive-deps

  // After generate → start polling
  useEffect(() => {
    if (generate.isSuccess) {
      setPhase('generating')
    }
  }, [generate.isSuccess])

  const handleCreateAndOptimize = () => {
    if (!rawPrompt.trim() || !style || !ratio) return
    create.mutate({ raw_prompt: rawPrompt, style, aspect_ratio: ratio })
  }

  const handleGenerate = () => {
    if (!projectId) return
    generate.mutate(undefined)
  }

  const handleRetry = () => {
    if (!projectId) return
    generate.mutate(undefined)
  }

  const handleDownload = () => {
    const url = progress.data?.image_url
    if (!url) return
    const a = document.createElement('a')
    a.href = url
    a.download = `image-${projectId?.slice(0, 8) ?? 'result'}.png`
    a.click()
  }

  const busy = create.isPending || phase === 'optimizing'

  return (
    <div className="images-module">
      <div className="mx-auto max-w-[680px] px-4 py-6 sm:px-8 sm:py-10">
        {/* Back link */}
        <button
          type="button"
          onClick={() => navigate('/images')}
          className="mb-5 flex items-center gap-1.5 border-none bg-none text-[13px] text-[var(--img-text-secondary)] hover:text-[var(--img-pink-deep)] sm:mb-6"
        >
          <ArrowLeft className="size-4" />
          返回列表
        </button>

        <h1 className="mb-2 text-[22px] font-bold text-[var(--img-text-primary)] sm:text-[28px]">
          创作新插画
        </h1>
        <p className="mb-6 text-[13px] text-[var(--img-text-secondary)] sm:mb-8 sm:text-sm">
          描述你的想法，选择风格，让 AI 为你绘制
        </p>

        {/* ===== Phase: Form ===== */}
        {(phase === 'form' || phase === 'optimizing') && (
          <div className="flex flex-col gap-8">
            {/* Raw prompt */}
            <div>
              <label
                htmlFor="raw-prompt"
                className="mb-2.5 block text-sm font-semibold text-[var(--img-text-primary)]"
              >
                描述你想要的图片
              </label>
              <textarea
                id="raw-prompt"
                className="img-input-area"
                maxLength={2000}
                placeholder="例如：一只猫咪坐在窗台上看夕阳，旁边放着一杯热茶…"
                value={rawPrompt}
                disabled={busy}
                onChange={(e) => setRawPrompt(e.target.value)}
              />
              <div className="mt-1.5 text-right text-[11px] text-[var(--img-text-muted)]">
                {rawPrompt.length}/2000
              </div>
            </div>

            {/* Style selector */}
            <div>
              <label className="mb-2.5 block text-sm font-semibold text-[var(--img-text-primary)]">
                选择风格
              </label>
              <StyleSelector value={style} onChange={setStyle} />
            </div>

            {/* Ratio selector */}
            <div>
              <label className="mb-2.5 block text-sm font-semibold text-[var(--img-text-primary)]">
                选择比例
              </label>
              <RatioSelector value={ratio} onChange={setRatio} />
            </div>

            {/* Submit */}
            <button
              type="button"
              className="img-btn-primary w-full"
              disabled={!rawPrompt.trim() || !style || !ratio || busy}
              onClick={handleCreateAndOptimize}
            >
              {busy ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  {phase === 'optimizing' ? '正在优化提示词…' : '创建中…'}
                </>
              ) : (
                <>
                  <Sparkles className="size-4" />
                  创建并优化提示词
                </>
              )}
            </button>

            {create.isError && (
              <p className="text-sm text-[#E07070]">{errorMessage(create.error)}</p>
            )}
          </div>
        )}

        {/* ===== Phase: Editing prompt ===== */}
        {phase === 'editing' && (
          <div className="flex flex-col gap-6">
            <PromptEditor
              value={optimizedPrompt}
              onChange={setOptimizedPrompt}
              onRegenerate={() => {
                if (!projectId) return
                void optimize.mutateAsync(undefined).then((res) => {
                  setOptimizedPrompt(res.optimized_prompt)
                })
              }}
              saving={updatePrompt.isPending}
              regenerating={optimize.isPending}
            />

            {optimize.isError && (
              <p className="text-sm text-[#E07070]">{errorMessage(optimize.error)}</p>
            )}

            <div className="flex gap-3">
              <button
                type="button"
                className="img-btn-ghost"
                onClick={() => {
                  setPhase('form')
                  setProjectId(null)
                  setOptimizedPrompt('')
                }}
              >
                返回修改
              </button>
              <button
                type="button"
                className="img-btn-primary flex-1"
                disabled={!optimizedPrompt.trim()}
                onClick={() => {
                  // Save then generate
                  if (projectId) {
                    updatePrompt.mutate(optimizedPrompt, {
                      onSuccess: () => handleGenerate(),
                    })
                  }
                }}
              >
                {updatePrompt.isPending || generate.isPending ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    提交中…
                  </>
                ) : (
                  '生成图片'
                )}
              </button>
            </div>
          </div>
        )}

        {/* ===== Phase: Generating / Result ===== */}
        {phase === 'generating' && (
          <GenerationProgress
            progress={progress.data}
            onRetry={handleRetry}
            onDownload={handleDownload}
            retrying={generate.isPending}
          />
        )}
      </div>
    </div>
  )
}

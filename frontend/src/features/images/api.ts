import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { request } from '@/api/client'
import type {
  ImageProject,
  ImageProjectListResponse,
  OptimizedPromptResponse,
  ProgressResponse,
} from './types'

const listKey = ['image-projects'] as const
const detailKey = (id: string) => ['image-projects', id] as const
const progressKey = (id: string) => ['image-projects', id, 'progress'] as const

export function useImageProjects() {
  return useQuery({
    queryKey: listKey,
    queryFn: () => request<ImageProjectListResponse>('/image-projects'),
  })
}

export function useImageProject(id: string) {
  return useQuery({
    queryKey: detailKey(id),
    queryFn: () => request<ImageProject>(`/image-projects/${id}`),
    enabled: !!id,
  })
}

export function useCreateImageProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { raw_prompt: string; style: string; aspect_ratio: string }) =>
      request<ImageProject>('/image-projects', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: listKey }),
  })
}

export function useOptimizePrompt(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      request<OptimizedPromptResponse>(`/image-projects/${id}/prompt`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: detailKey(id) }),
  })
}

export function useUpdatePrompt(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (optimized_prompt: string) =>
      request<ImageProject>(`/image-projects/${id}/prompt`, {
        method: 'PATCH',
        body: JSON.stringify({ optimized_prompt }),
      }),
    onSuccess: (project) => {
      queryClient.setQueryData(detailKey(id), project)
    },
  })
}

export function useGenerateImage(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      request<{ message: string; job_id: string }>(`/image-projects/${id}/generate`, {
        method: 'POST',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: detailKey(id) })
      queryClient.invalidateQueries({ queryKey: progressKey(id) })
    },
  })
}

export function useDeleteImageProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      request<void>(`/image-projects/${id}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: listKey }),
  })
}

/** 轮询进度：pending/generating 时每 2.5s 刷新，终态停止 */
export function useImageProgress(id: string) {
  return useQuery({
    queryKey: progressKey(id),
    queryFn: () => request<ProgressResponse>(`/image-projects/${id}/progress`),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'pending' || status === 'generating') return 2500
      return false
    },
  })
}

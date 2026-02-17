/**
 * api.ts - Axios-based API client for the LIMS OCR backend.
 *
 * All methods return typed promises aligned with backend response schemas.
 */

import axios, { type AxiosProgressEvent } from 'axios'
import type { ExtractionResult, JobDetail, JobSummary } from '@/types/lims'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 120_000,
})

// ── Upload ────────────────────────────────────────────────────────────────────

export interface UploadJob {
  job_id: string
  filename: string
  status: string
}

export async function uploadDocuments(
  files: File[],
  onProgress?: (percent: number) => void,
): Promise<UploadJob[]> {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }

  const response = await client.post<{ jobs: UploadJob[]; count: number }>(
    '/api/upload',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (event: AxiosProgressEvent) => {
        if (onProgress && event.total) {
          onProgress(Math.round((event.loaded / event.total) * 100))
        }
      },
    },
  )
  return response.data.jobs
}

// ── Jobs ──────────────────────────────────────────────────────────────────────

export async function listJobs(limit = 50, offset = 0): Promise<JobSummary[]> {
  const response = await client.get<{ jobs: JobSummary[]; total: number }>(
    '/api/jobs',
    { params: { limit, offset } },
  )
  return response.data.jobs
}

export async function getJob(jobId: string): Promise<JobDetail> {
  const response = await client.get<JobDetail>(`/api/jobs/${jobId}`)
  return response.data
}

export async function updateJobData(
  jobId: string,
  result: ExtractionResult,
): Promise<{ status: string; validation_error_count: number }> {
  const response = await client.put<{
    job_id: string
    status: string
    validation_error_count: number
  }>(`/api/jobs/${jobId}/data`, result)
  return response.data
}

export async function reprocessJob(jobId: string): Promise<void> {
  await client.post(`/api/jobs/${jobId}/reprocess`)
}

export async function deleteJob(jobId: string): Promise<void> {
  await client.delete(`/api/jobs/${jobId}`)
}

// ── Export ────────────────────────────────────────────────────────────────────

export async function exportJob(jobId: string): Promise<void> {
  const response = await client.post(`/api/jobs/${jobId}/export`, null, {
    responseType: 'blob',
  })

  // Trigger browser download
  const blob = new Blob([response.data], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `LIMS_LoadSheet_${jobId.slice(0, 8)}.xlsx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// ── Polling helper ────────────────────────────────────────────────────────────

/**
 * Poll a job until it reaches 'complete' or 'failed'.
 * Calls onUpdate on every poll with the latest job detail.
 */
export async function pollUntilComplete(
  jobId: string,
  onUpdate: (job: JobDetail) => void,
  intervalMs = 3000,
  maxWaitMs = 1_800_000,
): Promise<JobDetail> {
  const start = Date.now()
  return new Promise((resolve, reject) => {
    const interval = setInterval(async () => {
      try {
        const job = await getJob(jobId)
        onUpdate(job)
        if (job.status === 'complete' || job.status === 'failed') {
          clearInterval(interval)
          resolve(job)
        }
        if (Date.now() - start > maxWaitMs) {
          clearInterval(interval)
          reject(new Error(`Polling timeout for job ${jobId}`))
        }
      } catch (err) {
        clearInterval(interval)
        reject(err)
      }
    }, intervalMs)
  })
}

// ── Training ───────────────────────────────────────────────────────────────────

export interface TrainingExample {
  id: number
  name: string
  description: string | null
  created_at: string
  parsed_content: {
    sheet_count: number
    total_rows: number
    sheets: Record<string, { columns: string[]; examples: Record<string, string>[]; total_rows: number }>
  } | null
}

export async function listTrainingExamples(): Promise<TrainingExample[]> {
  const response = await client.get<TrainingExample[]>('/api/training')
  return response.data
}

export async function uploadTrainingExample(
  file: File,
  name: string,
  description: string,
): Promise<TrainingExample> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('name', name)
  formData.append('description', description)
  const response = await client.post<TrainingExample>('/api/training', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export async function deleteTrainingExample(id: number): Promise<void> {
  await client.delete(`/api/training/${id}`)
}

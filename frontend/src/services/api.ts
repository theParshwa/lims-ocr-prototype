/**
 * api.ts - Axios-based API client for the LIMS OCR backend.
 *
 * All methods return typed promises aligned with backend response schemas.
 */

import axios, { type AxiosProgressEvent } from 'axios'
import type { AuditLogEntry, ExtractionResult, JobDetail, JobSummary } from '@/types/lims'

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
  documentTypeHint?: string,
  userContext?: string,
): Promise<UploadJob[]> {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }
  if (documentTypeHint) {
    formData.append('document_type_hint', documentTypeHint)
  }
  if (userContext?.trim()) {
    formData.append('user_context', userContext.trim())
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

export async function getAuditLog(
  jobId: string,
  limit = 200,
  offset = 0,
): Promise<{ total: number; entries: AuditLogEntry[] }> {
  const response = await client.get<{ job_id: string; total: number; entries: AuditLogEntry[] }>(
    `/api/jobs/${jobId}/audit`,
    { params: { limit, offset } },
  )
  return response.data
}

/** Returns the direct URL to stream the original uploaded document (PDF/DOCX). */
export function getDocumentUrl(jobId: string): string {
  return `${BASE_URL}/api/jobs/${jobId}/document`
}

/**
 * Fetches the original document as a Blob (goes through the CORS-aware axios
 * client so the browser doesn't block cross-origin content).
 * Returns { blob, mimeType }.
 */
export async function fetchDocumentBlob(
  jobId: string,
): Promise<{ blob: Blob; mimeType: string }> {
  const response = await client.get(`/api/jobs/${jobId}/document`, {
    responseType: 'blob',
  })
  const mimeType: string = response.headers['content-type'] ?? 'application/octet-stream'
  return { blob: response.data as Blob, mimeType }
}

// ── Refine ─────────────────────────────────────────────────────────────────────

export interface RefineChange {
  sheet: string
  row_index: number
  field: string
  new_value: string | null
  explanation: string
}

export interface RefineResult {
  changes: RefineChange[]
  summary: string
  updated_result: ExtractionResult
}

export async function refineJob(jobId: string, instruction: string): Promise<RefineResult> {
  const response = await client.post<RefineResult>(`/api/jobs/${jobId}/refine`, { instruction })
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

// ── Agent Prompts ─────────────────────────────────────────────────────────────

export interface AgentPrompt {
  key: string
  name: string
  description: string
  system: string
  user: string
  system_preview?: string  // system with placeholders filled from current config
  user_preview?: string    // user with placeholders filled from current config
}

export async function getAgentPrompts(): Promise<AgentPrompt[]> {
  const response = await client.get<AgentPrompt[]>('/api/agent/prompts')
  return response.data
}

export async function updateAgentPrompt(
  key: string,
  patch: Partial<Pick<AgentPrompt, 'system' | 'user' | 'name' | 'description'>>,
): Promise<AgentPrompt> {
  const response = await client.put<AgentPrompt>(`/api/agent/prompts/${key}`, patch)
  return response.data
}

export async function resetAgentPrompt(key: string): Promise<AgentPrompt> {
  const response = await client.post<AgentPrompt>(`/api/agent/prompts/${key}/reset`)
  return response.data
}

// ── App Config ────────────────────────────────────────────────────────────────

export interface AppConfig {
  lims_system: string | null
  document_types: string[]
  enabled_sheets: string[]
  ai: {
    temperature: number
    max_tokens: number
    chunk_size: number
    chunk_overlap: number
  }
  confidence_threshold: number
  export_format: string
  load_sheet_templates: {
    LabWare: string
    LabVantage: string
    Veeva: string
  }
}

export async function getConfig(): Promise<AppConfig> {
  const response = await client.get<AppConfig>('/api/config')
  return response.data
}

export async function updateConfig(patch: Partial<AppConfig>): Promise<AppConfig> {
  const response = await client.put<AppConfig>('/api/config', patch)
  return response.data
}

export async function resetConfig(): Promise<AppConfig> {
  const response = await client.post<AppConfig>('/api/config/reset')
  return response.data
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

// ── RAG Knowledge Base ─────────────────────────────────────────────────────────

export interface RAGStats {
  total_embeddings: number
  training_embeddings: number
  correction_embeddings: number
  correction_examples: number
}

export interface CorrectionRecord {
  id: number
  job_id: string
  document_type: string | null
  sheet_name: string
  field_name: string
  original_value: string | null
  corrected_value: string | null
  context_text: string | null
  created_at: string
}

export async function getRagStats(): Promise<RAGStats> {
  const response = await client.get<RAGStats>('/api/rag/stats')
  return response.data
}

export async function listCorrections(
  limit = 50,
  offset = 0,
  sheetName?: string,
  documentType?: string,
): Promise<{ total: number; corrections: CorrectionRecord[] }> {
  const params: Record<string, string | number> = { limit, offset }
  if (sheetName) params.sheet_name = sheetName
  if (documentType) params.document_type = documentType
  const response = await client.get<{ total: number; corrections: CorrectionRecord[] }>(
    '/api/rag/corrections',
    { params },
  )
  return response.data
}

export async function deleteCorrection(id: number): Promise<void> {
  await client.delete(`/api/rag/corrections/${id}`)
}

export async function clearEmbeddings(sourceType?: 'training' | 'correction'): Promise<{ deleted_embeddings: number }> {
  const params = sourceType ? { source_type: sourceType } : {}
  const response = await client.delete<{ deleted_embeddings: number }>('/api/rag/embeddings', { params })
  return response.data
}

import { apiClient } from './client'
import type { PaginatedCases, Case } from './types'

export interface CaseFilters {
  page?: number
  size?: number
  type?: string
  status?: string
  root_cause?: string
  min_amount?: number
  max_amount?: number
  search?: string
}

export const casesApi = {
  list: (filters: CaseFilters = {}) =>
    apiClient.get<PaginatedCases>('/cases', { params: filters }).then(r => r.data),

  get: (id: string) =>
    apiClient.get<Case>(`/cases/${id}`).then(r => r.data),

  approve: (id: string) =>
    apiClient.post(`/cases/${id}/approve`).then(r => r.data),

  reject: (id: string) =>
    apiClient.post(`/cases/${id}/reject`).then(r => r.data),

  escalate: (id: string) =>
    apiClient.post(`/cases/${id}/escalate`).then(r => r.data),
}

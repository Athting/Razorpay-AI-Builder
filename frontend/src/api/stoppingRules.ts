import { apiClient } from './client'
import type { StoppingRule } from './types'

export const stoppingRulesApi = {
  list: () => apiClient.get<StoppingRule[]>('/stopping-rules').then(r => r.data),
  create: (data: Omit<StoppingRule, 'id' | 'created_at' | 'updated_at'>) =>
    apiClient.post<StoppingRule>('/stopping-rules', data).then(r => r.data),
  update: (id: string, data: Omit<StoppingRule, 'id' | 'created_at' | 'updated_at'>) =>
    apiClient.put<StoppingRule>(`/stopping-rules/${id}`, data).then(r => r.data),
  delete: (id: string) =>
    apiClient.delete(`/stopping-rules/${id}`).then(r => r.data),
}

export const customersApi = {
  list: (params?: { search?: string; dnd_only?: boolean }) =>
    apiClient.get('/customers', { params }).then(r => r.data),
  optOut: (id: string) => apiClient.post(`/customers/${id}/opt-out`).then(r => r.data),
  optIn: (id: string) => apiClient.post(`/customers/${id}/opt-in`).then(r => r.data),
}

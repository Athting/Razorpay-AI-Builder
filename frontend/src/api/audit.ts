import { apiClient } from './client'
import type { AuditLogEntry, AuditVerifyResult } from './types'

export const auditApi = {
  getTrail: (caseId: string) =>
    apiClient.get<AuditLogEntry[]>(`/audit/${caseId}`).then(r => r.data),

  verify: (caseId: string) =>
    apiClient.get<AuditVerifyResult>(`/audit/${caseId}/verify`).then(r => r.data),

  exportCsv: (caseId: string) =>
    `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/audit/${caseId}/export`,
}

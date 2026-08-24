import { apiClient } from './client'
import type { MetricsOverview, FunnelStage, TrendPoint } from './types'

export const metricsApi = {
  overview: () => apiClient.get<MetricsOverview>('/metrics/overview').then(r => r.data),
  funnel: () => apiClient.get<FunnelStage[]>('/metrics/funnel').then(r => r.data),
  trend: (days = 30) => apiClient.get<TrendPoint[]>('/metrics/trend', { params: { days } }).then(r => r.data),
  rootCauses: () => apiClient.get('/metrics/root-causes').then(r => r.data),
}

export const replayApi = {
  start: (speedMultiplier = 10) =>
    apiClient.post('/replay/start', null, { params: { speed_multiplier: speedMultiplier } }).then(r => r.data),
  status: (jobId: string) =>
    apiClient.get(`/replay/status/${jobId}`).then(r => r.data),
  seed: () => apiClient.post('/seed').then(r => r.data),
}

import { apiClient } from './client'

export interface Organization {
  id: string
  name: string
  slug: string
  webhook_path: string
  razorpay_connected: boolean
  notification_config: { email_recipients?: string[]; slack_webhook_url?: string; escalation_alerts?: boolean }
}

export const organizationApi = {
  list: () => apiClient.get<Organization[]>('/organizations').then(r => r.data),
  current: () => apiClient.get<Organization>('/organizations/current').then(r => r.data),
  create: (name: string) => apiClient.post<Organization>('/organizations', { name }).then(r => r.data),
  configureRazorpay: (data: { key_id: string; key_secret: string; webhook_secret: string }) =>
    apiClient.put('/organizations/current/razorpay', data).then(r => r.data),
  configureNotifications: (data: { email_recipients: string[]; slack_webhook_url?: string; escalation_alerts: boolean }) =>
    apiClient.put('/organizations/current/notifications', data).then(r => r.data),
  configureCommunications: (data: Record<string, string>) =>
    apiClient.put('/organizations/current/communications', data).then(r => r.data),
  connectRazorpay: () => apiClient.get<{ url: string }>('/organizations/current/razorpay/connect').then(r => r.data),
}

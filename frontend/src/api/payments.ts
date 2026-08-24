import { apiClient } from './client'
export const paymentsApi = {
  createLink: (data: { amount_paise: number; customer_name: string; customer_email?: string; customer_phone?: string; description?: string }) => apiClient.post('/payments/payment-links', data).then(r => r.data),
}

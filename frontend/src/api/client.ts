import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

// Attach JWT token from localStorage to every request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  const organizationId = localStorage.getItem('active_organization_id')
  if (organizationId) config.headers['X-Organization-ID'] = organizationId
  return config
})

// On 401, clear token and redirect to login
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const requestUrl = error.config?.url || ''
    // Failed sign-in attempts should be handled by the login form, not by a
    // forced navigation. For expired app sessions, clear both persisted token
    // and persisted user so protected routes cannot redirect in a loop.
    if (error.response?.status === 401 && !requestUrl.startsWith('/auth/')) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('auth-storage')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

import axios, { AxiosError } from 'axios'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token')
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error: AxiosError<{ detail: string }>) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.clear()
      window.location.href = '/auth/login'
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  register: (data: any) => api.post('/auth/register', data),
  login: (data: any) => api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
}

export const projectsApi = {
  create: (data: any) => api.post('/projects/create', data),
  get: (id: string) => api.get(`/projects/${id}`),
  list: () => api.get('/projects/'),
  assign: (id: string, freelancerId: string) =>
    api.post(`/projects/${id}/assign`, { freelancer_id: freelancerId }),
  update: (id: string, data: any) => api.patch(`/projects/${id}`, data),
  cancel: (id: string) => api.patch(`/projects/${id}/cancel`),
  delete: (id: string) => api.delete(`/projects/${id}`),
  apply: (id: string, data: any) => api.post(`/projects/${id}/apply`, data),
  getApplications: (id: string) => api.get(`/projects/${id}/applications`),
  reviewApplication: (projectId: string, appId: string, data: any) =>
    api.post(`/projects/${projectId}/applications/${appId}/review`, data),
  withdrawApplication: (id: string) => api.delete(`/projects/${id}/apply`),
  getMessages: (id: string) => api.get(`/projects/${id}/messages`),
  sendMessage: (id: string, content: string) => api.post(`/projects/${id}/messages`, { content }),
  assignMilestoneFreelancer: (projectId: string, milestoneId: string, freelancerId: string) =>
    api.post(`/projects/${projectId}/milestones/${milestoneId}/assign-freelancer`, { freelancer_id: freelancerId }),
}

export const milestonesApi = {
  submit: (data: any) => api.post('/milestones/submit', data),
  evaluate: (data: any) => api.post('/milestones/evaluate', data),
  getSubmissions: (milestoneId: string) => api.get(`/milestones/${milestoneId}/submissions`),
  raiseDispute: (data: any) => api.post('/milestones/dispute', data),
}

export const paymentsApi = {
  deposit: (data: any) => api.post('/payments/deposit', data),
  release: (milestoneId: string) => api.post('/payments/release', { milestone_id: milestoneId }),
  getEscrow: (projectId: string) => api.get(`/payments/escrow/${projectId}`),
  getTransactions: (projectId: string) => api.get(`/payments/transactions/${projectId}`),
}

export const reputationApi = {
  get: (freelancerId: string) => api.get(`/reputation/${freelancerId}`),
  me: () => api.get('/reputation/me/score'),
}

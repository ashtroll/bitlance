import axios from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth
export const authApi = {
  register: (data: any) => api.post('/auth/register', data),
  login: (data: any) => api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
};

// Projects
export const projectsApi = {
  create: (data: any) => api.post('/projects/create', data),
  get: (id: string) => api.get(`/projects/${id}`),
  list: () => api.get('/projects/'),
  assign: (id: string, freelancerId: string) =>
    api.post(`/projects/${id}/assign`, { freelancer_id: freelancerId }),
};

// Milestones
export const milestonesApi = {
  submit: (data: any) => api.post('/milestones/submit', data),
  evaluate: (data: any) => api.post('/milestones/evaluate', data),
};

// Payments
export const paymentsApi = {
  deposit: (data: any) => api.post('/payments/deposit', data),
  release: (milestoneId: string) => api.post('/payments/release', { milestone_id: milestoneId }),
  getEscrow: (projectId: string) => api.get(`/payments/escrow/${projectId}`),
  getTransactions: (projectId: string) => api.get(`/payments/transactions/${projectId}`),
};

// Reputation
export const reputationApi = {
  get: (freelancerId: string) => api.get(`/reputation/${freelancerId}`),
  me: () => api.get('/reputation/me/score'),
};

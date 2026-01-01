import axios from 'axios';

// API base URL - configurable via environment variable
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  getMe: () => api.get('/auth/me'),
  refreshToken: () => api.post('/auth/refresh'),
};

// Alliance API
export const allianceAPI = {
  list: () => api.get('/alliances'),
  get: (id) => api.get(`/alliances/${id}`),
  create: (data) => api.post('/alliances', data),
  join: (inviteCode) => api.post('/alliances/join', { invite_code: inviteCode }),
  leave: (id) => api.post(`/alliances/${id}/leave`),
  regenerateInvite: (id) => api.post(`/alliances/${id}/regenerate-invite`),
};

// Dashboard API
export const dashboardAPI = {
  getMyGames: () => api.get('/dashboard/my-games'),
  getMyStats: (gameId) => api.get(`/dashboard/my-stats/${gameId}`),
  getAllianceGames: (allianceId) => api.get(`/dashboard/alliance/${allianceId}/games`),
};

// Health check
export const healthCheck = () => api.get('/health');

export default api;

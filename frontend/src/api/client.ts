import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests if available
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// API endpoints
export const api = {
  // Authentication
  login: () => apiClient.get('/api/v1/user/login'),
  
  // User history
  getHistory: () => apiClient.get('/api/v1/user/history'),
  deleteAnalysis: (analysisId: string) => apiClient.delete(`/api/v1/user/history/${analysisId}`),
  
  // Results
  getResults: (analysisId: string) => apiClient.get(`/api/v1/results/${analysisId}`),
  exportResults: (analysisId: string, format: 'pdf' | 'docx' | 'xlsx') => 
    apiClient.get(`/api/v1/results/${analysisId}/export?format=${format}`, {
      responseType: 'blob'
    }),
  
  // File upload
  uploadFiles: (formData: FormData) => 
    apiClient.post('/api/v1/analysis/unified', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }),
};

export default apiClient;

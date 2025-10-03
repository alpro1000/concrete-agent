import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests if available
// Also handle FormData to let axios set the correct Content-Type with boundary
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  // If the data is FormData, remove the Content-Type header
  // so axios can set it automatically with the correct boundary
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type'];
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
    apiClient.post('/api/v1/analysis/unified', formData),
};

export default apiClient;

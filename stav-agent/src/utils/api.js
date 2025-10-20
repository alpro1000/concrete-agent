import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://concrete-agent.onrender.com';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Projects
export const getProjects = () => apiClient.get('/api/projects');
export const getProject = (projectId) => apiClient.get(`/api/projects/${projectId}`);
export const createProject = (name) => apiClient.post('/api/projects', { name });

// Upload
export const uploadFiles = (projectId, files) => {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  return apiClient.post(`/api/upload?project_id=${projectId}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

// Chat
export const sendChatMessage = (projectId, message) =>
  apiClient.post('/api/chat/message', {
    project_id: projectId,
    message,
    include_history: true,
  });

// Actions (buttons)
export const triggerAction = (projectId, action, positionId = null) =>
  apiClient.post('/api/chat/action', {
    project_id: projectId,
    action,
    position_id: positionId,
  });

// Results
export const getProjectResults = (projectId) =>
  apiClient.get(`/api/projects/${projectId}/results`);
export const getProjectStatus = (projectId) =>
  apiClient.get(`/api/projects/${projectId}/status`);

export default apiClient;

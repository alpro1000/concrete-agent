import axios from 'axios';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  'https://concrete-agent.onrender.com';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Projects
export const getProjects = () =>
  apiClient.get('/api/projects').catch(() => ({ data: { projects: [] } }));

export const getProject = (projectId) =>
  apiClient.get(`/api/projects/${projectId}`);

export const createProject = (name) =>
  apiClient.post('/api/projects', { name });

// Upload
export const uploadFiles = (projectId, files, onProgress) => {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  return apiClient.post(`/api/upload?project_id=${projectId}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (event) => {
      if (!onProgress || !event.total) return;
      const percent = Math.round((event.loaded * 100) / event.total);
      onProgress(percent);
    },
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
export const triggerAction = ({
  projectId,
  action,
  options = undefined,
  positionId = undefined,
  freeFormQuery = undefined,
}) => {
  const payload = {
    project_id: projectId,
    action,
  };

  if (options) {
    payload.options = options;
  }

  if (positionId) {
    payload.position_id = positionId;
  }

  if (freeFormQuery) {
    payload.free_form_query = freeFormQuery;
  }

  return apiClient.post('/api/chat/action', payload);
};

// Results
export const getProjectResults = (projectId) =>
  apiClient.get(`/api/projects/${projectId}/results`);

export const getProjectStatus = (projectId) =>
  apiClient.get(`/api/projects/${projectId}/status`);

export const getProjectFiles = (projectId) =>
  apiClient.get(`/api/projects/${projectId}/files`);

export default apiClient;

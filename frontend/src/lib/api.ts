// Unified API base for Vite
export const API_BASE =
  import.meta.env.VITE_API_URL || 
  'http://localhost:8000';

if (!API_BASE) {
  throw new Error('VITE_API_URL not configured');
}

// Generic fetch wrapper
export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;
  
  // Get token from localStorage
  const token = localStorage.getItem('auth_token');
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };
  
  // Add authorization header if token exists
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  
  // Don't set Content-Type for FormData - browser will set it with boundary
  if (!(options.body instanceof FormData)) {
    headers['Accept'] = 'application/json';
  }

  const res = await fetch(url, { ...options, headers });
  
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Request failed with ${res.status}`);
  }
  
  // Check if response is JSON
  const contentType = res.headers.get('content-type');
  if (contentType?.includes('application/json')) {
    return res.json() as Promise<T>;
  }
  
  // Return blob for file downloads
  return res.blob() as Promise<T>;
}

// Upload files endpoint
export async function uploadFiles(formData: FormData) {
  return apiFetch('/api/v1/analysis/unified', {
    method: 'POST',
    body: formData
  });
}

// Get results
export async function getResults(analysisId: string) {
  return apiFetch(`/api/v1/results/${analysisId}`);
}

// Get user history
export async function getHistory() {
  return apiFetch('/api/v1/user/history');
}

// Delete analysis
export async function deleteAnalysis(analysisId: string) {
  return apiFetch(`/api/v1/user/history/${analysisId}`, {
    method: 'DELETE'
  });
}

// Export results
export async function exportResults(analysisId: string, format: 'pdf' | 'docx' | 'xlsx') {
  return apiFetch(`/api/v1/results/${analysisId}/export?format=${format}`);
}

// Login
export async function login() {
  return apiFetch('/api/v1/user/login');
}


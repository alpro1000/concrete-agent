import axios from 'axios';
import type { AxiosInstance, AxiosResponse } from 'axios';
import type {
  ApiResponse,
  ConcreteAnalysisResult,
  MaterialAnalysisResult,
  ComparisonResult,
  HealthStatus,
  ServiceInfo,
  DetailedStatus,
  FileUpload,
  Language,
  TZDAnalysisResult,
  TZDHealthStatus,
} from '../types/api';

class ApiClient {
  private client: AxiosInstance;

  constructor(baseURL: string = 'http://localhost:8000') {
    this.client = axios.create({
      baseURL,
      timeout: 300000, // 5 minutes for long-running analysis
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    // Add request interceptor for logging
    this.client.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('API Request Error:', error);
        return Promise.reject(error);
      }
    );

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => {
        console.log(`API Response: ${response.status} ${response.config.url}`);
        return response;
      },
      (error) => {
        console.error('API Response Error:', error);
        
        // Enhanced error handling for better user experience
        if (error.response) {
          // Server responded with error status
          const { status, data } = error.response;
          
          if (status === 500 && data?.error) {
            // Check if it's an LLM service unavailable error
            if (data.error.includes('API недоступен') || data.error.includes('API key')) {
              error.message = 'LLM service is not configured. Please check API keys in server configuration.';
              error.user_friendly = true;
            } else {
              error.message = data.message || data.error || 'Internal server error';
            }
          } else if (status === 400) {
            error.message = data?.detail || data?.message || 'Bad request';
          } else if (status === 404) {
            error.message = 'Service endpoint not found';
          } else if (status >= 500) {
            error.message = 'Server error occurred. Please try again later.';
          }
        } else if (error.request) {
          // Network error
          error.message = 'Network error - unable to connect to server. Please check if the server is running.';
          error.user_friendly = true;
        } else {
          // Request setup error
          error.message = 'Request configuration error';
        }
        
        return Promise.reject(error);
      }
    );
  }

  // Utility method to create FormData
  private createFormData(data: Record<string, any>): FormData {
    const formData = new FormData();
    
    Object.entries(data).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (Array.isArray(value)) {
          // Handle file arrays
          value.forEach((item) => {
            formData.append(key, item);
          });
        } else {
          formData.append(key, value);
        }
      }
    });
    
    return formData;
  }

  // Health and status endpoints
  async getHealth(): Promise<HealthStatus> {
    const response: AxiosResponse<HealthStatus> = await this.client.get('/health');
    return response.data;
  }

  async getServiceInfo(): Promise<ServiceInfo> {
    const response: AxiosResponse<ServiceInfo> = await this.client.get('/');
    return response.data;
  }

  async getDetailedStatus(): Promise<DetailedStatus> {
    const response: AxiosResponse<DetailedStatus> = await this.client.get('/status');
    return response.data;
  }

  // File upload
  async uploadFiles(files: File[]): Promise<ApiResponse<{ uploaded: FileUpload[] }>> {
    const formData = this.createFormData({ files });
    
    const response: AxiosResponse<ApiResponse<{ uploaded: FileUpload[] }>> = 
      await this.client.post('/upload/files', formData);
    
    return response.data;
  }

  // Specialized upload endpoints
  async uploadDocs(
    files: File[],
    options?: {
      project_name?: string;
      auto_analyze?: boolean;
      language?: Language;
    }
  ): Promise<ApiResponse<any>> {
    const formData = this.createFormData({
      files,
      project_name: options?.project_name ?? 'Untitled Project',
      auto_analyze: options?.auto_analyze ?? true,
      language: options?.language ?? 'cz',
    });
    
    const response: AxiosResponse<ApiResponse<any>> = 
      await this.client.post('/upload/docs', formData);
    
    return response.data;
  }

  async uploadSmeta(
    files: File[],
    options?: {
      project_name?: string;
      estimate_type?: string;
      auto_analyze?: boolean;
      language?: Language;
    }
  ): Promise<ApiResponse<any>> {
    const formData = this.createFormData({
      files,
      project_name: options?.project_name ?? 'Untitled Project',
      estimate_type: options?.estimate_type ?? 'general',
      auto_analyze: options?.auto_analyze ?? true,
      language: options?.language ?? 'cz',
    });
    
    const response: AxiosResponse<ApiResponse<any>> = 
      await this.client.post('/upload/smeta', formData);
    
    return response.data;
  }

  async uploadDrawings(
    files: File[],
    options?: {
      project_name?: string;
      drawing_type?: string;
      scale?: string;
      auto_analyze?: boolean;
      extract_volumes?: boolean;
      language?: Language;
    }
  ): Promise<ApiResponse<any>> {
    const formData = this.createFormData({
      files,
      project_name: options?.project_name ?? 'Untitled Project',
      drawing_type: options?.drawing_type ?? 'general',
      scale: options?.scale,
      auto_analyze: options?.auto_analyze ?? true,
      extract_volumes: options?.extract_volumes ?? true,
      language: options?.language ?? 'cz',
    });
    
    const response: AxiosResponse<ApiResponse<any>> = 
      await this.client.post('/upload/drawings', formData);
    
    return response.data;
  }

  // Analysis endpoints
  async analyzeConcrete(
    docs: File[],
    smeta: File,
    options?: {
      use_claude?: boolean;
      claude_mode?: string;
      language?: Language;
    }
  ): Promise<ConcreteAnalysisResult> {
    const formData = this.createFormData({
      docs,
      smeta,
      use_claude: options?.use_claude ?? true,
      claude_mode: options?.claude_mode ?? 'enhancement',
      language: options?.language ?? 'cz',
    });

    const response: AxiosResponse<ConcreteAnalysisResult> = 
      await this.client.post('/analyze/concrete', formData);
    
    return response.data;
  }

  async analyzeMaterials(
    docs: File[],
    options?: {
      smeta?: File;
      material_query?: string;
      use_claude?: boolean;
      claude_mode?: string;
      language?: Language;
      include_drawing_analysis?: boolean;
    }
  ): Promise<MaterialAnalysisResult> {
    const formData = this.createFormData({
      docs,
      smeta: options?.smeta,
      material_query: options?.material_query,
      use_claude: options?.use_claude ?? true,
      claude_mode: options?.claude_mode ?? 'enhancement',
      language: options?.language ?? 'cz',
      include_drawing_analysis: options?.include_drawing_analysis ?? false,
    });

    const response: AxiosResponse<MaterialAnalysisResult> = 
      await this.client.post('/analyze/materials', formData);
    
    return response.data;
  }

  async analyzeTOV(
    docs: File[],
    options?: {
      smeta?: File;
      project_name?: string;
      project_duration_days?: number;
      use_claude?: boolean;
      claude_mode?: string;
      language?: Language;
      export_format?: string;
    }
  ): Promise<any> {
    const formData = this.createFormData({
      docs,
      smeta: options?.smeta,
      project_name: options?.project_name ?? 'TOV Analysis Project',
      project_duration_days: options?.project_duration_days,
      use_claude: options?.use_claude ?? true,
      claude_mode: options?.claude_mode ?? 'enhancement',
      language: options?.language ?? 'cz',
      export_format: options?.export_format ?? 'json',
    });

    const response: AxiosResponse<any> = 
      await this.client.post('/analyze/tov', formData);
    
    return response.data;
  }

  // Comparison endpoints
  async compareDocs(oldDocs: File[], newDocs: File[]): Promise<ComparisonResult> {
    const formData = this.createFormData({
      old_docs: oldDocs,
      new_docs: newDocs,
    });

    const response: AxiosResponse<ComparisonResult> = 
      await this.client.post('/compare/docs', formData);
    
    return response.data;
  }

  async compareSmeta(oldSmeta: File, newSmeta: File): Promise<ComparisonResult> {
    const formData = this.createFormData({
      old_smeta: oldSmeta,
      new_smeta: newSmeta,
    });

    const response: AxiosResponse<ComparisonResult> = 
      await this.client.post('/compare/smeta', formData);
    
    return response.data;
  }

  // Test endpoint
  async testEcho(data: Record<string, any>): Promise<any> {
    const response = await this.client.post('/test/echo', data, {
      headers: {
        'Content-Type': 'application/json',
      },
    });
    return response.data;
  }
}

// Create singleton instance
const apiClient = new ApiClient();

export default apiClient;
export { ApiClient };
export interface User {
  id: number;
  name: string;
  email: string;
  language: string;
  created_at: string;
}

export interface Analysis {
  id: string;
  filename: string;
  status: 'completed' | 'processing' | 'failed';
  uploaded_at: string;
  result_url?: string;
}

export interface AnalysisResult {
  summary: any;
  agents: any[];
  resources: any;
}

export interface FileUploadResult {
  name: string;
  type: string;
  category: 'technical' | 'quantities' | 'drawings';
  success: boolean;
  error?: string | null;
}

export interface AnalysisResponse {
  analysis_id: string;
  status: 'success' | 'error' | 'partial' | 'processing';
  files: FileUploadResult[];
  summary: {
    total: number;
    successful: number;
    failed: number;
  };
}

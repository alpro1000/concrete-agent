// TypeScript interfaces for API responses

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface FileUpload {
  filename: string;
  path: string;
}

export interface AnalysisRequest {
  docs: File[];
  smeta?: File;
  material_query?: string;
  use_claude?: boolean;
  claude_mode?: string;
  language?: string;
  include_drawing_analysis?: boolean;
}

export interface ConcreteMatch {
  grade: string;
  context: string;
  location: string;
  confidence: number;
  method: string;
  coordinates?: [number, number, number, number];
}

export interface StructuralElement {
  name: string;
  concrete_grade?: string;
  location: string;
  context: string;
}

export interface ConcreteAnalysisResult {
  success: boolean;
  analysis_method: string;
  concrete_summary: ConcreteMatch[];
  structural_elements?: StructuralElement[];
  volume_entries_found?: number;
  processing_time?: number;
  error?: string;
}

export interface MaterialMatch {
  material: string;
  quantity?: string;
  unit?: string;
  context: string;
  location: string;
  confidence: number;
}

export interface MaterialAnalysisResult {
  success: boolean;
  materials_found: MaterialMatch[];
  query_results?: MaterialMatch[];
  processing_time?: number;
  error?: string;
}

export interface DocumentComparison {
  old_version: string;
  new_version: string;
  changes: Array<{
    type: 'added' | 'removed' | 'modified';
    content: string;
    location?: string;
  }>;
  summary: string;
}

export interface ComparisonResult {
  success: boolean;
  comparison: DocumentComparison;
  processing_time?: number;
  error?: string;
}

export interface VolumeEntry {
  item: string;
  quantity: number;
  unit: string;
  location?: string;
  category?: string;
}

export interface VolumeAnalysisResult {
  success: boolean;
  volume_entries: VolumeEntry[];
  total_items: number;
  processing_time?: number;
  error?: string;
}

export interface HealthStatus {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  uptime: string;
}

export interface ServiceInfo {
  service: string;
  version: string;
  status: string;
  claude_status: string;
  environment: string;
  endpoints: Record<string, string>;
  dependencies: Record<string, boolean>;
}

export interface DetailedStatus {
  api_status: string;
  dependencies: Record<string, boolean>;
  claude_available: boolean;
  directories: Record<string, boolean>;
  python_path: string[];
  environment_vars: Record<string, string>;
}

export type Language = 'cs' | 'en' | 'ru';

export interface LanguageOption {
  code: Language;
  name: string;
  flag: string;
}
// src/types/index.ts
// TypeScript typy pro ConcreteAgent frontend

// Základní typy pro analýzu betonu
export interface ConcreteGrade {
  grade: string;
  exposure_classes: string[];
  context: string;
  location: string;
  confidence: number;
  source_document: string;
  line_number: number;
}

export interface ConcreteAnalysisResult {
  success: boolean;
  total_grades: number;
  grades: ConcreteGrade[];
  summary: {
    unique_grades: string[];
    locations: string[];
    total_confidence: number;
  };
}

// Typy pro analýzu objemů
export interface VolumeEntry {
  concrete_grade: string;
  volume_m3?: number;
  area_m2?: number;
  construction_element: string;
  cost?: number;
  confidence: number;
  source_document: string;
  line_number: number;
}

export interface VolumeAnalysisResult {
  success: boolean;
  total_volume_m3: number;
  total_cost: number;
  volumes: VolumeEntry[];
  summary: {
    by_grade: Record<string, number>;
    by_element: Record<string, number>;
  };
}

// Typy pro analýzu materiálů
export interface MaterialItem {
  material_type: string;
  material_name: string;
  specification: string;
  quantity?: number;
  unit: string;
  context: string;
  source_document: string;
  line_number: number;
  confidence: number;
}

export interface MaterialCategory {
  category_name: string;
  total_items: number;
  items: MaterialItem[];
  total_quantity: number;
  main_specifications: string[];
}

export interface MaterialAnalysisResult {
  success: boolean;
  total_materials: number;
  materials: MaterialItem[];
  categories: MaterialCategory[];
  summary: {
    by_type: Record<string, number>;
    by_specification: Record<string, number>;
  };
}

// Typy pro analýzu výkresů (budoucí rozšíření)
export interface DrawingElement {
  element_type: string;
  geometry: string;
  volume?: number;
  area?: number;
  source: string;
}

export interface DrawingAnalysisResult {
  success: boolean;
  elements: DrawingElement[];
  total_elements: number;
}

// Hlavní typ pro kompletní analýzu
export interface AnalysisResult {
  success: boolean;
  error_message?: string;
  concrete_analysis: ConcreteAnalysisResult;
  volume_analysis: VolumeAnalysisResult;
  material_analysis: MaterialAnalysisResult;
  drawing_analysis?: DrawingAnalysisResult;
  sources: string[];
  analysis_status: Record<string, string>;
  request_parameters: {
    material_query?: string;
    use_claude: boolean;
    claude_mode: string;
    language: string;
    documents_count: number;
    smeta_provided: boolean;
    include_drawing_analysis: boolean;
  };
}

// Typy pro API requesty
export interface AnalysisRequest {
  docs: File[];
  smeta?: File;
  material_query?: string;
  use_claude: boolean;
  claude_mode: string;
  language: string;
  include_drawing_analysis: boolean;
}

// UI stavy
export interface AppState {
  loading: boolean;
  error: string | null;
  result: AnalysisResult | null;
  language: 'cs' | 'en' | 'ru';
}

// Exportní formáty
export type ExportFormat = 'excel' | 'pdf' | 'json' | 'markdown';

// Stavy chyb
export interface ErrorState {
  type: 'network' | 'validation' | 'server' | 'unknown';
  message: string;
  details?: string;
}
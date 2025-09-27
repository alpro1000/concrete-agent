// src/services/api.ts
// API služby pro komunikaci s backend

import axios, { AxiosResponse } from 'axios';
import { AnalysisRequest, AnalysisResult } from '../types';

// Konfigurace API
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minut pro dlouhé analýzy
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

// Interceptor pro response
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    
    if (error.response) {
      // Server responded with error status
      const message = error.response.data?.error_message || 
                     error.response.data?.detail || 
                     'Server error';
      throw new Error(`Server error (${error.response.status}): ${message}`);
    } else if (error.request) {
      // Request was made but no response received
      throw new Error('Network error - no response from server');
    } else {
      // Something else happened
      throw new Error(`Request error: ${error.message}`);
    }
  }
);

// Hlavní API funkce
export const analyzeDocuments = async (
  request: AnalysisRequest
): Promise<AnalysisResult> => {
  const formData = new FormData();

  // Přidání dokumentů
  request.docs.forEach((file) => {
    formData.append('docs', file);
  });

  // Přidání sméty (pokud je)
  if (request.smeta) {
    formData.append('smeta', request.smeta);
  }

  // Přidání parametrů
  if (request.material_query) {
    formData.append('material_query', request.material_query);
  }
  
  formData.append('use_claude', request.use_claude.toString());
  formData.append('claude_mode', request.claude_mode);
  formData.append('language', request.language);
  formData.append('include_drawing_analysis', request.include_drawing_analysis.toString());

  try {
    const response: AxiosResponse<AnalysisResult> = await apiClient.post(
      '/analyze/materials',
      formData
    );

    return response.data;
  } catch (error) {
    console.error('Analysis API Error:', error);
    throw error;
  }
};

// Kontrola zdraví serveru
export const checkServerHealth = async (): Promise<boolean> => {
  try {
    const response = await apiClient.get('/health');
    return response.status === 200;
  } catch (error) {
    console.error('Health check failed:', error);
    return false;
  }
};

// Získání info o serveru
export const getServerInfo = async () => {
  try {
    const response = await apiClient.get('/');
    return response.data;
  } catch (error) {
    console.error('Server info failed:', error);
    throw error;
  }
};

// Export utility funkce
export const downloadReport = async (
  data: any, 
  format: 'json' | 'csv' | 'excel', 
  filename: string
) => {
  try {
    let blob: Blob;
    let mimeType: string;
    let fileExtension: string;

    switch (format) {
      case 'json':
        blob = new Blob([JSON.stringify(data, null, 2)], { 
          type: 'application/json' 
        });
        mimeType = 'application/json';
        fileExtension = '.json';
        break;
      
      case 'csv':
        // Jednoduchý CSV export pro tabulková data
        const csvContent = convertToCSV(data);
        blob = new Blob([csvContent], { type: 'text/csv' });
        mimeType = 'text/csv';
        fileExtension = '.csv';
        break;
      
      case 'excel':
        // Pro Excel bychom potřebovali knihovnu jako xlsx
        // Zatím fallback na CSV
        const excelContent = convertToCSV(data);
        blob = new Blob([excelContent], { type: 'text/csv' });
        mimeType = 'text/csv';
        fileExtension = '.csv';
        break;
      
      default:
        throw new Error('Unsupported format');
    }

    // Vytvoření a trigger download
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename + fileExtension;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

  } catch (error) {
    console.error('Download failed:', error);
    throw error;
  }
};

// Pomocná funkce pro konverzi na CSV
const convertToCSV = (data: any): string => {
  if (!data || typeof data !== 'object') {
    return '';
  }

  const lines: string[] = [];
  
  // Pokud máme array objektů, konvertujeme na CSV tabulku
  if (Array.isArray(data)) {
    if (data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    lines.push(headers.join(','));
    
    data.forEach(item => {
      const row = headers.map(header => {
        const value = item[header];
        // Escapujeme hodnoty s čárkami nebo uvozovkami
        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value || '';
      });
      lines.push(row.join(','));
    });
  } else {
    // Pro objekt vytvoříme key-value páry
    Object.entries(data).forEach(([key, value]) => {
      if (typeof value === 'object' && value !== null) {
        lines.push(`${key},${JSON.stringify(value)}`);
      } else {
        lines.push(`${key},${value}`);
      }
    });
  }

  return lines.join('\n');
};

// Copy to clipboard utility
export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    } else {
      // Fallback pro starší prohlížeče
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      const result = document.execCommand('copy');
      document.body.removeChild(textArea);
      return result;
    }
  } catch (error) {
    console.error('Copy to clipboard failed:', error);
    return false;
  }
};
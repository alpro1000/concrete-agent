import React, { useState } from 'react';
import {
  Typography,
  Button,
  message,
  Spin,
} from 'antd';
import { useTranslation } from 'react-i18next';
import ThreePanelUpload from '../components/ThreePanelUpload';
import ResultsPanel from '../components/ResultsPanel';
import apiClient from '../api/client';

const { Title, Paragraph } = Typography;

interface AnalysisResult {
  status: 'success' | 'error';
  message?: string;
  files: Array<{
    name: string;
    type: string;
    category?: string;
    success: boolean;
    error: string | null;
    result?: any;
  }>;
  summary: {
    total: number;
    successful: number;
    failed: number;
  };
  project_name?: string;
  language?: string;
  timestamp?: string;
}

const ProjectAnalysis: React.FC = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [technicalFiles, setTechnicalFiles] = useState<File[]>([]);
  const [quantitiesFiles, setQuantitiesFiles] = useState<File[]>([]);
  const [drawingsFiles, setDrawingsFiles] = useState<File[]>([]);

  const handleFilesChange = (technical: File[], quantities: File[], drawings: File[]) => {
    setTechnicalFiles(technical);
    setQuantitiesFiles(quantities);
    setDrawingsFiles(drawings);
  };

  const handleAnalyze = async () => {
    const totalFiles = technicalFiles.length + quantitiesFiles.length + drawingsFiles.length;
    
    if (totalFiles === 0) {
      message.warning(t('validation.fileRequired'));
      return;
    }

    setLoading(true);
    setAnalysisResult(null);

    try {
      const formData = new FormData();
      
      // Add files from each panel
      technicalFiles.forEach(file => {
        formData.append('technical_files', file);
      });
      quantitiesFiles.forEach(file => {
        formData.append('quantities_files', file);
      });
      drawingsFiles.forEach(file => {
        formData.append('drawings_files', file);
      });

      // Add metadata
      formData.append('ai_engine', 'auto');
      formData.append('language', localStorage.getItem('i18nextLng') || 'en');
      formData.append('project_name', 'Project Analysis');

      // Use the new unified analysis endpoint
      const response = await apiClient.post('/api/v1/analysis/unified', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 5 minutes
      });

      // Handle response with new format
      const data = response.data;
      setAnalysisResult(data);
      
      // Show appropriate message based on status code
      if (response.status === 200) {
        message.success(data.message || t('common.success'));
      } else if (response.status === 207) {
        message.warning(data.message || 'Partial success');
      } else if (data.status === 'error') {
        message.error(data.message || t('errors.analysisFailed'));
      }
    } catch (error: any) {
      console.error('Analysis error:', error);
      
      // Handle different error types
      if (error.response) {
        const { status, data } = error.response;
        if (status === 400) {
          message.error(data?.message || data?.detail || t('errors.validationError'));
        } else if (status === 500) {
          message.error(data?.message || t('errors.serverError'));
        } else {
          message.error(data?.message || t('errors.networkError'));
        }
      } else {
        message.error(t('errors.networkError') || 'Connection failed');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: '32px' }}>
        <Title level={2}>{t('home.title')}</Title>
        <Paragraph style={{ fontSize: '16px', color: '#8c8c8c' }}>
          {t('home.subtitle')}
        </Paragraph>
      </div>

      <ThreePanelUpload onFilesChange={handleFilesChange} />

      <div style={{ textAlign: 'center', marginTop: '32px' }}>
        <Button
          type="primary"
          size="large"
          loading={loading}
          onClick={handleAnalyze}
          disabled={technicalFiles.length === 0 && quantitiesFiles.length === 0 && drawingsFiles.length === 0}
          style={{ minWidth: '200px', height: '48px', fontSize: '16px' }}
        >
          {loading ? t('common.loading') : t('home.startAnalysis')}
        </Button>
      </div>

      {loading && (
        <div style={{ textAlign: 'center', marginTop: '32px' }}>
          <Spin size="large" />
          <Paragraph style={{ marginTop: '16px', color: '#8c8c8c' }}>
            {t('common.loading')}
          </Paragraph>
        </div>
      )}

      <ResultsPanel results={analysisResult} loading={loading} />
    </div>
  );
};

export default ProjectAnalysis;

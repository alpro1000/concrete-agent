import React, { useState } from 'react';
import {
  Typography,
  Button,
  Space,
  message,
  Card,
  Spin,
  Divider,
  Tabs
} from 'antd';
import {
  CheckCircleOutlined,
  FileTextOutlined,
  FileExcelOutlined,
  FilePdfOutlined,
  FileWordOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import ThreePanelUpload from '../components/ThreePanelUpload';
import apiClient from '../api/client';

const { Title, Paragraph, Text } = Typography;

interface AnalysisResult {
  success: boolean;
  project_summary?: string;
  technical_summary?: any;
  quantities_summary?: any;
  drawings_summary?: any;
  combined_results?: any;
  error_message?: string;
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

      // Make API call - for now, we'll use the TZD endpoint as a starting point
      // In production, you would create a new combined endpoint
      const response = await apiClient.post('/api/v1/tzd/analyze', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 5 minutes
      });

      if (response.data.success) {
        setAnalysisResult(response.data);
        message.success(t('common.success'));
      } else {
        message.error(response.data.error_message || t('errors.analysisFailed'));
      }
    } catch (error: any) {
      console.error('Analysis error:', error);
      message.error(error.response?.data?.detail || t('errors.networkError'));
    } finally {
      setLoading(false);
    }
  };

  const exportResults = (format: 'json' | 'pdf' | 'word' | 'excel') => {
    if (!analysisResult) return;

    try {
      if (format === 'json') {
        const dataStr = JSON.stringify(analysisResult, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
        const exportFileDefaultName = `analysis_${new Date().toISOString()}.json`;
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
        
        message.success(t('analysis.export.json'));
      } else {
        message.info(`${format.toUpperCase()} export coming soon!`);
      }
    } catch (error) {
      message.error(t('errors.unknownError'));
    }
  };

  const renderResults = () => {
    if (!analysisResult) return null;

    return (
      <Card style={{ marginTop: '24px' }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div style={{ textAlign: 'center' }}>
            <CheckCircleOutlined style={{ fontSize: '48px', color: '#52c41a' }} />
            <Title level={3} style={{ marginTop: '16px' }}>
              {t('analysis.title')}
            </Title>
          </div>

          <Divider />

          <Tabs
            defaultActiveKey="summary"
            items={[
              {
                key: 'summary',
                label: t('analysis.comparison.summary'),
                children: (
                  <Card>
                    <Paragraph>
                      {analysisResult.project_summary || 'Analysis completed successfully'}
                    </Paragraph>
                    {analysisResult.combined_results && (
                      <pre style={{ 
                        background: '#f5f5f5', 
                        padding: '16px', 
                        borderRadius: '4px',
                        overflow: 'auto'
                      }}>
                        {JSON.stringify(analysisResult.combined_results, null, 2)}
                      </pre>
                    )}
                  </Card>
                ),
              },
              {
                key: 'technical',
                label: t('home.panels.technical.title'),
                children: (
                  <Card>
                    <Text>Technical files analyzed: {technicalFiles.length}</Text>
                    {analysisResult.technical_summary && (
                      <pre style={{ 
                        background: '#f5f5f5', 
                        padding: '16px', 
                        borderRadius: '4px',
                        marginTop: '16px',
                        overflow: 'auto'
                      }}>
                        {JSON.stringify(analysisResult.technical_summary, null, 2)}
                      </pre>
                    )}
                  </Card>
                ),
              },
              {
                key: 'quantities',
                label: t('home.panels.quantities.title'),
                children: (
                  <Card>
                    <Text>Quantity files analyzed: {quantitiesFiles.length}</Text>
                    {analysisResult.quantities_summary && (
                      <pre style={{ 
                        background: '#f5f5f5', 
                        padding: '16px', 
                        borderRadius: '4px',
                        marginTop: '16px',
                        overflow: 'auto'
                      }}>
                        {JSON.stringify(analysisResult.quantities_summary, null, 2)}
                      </pre>
                    )}
                  </Card>
                ),
              },
              {
                key: 'drawings',
                label: t('home.panels.drawings.title'),
                children: (
                  <Card>
                    <Text>Drawing files analyzed: {drawingsFiles.length}</Text>
                    {analysisResult.drawings_summary && (
                      <pre style={{ 
                        background: '#f5f5f5', 
                        padding: '16px', 
                        borderRadius: '4px',
                        marginTop: '16px',
                        overflow: 'auto'
                      }}>
                        {JSON.stringify(analysisResult.drawings_summary, null, 2)}
                      </pre>
                    )}
                  </Card>
                ),
              },
            ]}
          />

          <Divider />

          <div style={{ textAlign: 'center' }}>
            <Space size="middle" wrap>
              <Button
                icon={<FileTextOutlined />}
                onClick={() => exportResults('json')}
              >
                {t('analysis.export.json')}
              </Button>
              <Button
                icon={<FilePdfOutlined />}
                onClick={() => exportResults('pdf')}
              >
                {t('analysis.export.pdf')}
              </Button>
              <Button
                icon={<FileWordOutlined />}
                onClick={() => exportResults('word')}
              >
                {t('analysis.export.word')}
              </Button>
              <Button
                icon={<FileExcelOutlined />}
                onClick={() => exportResults('excel')}
              >
                {t('analysis.export.excel')}
              </Button>
            </Space>
          </div>
        </Space>
      </Card>
    );
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

      {renderResults()}
    </div>
  );
};

export default ProjectAnalysis;

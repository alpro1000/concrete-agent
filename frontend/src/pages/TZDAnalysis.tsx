import React, { useState } from 'react';
import { 
  Row, 
  Col, 
  Typography, 
  Space, 
  message, 
  Spin,
  Card,
  Steps,
  Button,
  Alert
} from 'antd';
import { 
  UploadOutlined, 
  BarChartOutlined, 
  CheckCircleOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import TZDUpload from '../components/TZDUpload';
import TZDResults from '../components/TZDResults';
import apiClient from '../api/client';
import type { TZDAnalysisResult } from '../types/api';

const { Title, Paragraph } = Typography;

const TZDAnalysis: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [analysisResult, setAnalysisResult] = useState<TZDAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async (files: File[], engine: string, context?: string) => {
    setLoading(true);
    setError(null);
    setCurrentStep(1);

    try {
      const formData = new FormData();
      files.forEach(file => {
        formData.append('files', file);
      });
      formData.append('ai_engine', engine);
      if (context) {
        formData.append('project_context', context);
      }

      const response = await apiClient.post('/api/v1/tzd/analyze', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 5 minutes timeout for analysis
      });

      if (response.data.success) {
        setAnalysisResult(response.data);
        setCurrentStep(2);
        message.success('Анализ технического задания завершен успешно!');
      } else {
        throw new Error(response.data.error_message || 'Анализ не удался');
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Произошла ошибка при анализе';
      setError(errorMessage);
      message.error(`Ошибка анализа: ${errorMessage}`);
      setCurrentStep(0);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (format: 'json' | 'pdf') => {
    if (!analysisResult) return;

    try {
      if (format === 'json') {
        // Download as JSON
        const dataStr = JSON.stringify(analysisResult, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
        
        const exportFileDefaultName = `tzd_analysis_${analysisResult.analysis_id}.json`;
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
        
        message.success('JSON файл скачан');
      } else if (format === 'pdf') {
        // Request PDF generation from backend
        const response = await apiClient.get(`/api/v1/tzd/analysis/${analysisResult.analysis_id}/pdf`, {
          responseType: 'blob'
        });
        
        const blob = new Blob([response.data], { type: 'application/pdf' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `tzd_analysis_${analysisResult.analysis_id}.pdf`;
        link.click();
        window.URL.revokeObjectURL(url);
        
        message.success('PDF отчет скачан');
      }
    } catch (err: any) {
      message.error('Ошибка при скачивании файла');
      console.error('Download error:', err);
    }
  };

  const handleCopyJSON = () => {
    if (!analysisResult) return;
    
    const jsonString = JSON.stringify(analysisResult, null, 2);
    navigator.clipboard.writeText(jsonString).then(() => {
      message.success('JSON скопирован в буфер обмена');
    }).catch(() => {
      message.error('Ошибка копирования');
    });
  };

  const handleReset = () => {
    setCurrentStep(0);
    setAnalysisResult(null);
    setError(null);
  };

  const steps = [
    {
      title: 'Загрузка файлов',
      description: 'Выберите документы ТЗ для анализа',
      icon: <UploadOutlined />,
    },
    {
      title: 'Анализ документов',
      description: 'AI извлекает требования из документов',
      icon: <BarChartOutlined />,
    },
    {
      title: 'Результаты',
      description: 'Структурированные данные готовы',
      icon: <CheckCircleOutlined />,
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Header */}
        <Card>
          <Space direction="vertical">
            <Title level={2}>
              📋 TZD Reader - Анализ технических заданий
            </Title>
            <Paragraph type="secondary">
              Система автоматического извлечения требований из технических документов 
              с использованием AI через централизованный Orchestrator. Поддерживает 
              анализ PDF, DOCX и TXT файлов с соблюдением требований безопасности.
            </Paragraph>
          </Space>
        </Card>

        {/* Progress Steps */}
        <Card>
          <Steps current={currentStep} items={steps} />
        </Card>

        {/* Error Display */}
        {error && (
          <Alert
            message="Ошибка анализа"
            description={error}
            type="error"
            showIcon
            closable
            onClose={() => setError(null)}
            action={
              <Button size="small" onClick={handleReset}>
                Начать заново
              </Button>
            }
          />
        )}

        {/* Main Content */}
        <Row gutter={[24, 24]}>
          <Col span={24}>
            {currentStep === 0 && (
              <TZDUpload
                onAnalyze={handleAnalyze}
                loading={loading}
                disabled={loading}
              />
            )}

            {currentStep === 1 && (
              <Card>
                <div style={{ textAlign: 'center', padding: '60px 0' }}>
                  <Spin size="large" />
                  <div style={{ marginTop: '16px' }}>
                    <Title level={4}>Анализ документов...</Title>
                    <Paragraph type="secondary">
                      AI система обрабатывает ваши документы и извлекает ключевую информацию.
                      Это может занять несколько минут в зависимости от размера и сложности документов.
                    </Paragraph>
                  </div>
                </div>
              </Card>
            )}

            {currentStep === 2 && analysisResult && (
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <TZDResults
                  result={analysisResult}
                  onDownload={handleDownload}
                  onCopy={handleCopyJSON}
                />
                
                <Card>
                  <Space>
                    <Button 
                      icon={<ReloadOutlined />}
                      onClick={handleReset}
                    >
                      Анализировать новые документы
                    </Button>
                    <Button 
                      type="primary"
                      onClick={() => handleDownload('pdf')}
                    >
                      Скачать PDF отчет
                    </Button>
                  </Space>
                </Card>
              </Space>
            )}
          </Col>
        </Row>

        {/* Help Information */}
        <Card title="Справочная информация">
          <Row gutter={[16, 16]}>
            <Col span={8}>
              <Card size="small" title="Поддерживаемые форматы">
                <ul>
                  <li>PDF документы</li>
                  <li>Microsoft Word (.docx)</li>
                  <li>Текстовые файлы (.txt)</li>
                </ul>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" title="Извлекаемые данные">
                <ul>
                  <li>Объект строительства</li>
                  <li>Технические требования</li>
                  <li>Нормативные документы</li>
                  <li>Ограничения проекта</li>
                  <li>Условия эксплуатации</li>
                  <li>Функциональное назначение</li>
                </ul>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" title="Безопасность">
                <ul>
                  <li>Максимум 10MB на файл</li>
                  <li>До 5 файлов одновременно</li>
                  <li>Защита от path traversal</li>
                  <li>Проверка расширений файлов</li>
                </ul>
              </Card>
            </Col>
          </Row>
        </Card>
      </Space>
    </div>
  );
};

export default TZDAnalysis;
import React, { useState } from 'react';
import { 
  Row, 
  Col, 
  Typography, 
  Space, 
  message, 
  Spin,
  Card,
  Tabs,
  Divider,
  Tag,
  List
} from 'antd';
import { 
  CheckCircleOutlined,
  GlobalOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import TZDUploadSimple from '../components/TZDUploadSimple';
import apiClient from '../api/client';

const { Title, Paragraph, Text } = Typography;

interface TZDAnalysisResult {
  success: boolean;
  analysis_id: string;
  timestamp: string;
  project_object: string;
  requirements: string[];
  norms: string[];
  constraints: string[];
  environment: string;
  functions: string[];
  processing_metadata: any;
  error_message?: string;
}

// Helper function to normalize diacritics
const normalizeDiacritics = (text: string): string => {
  if (!text) return text;
  return text.normalize('NFC');
};

const TZDAnalysis: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<TZDAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [translations, setTranslations] = useState<{
    ru: string;
    cs: string;
    en: string;
  } | null>(null);

  const handleAnalyze = async (files: File[], engine: string) => {
    setLoading(true);
    setError(null);
    setAnalysisResult(null);
    setTranslations(null);

    try {
      const formData = new FormData();
      files.forEach(file => {
        formData.append('files', file);
      });
      formData.append('ai_engine', engine);

      const response = await apiClient.post('/api/v1/tzd/analyze', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 5 minutes timeout for analysis
      });

      if (response.data.success) {
        const result = response.data;
        
        // Normalize all text fields
        const normalizedResult = {
          ...result,
          project_object: normalizeDiacritics(result.project_object),
          requirements: result.requirements.map(normalizeDiacritics),
          norms: result.norms.map(normalizeDiacritics),
          constraints: result.constraints.map(normalizeDiacritics),
          environment: normalizeDiacritics(result.environment),
          functions: result.functions.map(normalizeDiacritics),
        };
        
        setAnalysisResult(normalizedResult);
        
        // Generate translations (simple mock for now)
        const projectDesc = normalizedResult.project_object || 'Описание проекта недоступно';
        setTranslations({
          ru: projectDesc, // Russian (original)
          cs: projectDesc, // Czech (would need translation API)
          en: projectDesc, // English (would need translation API)
        });
        
        message.success('Анализ технического задания завершен успешно!');
      } else {
        throw new Error(response.data.error_message || 'Анализ не удался');
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Произошла ошибка при анализе';
      setError(errorMessage);
      message.error(`Ошибка анализа: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  const renderResults = () => {
    if (!analysisResult) return null;

    return (
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card
          title={
            <Space>
              <CheckCircleOutlined style={{ color: '#52c41a' }} />
              <span>Результаты анализа</span>
            </Space>
          }
        >
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <Text strong>ID анализа:</Text> <Tag>{analysisResult.analysis_id}</Tag>
            </div>
            <div>
              <Text strong>Время обработки:</Text>{' '}
              <Text type="secondary">{analysisResult.timestamp}</Text>
            </div>
            <Divider />
            
            <div>
              <Title level={4}>
                <FileTextOutlined /> Описание проекта
              </Title>
              <Paragraph>{analysisResult.project_object}</Paragraph>
            </div>

            <Divider />

            <Row gutter={16}>
              <Col span={12}>
                <Card size="small" title="Требования" bordered={false}>
                  <List
                    size="small"
                    dataSource={analysisResult.requirements}
                    renderItem={(item) => <List.Item>• {item}</List.Item>}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" title="Нормы" bordered={false}>
                  <List
                    size="small"
                    dataSource={analysisResult.norms}
                    renderItem={(item) => <List.Item>• {item}</List.Item>}
                  />
                </Card>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Card size="small" title="Ограничения" bordered={false}>
                  <List
                    size="small"
                    dataSource={analysisResult.constraints}
                    renderItem={(item) => <List.Item>• {item}</List.Item>}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" title="Функции" bordered={false}>
                  <List
                    size="small"
                    dataSource={analysisResult.functions}
                    renderItem={(item) => <List.Item>• {item}</List.Item>}
                  />
                </Card>
              </Col>
            </Row>

            {analysisResult.environment && (
              <>
                <Divider />
                <div>
                  <Title level={5}>Условия окружающей среды</Title>
                  <Paragraph>{analysisResult.environment}</Paragraph>
                </div>
              </>
            )}
          </Space>
        </Card>

        {translations && (
          <Card
            title={
              <Space>
                <GlobalOutlined style={{ color: '#1890ff' }} />
                <span>Переводы описания проекта</span>
              </Space>
            }
          >
            <Tabs
              items={[
                {
                  key: 'ru',
                  label: '🇷🇺 Русский',
                  children: <Paragraph>{translations.ru}</Paragraph>,
                },
                {
                  key: 'cs',
                  label: '🇨🇿 Čeština',
                  children: <Paragraph>{translations.cs}</Paragraph>,
                },
                {
                  key: 'en',
                  label: '🇬🇧 English',
                  children: <Paragraph>{translations.en}</Paragraph>,
                },
              ]}
            />
          </Card>
        )}
      </Space>
    );
  };

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Space direction="vertical" size="small">
            <Title level={2}>TZD Reader - Анализ технических заданий</Title>
            <Paragraph type="secondary">
              Загрузите технические документы для автоматического извлечения требований,
              норм, ограничений и другой ключевой информации. Система поддерживает PDF,
              DOCX и TXT файлы с автоматической проверкой и исправлением диакритики.
            </Paragraph>
          </Space>
        </Card>

        {error && (
          <Card>
            <Text type="danger">{error}</Text>
          </Card>
        )}

        {!analysisResult && !loading && (
          <TZDUploadSimple
            onAnalyze={handleAnalyze}
            loading={loading}
            disabled={loading}
          />
        )}

        {loading && (
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

        {analysisResult && renderResults()}
      </Space>
    </div>
  );
};

export default TZDAnalysis;

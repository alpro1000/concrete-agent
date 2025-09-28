import React, { useState, useEffect } from 'react';
import { 
  Row, 
  Col, 
  Card, 
  Typography, 
  Button, 
  Space, 
  Spin, 
  Alert, 
  Tabs, 
  Progress,
  Statistic,
  message,
  Divider
} from 'antd';
import { 
  DownloadOutlined, 
  ReloadOutlined, 
  BarChartOutlined,
  TableOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import ResultsTable from '../components/ResultsTable';
import ResultsChart from '../components/ResultsChart';
import LogsDisplay from '../components/LogsDisplay';
import type { LogEntry } from '../components/LogsDisplay';
import apiClient from '../api/client';
import type { 
  ConcreteAnalysisResult, 
  MaterialAnalysisResult, 
  ComparisonResult,
  Language 
} from '../types/api';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

interface AnalysisData {
  docs: File[];
  smeta: File[];
  drawings: File[];
  material_query?: string;
  use_claude: boolean;
  claude_mode: string;
  language: Language;
  include_drawing_analysis: boolean;
  analysis_type: 'concrete' | 'materials' | 'comparison' | 'tov' | 'integrated';
  project_name?: string;
  project_duration_days?: number;
}

interface AnalysisProps {
  analysisData: AnalysisData;
  onBack: () => void;
}

const Analysis: React.FC<AnalysisProps> = ({ analysisData, onBack }) => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<ConcreteAnalysisResult | MaterialAnalysisResult | ComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [chartType, setChartType] = useState<'bar' | 'pie' | 'line'>('bar');

  useEffect(() => {
    startAnalysis();
  }, []);

  const addLog = (level: LogEntry['level'], message: string, details?: string) => {
    const logEntry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      details,
      source: 'frontend',
    };
    setLogs(prev => [...prev, logEntry]);
  };

  const simulateProgress = () => {
    let currentProgress = 0;
    const interval = setInterval(() => {
      currentProgress += Math.random() * 15;
      if (currentProgress >= 90) {
        setProgress(90);
        clearInterval(interval);
      } else {
        setProgress(currentProgress);
      }
    }, 1000);
    return interval;
  };

  const startAnalysis = async () => {
    setLoading(true);
    setError(null);
    setProgress(0);
    addLog('info', 'Starting analysis...', `Type: ${analysisData.analysis_type}`);

    const progressInterval = simulateProgress();

    try {
      let result;

      switch (analysisData.analysis_type) {
        case 'concrete':
          addLog('info', 'Analyzing concrete structures...');
          if (analysisData.smeta.length === 0) {
            throw new Error('At least one smeta file is required for concrete analysis');
          }
          result = await apiClient.analyzeConcrete(
            analysisData.docs,
            analysisData.smeta[0], // Use first smeta file for concrete analysis
            {
              use_claude: analysisData.use_claude,
              claude_mode: analysisData.claude_mode,
              language: analysisData.language,
            }
          );
          break;

        case 'materials':
          addLog('info', 'Analyzing materials...');
          result = await apiClient.analyzeMaterials(
            analysisData.docs,
            {
              smeta: analysisData.smeta.length > 0 ? analysisData.smeta[0] : undefined,
              material_query: analysisData.material_query,
              use_claude: analysisData.use_claude,
              claude_mode: analysisData.claude_mode,
              language: analysisData.language,
              include_drawing_analysis: analysisData.include_drawing_analysis,
            }
          );
          break;

        case 'tov':
          addLog('info', 'Running TOV resource planning analysis...');
          result = await apiClient.analyzeTOV(
            analysisData.docs,
            {
              smeta: analysisData.smeta.length > 0 ? analysisData.smeta[0] : undefined,
              project_name: analysisData.project_name,
              project_duration_days: analysisData.project_duration_days,
              use_claude: analysisData.use_claude,
              claude_mode: analysisData.claude_mode,
              language: analysisData.language,
              export_format: 'json',
            }
          );
          break;

        case 'integrated':
          addLog('info', 'Running integrated analysis across all uploaded files...');
          // For integrated analysis, we run multiple analyses
          const integratedResults: any = {
            docs_analysis: null,
            smeta_analysis: null,
            drawings_analysis: null,
            tov_analysis: null
          };

          if (analysisData.docs.length > 0) {
            addLog('info', 'Processing project documents...');
            // Process docs using upload endpoint with auto-analysis
            const docsResult = await apiClient.uploadDocs(analysisData.docs, {
              project_name: analysisData.project_name,
              auto_analyze: true,
              language: analysisData.language
            });
            integratedResults.docs_analysis = docsResult;
          }

          if (analysisData.smeta.length > 0) {
            addLog('info', 'Processing estimates...');
            const smetaResult = await apiClient.uploadSmeta(analysisData.smeta, {
              project_name: analysisData.project_name,
              auto_analyze: true,
              language: analysisData.language
            });
            integratedResults.smeta_analysis = smetaResult;

            // Also run TOV analysis if we have estimates
            const tovResult = await apiClient.analyzeTOV([], {
              smeta: analysisData.smeta[0],
              project_name: analysisData.project_name,
              project_duration_days: analysisData.project_duration_days,
              use_claude: analysisData.use_claude,
              claude_mode: analysisData.claude_mode,
              language: analysisData.language
            });
            integratedResults.tov_analysis = tovResult;
          }

          if (analysisData.drawings.length > 0) {
            addLog('info', 'Processing drawings and BIM models...');
            const drawingsResult = await apiClient.uploadDrawings(analysisData.drawings, {
              project_name: analysisData.project_name,
              auto_analyze: true,
              extract_volumes: true,
              language: analysisData.language
            });
            integratedResults.drawings_analysis = drawingsResult;
          }

          result = {
            success: true,
            analysis_type: 'integrated',
            results: integratedResults,
            project_name: analysisData.project_name,
            timestamp: new Date().toISOString()
          };
          break;

        case 'comparison':
          addLog('info', 'Comparing documents...');
          if (analysisData.docs.length < 2) {
            throw new Error('At least 2 documents are required for comparison');
          }
          const midpoint = Math.ceil(analysisData.docs.length / 2);
          const oldDocs = analysisData.docs.slice(0, midpoint);
          const newDocs = analysisData.docs.slice(midpoint);
          result = await apiClient.compareDocs(oldDocs, newDocs);
          break;

        default:
          throw new Error('Invalid analysis type');
      }

      clearInterval(progressInterval);
      setProgress(100);
      setResults(result);
      addLog('info', 'Analysis completed successfully', `Processing time: ${result.processing_time || 'Unknown'}s`);

      if (!result.success) {
        addLog('error', 'Analysis failed', result.error);
        setError(result.error || 'Analysis failed');
      }

    } catch (err: any) {
      clearInterval(progressInterval);
      const errorMessage = err.message || 'Analysis failed';
      setError(errorMessage);
      addLog('error', 'Analysis failed', errorMessage);
      message.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (format: 'json' | 'excel' | 'pdf') => {
    if (!results) return;

    const blob = new Blob([JSON.stringify(results, null, 2)], { 
      type: 'application/json' 
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analysis-results.${format === 'json' ? 'json' : format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    addLog('info', `Downloaded results as ${format.toUpperCase()}`);
  };

  const renderLoadingState = () => (
    <Row gutter={[24, 24]}>
      <Col span={24} style={{ textAlign: 'center' }}>
        <Card>
          <Space direction="vertical" size="large">
            <Spin size="large" />
            <Title level={3}>{t('common.loading')}</Title>
            <Progress 
              percent={Math.round(progress)} 
              status="active" 
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
            />
            <Text type="secondary">
              Processing {analysisData.analysis_type} analysis...
            </Text>
          </Space>
        </Card>
      </Col>
    </Row>
  );

  const renderResults = () => {
    if (!results) return null;

    const isConcreteResult = (r: any): r is ConcreteAnalysisResult => 
      'concrete_summary' in r;
    const isMaterialResult = (r: any): r is MaterialAnalysisResult => 
      'materials_found' in r;
    const isComparisonResult = (r: any): r is ComparisonResult => 
      'comparison' in r;

    return (
      <Row gutter={[24, 24]}>
        <Col span={24}>
          <Card>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="Status"
                  value={results.success ? 'Success' : 'Failed'}
                  prefix={results.success ? <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
                  valueStyle={{ color: results.success ? '#3f8600' : '#cf1322' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Processing Time"
                  value={results.processing_time || 0}
                  suffix="s"
                />
              </Col>
              <Col span={12}>
                <Space>
                  <Button
                    type="primary"
                    icon={<DownloadOutlined />}
                    onClick={() => handleDownload('json')}
                  >
                    {t('analysis.export.json')}
                  </Button>
                  <Button
                    icon={<DownloadOutlined />}
                    onClick={() => handleDownload('excel')}
                  >
                    {t('analysis.export.excel')}
                  </Button>
                  <Button
                    icon={<DownloadOutlined />}
                    onClick={() => handleDownload('pdf')}
                  >
                    {t('analysis.export.pdf')}
                  </Button>
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={startAnalysis}
                  >
                    Retry
                  </Button>
                </Space>
              </Col>
            </Row>
          </Card>
        </Col>

        <Col span={24}>
          <Tabs defaultActiveKey="table">
            <TabPane tab={<><TableOutlined /> Table View</>} key="table">
              {isConcreteResult(results) && (
                <ResultsTable
                  title={t('analysis.concrete.title')}
                  data={results.concrete_summary}
                  type="concrete"
                />
              )}
              {isMaterialResult(results) && (
                <ResultsTable
                  title={t('analysis.materials.title')}
                  data={results.materials_found}
                  type="materials"
                />
              )}
              {isComparisonResult(results) && (
                <Card>
                  <Title level={4}>{t('analysis.comparison.title')}</Title>
                  <Alert
                    message={results.comparison.summary}
                    type="info"
                    showIcon
                  />
                </Card>
              )}
            </TabPane>

            <TabPane tab={<><BarChartOutlined /> Chart View</>} key="chart">
              {(isConcreteResult(results) || isMaterialResult(results)) && (
                <ResultsChart
                  title="Analysis Results"
                  data={isConcreteResult(results) ? results.concrete_summary : results.materials_found}
                  type={isConcreteResult(results) ? 'concrete' : 'materials'}
                  chartType={chartType}
                  onChartTypeChange={setChartType}
                />
              )}
            </TabPane>
          </Tabs>
        </Col>
      </Row>
    );
  };

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={[24, 24]}>
        <Col span={24}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={2}>{t('analysis.title')}</Title>
            <Button onClick={onBack}>
              {t('common.back')}
            </Button>
          </div>
          <Divider />
        </Col>

        {loading && renderLoadingState()}

        {error && (
          <Col span={24}>
            <Alert
              message={t('common.error')}
              description={error}
              type="error"
              showIcon
              closable
            />
          </Col>
        )}

        {results && !loading && renderResults()}

        <Col span={24}>
          <LogsDisplay
            logs={logs}
            title={t('analysis.logs.title')}
            onClear={() => setLogs([])}
            compact={loading}
          />
        </Col>
      </Row>
    </div>
  );
};

export default Analysis;
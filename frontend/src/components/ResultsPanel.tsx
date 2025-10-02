import React from 'react';
import {
  Card,
  Tabs,
  Button,
  Space,
  Typography,
  Tag,
  Divider,
  Empty,
  message,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  FileTextOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  FileExcelOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

interface FileResult {
  name: string;
  type: string;
  category?: string;
  success: boolean;
  error: string | null;
  result?: any;
}

interface ResultsPanelProps {
  results: {
    status: 'success' | 'error';
    message?: string;
    files: FileResult[];
    summary: {
      total: number;
      successful: number;
      failed: number;
    };
    project_name?: string;
    language?: string;
    timestamp?: string;
  } | null;
  loading?: boolean;
  onClose?: () => void;
}

const ResultsPanel: React.FC<ResultsPanelProps> = ({ results, loading, onClose }) => {
  const { t } = useTranslation();

  const handleExport = (format: 'json' | 'pdf' | 'word' | 'excel') => {
    if (!results) return;

    try {
      if (format === 'json') {
        const dataStr = JSON.stringify(results, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        const timestamp = new Date().toISOString().split('T')[0];
        link.href = url;
        link.download = `analysis_${timestamp}.json`;
        link.click();
        URL.revokeObjectURL(url);
        message.success(t('analysis.export.json'));
      } else {
        message.info(`${format.toUpperCase()} export requires backend support`);
      }
    } catch (error) {
      message.error(t('errors.unknownError'));
    }
  };

  if (loading) {
    return null; // Loading handled by parent
  }

  if (!results) {
    return null;
  }

  const { files, summary, status, message: statusMessage } = results;

  // Group files by category
  const filesByCategory = files.reduce((acc, file) => {
    const category = file.category || 'other';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(file);
    return acc;
  }, {} as Record<string, FileResult[]>);

  const renderFilesList = (filesList: FileResult[]) => {
    if (!filesList || filesList.length === 0) {
      return <Empty description={t('common.noData')} />;
    }

    return (
      <div style={{ marginTop: '16px' }}>
        {filesList.map((file, index) => (
          <Card
            key={index}
            size="small"
            style={{
              marginBottom: '8px',
              borderLeft: file.success ? '4px solid #52c41a' : '4px solid #ff4d4f',
            }}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space>
                {file.success ? (
                  <CheckCircleOutlined style={{ color: '#52c41a', fontSize: '20px' }} />
                ) : (
                  <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: '20px' }} />
                )}
                <Text strong>{file.name}</Text>
                <Tag color={file.success ? 'success' : 'error'}>
                  {file.type.toUpperCase()}
                </Tag>
              </Space>

              {file.error && (
                <Text type="danger" style={{ fontSize: '12px' }}>
                  ❌ {file.error}
                </Text>
              )}

              {file.success && file.result && (
                <div style={{ marginTop: '8px' }}>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    Agent: {file.result.agent_used || 'N/A'} | 
                    Type: {file.result.detected_type || 'N/A'}
                  </Text>
                </div>
              )}
            </Space>
          </Card>
        ))}
      </div>
    );
  };

  const renderFormattedView = () => {
    return (
      <div>
        <Card>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Title level={4}>
              {status === 'success' ? '✅ ' : '❌ '}
              {statusMessage || 'Analysis Complete'}
            </Title>

            <Divider />

            <div>
              <Text strong>Summary:</Text>
              <ul style={{ marginTop: '8px' }}>
                <li>Total files: {summary.total}</li>
                <li style={{ color: '#52c41a' }}>Successful: {summary.successful}</li>
                <li style={{ color: '#ff4d4f' }}>Failed: {summary.failed}</li>
              </ul>
            </div>

            <Divider />

            {Object.entries(filesByCategory).map(([category, categoryFiles]) => (
              <div key={category}>
                <Title level={5}>{category.charAt(0).toUpperCase() + category.slice(1)}</Title>
                {renderFilesList(categoryFiles)}
              </div>
            ))}
          </Space>
        </Card>
      </div>
    );
  };

  const renderJSONView = () => {
    return (
      <div
        style={{
          background: '#f5f5f5',
          padding: '16px',
          borderRadius: '4px',
          maxHeight: '600px',
          overflow: 'auto',
        }}
      >
        <pre style={{ margin: 0, fontSize: '12px', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {JSON.stringify(results, null, 2)}
        </pre>
      </div>
    );
  };

  return (
    <Card
      style={{ marginTop: '24px' }}
      title={
        <Space>
          {status === 'success' ? (
            <CheckCircleOutlined style={{ color: '#52c41a', fontSize: '24px' }} />
          ) : (
            <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: '24px' }} />
          )}
          <span>{t('analysis.title')}</span>
        </Space>
      }
      extra={
        onClose && (
          <Button onClick={onClose} type="text">
            Close
          </Button>
        )
      }
    >
      <Tabs defaultActiveKey="formatted">
        <TabPane tab="Formatted View" key="formatted">
          {renderFormattedView()}
        </TabPane>
        <TabPane tab="JSON View" key="json">
          {renderJSONView()}
        </TabPane>
      </Tabs>

      <Divider />

      <div style={{ textAlign: 'center' }}>
        <Space size="middle" wrap>
          <Button
            icon={<FileTextOutlined />}
            onClick={() => handleExport('json')}
            type="primary"
          >
            {t('analysis.export.json') || 'Export JSON'}
          </Button>
          <Button
            icon={<FilePdfOutlined />}
            onClick={() => handleExport('pdf')}
          >
            {t('analysis.export.pdf') || 'Export PDF'}
          </Button>
          <Button
            icon={<FileWordOutlined />}
            onClick={() => handleExport('word')}
          >
            {t('analysis.export.word') || 'Export Word'}
          </Button>
          <Button
            icon={<FileExcelOutlined />}
            onClick={() => handleExport('excel')}
          >
            {t('analysis.export.excel') || 'Export Excel'}
          </Button>
        </Space>
      </div>
    </Card>
  );
};

export default ResultsPanel;

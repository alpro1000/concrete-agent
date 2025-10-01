import React from 'react';
import { Card, Button, Space, Typography, Divider, message } from 'antd';
import {
  DownloadOutlined,
  FileExcelOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { Text, Paragraph } = Typography;

interface ResultsExportProps {
  results: any;
  projectName?: string;
  onExport?: (format: 'json' | 'excel' | 'pdf' | 'word') => void;
}

const ResultsExport: React.FC<ResultsExportProps> = ({
  results,
  projectName = 'analysis',
  onExport,
}) => {
  const { t } = useTranslation();

  const handleExport = (format: 'json' | 'excel' | 'pdf' | 'word') => {
    if (onExport) {
      onExport(format);
      return;
    }

    // Default export behavior - download as JSON
    if (format === 'json') {
      const dataStr = JSON.stringify(results, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${projectName}_${new Date().toISOString().split('T')[0]}.json`;
      link.click();
      URL.revokeObjectURL(url);
      message.success(t('analysis.export.json'));
    } else {
      // For other formats, show a message that backend support is needed
      message.info(`${format.toUpperCase()} export requires backend support`);
    }
  };

  if (!results) {
    return null;
  }

  return (
    <Card
      title={
        <Space>
          <DownloadOutlined />
          <span>{t('analysis.export.json').replace(' JSON', '')} {t('common.results')}</span>
        </Space>
      }
      style={{ marginTop: '24px' }}
    >
      <Paragraph>
        {t('analysis.title')} - {projectName}
      </Paragraph>
      
      <Divider />
      
      <Space size="middle" wrap>
        <Button
          type="primary"
          icon={<FileTextOutlined />}
          onClick={() => handleExport('json')}
        >
          {t('analysis.export.json')}
        </Button>
        
        <Button
          icon={<FileExcelOutlined />}
          onClick={() => handleExport('excel')}
        >
          {t('analysis.export.excel')}
        </Button>
        
        <Button
          icon={<FilePdfOutlined />}
          onClick={() => handleExport('pdf')}
        >
          {t('analysis.export.pdf')}
        </Button>
        
        <Button
          icon={<FileWordOutlined />}
          onClick={() => handleExport('word')}
        >
          {t('analysis.export.word')}
        </Button>
      </Space>
      
      <Divider />
      
      <div style={{ maxHeight: '300px', overflow: 'auto', background: '#f5f5f5', padding: '12px', borderRadius: '4px' }}>
        <Text code style={{ fontSize: '11px', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {JSON.stringify(results, null, 2)}
        </Text>
      </div>
    </Card>
  );
};

export default ResultsExport;

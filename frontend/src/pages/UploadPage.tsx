import React, { useState } from 'react';
import { Upload, Button, Card, message, Tabs, Space, Table, Tag } from 'antd';
import { UploadOutlined, FilePdfOutlined, FileWordOutlined, FileExcelOutlined, FileTextOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { uploadFiles, exportResults } from '../lib/api';
import type { UploadFile } from 'antd';
import type { AnalysisResponse } from '../types';
import './UploadPage.css';

const { Dragger } = Upload;
const { TabPane } = Tabs;

const UploadPage: React.FC = () => {
  const { t } = useTranslation();
  const [technicalFiles, setTechnicalFiles] = useState<UploadFile[]>([]);
  const [quantitiesFiles, setQuantitiesFiles] = useState<UploadFile[]>([]);
  const [drawingsFiles, setDrawingsFiles] = useState<UploadFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<AnalysisResponse | null>(null);

  const handleUpload = async () => {
    if (technicalFiles.length === 0 && quantitiesFiles.length === 0 && drawingsFiles.length === 0) {
      message.error(t('messages.error'));
      return;
    }

    setLoading(true);
    const formData = new FormData();

    // Use exact backend field names
    technicalFiles.forEach((file) => {
      if (file.originFileObj) {
        formData.append('project_documentation', file.originFileObj);
      }
    });

    quantitiesFiles.forEach((file) => {
      if (file.originFileObj) {
        formData.append('budget_estimate', file.originFileObj);
      }
    });

    drawingsFiles.forEach((file) => {
      if (file.originFileObj) {
        formData.append('drawings', file.originFileObj);
      }
    });

    try {
      const response = await uploadFiles(formData);
      setResults(response as AnalysisResponse);
      message.success(t('upload.uploadSuccess'));
    } catch (error) {
      console.error('Upload error:', error);
      message.error(t('messages.serverError'));
    } finally {
      setLoading(false);
    }
  };

  const uploadProps = {
    beforeUpload: () => false,
    maxCount: 10,
  };

  const handleExport = async (format: 'pdf' | 'docx' | 'xlsx' | 'json') => {
    if (!results) return;

    if (format === 'json') {
      const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analysis_${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
      message.success('JSON exported successfully');
    } else {
      try {
        const blob = await exportResults((results as any).analysis_id, format);
        const url = URL.createObjectURL(blob as Blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `analysis_${Date.now()}.${format}`;
        a.click();
        URL.revokeObjectURL(url);
        message.success(t('export.title') + ' ' + format.toUpperCase());
      } catch (error) {
        console.error('Export error:', error);
        message.info('Export feature will be available soon');
      }
    }
  };

  const resultsColumns = [
    {
      title: t('analyses.fileName'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('analyses.status'),
      dataIndex: 'success',
      key: 'success',
      render: (success: boolean) => (
        <Tag color={success ? 'success' : 'error'}>
          {success ? '✅ ' + t('status.completed') : '❌ ' + t('status.failed')}
        </Tag>
      ),
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => {
        const categoryMap: Record<string, string> = {
          technical: t('technical.title'),
          quantities: t('quantities.title'),
          drawings: t('drawings.title'),
        };
        return categoryMap[category] || category;
      },
    },
  ];

  return (
    <div className="upload-page">
      <div className="upload-container">
        <h2>{t('upload.title')}</h2>
        
        <div className="upload-panels">
          <Card title={t('technical.title')} className="upload-panel">
            <p className="formats">{t('technical.formats')}</p>
            <Dragger
              {...uploadProps}
              fileList={technicalFiles}
              onChange={({ fileList }) => setTechnicalFiles(fileList)}
              accept=".pdf,.docx,.doc,.txt"
            >
              <p className="ant-upload-drag-icon">
                <UploadOutlined />
              </p>
              <p className="ant-upload-text">{t('upload.dragDrop')}</p>
            </Dragger>
          </Card>

          <Card title={t('quantities.title')} className="upload-panel">
            <p className="formats">{t('quantities.formats')}</p>
            <Dragger
              {...uploadProps}
              fileList={quantitiesFiles}
              onChange={({ fileList }) => setQuantitiesFiles(fileList)}
              accept=".xls,.xlsx,.xml,.xc4,.csv"
            >
              <p className="ant-upload-drag-icon">
                <UploadOutlined />
              </p>
              <p className="ant-upload-text">{t('upload.dragDrop')}</p>
            </Dragger>
          </Card>

          <Card title={t('drawings.title')} className="upload-panel">
            <p className="formats">{t('drawings.formats')}</p>
            <Dragger
              {...uploadProps}
              fileList={drawingsFiles}
              onChange={({ fileList }) => setDrawingsFiles(fileList)}
              accept=".pdf,.dwg,.dxf,.jpg,.jpeg,.png"
            >
              <p className="ant-upload-drag-icon">
                <UploadOutlined />
              </p>
              <p className="ant-upload-text">{t('upload.dragDrop')}</p>
            </Dragger>
          </Card>
        </div>

        <div className="upload-actions">
          <Button
            type="primary"
            size="large"
            loading={loading}
            onClick={handleUpload}
            disabled={technicalFiles.length === 0 && quantitiesFiles.length === 0 && drawingsFiles.length === 0}
          >
            {loading ? t('upload.uploading') : t('nav.upload')}
          </Button>
        </div>

        {results && (
          <Card title="Results" className="results-panel">
            <Tabs defaultActiveKey="summary">
              <TabPane tab={t('tabs.summary')} key="summary">
                <div className="summary-stats">
                  <div className="stat-item">
                    <span className="stat-label">Total:</span>
                    <span className="stat-value">{results.summary.total}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">✅ Successful:</span>
                    <span className="stat-value">{results.summary.successful}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">❌ Failed:</span>
                    <span className="stat-value">{results.summary.failed}</span>
                  </div>
                </div>
                <Table
                  dataSource={results.files}
                  columns={resultsColumns}
                  rowKey="name"
                  pagination={false}
                />
              </TabPane>

              <TabPane tab={t('tabs.byAgents')} key="agents">
                <p>Agent analysis will appear here</p>
              </TabPane>

              <TabPane tab={t('tabs.resources')} key="resources">
                <div className="resources-placeholder">
                  <p>{t('resources.placeholder')}</p>
                  <ul>
                    <li>{t('resources.materials')}</li>
                    <li>{t('resources.labor')}</li>
                    <li>{t('resources.technology')}</li>
                    <li>{t('resources.schedule')}</li>
                  </ul>
                </div>
              </TabPane>

              <TabPane tab="JSON" key="json">
                <pre style={{ maxHeight: '400px', overflow: 'auto' }}>
                  {JSON.stringify(results, null, 2)}
                </pre>
              </TabPane>
            </Tabs>

            <Space style={{ marginTop: '20px' }}>
              <Button icon={<FileTextOutlined />} onClick={() => handleExport('json')}>
                {t('export.json')}
              </Button>
              <Button icon={<FilePdfOutlined />} onClick={() => handleExport('pdf')}>
                {t('export.pdf')}
              </Button>
              <Button icon={<FileWordOutlined />} onClick={() => handleExport('docx')}>
                {t('export.docx')}
              </Button>
              <Button icon={<FileExcelOutlined />} onClick={() => handleExport('xlsx')}>
                {t('export.xlsx')}
              </Button>
            </Space>
          </Card>
        )}
      </div>
    </div>
  );
};

export default UploadPage;

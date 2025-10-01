import React, { useState } from 'react';
import { Upload, Card, Row, Col, Typography, message, Button, Space } from 'antd';
import { InboxOutlined, FileTextOutlined, TableOutlined, PictureOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { UploadFile, RcFile } from 'antd/es/upload/interface';

const { Dragger } = Upload;
const { Title, Text, Paragraph } = Typography;

// File type configurations for each panel
const PANEL_CONFIGS = {
  technical: {
    icon: FileTextOutlined,
    accept: '.pdf,.docx,.doc,.txt',
    maxSize: 10 * 1024 * 1024, // 10MB
  },
  quantities: {
    icon: TableOutlined,
    accept: '.xlsx,.xls,.xml,.xc4,.csv',
    maxSize: 15 * 1024 * 1024, // 15MB
  },
  drawings: {
    icon: PictureOutlined,
    accept: '.pdf,.dwg,.dxf,.jpg,.jpeg,.png,.rvt,.pln',
    maxSize: 50 * 1024 * 1024, // 50MB
  },
};

interface ThreePanelUploadProps {
  onFilesChange?: (technical: File[], quantities: File[], drawings: File[]) => void;
}

const ThreePanelUpload: React.FC<ThreePanelUploadProps> = ({ onFilesChange }) => {
  const { t } = useTranslation();
  const [technicalFiles, setTechnicalFiles] = useState<UploadFile[]>([]);
  const [quantitiesFiles, setQuantitiesFiles] = useState<UploadFile[]>([]);
  const [drawingsFiles, setDrawingsFiles] = useState<UploadFile[]>([]);

  // Notify parent component of file changes
  const notifyFilesChange = (
    tech: UploadFile[],
    quant: UploadFile[],
    draw: UploadFile[]
  ) => {
    if (onFilesChange) {
      const getTrueFiles = (files: UploadFile[]) =>
        files.map(f => f.originFileObj as File).filter(Boolean);
      
      onFilesChange(
        getTrueFiles(tech),
        getTrueFiles(quant),
        getTrueFiles(draw)
      );
    }
  };

  // Validate file before upload
  const beforeUpload = (file: RcFile, panelType: keyof typeof PANEL_CONFIGS): boolean => {
    const config = PANEL_CONFIGS[panelType];
    
    // Check file size
    if (file.size > config.maxSize) {
      message.error(
        `${t('errors.fileTooBig')}: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)}MB)`
      );
      return false;
    }

    // Check file extension
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!config.accept.includes(ext)) {
      message.error(`${t('errors.invalidFormat')}: ${file.name}`);
      return false;
    }

    return true;
  };

  // Handle file list changes for each panel
  const handleChange = (
    info: any,
    panelType: 'technical' | 'quantities' | 'drawings'
  ) => {
    let fileList = [...info.fileList];
    
    // Limit to 10 files per panel
    fileList = fileList.slice(-10);
    
    // Update file list with status
    fileList = fileList.map(file => {
      if (file.response) {
        file.url = file.response.url;
      }
      return file;
    });

    // Update state based on panel type
    switch (panelType) {
      case 'technical':
        setTechnicalFiles(fileList);
        notifyFilesChange(fileList, quantitiesFiles, drawingsFiles);
        break;
      case 'quantities':
        setQuantitiesFiles(fileList);
        notifyFilesChange(technicalFiles, fileList, drawingsFiles);
        break;
      case 'drawings':
        setDrawingsFiles(fileList);
        notifyFilesChange(technicalFiles, quantitiesFiles, fileList);
        break;
    }
  };

  // Clear files from a panel
  const clearPanel = (panelType: 'technical' | 'quantities' | 'drawings') => {
    switch (panelType) {
      case 'technical':
        setTechnicalFiles([]);
        notifyFilesChange([], quantitiesFiles, drawingsFiles);
        break;
      case 'quantities':
        setQuantitiesFiles([]);
        notifyFilesChange(technicalFiles, [], drawingsFiles);
        break;
      case 'drawings':
        setDrawingsFiles([]);
        notifyFilesChange(technicalFiles, quantitiesFiles, []);
        break;
    }
    message.info(t('common.success'));
  };

  // Render a single upload panel
  const renderPanel = (
    panelType: 'technical' | 'quantities' | 'drawings',
    files: UploadFile[]
  ) => {
    const config = PANEL_CONFIGS[panelType];
    const Icon = config.icon;
    const panelKey = `home.panels.${panelType}`;

    return (
      <Card
        hoverable
        style={{
          height: '100%',
          borderRadius: '8px',
          border: files.length > 0 ? '2px solid #52c41a' : '1px solid #d9d9d9',
        }}
        bodyStyle={{ padding: '16px' }}
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div style={{ textAlign: 'center' }}>
            <Icon style={{ fontSize: '32px', color: '#1890ff', marginBottom: '8px' }} />
            <Title level={4} style={{ margin: '8px 0' }}>
              {t(`${panelKey}.title`)}
            </Title>
            <Paragraph style={{ fontSize: '12px', color: '#8c8c8c', margin: '4px 0' }}>
              {t(`${panelKey}.description`)}
            </Paragraph>
            <Text type="secondary" style={{ fontSize: '11px', display: 'block', marginBottom: '4px' }}>
              {t(`${panelKey}.formats`)}
            </Text>
            {t(`${panelKey}.examples`) && (
              <Text type="secondary" style={{ fontSize: '10px', fontStyle: 'italic' }}>
                {t(`${panelKey}.examples`)}
              </Text>
            )}
          </div>

          <Dragger
            multiple
            fileList={files}
            beforeUpload={(file) => beforeUpload(file, panelType)}
            onChange={(info) => handleChange(info, panelType)}
            accept={config.accept}
            showUploadList={{
              showPreviewIcon: false,
              showRemoveIcon: true,
            }}
            customRequest={({ onSuccess }) => {
              // Custom request to prevent actual upload - just store locally
              setTimeout(() => {
                onSuccess?.('ok');
              }, 0);
            }}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined style={{ color: '#1890ff' }} />
            </p>
            <p className="ant-upload-text">{t(`${panelKey}.dragHint`)}</p>
            <p className="ant-upload-hint" style={{ fontSize: '11px' }}>
              {t('validation.maxFiles', { max: 10 })} • Max: {(config.maxSize / 1024 / 1024).toFixed(0)}MB
            </p>
          </Dragger>

          {files.length > 0 && (
            <div style={{ textAlign: 'center' }}>
              <Space>
                <Text strong>{files.length} {t('common.upload')}</Text>
                <Button
                  type="link"
                  danger
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={() => clearPanel(panelType)}
                >
                  {t('common.delete')}
                </Button>
              </Space>
            </div>
          )}
        </Space>
      </Card>
    );
  };

  return (
    <div style={{ width: '100%' }}>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          {renderPanel('technical', technicalFiles)}
        </Col>
        <Col xs={24} md={8}>
          {renderPanel('quantities', quantitiesFiles)}
        </Col>
        <Col xs={24} md={8}>
          {renderPanel('drawings', drawingsFiles)}
        </Col>
      </Row>
      
      {(technicalFiles.length > 0 || quantitiesFiles.length > 0 || drawingsFiles.length > 0) && (
        <div style={{ marginTop: '24px', textAlign: 'center' }}>
          <Card style={{ background: '#f0f2f5' }}>
            <Space size="large">
              <Text>
                <FileTextOutlined /> {t('home.panels.technical.title')}: <strong>{technicalFiles.length}</strong>
              </Text>
              <Text>
                <TableOutlined /> {t('home.panels.quantities.title')}: <strong>{quantitiesFiles.length}</strong>
              </Text>
              <Text>
                <PictureOutlined /> {t('home.panels.drawings.title')}: <strong>{drawingsFiles.length}</strong>
              </Text>
            </Space>
          </Card>
        </div>
      )}
    </div>
  );
};

export default ThreePanelUpload;

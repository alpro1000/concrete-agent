import React, { useState } from 'react';
import { Upload, Button, message, Card, Typography, Space, Tag, List } from 'antd';
import { InboxOutlined, DeleteOutlined, FileOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { UploadProps, UploadFile } from 'antd';

const { Dragger } = Upload;
const { Text, Title } = Typography;

interface FileUploadProps {
  value?: File[];
  onChange?: (files: File[]) => void;
  maxFiles?: number;
  maxSize?: number; // in MB
  acceptedTypes?: string[];
  title?: string;
  description?: string;
  multiple?: boolean;
  disabled?: boolean;
}

const FileUpload: React.FC<FileUploadProps> = ({
  value = [],
  onChange,
  maxFiles = 10,
  maxSize = 10,
  acceptedTypes = ['.pdf', '.docx', '.xlsx', '.csv', '.txt'],
  title,
  description,
  multiple = true,
  disabled = false,
}) => {
  const { t } = useTranslation();
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const validateFile = (file: File): boolean => {
    // Check file size
    if (file.size > maxSize * 1024 * 1024) {
      message.error(`${file.name}: ${t('errors.fileTooBig')} (${formatFileSize(file.size)})`);
      return false;
    }

    // Check file type
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!acceptedTypes.includes(fileExtension)) {
      message.error(`${file.name}: ${t('errors.invalidFormat')}`);
      return false;
    }

    return true;
  };

  const handleUpload: UploadProps['customRequest'] = ({ onSuccess }) => {
    // Simulate upload success
    setTimeout(() => {
      onSuccess?.('ok');
    }, 100);
  };

  const handleChange: UploadProps['onChange'] = (info) => {
    let newFileList = [...info.fileList];

    // Filter only successfully uploaded files
    newFileList = newFileList.filter(file => {
      if (file.status === 'error') {
        return false;
      }
      return true;
    });

    // Limit number of files
    if (newFileList.length > maxFiles) {
      message.warning(t('validation.maxFiles', { max: maxFiles }));
      newFileList = newFileList.slice(0, maxFiles);
    }

    setFileList(newFileList);

    // Convert UploadFile[] to File[]
    const files = newFileList
      .filter(file => file.originFileObj)
      .map(file => file.originFileObj as File);

    onChange?.(files);
  };

  const handleBeforeUpload = (file: File, fileList: File[]): boolean => {
    const isValid = validateFile(file);
    if (!isValid) {
      return false;
    }

    // Check total number of files
    if (value.length + fileList.length > maxFiles) {
      message.warning(t('validation.maxFiles', { max: maxFiles }));
      return false;
    }

    return true;
  };

  const handleRemove = (file: UploadFile) => {
    const newFiles = value.filter((_, index) => index !== fileList.indexOf(file));
    onChange?.(newFiles);
  };

  const uploadProps: UploadProps = {
    name: 'file',
    multiple,
    fileList,
    customRequest: handleUpload,
    onChange: handleChange,
    beforeUpload: handleBeforeUpload,
    onRemove: handleRemove,
    disabled,
    accept: acceptedTypes.join(','),
    showUploadList: {
      showPreviewIcon: false,
      showRemoveIcon: true,
      showDownloadIcon: false,
    },
  };

  return (
    <Card>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {title && <Title level={4}>{title}</Title>}
        
        <Dragger {...uploadProps}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
          </p>
          <p className="ant-upload-text">
            {description || t('home.fileUpload.description')}
          </p>
          <p className="ant-upload-hint">
            <Space direction="vertical" size="small">
              <Text type="secondary">
                {t('home.fileUpload.supportedFormats')}: {acceptedTypes.join(', ')}
              </Text>
              <Text type="secondary">
                {t('home.fileUpload.maxSize')}: {maxSize}MB
              </Text>
              {multiple && (
                <Text type="secondary">
                  {t('home.fileUpload.multiple')}
                </Text>
              )}
            </Space>
          </p>
        </Dragger>

        {value.length > 0 && (
          <div>
            <Title level={5}>{t('common.upload')} ({value.length})</Title>
            <List
              size="small"
              dataSource={value}
              renderItem={(file, index) => (
                <List.Item
                  actions={[
                    <Button
                      type="text"
                      icon={<DeleteOutlined />}
                      size="small"
                      onClick={() => {
                        const newFiles = value.filter((_, i) => i !== index);
                        onChange?.(newFiles);
                      }}
                      disabled={disabled}
                    />
                  ]}
                >
                  <List.Item.Meta
                    avatar={<FileOutlined />}
                    title={file.name}
                    description={
                      <Space>
                        <Tag color="blue">{formatFileSize(file.size)}</Tag>
                        <Tag color="green">{file.type || 'Unknown'}</Tag>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </div>
        )}
      </Space>
    </Card>
  );
};

export default FileUpload;
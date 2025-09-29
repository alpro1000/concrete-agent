import React, { useState } from 'react';
import { 
  Card, 
  Upload, 
  Button, 
  Select, 
  Form, 
  Typography, 
  Space, 
  message, 
  Alert,
  Tag,
  Row,
  Col,
  Input
} from 'antd';
import { 
  InboxOutlined, 
  UploadOutlined, 
  SafetyOutlined,
  FileTextOutlined,
  SettingOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { UploadProps, UploadFile } from 'antd';

const { Dragger } = Upload;
const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

interface TZDUploadProps {
  onAnalyze: (files: File[], engine: string, context?: string) => Promise<void>;
  loading?: boolean;
  disabled?: boolean;
}

const TZDUpload: React.FC<TZDUploadProps> = ({
  onAnalyze,
  loading = false,
  disabled = false,
}) => {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  const allowedTypes = ['.pdf', '.docx', '.txt'];
  const maxFileSize = 10; // MB
  const maxFiles = 5;

  const uploadProps: UploadProps = {
    name: 'files',
    multiple: true,
    fileList,
    beforeUpload: (file) => {
      // Validate file extension
      const isValidType = allowedTypes.some(type => 
        file.name.toLowerCase().endsWith(type)
      );
      
      if (!isValidType) {
        message.error(`${file.name}: Допустимы только файлы ${allowedTypes.join(', ')}`);
        return Upload.LIST_IGNORE;
      }

      // Validate file size
      const isValidSize = file.size / 1024 / 1024 < maxFileSize;
      if (!isValidSize) {
        message.error(`${file.name}: Размер файла не должен превышать ${maxFileSize}MB`);
        return Upload.LIST_IGNORE;
      }

      // Check max files limit
      if (selectedFiles.length >= maxFiles) {
        message.error(`Максимум ${maxFiles} файлов`);
        return Upload.LIST_IGNORE;
      }

      return false; // Prevent auto upload
    },
    onChange: (info) => {
      const { fileList: newFileList } = info;
      setFileList(newFileList);
      
      // Update selected files
      const files = newFileList
        .filter(file => file.status !== 'error')
        .map(file => file.originFileObj as File)
        .filter(Boolean);
      
      setSelectedFiles(files);
    },
    onRemove: (file) => {
      const newFileList = fileList.filter(item => item.uid !== file.uid);
      setFileList(newFileList);
      
      const files = newFileList
        .map(item => item.originFileObj as File)
        .filter(Boolean);
      setSelectedFiles(files);
    },
    disabled: disabled || loading,
  };

  const handleAnalyze = async () => {
    if (selectedFiles.length === 0) {
      message.warning('Выберите файлы для анализа');
      return;
    }

    try {
      const values = await form.validateFields();
      await onAnalyze(selectedFiles, values.engine, values.context);
    } catch (error) {
      console.error('Form validation failed:', error);
    }
  };

  const securityFeatures = [
    { text: `Максимум ${maxFiles} файлов`, icon: <FileTextOutlined /> },
    { text: `Размер до ${maxFileSize}MB`, icon: <SafetyOutlined /> },
    { text: 'Защита от path traversal', icon: <SafetyOutlined /> },
    { text: 'Проверка расширений', icon: <SettingOutlined /> },
  ];

  return (
    <Card 
      title={
        <Space>
          <UploadOutlined />
          Загрузка технических документов
        </Space>
      }
      className="tzd-upload-card"
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Security Information */}
        <Alert
          message="Требования безопасности"
          description={
            <Row gutter={[16, 8]}>
              {securityFeatures.map((feature, index) => (
                <Col span={12} key={index}>
                  <Space size="small">
                    {feature.icon}
                    <Text type="secondary">{feature.text}</Text>
                  </Space>
                </Col>
              ))}
            </Row>
          }
          type="info"
          showIcon
        />

        {/* File Upload Area */}
        <Dragger {...uploadProps} style={{ padding: '20px' }}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
          </p>
          <p className="ant-upload-text">
            <Title level={4}>Перетащите файлы сюда или нажмите для выбора</Title>
          </p>
          <p className="ant-upload-hint">
            <Text type="secondary">
              Поддерживаются файлы: {allowedTypes.join(', ')}
              <br />
              Максимальный размер: {maxFileSize}MB на файл
            </Text>
          </p>
        </Dragger>

        {/* Configuration Form */}
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            engine: 'auto',
            context: ''
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="engine"
                label="AI движок"
                tooltip="Выберите AI движок для анализа. 'auto' - автоматический выбор лучшего"
              >
                <Select>
                  <Option value="auto">
                    <Space>
                      <SettingOutlined />
                      Автоматический (рекомендуется)
                    </Space>
                  </Option>
                  <Option value="claude">Claude 3.5 Sonnet</Option>
                  <Option value="gpt">GPT-4</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="context"
                label="Контекст проекта (опционально)"
                tooltip="Дополнительная информация о проекте для более точного анализа"
              >
                <Input.TextArea 
                  placeholder="Например: строительство жилого комплекса..."
                  rows={3}
                />
              </Form.Item>
            </Col>
          </Row>
        </Form>

        {/* File List and Status */}
        {selectedFiles.length > 0 && (
          <Card size="small" title="Выбранные файлы">
            <Space direction="vertical" style={{ width: '100%' }}>
              {selectedFiles.map((file, index) => (
                <div key={index} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Space>
                    <FileTextOutlined />
                    <Text>{file.name}</Text>
                    <Tag color="blue">{(file.size / 1024 / 1024).toFixed(1)} MB</Tag>
                  </Space>
                </div>
              ))}
            </Space>
          </Card>
        )}

        {/* Analysis Button */}
        <Button
          type="primary"
          size="large"
          icon={<BarChartOutlined />}
          onClick={handleAnalyze}
          loading={loading}
          disabled={disabled || selectedFiles.length === 0}
          block
        >
          {loading ? 'Анализ документов...' : 'Анализировать техническое задание'}
        </Button>

        {/* Help Information */}
        <Alert
          message="Что анализирует TZD Reader?"
          description={
            <div>
              <Paragraph>
                <strong>Система извлекает следующую информацию:</strong>
              </Paragraph>
              <ul style={{ paddingLeft: '20px' }}>
                <li><strong>Объект строительства</strong> - название и описание проекта</li>
                <li><strong>Требования</strong> - технические характеристики, материалы, марки бетона</li>
                <li><strong>Нормы</strong> - ссылки на СНиП, ГОСТ, ČSN EN стандарты</li>
                <li><strong>Ограничения</strong> - бюджетные, временные, технические</li>
                <li><strong>Условия эксплуатации</strong> - климат, нагрузки, особенности</li>
                <li><strong>Функции</strong> - назначение и основные функции объекта</li>
              </ul>
            </div>
          }
          type="success"
          showIcon={false}
        />
      </Space>
    </Card>
  );
};

export default TZDUpload;
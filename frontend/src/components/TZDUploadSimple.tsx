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
  Row,
  Col,
  Divider
} from 'antd';
import { 
  FilePdfOutlined,
  FileWordOutlined,
  FileTextOutlined,
  RocketOutlined
} from '@ant-design/icons';
import type { UploadProps, UploadFile } from 'antd';

const { Dragger } = Upload;
const { Title, Text } = Typography;
const { Option } = Select;

interface TZDUploadSimpleProps {
  onAnalyze: (files: File[], engine: string) => Promise<void>;
  loading?: boolean;
  disabled?: boolean;
}

const TZDUploadSimple: React.FC<TZDUploadSimpleProps> = ({
  onAnalyze,
  loading = false,
  disabled = false,
}) => {
  const [form] = Form.useForm();
  const [pdfFiles, setPdfFiles] = useState<UploadFile[]>([]);
  const [docxFiles, setDocxFiles] = useState<UploadFile[]>([]);
  const [txtFiles, setTxtFiles] = useState<UploadFile[]>([]);

  const maxFileSize = 10; // MB

  const createUploadProps = (
    fileList: UploadFile[],
    setFileList: React.Dispatch<React.SetStateAction<UploadFile[]>>,
    acceptedExtension: string
  ): UploadProps => ({
    name: 'files',
    multiple: true,
    fileList,
    accept: acceptedExtension,
    beforeUpload: (file) => {
      // Validate file size
      const isValidSize = file.size / 1024 / 1024 < maxFileSize;
      if (!isValidSize) {
        message.error(`${file.name}: Размер файла не должен превышать ${maxFileSize}MB`);
        return Upload.LIST_IGNORE;
      }
      return false; // Prevent auto upload
    },
    onChange: (info) => {
      setFileList(info.fileList);
    },
    onRemove: (file) => {
      const newFileList = fileList.filter(item => item.uid !== file.uid);
      setFileList(newFileList);
    },
  });

  const handleSubmit = async (values: any) => {
    const allFiles = [
      ...pdfFiles.map(f => f.originFileObj as File),
      ...docxFiles.map(f => f.originFileObj as File),
      ...txtFiles.map(f => f.originFileObj as File),
    ].filter(Boolean);

    if (allFiles.length === 0) {
      message.error('Загрузите хотя бы один файл');
      return;
    }

    try {
      await onAnalyze(allFiles, values.engine || 'auto');
    } catch (error) {
      message.error('Ошибка при анализе документов');
    }
  };

  const getTotalFilesCount = () => {
    return pdfFiles.length + docxFiles.length + txtFiles.length;
  };

  return (
    <Card>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div>
          <Title level={3}>Загрузка документов для анализа</Title>
          <Text type="secondary">
            Загрузите технические документы в форматах PDF, DOCX или TXT для анализа технического задания
          </Text>
        </div>

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ engine: 'auto' }}
        >
          <Row gutter={16}>
            {/* PDF Upload */}
            <Col xs={24} md={8}>
              <Card
                size="small"
                title={
                  <Space>
                    <FilePdfOutlined style={{ color: '#ff4d4f' }} />
                    <span>PDF документы</span>
                  </Space>
                }
              >
                <Dragger {...createUploadProps(pdfFiles, setPdfFiles, '.pdf')}>
                  <p className="ant-upload-drag-icon">
                    <FilePdfOutlined style={{ color: '#ff4d4f' }} />
                  </p>
                  <p className="ant-upload-text">Нажмите или перетащите PDF файлы</p>
                  <p className="ant-upload-hint">Максимальный размер: 10MB</p>
                </Dragger>
              </Card>
            </Col>

            {/* DOCX Upload */}
            <Col xs={24} md={8}>
              <Card
                size="small"
                title={
                  <Space>
                    <FileWordOutlined style={{ color: '#1890ff' }} />
                    <span>DOCX документы</span>
                  </Space>
                }
              >
                <Dragger {...createUploadProps(docxFiles, setDocxFiles, '.docx')}>
                  <p className="ant-upload-drag-icon">
                    <FileWordOutlined style={{ color: '#1890ff' }} />
                  </p>
                  <p className="ant-upload-text">Нажмите или перетащите DOCX файлы</p>
                  <p className="ant-upload-hint">Максимальный размер: 10MB</p>
                </Dragger>
              </Card>
            </Col>

            {/* TXT Upload */}
            <Col xs={24} md={8}>
              <Card
                size="small"
                title={
                  <Space>
                    <FileTextOutlined style={{ color: '#52c41a' }} />
                    <span>TXT документы</span>
                  </Space>
                }
              >
                <Dragger {...createUploadProps(txtFiles, setTxtFiles, '.txt')}>
                  <p className="ant-upload-drag-icon">
                    <FileTextOutlined style={{ color: '#52c41a' }} />
                  </p>
                  <p className="ant-upload-text">Нажмите или перетащите TXT файлы</p>
                  <p className="ant-upload-hint">Максимальный размер: 10MB</p>
                </Dragger>
              </Card>
            </Col>
          </Row>

          <Divider />

          <Row gutter={16} align="middle">
            <Col xs={24} md={12}>
              <Form.Item
                label="AI движок"
                name="engine"
                tooltip="Выберите AI движок для анализа или используйте автовыбор"
              >
                <Select>
                  <Option value="auto">🤖 Автовыбор (рекомендуется)</Option>
                  <Option value="gpt">GPT-4</Option>
                  <Option value="claude">Claude</Option>
                </Select>
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Form.Item>
                <Button
                  type="primary"
                  size="large"
                  htmlType="submit"
                  loading={loading}
                  disabled={disabled || getTotalFilesCount() === 0}
                  icon={<RocketOutlined />}
                  block
                >
                  Анализировать ({getTotalFilesCount()} файл{getTotalFilesCount() !== 1 ? 'ов' : ''})
                </Button>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Space>
    </Card>
  );
};

export default TZDUploadSimple;

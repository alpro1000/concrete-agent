import React from 'react';
import { 
  Card, 
  Typography, 
  Space, 
  Tag, 
  List, 
  Row, 
  Col, 
  Statistic, 
  Divider,
  Button,
  Alert,
  Collapse,
  Badge,
  Descriptions
} from 'antd';
import { 
  ProjectOutlined,
  CheckCircleOutlined,
  BookOutlined,
  ExclamationCircleOutlined,
  EnvironmentOutlined,
  ToolOutlined,
  DownloadOutlined,
  CopyOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { TZDAnalysisResult } from '../types/api';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface TZDResultsProps {
  result: TZDAnalysisResult;
  onDownload?: (format: 'json' | 'pdf') => void;
  onCopy?: () => void;
}

const TZDResults: React.FC<TZDResultsProps> = ({
  result,
  onDownload,
  onCopy
}) => {
  const { t } = useTranslation();

  if (!result.success) {
    return (
      <Alert
        message="Ошибка анализа"
        description={result.error_message || 'Произошла ошибка при анализе документов'}
        type="error"
        showIcon
        action={
          <Button size="small" danger>
            Повторить
          </Button>
        }
      />
    );
  }

  const hasData = result.project_object || 
                  result.requirements.length > 0 || 
                  result.norms.length > 0 ||
                  result.constraints.length > 0 ||
                  result.functions.length > 0;

  const getStatusColor = (items: string[] | string): string => {
    if (Array.isArray(items)) {
      return items.length > 0 ? 'success' : 'default';
    }
    return items ? 'success' : 'default';
  };

  const getStatusCount = (items: string[] | string): number => {
    if (Array.isArray(items)) {
      return items.length;
    }
    return items ? 1 : 0;
  };

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {/* Analysis Status */}
      <Card>
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="Статус анализа"
              value="Успешно"
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="ID анализа"
              value={result.analysis_id}
              prefix={<InfoCircleOutlined />}
              valueStyle={{ fontSize: '14px' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Обработано файлов"
              value={result.processing_metadata.processed_files || 0}
              prefix={<ToolOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="AI движок"
              value={result.processing_metadata.ai_engine || 'Не указан'}
              prefix={<ProjectOutlined />}
              valueStyle={{ fontSize: '14px' }}
            />
          </Col>
        </Row>
      </Card>

      {/* Main Results */}
      {hasData ? (
        <Card 
          title={
            <Space>
              <ProjectOutlined />
              Результаты анализа ТЗ
            </Space>
          }
          extra={
            <Space>
              <Button 
                icon={<CopyOutlined />} 
                onClick={onCopy}
                type="text"
              >
                Копировать JSON
              </Button>
              <Button 
                icon={<DownloadOutlined />} 
                onClick={() => onDownload?.('json')}
                type="text"
              >
                JSON
              </Button>
              <Button 
                icon={<DownloadOutlined />} 
                onClick={() => onDownload?.('pdf')}
                type="primary"
              >
                PDF отчет
              </Button>
            </Space>
          }
        >
          <Collapse defaultActiveKey={['object', 'requirements']} ghost>
            {/* Project Object */}
            <Panel
              header={
                <Space>
                  <Badge 
                    status={getStatusColor(result.project_object)} 
                    text={<strong>Объект строительства</strong>}
                  />
                </Space>
              }
              key="object"
            >
              {result.project_object ? (
                <Card size="small" style={{ backgroundColor: '#f6ffed' }}>
                  <Paragraph>
                    <Text strong>{result.project_object}</Text>
                  </Paragraph>
                </Card>
              ) : (
                <Text type="secondary">Информация об объекте не найдена</Text>
              )}
            </Panel>

            {/* Requirements */}
            <Panel
              header={
                <Space>
                  <Badge 
                    status={getStatusColor(result.requirements)} 
                    text={<strong>Требования ({result.requirements.length})</strong>}
                  />
                </Space>
              }
              key="requirements"
            >
              {result.requirements.length > 0 ? (
                <List
                  dataSource={result.requirements}
                  renderItem={(item, index) => (
                    <List.Item key={index}>
                      <Space>
                        <CheckCircleOutlined style={{ color: '#52c41a' }} />
                        <Text>{item}</Text>
                      </Space>
                    </List.Item>
                  )}
                />
              ) : (
                <Text type="secondary">Требования не найдены</Text>
              )}
            </Panel>

            {/* Norms */}
            <Panel
              header={
                <Space>
                  <Badge 
                    status={getStatusColor(result.norms)} 
                    text={<strong>Нормативные документы ({result.norms.length})</strong>}
                  />
                </Space>
              }
              key="norms"
            >
              {result.norms.length > 0 ? (
                <List
                  dataSource={result.norms}
                  renderItem={(item, index) => (
                    <List.Item key={index}>
                      <Space>
                        <BookOutlined style={{ color: '#1890ff' }} />
                        <Tag color="blue">{item}</Tag>
                      </Space>
                    </List.Item>
                  )}
                />
              ) : (
                <Text type="secondary">Нормативные документы не найдены</Text>
              )}
            </Panel>

            {/* Constraints */}
            <Panel
              header={
                <Space>
                  <Badge 
                    status={getStatusColor(result.constraints)} 
                    text={<strong>Ограничения ({result.constraints.length})</strong>}
                  />
                </Space>
              }
              key="constraints"
            >
              {result.constraints.length > 0 ? (
                <List
                  dataSource={result.constraints}
                  renderItem={(item, index) => (
                    <List.Item key={index}>
                      <Space>
                        <ExclamationCircleOutlined style={{ color: '#faad14' }} />
                        <Text>{item}</Text>
                      </Space>
                    </List.Item>
                  )}
                />
              ) : (
                <Text type="secondary">Ограничения не найдены</Text>
              )}
            </Panel>

            {/* Environment */}
            <Panel
              header={
                <Space>
                  <Badge 
                    status={getStatusColor(result.environment)} 
                    text={<strong>Условия эксплуатации</strong>}
                  />
                </Space>
              }
              key="environment"
            >
              {result.environment ? (
                <Card size="small" style={{ backgroundColor: '#f0f9ff' }}>
                  <Space>
                    <EnvironmentOutlined style={{ color: '#1890ff' }} />
                    <Text>{result.environment}</Text>
                  </Space>
                </Card>
              ) : (
                <Text type="secondary">Условия эксплуатации не указаны</Text>
              )}
            </Panel>

            {/* Functions */}
            <Panel
              header={
                <Space>
                  <Badge 
                    status={getStatusColor(result.functions)} 
                    text={<strong>Функции ({result.functions.length})</strong>}
                  />
                </Space>
              }
              key="functions"
            >
              {result.functions.length > 0 ? (
                <List
                  dataSource={result.functions}
                  renderItem={(item, index) => (
                    <List.Item key={index}>
                      <Space>
                        <ToolOutlined style={{ color: '#52c41a' }} />
                        <Text>{item}</Text>
                      </Space>
                    </List.Item>
                  )}
                />
              ) : (
                <Text type="secondary">Функции не найдены</Text>
              )}
            </Panel>
          </Collapse>
        </Card>
      ) : (
        <Alert
          message="Анализ завершен, но данные не найдены"
          description="Возможно, документы не содержат технического задания или данные представлены в неподдерживаемом формате"
          type="warning"
          showIcon
        />
      )}

      {/* Processing Metadata */}
      <Card size="small" title="Метаданные обработки">
        <Descriptions size="small" column={2}>
          <Descriptions.Item label="Время анализа">
            {new Date(result.timestamp).toLocaleString('ru-RU')}
          </Descriptions.Item>
          <Descriptions.Item label="Файлов обработано">
            {result.processing_metadata.processed_files || 0}
          </Descriptions.Item>
          <Descriptions.Item label="AI движок">
            {result.processing_metadata.ai_engine || 'Не указан'}
          </Descriptions.Item>
          <Descriptions.Item label="Orchestrator">
            {result.processing_metadata.llm_orchestrator_used ? (
              <Tag color="green">Включен</Tag>
            ) : (
              <Tag color="default">Отключен</Tag>
            )}
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </Space>
  );
};

export default TZDResults;
import React, { useState } from 'react';
import { Card, Typography, List, Tag, Button, Space, Alert, Collapse, Empty } from 'antd';
import { 
  ExclamationCircleOutlined, 
  InfoCircleOutlined, 
  WarningOutlined, 
  BugOutlined,
  ClearOutlined,
  ExpandOutlined,
  CompressOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { Title, Text } = Typography;
const { Panel } = Collapse;

export interface LogEntry {
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'debug';
  message: string;
  details?: string;
  source?: string;
}

interface LogsDisplayProps {
  logs: LogEntry[];
  title?: string;
  maxHeight?: number;
  showClear?: boolean;
  onClear?: () => void;
  compact?: boolean;
}

const LogsDisplay: React.FC<LogsDisplayProps> = ({
  logs,
  title,
  maxHeight = 300,
  showClear = true,
  onClear,
  compact = false,
}) => {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  const getLogIcon = (level: LogEntry['level']) => {
    switch (level) {
      case 'error':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'warning':
        return <WarningOutlined style={{ color: '#faad14' }} />;
      case 'info':
        return <InfoCircleOutlined style={{ color: '#1890ff' }} />;
      case 'debug':
        return <BugOutlined style={{ color: '#722ed1' }} />;
      default:
        return <InfoCircleOutlined />;
    }
  };

  const getLogColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
        return 'processing';
      case 'debug':
        return 'purple';
      default:
        return 'default';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString();
    } catch {
      return timestamp;
    }
  };

  const getLogCounts = () => {
    return logs.reduce((acc, log) => {
      acc[log.level] = (acc[log.level] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
  };

  const logCounts = getLogCounts();
  const hasErrors = logCounts.error > 0;
  const hasWarnings = logCounts.warning > 0;

  if (logs.length === 0) {
    return (
      <Card>
        <Title level={4}>{title || t('analysis.logs.title')}</Title>
        <Empty description={t('analysis.logs.info')} />
      </Card>
    );
  }

  const renderCompactView = () => (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4}>{title || t('analysis.logs.title')}</Title>
        <Space>
          {hasErrors && (
            <Tag color="error" icon={<ExclamationCircleOutlined />}>
              {logCounts.error} {t('analysis.logs.errors')}
            </Tag>
          )}
          {hasWarnings && (
            <Tag color="warning" icon={<WarningOutlined />}>
              {logCounts.warning} {t('analysis.logs.warnings')}
            </Tag>
          )}
          <Button
            type="text"
            icon={expanded ? <CompressOutlined /> : <ExpandOutlined />}
            onClick={() => setExpanded(!expanded)}
          />
        </Space>
      </div>

      <Collapse activeKey={expanded ? ['1'] : []} onChange={() => setExpanded(!expanded)}>
        <Panel header={`${logs.length} log entries`} key="1">
          {renderLogsList()}
        </Panel>
      </Collapse>
    </Card>
  );

  const renderLogsList = () => (
    <div style={{ maxHeight, overflowY: 'auto' }}>
      <List
        size="small"
        dataSource={logs}
        renderItem={(log, index) => (
          <List.Item key={index}>
            <List.Item.Meta
              avatar={getLogIcon(log.level)}
              title={
                <Space>
                  <Tag color={getLogColor(log.level)}>
                    {log.level.toUpperCase()}
                  </Tag>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    {formatTimestamp(log.timestamp)}
                  </Text>
                  {log.source && (
                    <Tag color="blue">
                      {log.source}
                    </Tag>
                  )}
                </Space>
              }
              description={
                <div>
                  <Text>{log.message}</Text>
                  {log.details && (
                    <div style={{ marginTop: 4 }}>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {log.details}
                      </Text>
                    </div>
                  )}
                </div>
              }
            />
          </List.Item>
        )}
      />
    </div>
  );

  const renderFullView = () => (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4}>{title || t('analysis.logs.title')} ({logs.length})</Title>
        <Space>
          {hasErrors && (
            <Alert
              message={`${logCounts.error} ${t('analysis.logs.errors')}`}
              type="error"
              showIcon
            />
          )}
          {hasWarnings && (
            <Alert
              message={`${logCounts.warning} ${t('analysis.logs.warnings')}`}
              type="warning"
              showIcon
            />
          )}
          {showClear && (
            <Button
              type="default"
              icon={<ClearOutlined />}
              size="small"
              onClick={onClear}
            >
              Clear
            </Button>
          )}
        </Space>
      </div>

      {renderLogsList()}
    </Card>
  );

  return compact ? renderCompactView() : renderFullView();
};

export default LogsDisplay;
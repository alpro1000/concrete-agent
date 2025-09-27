import { Table, Tag, Progress, Card, Typography, Space, Tooltip } from 'antd';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import type { ConcreteMatch, MaterialMatch, VolumeEntry } from '../types/api';

const { Title } = Typography;

interface ResultsTableProps<T> {
  title: string;
  data: T[];
  type: 'concrete' | 'materials' | 'volumes';
  loading?: boolean;
  size?: 'small' | 'middle' | 'large';
}

const ResultsTable = <T extends ConcreteMatch | MaterialMatch | VolumeEntry>({
  title,
  data,
  type,
  loading = false,
  size = 'middle',
}: ResultsTableProps<T>) => {
  const { t } = useTranslation();

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'green';
    if (confidence >= 0.6) return 'orange';
    return 'red';
  };

  const getConfidenceText = (confidence: number): string => {
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.6) return 'Medium';
    return 'Low';
  };

  const concreteColumns: ColumnsType<ConcreteMatch> = [
    {
      title: t('analysis.concrete.grades'),
      dataIndex: 'grade',
      key: 'grade',
      render: (grade: string) => <Tag color="blue">{grade}</Tag>,
      width: 150,
    },
    {
      title: t('analysis.concrete.location'),
      dataIndex: 'location',
      key: 'location',
      ellipsis: true,
    },
    {
      title: t('analysis.concrete.context'),
      dataIndex: 'context',
      key: 'context',
      ellipsis: {
        showTitle: false,
      },
      render: (context: string) => (
        <Tooltip placement="topLeft" title={context}>
          {context}
        </Tooltip>
      ),
    },
    {
      title: t('analysis.concrete.confidence'),
      dataIndex: 'confidence',
      key: 'confidence',
      width: 120,
      render: (confidence: number) => (
        <Space direction="vertical" size="small">
          <Progress 
            percent={Math.round(confidence * 100)} 
            size="small" 
            strokeColor={getConfidenceColor(confidence)}
            showInfo={false}
          />
          <Tag color={getConfidenceColor(confidence)}>
            {getConfidenceText(confidence)}
          </Tag>
        </Space>
      ),
      sorter: (a: ConcreteMatch, b: ConcreteMatch) => a.confidence - b.confidence,
    },
    {
      title: 'Method',
      dataIndex: 'method',
      key: 'method',
      width: 100,
      render: (method: string) => <Tag color="purple">{method}</Tag>,
    },
  ];

  const materialColumns: ColumnsType<MaterialMatch> = [
    {
      title: t('analysis.materials.type'),
      dataIndex: 'material',
      key: 'material',
      render: (material: string) => <Tag color="cyan">{material}</Tag>,
    },
    {
      title: t('analysis.materials.quantity'),
      key: 'quantity',
      render: (record: MaterialMatch) => (
        <Space>
          {record.quantity && <span>{record.quantity}</span>}
          {record.unit && <Tag color="geekblue">{record.unit}</Tag>}
        </Space>
      ),
      width: 150,
    },
    {
      title: t('analysis.concrete.location'),
      dataIndex: 'location',
      key: 'location',
      ellipsis: true,
    },
    {
      title: t('analysis.concrete.context'),
      dataIndex: 'context',
      key: 'context',
      ellipsis: {
        showTitle: false,
      },
      render: (context: string) => (
        <Tooltip placement="topLeft" title={context}>
          {context}
        </Tooltip>
      ),
    },
    {
      title: t('analysis.concrete.confidence'),
      dataIndex: 'confidence',
      key: 'confidence',
      width: 120,
      render: (confidence: number) => (
        <Space direction="vertical" size="small">
          <Progress 
            percent={Math.round(confidence * 100)} 
            size="small" 
            strokeColor={getConfidenceColor(confidence)}
            showInfo={false}
          />
          <Tag color={getConfidenceColor(confidence)}>
            {getConfidenceText(confidence)}
          </Tag>
        </Space>
      ),
      sorter: (a: MaterialMatch, b: MaterialMatch) => a.confidence - b.confidence,
    },
  ];

  const volumeColumns: ColumnsType<VolumeEntry> = [
    {
      title: t('analysis.volumes.items'),
      dataIndex: 'item',
      key: 'item',
      ellipsis: true,
    },
    {
      title: t('analysis.materials.quantity'),
      dataIndex: 'quantity',
      key: 'quantity',
      width: 120,
      sorter: (a: VolumeEntry, b: VolumeEntry) => a.quantity - b.quantity,
    },
    {
      title: t('analysis.materials.unit'),
      dataIndex: 'unit',
      key: 'unit',
      width: 100,
      render: (unit: string) => <Tag color="geekblue">{unit}</Tag>,
    },
    {
      title: t('analysis.volumes.category'),
      dataIndex: 'category',
      key: 'category',
      width: 150,
      render: (category: string) => category ? <Tag color="orange">{category}</Tag> : '-',
    },
    {
      title: t('analysis.concrete.location'),
      dataIndex: 'location',
      key: 'location',
      ellipsis: true,
      render: (location: string) => location || '-',
    },
  ];

  const getColumns = (): ColumnsType<any> => {
    switch (type) {
      case 'concrete':
        return concreteColumns;
      case 'materials':
        return materialColumns;
      case 'volumes':
        return volumeColumns;
      default:
        return [];
    }
  };

  return (
    <Card>
      <Title level={4}>{title} ({data.length})</Title>
      <Table
        columns={getColumns()}
        dataSource={data.map((item, index) => ({ ...item, key: index }))}
        loading={loading}
        size={size}
        scroll={{ x: 800 }}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) => 
            `${range[0]}-${range[1]} of ${total} items`,
        }}
      />
    </Card>
  );
};

export default ResultsTable;
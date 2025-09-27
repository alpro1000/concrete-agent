import React, { useState, useEffect } from 'react';
import { 
  Row, 
  Col, 
  Card, 
  Typography, 
  Table, 
  Button, 
  Space, 
  Tag, 
  Empty,
  message,
  Modal,
  Descriptions
} from 'antd';
import { 
  EyeOutlined, 
  DownloadOutlined, 
  DeleteOutlined,
  ReloadOutlined,
  HistoryOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

interface Report {
  id: string;
  date: string;
  type: 'concrete' | 'materials' | 'comparison';
  status: 'success' | 'failed' | 'processing';
  filesCount: number;
  processingTime?: number;
  results?: any;
}

const Reports: React.FC = () => {
  const { t } = useTranslation();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [detailsVisible, setDetailsVisible] = useState(false);

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    setLoading(true);
    try {
      // Simulate loading reports from localStorage or API
      const savedReports = localStorage.getItem('analysis-reports');
      if (savedReports) {
        setReports(JSON.parse(savedReports));
      } else {
        // Create some sample reports for demonstration
        const sampleReports: Report[] = [
          {
            id: '1',
            date: new Date(Date.now() - 86400000).toISOString(),
            type: 'materials',
            status: 'success',
            filesCount: 3,
            processingTime: 45,
          },
          {
            id: '2',
            date: new Date(Date.now() - 172800000).toISOString(),
            type: 'concrete',
            status: 'success',
            filesCount: 5,
            processingTime: 67,
          },
          {
            id: '3',
            date: new Date(Date.now() - 259200000).toISOString(),
            type: 'comparison',
            status: 'failed',
            filesCount: 2,
          },
        ];
        setReports(sampleReports);
        localStorage.setItem('analysis-reports', JSON.stringify(sampleReports));
      }
    } catch (error) {
      message.error('Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  const handleView = (report: Report) => {
    setSelectedReport(report);
    setDetailsVisible(true);
  };

  const handleDownload = (report: Report) => {
    // Simulate download
    const blob = new Blob([JSON.stringify(report, null, 2)], { 
      type: 'application/json' 
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report-${report.id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    message.success('Report downloaded');
  };

  const handleDelete = (report: Report) => {
    Modal.confirm({
      title: 'Delete Report',
      content: 'Are you sure you want to delete this report?',
      onOk: () => {
        const newReports = reports.filter(r => r.id !== report.id);
        setReports(newReports);
        localStorage.setItem('analysis-reports', JSON.stringify(newReports));
        message.success('Report deleted');
      },
    });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusColor = (status: Report['status']) => {
    switch (status) {
      case 'success':
        return 'success';
      case 'failed':
        return 'error';
      case 'processing':
        return 'processing';
      default:
        return 'default';
    }
  };

  const getTypeColor = (type: Report['type']) => {
    switch (type) {
      case 'concrete':
        return 'blue';
      case 'materials':
        return 'green';
      case 'comparison':
        return 'orange';
      default:
        return 'default';
    }
  };

  const columns: ColumnsType<Report> = [
    {
      title: t('reports.date'),
      dataIndex: 'date',
      key: 'date',
      render: (date: string) => formatDate(date),
      sorter: (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
    },
    {
      title: t('reports.type'),
      dataIndex: 'type',
      key: 'type',
      render: (type: Report['type']) => (
        <Tag color={getTypeColor(type)}>
          {t(`analysis.${type}.title`)}
        </Tag>
      ),
      filters: [
        { text: t('analysis.concrete.title'), value: 'concrete' },
        { text: t('analysis.materials.title'), value: 'materials' },
        { text: t('analysis.comparison.title'), value: 'comparison' },
      ],
      onFilter: (value, record) => record.type === value,
    },
    {
      title: t('reports.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: Report['status']) => (
        <Tag color={getStatusColor(status)}>
          {status.toUpperCase()}
        </Tag>
      ),
      filters: [
        { text: 'Success', value: 'success' },
        { text: 'Failed', value: 'failed' },
        { text: 'Processing', value: 'processing' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: 'Files',
      dataIndex: 'filesCount',
      key: 'filesCount',
      sorter: (a, b) => a.filesCount - b.filesCount,
    },
    {
      title: 'Processing Time',
      dataIndex: 'processingTime',
      key: 'processingTime',
      render: (time?: number) => time ? `${time}s` : '-',
      sorter: (a, b) => (a.processingTime || 0) - (b.processingTime || 0),
    },
    {
      title: t('reports.actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleView(record)}
          >
            {t('common.view')}
          </Button>
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => handleDownload(record)}
          >
            {t('common.download')}
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            {t('common.delete')}
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={[24, 24]}>
        <Col span={24}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={2}>
              <HistoryOutlined /> {t('reports.title')}
            </Title>
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              onClick={loadReports}
              loading={loading}
            >
              {t('common.refresh', { defaultValue: 'Refresh' })}
            </Button>
          </div>
        </Col>

        <Col span={24}>
          {reports.length === 0 ? (
            <Card>
              <Empty
                description={t('reports.recent')}
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            </Card>
          ) : (
            <Card>
              <Table
                columns={columns}
                dataSource={reports}
                loading={loading}
                rowKey="id"
                pagination={{
                  pageSize: 10,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total, range) => 
                    `${range[0]}-${range[1]} of ${total} reports`,
                }}
              />
            </Card>
          )}
        </Col>
      </Row>

      <Modal
        title="Report Details"
        open={detailsVisible}
        onCancel={() => setDetailsVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailsVisible(false)}>
            {t('common.close')}
          </Button>,
          <Button 
            key="download" 
            type="primary" 
            icon={<DownloadOutlined />}
            onClick={() => selectedReport && handleDownload(selectedReport)}
          >
            {t('common.download')}
          </Button>,
        ]}
        width={800}
      >
        {selectedReport && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="ID">{selectedReport.id}</Descriptions.Item>
            <Descriptions.Item label={t('reports.type')}>
              <Tag color={getTypeColor(selectedReport.type)}>
                {t(`analysis.${selectedReport.type}.title`)}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('reports.date')}>
              {formatDate(selectedReport.date)}
            </Descriptions.Item>
            <Descriptions.Item label={t('reports.status')}>
              <Tag color={getStatusColor(selectedReport.status)}>
                {selectedReport.status.toUpperCase()}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Files Count">
              {selectedReport.filesCount}
            </Descriptions.Item>
            <Descriptions.Item label="Processing Time">
              {selectedReport.processingTime ? `${selectedReport.processingTime}s` : '-'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default Reports;
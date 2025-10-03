import React, { useState, useEffect } from 'react';
import { Card, Tabs, Form, Input, Select, Button, Table, Space, message, Modal, Spin, Empty } from 'antd';
import { DeleteOutlined, EyeOutlined, DownloadOutlined, CheckCircleOutlined, ClockCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { login, getHistory, deleteAnalysis as deleteAnalysisApi, exportResults } from '../lib/api';
import type { User, Analysis } from '../types';
import { languageOptions } from '../i18n';
import './AccountPage.css';

const { TabPane } = Tabs;

const AccountPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [user, setUser] = useState<User | null>(null);
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(false);
  const [analysesLoading, setAnalysesLoading] = useState(false);

  useEffect(() => {
    loadUserData();
    loadAnalyses();
  }, []);

  const loadUserData = async () => {
    try {
      const response = await login();
      setUser(response as User);
      localStorage.setItem('auth_token', (response as any).token);
    } catch (error) {
      console.error('Failed to load user data:', error);
    }
  };

  const loadAnalyses = async () => {
    setAnalysesLoading(true);
    try {
      const response = await getHistory();
      setAnalyses(response as Analysis[]);
    } catch (error) {
      console.error('Failed to load analyses:', error);
    } finally {
      setAnalysesLoading(false);
    }
  };

  const handleSaveProfile = async (values: any) => {
    setLoading(true);
    try {
      // Mock save - in real app, call API
      await new Promise(resolve => setTimeout(resolve, 500));
      message.success(t('profile.saved'));
      
      // Update language if changed
      if (values.language !== i18n.language) {
        i18n.changeLanguage(values.language);
        localStorage.setItem('language', values.language);
      }
    } catch (error) {
      message.error(t('messages.error'));
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAnalysis = (analysisId: string) => {
    Modal.confirm({
      title: t('analyses.deleteConfirm'),
      okText: t('common.yes'),
      cancelText: t('common.no'),
      okType: 'danger',
      onOk: async () => {
        try {
          await deleteAnalysisApi(analysisId);
          setAnalyses(analyses.filter(a => a.id !== analysisId));
          message.success(t('analyses.deleted'));
        } catch (error) {
          message.error(t('messages.error'));
        }
      },
    });
  };

  const handleViewResults = (_analysisId: string) => {
    message.info('View results feature will be integrated with main results panel');
  };

  const handleDownload = async (analysisId: string) => {
    try {
      const blob = await exportResults(analysisId, 'pdf');
      const url = URL.createObjectURL(blob as Blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analysis_${analysisId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      message.success('Downloaded successfully');
    } catch (error) {
      message.error('Download failed');
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'processing':
        return <ClockCircleOutlined style={{ color: '#1890ff' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#f5222d' }} />;
      default:
        return null;
    }
  };

  const analysesColumns = [
    {
      title: t('analyses.fileName'),
      dataIndex: 'filename',
      key: 'filename',
    },
    {
      title: t('analyses.uploadDate'),
      dataIndex: 'uploaded_at',
      key: 'uploaded_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
    {
      title: t('analyses.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Space>
          {statusIcon(status)}
          {t(`status.${status}`)}
        </Space>
      ),
    },
    {
      title: t('analyses.actions'),
      key: 'actions',
      render: (_: any, record: Analysis) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewResults(record.id)}
          >
            {t('analyses.viewResults')}
          </Button>
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => handleDownload(record.id)}
          >
            {t('analyses.download')}
          </Button>
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteAnalysis(record.id)}
          >
            {t('analyses.delete')}
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="account-page">
      <div className="account-container">
        <h2>{t('nav.account')}</h2>

        <Tabs defaultActiveKey="profile">
          <TabPane tab={t('dashboard.profile')} key="profile">
            <Card>
              {user ? (
                <Form
                  layout="vertical"
                  initialValues={user}
                  onFinish={handleSaveProfile}
                >
                  <Form.Item
                    label={t('profile.name')}
                    name="name"
                    rules={[{ required: true }]}
                  >
                    <Input />
                  </Form.Item>

                  <Form.Item
                    label={t('profile.email')}
                    name="email"
                    rules={[{ required: true, type: 'email' }]}
                  >
                    <Input />
                  </Form.Item>

                  <Form.Item
                    label={t('profile.language')}
                    name="language"
                  >
                    <Select>
                      {languageOptions.map((lang) => (
                        <Select.Option key={lang.code} value={lang.code}>
                          {lang.flag} {lang.name}
                        </Select.Option>
                      ))}
                    </Select>
                  </Form.Item>

                  <Form.Item>
                    <Space>
                      <Button type="primary" htmlType="submit" loading={loading}>
                        {t('profile.saveChanges')}
                      </Button>
                      <span className="member-since">
                        {t('profile.createdAt')}: {new Date(user.created_at).toLocaleDateString()}
                      </span>
                    </Space>
                  </Form.Item>
                </Form>
              ) : (
                <Spin />
              )}
            </Card>
          </TabPane>

          <TabPane tab={t('dashboard.analyses')} key="analyses">
            <Card>
              {analysesLoading ? (
                <div style={{ textAlign: 'center', padding: '40px' }}>
                  <Spin tip={t('analyses.loading')} />
                </div>
              ) : analyses.length > 0 ? (
                <Table
                  dataSource={analyses}
                  columns={analysesColumns}
                  rowKey="id"
                  pagination={{ pageSize: 10 }}
                />
              ) : (
                <Empty
                  description={t('analyses.noAnalyses')}
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              )}
            </Card>
          </TabPane>

          <TabPane tab={t('dashboard.settings')} key="settings">
            <Card>
              <div className="settings-placeholder">
                <p>{t('dashboard.settingsPlaceholder')}</p>
              </div>
            </Card>
          </TabPane>
        </Tabs>
      </div>
    </div>
  );
};

export default AccountPage;

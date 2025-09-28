import React, { useState } from 'react';
import { 
  Row, 
  Col, 
  Card, 
  Typography, 
  Button, 
  Input, 
  Select, 
  Switch, 
  Space, 
  Form, 
  message,
  Alert
} from 'antd';
import { PlayCircleOutlined, SettingOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import FileUpload from '../components/FileUpload';
import LanguageSelector from '../components/LanguageSelector';
import type { Language } from '../types/api';

const { Title, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

interface AnalysisFormData {
  docs: File[];
  smeta: File[];
  drawings: File[];
  material_query?: string;
  use_claude: boolean;
  claude_mode: string;
  language: Language;
  include_drawing_analysis: boolean;
  analysis_type: 'concrete' | 'materials' | 'comparison' | 'tov' | 'integrated';
  project_name?: string;
  project_duration_days?: number;
}

interface HomeProps {
  onAnalysisStart: (data: AnalysisFormData) => void;
}

const Home: React.FC<HomeProps> = ({ onAnalysisStart }) => {
  const { t, i18n } = useTranslation();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [docs, setDocs] = useState<File[]>([]);
  const [smeta, setSmeta] = useState<File[]>([]);
  const [drawings, setDrawings] = useState<File[]>([]);

  const handleAnalyze = async () => {
    try {
      setLoading(true);

      // Validate form
      const values = await form.validateFields();
      
      if (docs.length === 0 && smeta.length === 0 && drawings.length === 0) {
        message.error(t('validation.atLeastOneFileRequired'));
        return;
      }

      const analysisData: AnalysisFormData = {
        docs,
        smeta,
        drawings,
        material_query: values.material_query,
        use_claude: values.use_claude,
        claude_mode: values.claude_mode,
        language: values.language || (i18n.language as Language),
        include_drawing_analysis: values.include_drawing_analysis,
        analysis_type: values.analysis_type,
        project_name: values.project_name,
        project_duration_days: values.project_duration_days,
      };

      // Call the parent component to handle the analysis
      onAnalysisStart(analysisData);

    } catch (error) {
      console.error('Form validation failed:', error);
      message.error(t('errors.unknownError'));
    } finally {
      setLoading(false);
    }
  };

  const renderAnalysisOptions = () => (
    <Card title={<><SettingOutlined /> {t('home.options.title')}</>}>
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          use_claude: true,
          claude_mode: 'enhancement',
          language: i18n.language,
          include_drawing_analysis: false,
          analysis_type: 'materials',
        }}
      >
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label={t('nav.analysis')}
              name="analysis_type"
            >
              <Select>
                <Option value="materials">{t('analysis.materials.title')}</Option>
                <Option value="concrete">{t('analysis.concrete.title')}</Option>
                <Option value="comparison">{t('analysis.comparison.title')}</Option>
                <Option value="tov">{t('analysis.tov.title')}</Option>
                <Option value="integrated">{t('analysis.integrated.title')}</Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label={t('home.options.language')}
              name="language"
            >
              <LanguageSelector />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label={t('home.options.useClaude')}
              name="use_claude"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label={t('home.options.claudeMode')}
              name="claude_mode"
            >
              <Select>
                <Option value="enhancement">Enhancement</Option>
                <Option value="primary">Primary</Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          label={t('home.options.includeDrawings')}
          name="include_drawing_analysis"
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>

        <Form.Item
          label={t('home.project.name')}
          name="project_name"
        >
          <Input placeholder={t('home.project.namePlaceholder')} />
        </Form.Item>

        <Form.Item
          label={t('home.project.duration')}
          name="project_duration_days"
        >
          <Input type="number" placeholder={t('home.project.durationPlaceholder')} />
        </Form.Item>

        <Form.Item
          label={t('home.materialQuery.title')}
          name="material_query"
        >
          <TextArea
            placeholder={t('home.materialQuery.placeholder')}
            rows={3}
          />
        </Form.Item>

        <Alert
          message={t('home.materialQuery.examples')}
          type="info"
          showIcon
          style={{ marginTop: 8 }}
        />
      </Form>
    </Card>
  );

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={[24, 24]}>
        <Col span={24}>
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <Title level={1}>{t('home.title')}</Title>
            <Paragraph style={{ fontSize: '18px', color: '#666' }}>
              {t('home.subtitle')}
            </Paragraph>
          </div>
        </Col>

        <Col xs={24} lg={8}>
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <FileUpload
              title={t('home.upload.docs.title')}
              description={t('home.upload.docs.description')}
              value={docs}
              onChange={setDocs}
              maxFiles={10}
              maxSize={10}
              multiple
              acceptedTypes={['.pdf', '.docx', '.txt', '.doc', '.rtf']}
            />
          </Space>
        </Col>

        <Col xs={24} lg={8}>
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <FileUpload
              title={t('home.upload.smeta.title')}
              description={t('home.upload.smeta.description')}
              value={smeta}
              onChange={setSmeta}
              maxFiles={5}
              maxSize={10}
              multiple={true}
              acceptedTypes={['.xlsx', '.xls', '.xml', '.csv', '.xc4', '.json', '.ods']}
            />
          </Space>
        </Col>

        <Col xs={24} lg={8}>
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <FileUpload
              title={t('home.upload.drawings.title')}
              description={t('home.upload.drawings.description')}
              value={drawings}
              onChange={setDrawings}
              maxFiles={10}
              maxSize={50}
              multiple={true}
              acceptedTypes={['.dwg', '.dxf', '.pdf', '.ifc', '.step', '.iges', '.3dm']}
            />
          </Space>
        </Col>

        <Col span={24}>
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            {renderAnalysisOptions()}

            <Card>
              <Button
                type="primary"
                size="large"
                icon={<PlayCircleOutlined />}
                onClick={handleAnalyze}
                loading={loading}
                disabled={docs.length === 0 && smeta.length === 0 && drawings.length === 0}
                block
              >
                {t('home.startAnalysis')}
              </Button>
            </Card>
          </Space>
        </Col>
      </Row>
    </div>
  );
};

export default Home;
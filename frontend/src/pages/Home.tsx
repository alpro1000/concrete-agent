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
  smeta?: File;
  material_query?: string;
  use_claude: boolean;
  claude_mode: string;
  language: Language;
  include_drawing_analysis: boolean;
  analysis_type: 'concrete' | 'materials' | 'comparison';
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

  const handleAnalyze = async () => {
    try {
      setLoading(true);

      // Validate form
      const values = await form.validateFields();
      
      if (docs.length === 0) {
        message.error(t('validation.fileRequired'));
        return;
      }

      const analysisData: AnalysisFormData = {
        docs,
        smeta: smeta[0],
        material_query: values.material_query,
        use_claude: values.use_claude,
        claude_mode: values.claude_mode,
        language: values.language || (i18n.language as Language),
        include_drawing_analysis: values.include_drawing_analysis,
        analysis_type: values.analysis_type,
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

        <Col xs={24} lg={12}>
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <FileUpload
              title={t('home.fileUpload.title')}
              description={t('home.fileUpload.description')}
              value={docs}
              onChange={setDocs}
              maxFiles={10}
              maxSize={10}
              multiple
            />

            <Card title="Budget/Smeta (Optional)" size="small">
              <FileUpload
                value={smeta}
                onChange={setSmeta}
                maxFiles={1}
                maxSize={10}
                multiple={false}
                acceptedTypes={['.xlsx', '.csv', '.pdf']}
              />
            </Card>
          </Space>
        </Col>

        <Col xs={24} lg={12}>
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            {renderAnalysisOptions()}

            <Card>
              <Button
                type="primary"
                size="large"
                icon={<PlayCircleOutlined />}
                onClick={handleAnalyze}
                loading={loading}
                disabled={docs.length === 0}
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
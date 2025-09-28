import { useState } from 'react';
import { Layout, Menu, ConfigProvider, theme } from 'antd';
import { 
  HomeOutlined, 
  BarChartOutlined, 
  FileTextOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

// Import pages
import Home from './pages/Home';
import Analysis from './pages/Analysis';
import Reports from './pages/Reports';

// Import components
import LanguageSelector from './components/LanguageSelector';

// Import i18n
import './i18n';

// Import styles
import './styles/globals.css';

const { Header, Content, Footer } = Layout;

interface AnalysisData {
  docs: File[];
  smeta: File[];
  drawings: File[];
  material_query?: string;
  use_claude: boolean;
  claude_mode: string;
  language: 'cs' | 'en' | 'ru';
  include_drawing_analysis: boolean;
  analysis_type: 'concrete' | 'materials' | 'comparison' | 'tov' | 'integrated';
  project_name?: string;
  project_duration_days?: number;
}

function App() {
  const { t } = useTranslation();
  const [currentPage, setCurrentPage] = useState<'home' | 'analysis' | 'reports'>('home');
  const [analysisData, setAnalysisData] = useState<AnalysisData | null>(null);

  const handleAnalysisStart = (data: AnalysisData) => {
    setAnalysisData(data);
    setCurrentPage('analysis');
  };

  const handleBackToHome = () => {
    setCurrentPage('home');
    setAnalysisData(null);
  };

  const menuItems = [
    {
      key: 'home',
      icon: <HomeOutlined />,
      label: t('nav.home'),
    },
    {
      key: 'reports',
      icon: <FileTextOutlined />,
      label: t('nav.reports'),
    },
  ];

  const renderContent = () => {
    switch (currentPage) {
      case 'home':
        return <Home onAnalysisStart={handleAnalysisStart} />;
      case 'analysis':
        return analysisData ? (
          <Analysis analysisData={analysisData} onBack={handleBackToHome} />
        ) : (
          <Home onAnalysisStart={handleAnalysisStart} />
        );
      case 'reports':
        return <Reports />;
      default:
        return <Home onAnalysisStart={handleAnalysisStart} />;
    }
  };

  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1890ff',
          borderRadius: 6,
        },
      }}
    >
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          backgroundColor: '#001529',
          padding: '0 24px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{ 
              color: 'white', 
              fontSize: '20px', 
              fontWeight: 'bold',
              marginRight: '32px'
            }}>
              <BarChartOutlined style={{ marginRight: '8px' }} />
              {t('home.title')}
            </div>
            
            <Menu
              theme="dark"
              mode="horizontal"
              selectedKeys={[currentPage]}
              items={menuItems}
              onClick={({ key }) => setCurrentPage(key as any)}
              style={{ 
                backgroundColor: 'transparent', 
                borderBottom: 'none',
                minWidth: '200px'
              }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <LanguageSelector />
          </div>
        </Header>

        <Content className="main-content">
          {renderContent()}
        </Content>

        <Footer style={{ textAlign: 'center', backgroundColor: '#f0f2f5' }}>
          Construction Analysis Frontend ©2024 | 
          Built with React + Vite + TypeScript + Ant Design
        </Footer>
      </Layout>
    </ConfigProvider>
  );
}

export default App;

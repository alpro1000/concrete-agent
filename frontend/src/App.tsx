import { Layout, ConfigProvider, theme } from 'antd';
import { 
  BarChartOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

// Import page
import TZDAnalysis from './pages/TZDAnalysis';

// Import components
import LanguageSelector from './components/LanguageSelector';

// Import i18n
import './i18n';

// Import styles
import './styles/globals.css';

const { Header, Content, Footer } = Layout;

function App() {
  useTranslation(); // Initialize translation

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
              TZD Reader - Анализ технических заданий
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <LanguageSelector />
          </div>
        </Header>

        <Content className="main-content">
          <TZDAnalysis />
        </Content>

        <Footer style={{ textAlign: 'center', backgroundColor: '#f0f2f5' }}>
          TZD Reader ©2024 | Built with React + Vite + TypeScript + Ant Design
        </Footer>
      </Layout>
    </ConfigProvider>
  );
}

export default App;

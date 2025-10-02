import { Layout, ConfigProvider, theme } from 'antd';

// Import pages
import ProjectAnalysis from './pages/ProjectAnalysis';

// Import components
import Header from './components/Header';

// Import i18n
import './i18n';

// Import styles
import './styles/globals.css';

const { Content, Footer } = Layout;

function App() {
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
        <Header />

        <Content className="main-content">
          <ProjectAnalysis />
        </Content>

        <Footer style={{ textAlign: 'center', backgroundColor: '#f0f2f5' }}>
          Stav Agent ©2024 | Built with React + Vite + TypeScript + Ant Design
        </Footer>
      </Layout>
    </ConfigProvider>
  );
}

export default App;

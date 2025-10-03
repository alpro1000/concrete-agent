import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from 'antd';
import Header from './components/Header';
import UploadPage from './pages/UploadPage';
import AccountPage from './pages/AccountPage';
import './App.css';

const { Content, Footer } = Layout;

function App() {
  return (
    <Router>
      <Layout style={{ minHeight: '100vh' }}>
        <Header />
        <Content style={{ padding: '0', background: '#fff' }}>
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/account" element={<AccountPage />} />
          </Routes>
        </Content>
        <Footer style={{ textAlign: 'center', background: '#f0f2f5' }}>
          © 2025 Stav Agent
        </Footer>
      </Layout>
    </Router>
  );
}

export default App;

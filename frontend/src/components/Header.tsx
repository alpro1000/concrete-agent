import React from 'react';
import { Layout, Select, Menu, Drawer } from 'antd';
import { GlobalOutlined, MenuOutlined } from '@ant-design/icons';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { languageOptions } from '../i18n';
import './Header.css';

const { Header: AntHeader } = Layout;

const Header: React.FC = () => {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  const handleLanguageChange = (value: string) => {
    i18n.changeLanguage(value);
    localStorage.setItem('language', value);
  };

  const menuItems = [
    {
      key: '/',
      label: <Link to="/">{t('nav.upload')}</Link>,
    },
    {
      key: '/account',
      label: <Link to="/account">{t('nav.account')}</Link>,
    },
  ];

  return (
    <AntHeader className="app-header">
      <div className="header-content">
        <div className="logo-section">
          <h1 className="app-title">{t('app.name')}</h1>
          <span className="app-tagline">{t('app.tagline')}</span>
        </div>
        
        <div className="desktop-nav">
          <Menu
            mode="horizontal"
            selectedKeys={[location.pathname]}
            items={menuItems}
            style={{ flex: 1, minWidth: 0, backgroundColor: 'transparent', borderBottom: 'none' }}
          />
          
          <Select
            value={i18n.language}
            onChange={handleLanguageChange}
            style={{ width: 150 }}
            suffixIcon={<GlobalOutlined />}
          >
            {languageOptions.map((lang) => (
              <Select.Option key={lang.code} value={lang.code}>
                {lang.flag} {lang.name}
              </Select.Option>
            ))}
          </Select>
        </div>

        <div className="mobile-nav">
          <MenuOutlined onClick={() => setMobileMenuOpen(true)} style={{ fontSize: '24px', cursor: 'pointer' }} />
        </div>

        <Drawer
          title={t('app.name')}
          placement="right"
          onClose={() => setMobileMenuOpen(false)}
          open={mobileMenuOpen}
        >
          <Menu
            mode="vertical"
            selectedKeys={[location.pathname]}
            items={menuItems}
          />
          <div style={{ marginTop: '20px' }}>
            <Select
              value={i18n.language}
              onChange={handleLanguageChange}
              style={{ width: '100%' }}
              suffixIcon={<GlobalOutlined />}
            >
              {languageOptions.map((lang) => (
                <Select.Option key={lang.code} value={lang.code}>
                  {lang.flag} {lang.name}
                </Select.Option>
              ))}
            </Select>
          </div>
        </Drawer>
      </div>
    </AntHeader>
  );
};

export default Header;

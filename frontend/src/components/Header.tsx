import React from "react";
import { useTranslation } from "react-i18next";

const Header: React.FC = () => {
  const { i18n } = useTranslation();

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
  };

  return (
    <header 
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        backgroundColor: '#003333', // dark teal
        color: 'white',
        padding: '12px 24px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
      }}
    >
      <div 
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
        }}
      >
        <img 
          src="/assets/stav-logo.svg" 
          alt="Stav Agent Logo" 
          style={{
            height: '48px',
            width: 'auto',
          }}
        />
        <h1 
          style={{
            fontSize: '20px',
            fontWeight: 'bold',
            margin: 0,
          }}
        >
          Stav Agent
        </h1>
      </div>

      <div 
        style={{
          display: 'flex',
          gap: '8px',
        }}
      >
        <button 
          onClick={() => changeLanguage("cs")} 
          style={{
            padding: '6px 12px',
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            fontSize: '20px',
            transition: 'opacity 0.2s',
          }}
          onMouseEnter={(e) => e.currentTarget.style.opacity = '0.7'}
          onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
          title="Čeština"
        >
          🇨🇿
        </button>
        <button 
          onClick={() => changeLanguage("ru")} 
          style={{
            padding: '6px 12px',
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            fontSize: '20px',
            transition: 'opacity 0.2s',
          }}
          onMouseEnter={(e) => e.currentTarget.style.opacity = '0.7'}
          onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
          title="Русский"
        >
          🇷🇺
        </button>
        <button 
          onClick={() => changeLanguage("en")} 
          style={{
            padding: '6px 12px',
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            fontSize: '20px',
            transition: 'opacity 0.2s',
          }}
          onMouseEnter={(e) => e.currentTarget.style.opacity = '0.7'}
          onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
          title="English"
        >
          🇬🇧
        </button>
      </div>
    </header>
  );
};

export default Header;

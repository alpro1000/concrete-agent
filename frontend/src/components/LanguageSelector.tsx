import React from 'react';
import { Select, Space } from 'antd';
import { GlobalOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { languageOptions } from '../i18n';
import type { Language } from '../types/api';

const { Option } = Select;

interface LanguageSelectorProps {
  value?: Language;
  onChange?: (language: Language) => void;
  size?: 'small' | 'middle' | 'large';
  style?: React.CSSProperties;
}

const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  value,
  onChange,
  size = 'middle',
  style,
}) => {
  const { i18n } = useTranslation();

  const handleChange = (selectedLanguage: Language) => {
    i18n.changeLanguage(selectedLanguage);
    onChange?.(selectedLanguage);
  };

  const currentLanguage = (value || i18n.language) as Language;

  return (
    <Select
      value={currentLanguage}
      onChange={handleChange}
      size={size}
      style={{ minWidth: 150, ...style }}
      suffixIcon={<GlobalOutlined />}
      optionLabelProp="label"
    >
      {languageOptions.map((option) => (
        <Option key={option.code} value={option.code} label={
          <Space>
            <span>{option.flag}</span>
            <span>{option.name}</span>
          </Space>
        }>
          <Space>
            <span style={{ fontSize: '16px' }}>{option.flag}</span>
            <span>{option.name}</span>
          </Space>
        </Option>
      ))}
    </Select>
  );
};

export default LanguageSelector;
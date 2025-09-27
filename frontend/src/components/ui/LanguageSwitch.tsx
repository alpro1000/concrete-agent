// src/components/ui/LanguageSwitch.tsx
// Komponenta pro přepínání jazyků

import React from 'react';
import {
  FormControl,
  Select,
  MenuItem,
  Box,
  Typography,
  SelectChangeEvent,
} from '@mui/material';
import { Language as LanguageIcon } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { Language, supportedLanguages, getLanguageNames } from '../../utils/i18n';

interface LanguageSwitchProps {
  variant?: 'outlined' | 'standard' | 'filled';
  size?: 'small' | 'medium';
  showLabel?: boolean;
}

export const LanguageSwitch: React.FC<LanguageSwitchProps> = ({
  variant = 'outlined',
  size = 'small',
  showLabel = true
}) => {
  const { i18n, t } = useTranslation();
  const currentLanguage = i18n.language as Language;
  
  const handleLanguageChange = (event: SelectChangeEvent<string>) => {
    const newLanguage = event.target.value as Language;
    i18n.changeLanguage(newLanguage);
  };

  const languageNames = getLanguageNames(currentLanguage);

  // Mapování jazyků na jejich vlajky (emoji)
  const languageFlags: Record<Language, string> = {
    cs: '🇨🇿',
    en: '🇬🇧',
    ru: '🇷🇺'
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      {showLabel && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <LanguageIcon fontSize="small" />
          <Typography variant="body2">
            {t('form.language')}
          </Typography>
        </Box>
      )}
      
      <FormControl variant={variant} size={size} sx={{ minWidth: 120 }}>
        <Select
          value={currentLanguage}
          onChange={handleLanguageChange}
          sx={{
            '& .MuiSelect-select': {
              display: 'flex',
              alignItems: 'center',
              gap: 1,
            },
          }}
        >
          {supportedLanguages.map((lang) => (
            <MenuItem 
              key={lang} 
              value={lang}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
              }}
            >
              <span style={{ fontSize: '1.2em' }}>
                {languageFlags[lang]}
              </span>
              <span>{languageNames[lang]}</span>
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Box>
  );
};
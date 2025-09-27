// src/components/agents/ConcreteAgent.tsx
// Komponenta pro zobrazení výsledků ConcreteAgent

import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  Alert,
  Skeleton,
  AccordionSummary,
  AccordionDetails,
  Accordion,
} from '@mui/material';
import { ExpandMore, Construction } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { ConcreteAnalysisResult } from '../../types';
import { DataTable, Column } from '../ui/DataTable';

interface ConcreteAgentProps {
  data: ConcreteAnalysisResult | null;
  loading: boolean;
  expanded?: boolean;
  onExpandChange?: (expanded: boolean) => void;
}

export const ConcreteAgent: React.FC<ConcreteAgentProps> = ({
  data,
  loading,
  expanded = false,
  onExpandChange
}) => {
  const { t } = useTranslation();

  // Definice sloupců pro tabulku
  const columns: Column[] = [
    {
      id: 'grade',
      label: t('agents.concrete.grade'),
      minWidth: 100,
      type: 'badge',
    },
    {
      id: 'location',
      label: t('agents.concrete.location'),
      minWidth: 150,
    },
    {
      id: 'context',
      label: t('agents.concrete.context'),
      minWidth: 200,
    },
    {
      id: 'exposure_classes',
      label: t('agents.concrete.exposureClasses'),
      minWidth: 120,
      format: (value: string[]) => (
        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
          {value?.map((cls, index) => (
            <Chip key={index} label={cls} size="small" variant="outlined" />
          )) || '-'}
        </Box>
      ),
    },
    {
      id: 'confidence',
      label: t('agents.concrete.confidence'),
      minWidth: 100,
      type: 'confidence',
      align: 'center',
    },
    {
      id: 'source_document',
      label: t('agents.concrete.source'),
      minWidth: 150,
      format: (value: string) => {
        const filename = value?.split('/').pop() || value;
        return filename?.length > 20 ? `${filename.slice(0, 17)}...` : filename;
      },
    },
  ];

  const renderContent = () => {
    if (loading) {
      return (
        <Box sx={{ p: 2 }}>
          <Skeleton variant="text" width="60%" />
          <Skeleton variant="rectangular" height={200} sx={{ mt: 1 }} />
        </Box>
      );
    }

    if (!data || !data.success) {
      return (
        <Alert severity="error" sx={{ m: 2 }}>
          {data?.success === false 
            ? t('results.error')
            : t('agents.concrete.noGrades')
          }
        </Alert>
      );
    }

    if (!data.grades || data.grades.length === 0) {
      return (
        <Alert severity="info" sx={{ m: 2 }}>
          {t('agents.concrete.noGrades')}
        </Alert>
      );
    }

    return (
      <Box sx={{ p: 2 }}>
        {/* Statistiky */}
        <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Chip 
            icon={<Construction />}
            label={t('agents.concrete.totalGrades', { count: data.total_grades })}
            color="primary"
            variant="outlined"
          />
          {data.summary?.unique_grades && (
            <Chip 
              label={`Unikátní marky: ${data.summary.unique_grades.length}`}
              variant="outlined"
            />
          )}
        </Box>

        {/* Přehled unikátních marky */}
        {data.summary?.unique_grades && data.summary.unique_grades.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Nalezené marky betonu:
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {data.summary.unique_grades.map((grade, index) => (
                <Chip 
                  key={index} 
                  label={grade} 
                  color="primary"
                  size="small"
                />
              ))}
            </Box>
          </Box>
        )}

        {/* Tabulka s detaily */}
        <DataTable
          columns={columns}
          rows={data.grades}
          emptyMessage={t('agents.concrete.noGrades')}
          defaultRowsPerPage={5}
          maxHeight={300}
        />
      </Box>
    );
  };

  if (onExpandChange) {
    return (
      <Accordion 
        expanded={expanded} 
        onChange={(_, isExpanded) => onExpandChange(isExpanded)}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Construction color="primary" />
            <Typography variant="h6">
              {t('agents.concrete.title')}
            </Typography>
            {data && data.success && (
              <Chip 
                label={data.total_grades || 0}
                size="small"
                color="primary"
              />
            )}
          </Box>
        </AccordionSummary>
        <AccordionDetails sx={{ p: 0 }}>
          {renderContent()}
        </AccordionDetails>
      </Accordion>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <Construction color="primary" />
          <Typography variant="h6">
            {t('agents.concrete.title')}
          </Typography>
          {data && data.success && (
            <Chip 
              label={data.total_grades || 0}
              size="small"
              color="primary"
            />
          )}
        </Box>
        {renderContent()}
      </CardContent>
    </Card>
  );
};
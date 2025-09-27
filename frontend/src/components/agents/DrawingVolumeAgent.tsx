// src/components/agents/DrawingVolumeAgent.tsx
// Komponenta pro zobrazení výsledků DrawingVolumeAgent

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
import { ExpandMore, Architecture, Engineering } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { DrawingAnalysisResult } from '../../types';
import { DataTable, Column } from '../ui/DataTable';

interface DrawingVolumeAgentProps {
  data: DrawingAnalysisResult | null;
  loading: boolean;
  expanded?: boolean;
  onExpandChange?: (expanded: boolean) => void;
}

export const DrawingVolumeAgent: React.FC<DrawingVolumeAgentProps> = ({
  data,
  loading,
  expanded = false,
  onExpandChange
}) => {
  const { t } = useTranslation();

  // Definice sloupců pro tabulku
  const columns: Column[] = [
    {
      id: 'element_type',
      label: t('agents.drawing.element'),
      minWidth: 120,
      type: 'badge',
    },
    {
      id: 'geometry',
      label: t('agents.drawing.geometry'),
      minWidth: 150,
    },
    {
      id: 'volume',
      label: t('agents.drawing.volume'),
      minWidth: 120,
      type: 'number',
      format: (value: number, row: any) => {
        if (value) {
          return `${value.toFixed(2)} m³`;
        } else if (row.area) {
          return `${row.area.toFixed(2)} m²`;
        }
        return '-';
      },
      align: 'right',
    },
    {
      id: 'source',
      label: t('agents.drawing.source'),
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
        <Alert severity="warning" sx={{ m: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Engineering />
            <Box>
              <Typography variant="body2" fontWeight="medium">
                Analýza výkresů není k dispozici
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Tato funkce je zatím ve vývoji. DrawingVolumeAgent bude brzy dostupný.
              </Typography>
            </Box>
          </Box>
        </Alert>
      );
    }

    if (!data.elements || data.elements.length === 0) {
      return (
        <Alert severity="info" sx={{ m: 2 }}>
          {t('agents.drawing.noElements')}
        </Alert>
      );
    }

    return (
      <Box sx={{ p: 2 }}>
        {/* Statistiky */}
        <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Chip 
            icon={<Architecture />}
            label={t('agents.drawing.totalElements', { count: data.total_elements })}
            color="primary"
            variant="outlined"
          />
        </Box>

        {/* Informace o beta funkci */}
        <Alert severity="info" sx={{ mb: 2 }}>
          <Typography variant="body2">
            <strong>Beta funkce:</strong> Analýza geometrie z výkresů je experimentální funkce. 
            Výsledky mohou být neúplné nebo nepřesné.
          </Typography>
        </Alert>

        {/* Tabulka s detaily */}
        <DataTable
          columns={columns}
          rows={data.elements}
          emptyMessage={t('agents.drawing.noElements')}
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
            <Architecture color="primary" />
            <Typography variant="h6">
              {t('agents.drawing.title')}
            </Typography>
            <Chip 
              label="BETA"
              size="small"
              color="warning"
              variant="outlined"
            />
            {data && data.success && (
              <Chip 
                label={data.total_elements || 0}
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
          <Architecture color="primary" />
          <Typography variant="h6">
            {t('agents.drawing.title')}
          </Typography>
          <Chip 
            label="BETA"
            size="small"
            color="warning"
            variant="outlined"
          />
          {data && data.success && (
            <Chip 
              label={data.total_elements || 0}
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
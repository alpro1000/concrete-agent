// src/components/agents/VolumeAgent.tsx
// Komponenta pro zobrazení výsledků VolumeAgent

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
  Grid,
} from '@mui/material';
import { ExpandMore, Assessment, Euro } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { VolumeAnalysisResult } from '../../types';
import { DataTable, Column } from '../ui/DataTable';
import { Doughnut, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

// Registrace Chart.js komponent
ChartJS.register(
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

interface VolumeAgentProps {
  data: VolumeAnalysisResult | null;
  loading: boolean;
  expanded?: boolean;
  onExpandChange?: (expanded: boolean) => void;
}

export const VolumeAgent: React.FC<VolumeAgentProps> = ({
  data,
  loading,
  expanded = false,
  onExpandChange
}) => {
  const { t } = useTranslation();

  // Definice sloupců pro tabulku
  const columns: Column[] = [
    {
      id: 'concrete_grade',
      label: t('agents.volume.grade'),
      minWidth: 100,
      type: 'badge',
    },
    {
      id: 'construction_element',
      label: t('agents.volume.element'),
      minWidth: 150,
    },
    {
      id: 'volume_m3',
      label: t('agents.volume.volume'),
      minWidth: 100,
      type: 'number',
      format: (value: number) => value ? `${value.toFixed(2)} m³` : '-',
      align: 'right',
    },
    {
      id: 'area_m2',
      label: t('agents.volume.area'),
      minWidth: 100,
      type: 'number',
      format: (value: number) => value ? `${value.toFixed(2)} m²` : '-',
      align: 'right',
    },
    {
      id: 'cost',
      label: t('agents.volume.cost'),
      minWidth: 120,
      type: 'number',
      format: (value: number) => value ? `${value.toLocaleString()} Kč` : '-',
      align: 'right',
    },
    {
      id: 'confidence',
      label: t('agents.volume.confidence'),
      minWidth: 100,
      type: 'confidence',
      align: 'center',
    },
    {
      id: 'source_document',
      label: t('agents.volume.source'),
      minWidth: 150,
      format: (value: string) => {
        const filename = value?.split('/').pop() || value;
        return filename?.length > 20 ? `${filename.slice(0, 17)}...` : filename;
      },
    },
  ];

  // Příprava dat pro grafy
  const prepareChartData = () => {
    if (!data || !data.volumes || data.volumes.length === 0) {
      return { volumeByGrade: null, costByElement: null };
    }

    // Data pro koláčový graf - objemy podle marky
    const volumeByGrade = data.summary?.by_grade || {};
    const gradeLabels = Object.keys(volumeByGrade);
    const volumeValues = Object.values(volumeByGrade);

    const volumeChartData = gradeLabels.length > 0 ? {
      labels: gradeLabels,
      datasets: [{
        data: volumeValues,
        backgroundColor: [
          '#FF6384',
          '#36A2EB',
          '#FFCE56',
          '#4BC0C0',
          '#9966FF',
          '#FF9F40',
        ],
        borderWidth: 2,
      }],
    } : null;

    // Data pro sloupcový graf - náklady podle elementů
    const costsByElement: Record<string, number> = {};
    data.volumes.forEach(volume => {
      if (volume.cost && volume.construction_element) {
        costsByElement[volume.construction_element] = 
          (costsByElement[volume.construction_element] || 0) + volume.cost;
      }
    });

    const elementLabels = Object.keys(costsByElement);
    const costValues = Object.values(costsByElement);

    const costChartData = elementLabels.length > 0 ? {
      labels: elementLabels,
      datasets: [{
        label: 'Náklady (Kč)',
        data: costValues,
        backgroundColor: '#36A2EB',
        borderColor: '#36A2EB',
        borderWidth: 1,
      }],
    } : null;

    return { volumeByGrade: volumeChartData, costByElement: costChartData };
  };

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
            : t('agents.volume.noVolumes')
          }
        </Alert>
      );
    }

    if (!data.volumes || data.volumes.length === 0) {
      return (
        <Alert severity="info" sx={{ m: 2 }}>
          {t('agents.volume.noVolumes')}
        </Alert>
      );
    }

    const chartData = prepareChartData();

    return (
      <Box sx={{ p: 2 }}>
        {/* Statistiky */}
        <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Chip 
            icon={<Assessment />}
            label={t('agents.volume.totalVolume', { 
              volume: data.total_volume_m3?.toFixed(2) || '0' 
            })}
            color="primary"
            variant="outlined"
          />
          <Chip 
            icon={<Euro />}
            label={t('agents.volume.totalCost', { 
              cost: data.total_cost?.toLocaleString() || '0' 
            })}
            color="secondary"
            variant="outlined"
          />
        </Box>

        {/* Grafy */}
        {(chartData.volumeByGrade || chartData.costByElement) && (
          <Grid container spacing={2} sx={{ mb: 3 }}>
            {chartData.volumeByGrade && (
              <Grid item xs={12} md={6}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="subtitle2" gutterBottom>
                      Objemy podle marky betonu
                    </Typography>
                    <Box sx={{ height: 200, display: 'flex', justifyContent: 'center' }}>
                      <Doughnut 
                        data={chartData.volumeByGrade}
                        options={{
                          responsive: true,
                          maintainAspectRatio: false,
                          plugins: {
                            legend: {
                              position: 'bottom',
                            },
                          },
                        }}
                      />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            )}
            
            {chartData.costByElement && (
              <Grid item xs={12} md={6}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="subtitle2" gutterBottom>
                      Náklady podle elementů
                    </Typography>
                    <Box sx={{ height: 200 }}>
                      <Bar 
                        data={chartData.costByElement}
                        options={{
                          responsive: true,
                          maintainAspectRatio: false,
                          plugins: {
                            legend: {
                              display: false,
                            },
                          },
                          scales: {
                            y: {
                              beginAtZero: true,
                            },
                          },
                        }}
                      />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            )}
          </Grid>
        )}

        {/* Tabulka s detaily */}
        <DataTable
          columns={columns}
          rows={data.volumes}
          emptyMessage={t('agents.volume.noVolumes')}
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
            <Assessment color="primary" />
            <Typography variant="h6">
              {t('agents.volume.title')}
            </Typography>
            {data && data.success && (
              <Chip 
                label={`${data.total_volume_m3?.toFixed(1) || 0} m³`}
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
          <Assessment color="primary" />
          <Typography variant="h6">
            {t('agents.volume.title')}
          </Typography>
          {data && data.success && (
            <Chip 
              label={`${data.total_volume_m3?.toFixed(1) || 0} m³`}
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
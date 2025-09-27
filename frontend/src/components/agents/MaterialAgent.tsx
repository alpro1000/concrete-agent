// src/components/agents/MaterialAgent.tsx
// Komponenta pro zobrazení výsledků MaterialAgent

import React, { useState } from 'react';
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
  Tabs,
  Tab,
  Collapse,
  IconButton,
} from '@mui/material';
import { 
  ExpandMore, 
  Build, 
  ExpandLess, 
  ExpandMore as ExpandMoreIcon,
  Category 
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { MaterialAnalysisResult, MaterialCategory } from '../../types';
import { DataTable, Column } from '../ui/DataTable';

interface MaterialAgentProps {
  data: MaterialAnalysisResult | null;
  loading: boolean;
  expanded?: boolean;
  onExpandChange?: (expanded: boolean) => void;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel = ({ children, value, index }: TabPanelProps) => (
  <div hidden={value !== index}>
    {value === index && <Box sx={{ pt: 2 }}>{children}</Box>}
  </div>
);

export const MaterialAgent: React.FC<MaterialAgentProps> = ({
  data,
  loading,
  expanded = false,
  onExpandChange
}) => {
  const { t } = useTranslation();
  const [tabValue, setTabValue] = useState(0);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  // Definice sloupců pro tabulku všech materiálů
  const allMaterialsColumns: Column[] = [
    {
      id: 'material_type',
      label: t('agents.material.type'),
      minWidth: 120,
      type: 'badge',
    },
    {
      id: 'material_name',
      label: t('agents.material.name'),
      minWidth: 150,
    },
    {
      id: 'specification',
      label: t('agents.material.specification'),
      minWidth: 120,
      type: 'badge',
    },
    {
      id: 'quantity',
      label: t('agents.material.quantity'),
      minWidth: 100,
      type: 'number',
      align: 'right',
      format: (value: number, row: any) => 
        value ? `${value.toLocaleString()} ${row.unit || ''}` : '-',
    },
    {
      id: 'context',
      label: t('agents.material.context'),
      minWidth: 200,
    },
    {
      id: 'confidence',
      label: t('agents.material.confidence'),
      minWidth: 100,
      type: 'confidence',
      align: 'center',
    },
    {
      id: 'source_document',
      label: t('agents.material.source'),
      minWidth: 150,
      format: (value: string) => {
        const filename = value?.split('/').pop() || value;
        return filename?.length > 20 ? `${filename.slice(0, 17)}...` : filename;
      },
    },
  ];

  // Definice sloupců pro tabulku materiálů v kategorii
  const categoryMaterialsColumns: Column[] = [
    {
      id: 'material_name',
      label: t('agents.material.name'),
      minWidth: 150,
    },
    {
      id: 'specification',
      label: t('agents.material.specification'),
      minWidth: 120,
      type: 'badge',
    },
    {
      id: 'quantity',
      label: t('agents.material.quantity'),
      minWidth: 100,
      type: 'number',
      align: 'right',
      format: (value: number, row: any) => 
        value ? `${value.toLocaleString()} ${row.unit || ''}` : '-',
    },
    {
      id: 'confidence',
      label: t('agents.material.confidence'),
      minWidth: 100,
      type: 'confidence',
      align: 'center',
    },
  ];

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const toggleCategoryExpanded = (categoryName: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(categoryName)) {
      newExpanded.delete(categoryName);
    } else {
      newExpanded.add(categoryName);
    }
    setExpandedCategories(newExpanded);
  };

  const renderCategoryCard = (category: MaterialCategory) => {
    const isExpanded = expandedCategories.has(category.category_name);
    
    return (
      <Card key={category.category_name} variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Box 
            sx={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              cursor: 'pointer'
            }}
            onClick={() => toggleCategoryExpanded(category.category_name)}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Category color="primary" />
              <Typography variant="h6">
                {category.category_name}
              </Typography>
              <Chip 
                label={`${category.total_items} položek`}
                size="small"
                color="primary"
                variant="outlined"
              />
              {category.total_quantity > 0 && (
                <Chip 
                  label={`${category.total_quantity.toLocaleString()}`}
                  size="small"
                  variant="outlined"
                />
              )}
            </Box>
            <IconButton size="small">
              {isExpanded ? <ExpandLess /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>

          {/* Hlavní specifikace */}
          {category.main_specifications && category.main_specifications.length > 0 && (
            <Box sx={{ mt: 1, mb: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Hlavní specifikace:
              </Typography>
              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                {category.main_specifications.map((spec, index) => (
                  <Chip 
                    key={index} 
                    label={spec} 
                    size="small"
                    variant="outlined"
                  />
                ))}
              </Box>
            </Box>
          )}

          <Collapse in={isExpanded}>
            <DataTable
              columns={categoryMaterialsColumns}
              rows={category.items}
              emptyMessage="Žádné materiály v této kategorii"
              defaultRowsPerPage={10}
              maxHeight={400}
            />
          </Collapse>
        </CardContent>
      </Card>
    );
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
            : t('agents.material.noMaterials')
          }
        </Alert>
      );
    }

    if (!data.materials || data.materials.length === 0) {
      return (
        <Alert severity="info" sx={{ m: 2 }}>
          {t('agents.material.noMaterials')}
        </Alert>
      );
    }

    return (
      <Box sx={{ p: 2 }}>
        {/* Statistiky */}
        <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Chip 
            icon={<Build />}
            label={t('agents.material.totalMaterials', { count: data.total_materials })}
            color="primary"
            variant="outlined"
          />
          <Chip 
            label={`${t('agents.material.categories')}: ${data.categories?.length || 0}`}
            variant="outlined"
          />
        </Box>

        {/* Taby pro přepínání mezi zobrazením */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label="Podle kategorií" />
            <Tab label="Všechny materiály" />
          </Tabs>
        </Box>

        {/* Zobrazení podle kategorií */}
        <TabPanel value={tabValue} index={0}>
          {data.categories && data.categories.length > 0 ? (
            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Klikněte na kategorii pro zobrazení detailů
              </Typography>
              {data.categories.map(renderCategoryCard)}
            </Box>
          ) : (
            <Alert severity="info">
              Žádné kategorie k zobrazení
            </Alert>
          )}
        </TabPanel>

        {/* Zobrazení všech materiálů */}
        <TabPanel value={tabValue} index={1}>
          <DataTable
            columns={allMaterialsColumns}
            rows={data.materials}
            emptyMessage={t('agents.material.noMaterials')}
            defaultRowsPerPage={10}
            maxHeight={400}
          />
        </TabPanel>
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
            <Build color="primary" />
            <Typography variant="h6">
              {t('agents.material.title')}
            </Typography>
            {data && data.success && (
              <Chip 
                label={data.total_materials || 0}
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
          <Build color="primary" />
          <Typography variant="h6">
            {t('agents.material.title')}
          </Typography>
          {data && data.success && (
            <Chip 
              label={data.total_materials || 0}
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
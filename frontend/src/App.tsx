// src/App.tsx
// Hlavní komponenta aplikace ConcreteAgent Frontend

import React, { useState, useEffect } from 'react';
import {
  Container,
  AppBar,
  Toolbar,
  Typography,
  Box,
  Paper,
  TextField,
  Button,
  FormControlLabel,
  Switch,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Snackbar,
  LinearProgress,
  Grid,
  Divider,
} from '@mui/material';
import { 
  Analytics, 
  CloudUpload, 
  Download, 
  ContentCopy,
  Add 
} from '@mui/icons-material';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { useTranslation } from 'react-i18next';

// Import komponent
import { FileUpload } from './components/ui/FileUpload';
import { LanguageSwitch } from './components/ui/LanguageSwitch';
import { ConcreteAgent } from './components/agents/ConcreteAgent';
import { VolumeAgent } from './components/agents/VolumeAgent';
import { MaterialAgent } from './components/agents/MaterialAgent';
import { DrawingVolumeAgent } from './components/agents/DrawingVolumeAgent';

// Import typů a služeb
import { AnalysisRequest, AnalysisResult, AppState } from './types';
import { analyzeDocuments, checkServerHealth, copyToClipboard, downloadReport } from './services/api';

// Import i18n
import './utils/i18n';

// Definice téma Material-UI
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
  typography: {
    h4: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 500,
    },
  },
});

function App() {
  const { t, i18n } = useTranslation();
  
  // Stav aplikace
  const [appState, setAppState] = useState<AppState>({
    loading: false,
    error: null,
    result: null,
    language: 'cs',
  });

  // Stav formuláře
  const [formData, setFormData] = useState({
    docs: [] as File[],
    smeta: null as File | null,
    materialQuery: '',
    useClaude: true,
    claudeMode: 'enhancement',
    includeDrawings: false,
  });

  // Stav UI
  const [expandedAgents, setExpandedAgents] = useState({
    concrete: true,
    volume: false,
    material: false,
    drawing: false,
  });
  
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success' as 'success' | 'error' | 'warning' | 'info',
  });

  const [serverHealthy, setServerHealthy] = useState(true);

  // Kontrola zdraví serveru při načtení
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const healthy = await checkServerHealth();
        setServerHealthy(healthy);
      } catch (error) {
        setServerHealthy(false);
      }
    };
    
    checkHealth();
    // Periodická kontrola každých 30 sekund
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Synchronizace jazyka s i18n
  useEffect(() => {
    setAppState(prev => ({ ...prev, language: i18n.language as any }));
  }, [i18n.language]);

  // Handler pro analýzu
  const handleAnalyze = async () => {
    if (formData.docs.length === 0) {
      showSnackbar(t('errors.noFilesSelected'), 'error');
      return;
    }

    setAppState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const request: AnalysisRequest = {
        docs: formData.docs,
        smeta: formData.smeta || undefined,
        material_query: formData.materialQuery || undefined,
        use_claude: formData.useClaude,
        claude_mode: formData.claudeMode,
        language: i18n.language,
        include_drawing_analysis: formData.includeDrawings,
      };

      const result = await analyzeDocuments(request);
      
      setAppState(prev => ({ 
        ...prev, 
        loading: false, 
        result, 
        error: null 
      }));

      // Automaticky rozbalit sekce s výsledky
      if (result.success) {
        setExpandedAgents({
          concrete: Boolean(result.concrete_analysis?.success && result.concrete_analysis?.total_grades > 0),
          volume: Boolean(result.volume_analysis?.success && result.volume_analysis?.volumes?.length > 0),
          material: Boolean(result.material_analysis?.success && result.material_analysis?.total_materials > 0),
          drawing: Boolean(result.drawing_analysis?.success && result.drawing_analysis?.total_elements > 0),
        });
      }

      showSnackbar(
        result.success ? t('status.success') : t('status.error'), 
        result.success ? 'success' : 'error'
      );

    } catch (error: any) {
      console.error('Analysis error:', error);
      setAppState(prev => ({ 
        ...prev, 
        loading: false, 
        error: error.message || t('errors.unknown') 
      }));
      showSnackbar(error.message || t('errors.unknown'), 'error');
    }
  };

  // Helper pro zobrazení notifikací
  const showSnackbar = (message: string, severity: typeof snackbar.severity) => {
    setSnackbar({ open: true, message, severity });
  };

  // Handler pro export
  const handleExport = async (format: 'json' | 'csv' | 'excel') => {
    if (!appState.result) return;

    try {
      await downloadReport(
        appState.result, 
        format, 
        `concrete-analysis-${new Date().toISOString().split('T')[0]}`
      );
      showSnackbar('Report downloaded successfully', 'success');
    } catch (error) {
      showSnackbar('Download failed', 'error');
    }
  };

  // Handler pro kopírování JSON
  const handleCopyJSON = async () => {
    if (!appState.result) return;

    try {
      const success = await copyToClipboard(JSON.stringify(appState.result, null, 2));
      showSnackbar(
        success ? 'JSON copied to clipboard' : 'Copy failed', 
        success ? 'success' : 'error'
      );
    } catch (error) {
      showSnackbar('Copy failed', 'error');
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      
      {/* AppBar */}
      <AppBar position="static" elevation={1}>
        <Toolbar>
          <Analytics sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            {t('app.title')}
          </Typography>
          <LanguageSwitch />
        </Toolbar>
      </AppBar>

      {/* Indikátor načítání */}
      {appState.loading && (
        <LinearProgress color="primary" />
      )}

      <Container maxWidth="xl" sx={{ py: 3 }}>
        {/* Varování při nedostupnosti serveru */}
        {!serverHealthy && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            Server není dostupný. Zkontrolujte, zda backend běží na http://localhost:8000
          </Alert>
        )}

        {/* Subtitle */}
        <Typography variant="subtitle1" color="text.secondary" gutterBottom>
          {t('app.subtitle')}
        </Typography>

        <Grid container spacing={3}>
          {/* Levý panel - formulář */}
          <Grid size={{ xs: 12, lg: 4 }}>
            <Paper sx={{ p: 3, position: 'sticky', top: 20 }}>
              <Typography variant="h6" gutterBottom>
                Analýza dokumentů
              </Typography>

              {/* Upload dokumentů */}
              <Box sx={{ mb: 3 }}>
                <FileUpload
                  files={formData.docs}
                  onFilesChange={(files) => setFormData(prev => ({ ...prev, docs: files }))}
                  label={t('upload.documents')}
                  multiple
                />
              </Box>

              {/* Upload sméty */}
              <Box sx={{ mb: 3 }}>
                <FileUpload
                  files={formData.smeta ? [formData.smeta] : []}
                  onFilesChange={(files) => setFormData(prev => ({ ...prev, smeta: files[0] || null }))}
                  label={t('upload.smeta')}
                  multiple={false}
                />
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Dotaz na materiál */}
              <TextField
                fullWidth
                label={t('form.materialQuery')}
                placeholder={t('form.materialQueryPlaceholder')}
                value={formData.materialQuery}
                onChange={(e) => setFormData(prev => ({ ...prev, materialQuery: e.target.value }))}
                sx={{ mb: 2 }}
              />

              {/* Claude AI */}
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.useClaude}
                    onChange={(e) => setFormData(prev => ({ ...prev, useClaude: e.target.checked }))}
                  />
                }
                label={t('form.useClaude')}
                sx={{ mb: 2, display: 'block' }}
              />

              {/* Claude mode */}
              {formData.useClaude && (
                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>{t('form.claudeMode')}</InputLabel>
                  <Select
                    value={formData.claudeMode}
                    label={t('form.claudeMode')}
                    onChange={(e) => setFormData(prev => ({ ...prev, claudeMode: e.target.value }))}
                  >
                    <MenuItem value="enhancement">{t('claudeModes.enhancement')}</MenuItem>
                    <MenuItem value="primary">{t('claudeModes.primary')}</MenuItem>
                  </Select>
                </FormControl>
              )}

              {/* Include drawings */}
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.includeDrawings}
                    onChange={(e) => setFormData(prev => ({ ...prev, includeDrawings: e.target.checked }))}
                  />
                }
                label={t('form.includeDrawings')}
                sx={{ mb: 3, display: 'block' }}
              />

              {/* Tlačítko analýzy */}
              <Button
                fullWidth
                variant="contained"
                size="large"
                onClick={handleAnalyze}
                disabled={appState.loading || formData.docs.length === 0}
                startIcon={appState.loading ? <CircularProgress size={20} /> : <Analytics />}
              >
                {appState.loading ? t('form.analyzing') : t('form.analyze')}
              </Button>

              {/* Export tlačítka */}
              {appState.result && (
                <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Button
                    size="small"
                    startIcon={<Download />}
                    onClick={() => handleExport('json')}
                  >
                    JSON
                  </Button>
                  <Button
                    size="small"
                    startIcon={<Download />}
                    onClick={() => handleExport('csv')}
                  >
                    CSV
                  </Button>
                  <Button
                    size="small"
                    startIcon={<ContentCopy />}
                    onClick={handleCopyJSON}
                  >
                    Copy
                  </Button>
                </Box>
              )}
            </Paper>
          </Grid>

          {/* Pravý panel - výsledky */}
          <Grid item xs={12} lg={8}>
            {appState.error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {appState.error}
              </Alert>
            )}

            {appState.result ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Typography variant="h5" gutterBottom>
                  {t('results.title')}
                </Typography>

                {/* ConcreteAgent výsledky */}
                <ConcreteAgent
                  data={appState.result.concrete_analysis}
                  loading={appState.loading}
                  expanded={expandedAgents.concrete}
                  onExpandChange={(expanded) => 
                    setExpandedAgents(prev => ({ ...prev, concrete: expanded }))
                  }
                />

                {/* VolumeAgent výsledky */}
                <VolumeAgent
                  data={appState.result.volume_analysis}
                  loading={appState.loading}
                  expanded={expandedAgents.volume}
                  onExpandChange={(expanded) => 
                    setExpandedAgents(prev => ({ ...prev, volume: expanded }))
                  }
                />

                {/* MaterialAgent výsledky */}
                <MaterialAgent
                  data={appState.result.material_analysis}
                  loading={appState.loading}
                  expanded={expandedAgents.material}
                  onExpandChange={(expanded) => 
                    setExpandedAgents(prev => ({ ...prev, material: expanded }))
                  }
                />

                {/* DrawingVolumeAgent výsledky */}
                <DrawingVolumeAgent
                  data={appState.result.drawing_analysis}
                  loading={appState.loading}
                  expanded={expandedAgents.drawing}
                  onExpandChange={(expanded) => 
                    setExpandedAgents(prev => ({ ...prev, drawing: expanded }))
                  }
                />
              </Box>
            ) : (
              <Paper sx={{ p: 4, textAlign: 'center' }}>
                <CloudUpload sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  Nahrajte dokumenty a spusťte analýzu
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Systém automaticky analyzuje marky betonu, objemy, materiály a geometrii
                </Typography>
              </Paper>
            )}
          </Grid>
        </Grid>
      </Container>

      {/* Snackbar pro notifikace */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
      >
        <Alert 
          onClose={() => setSnackbar(prev => ({ ...prev, open: false }))} 
          severity={snackbar.severity}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </ThemeProvider>
  );
}

export default App;

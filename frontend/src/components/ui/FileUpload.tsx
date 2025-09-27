// src/components/ui/FileUpload.tsx
// Komponenta pro upload souborů s drag & drop

import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Box,
  Paper,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Alert,
  Chip,
} from '@mui/material';
import {
  CloudUpload,
  Delete,
  InsertDriveFile,
  Warning,
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';

interface FileUploadProps {
  files: File[];
  onFilesChange: (files: File[]) => void;
  acceptedTypes?: string[];
  maxSize?: number; // v MB
  multiple?: boolean;
  label?: string;
  helperText?: string;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  files,
  onFilesChange,
  acceptedTypes = ['.pdf', '.docx', '.txt', '.xlsx', '.csv'],
  maxSize = 10, // 10MB
  multiple = true,
  label,
  helperText
}) => {
  const { t } = useTranslation();
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    setError(null);

    // Kontrola chyb
    if (rejectedFiles.length > 0) {
      const firstError = rejectedFiles[0];
      if (firstError.errors.some((e: any) => e.code === 'file-too-large')) {
        setError(t('errors.fileTooBig'));
      } else if (firstError.errors.some((e: any) => e.code === 'file-invalid-type')) {
        setError(t('errors.unsupportedFormat'));
      } else {
        setError(t('errors.unknown'));
      }
      return;
    }

    // Přidání nových souborů
    if (multiple) {
      onFilesChange([...files, ...acceptedFiles]);
    } else {
      onFilesChange(acceptedFiles.slice(0, 1));
    }
  }, [files, multiple, onFilesChange, t]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedTypes.reduce((acc, type) => {
      // Konverze přípon na MIME typy
      const mimeTypes: Record<string, string> = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.txt': 'text/plain',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.csv': 'text/csv',
      };
      const mimeType = mimeTypes[type];
      if (mimeType) {
        acc[mimeType] = [type];
      }
      return acc;
    }, {} as Record<string, string[]>),
    maxSize: maxSize * 1024 * 1024, // konverze na byty
    multiple,
  });

  const removeFile = (index: number) => {
    const newFiles = files.filter((_, i) => i !== index);
    onFilesChange(newFiles);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  return (
    <Box>
      {label && (
        <Typography variant="subtitle1" gutterBottom>
          {label}
        </Typography>
      )}
      
      <Paper
        {...getRootProps()}
        sx={{
          p: 3,
          border: '2px dashed',
          borderColor: isDragActive ? 'primary.main' : 'grey.300',
          backgroundColor: isDragActive ? 'primary.50' : 'grey.50',
          cursor: 'pointer',
          textAlign: 'center',
          transition: 'all 0.2s ease',
          '&:hover': {
            borderColor: 'primary.main',
            backgroundColor: 'primary.50',
          },
        }}
      >
        <input {...getInputProps()} />
        <CloudUpload 
          sx={{ 
            fontSize: 48, 
            color: isDragActive ? 'primary.main' : 'grey.400',
            mb: 2 
          }} 
        />
        <Typography variant="h6" gutterBottom>
          {isDragActive 
            ? t('upload.dragAndDrop')
            : t('upload.dragAndDrop')
          }
        </Typography>
        <Button variant="outlined" component="span">
          {t('upload.selectFiles')}
        </Button>
      </Paper>

      {helperText && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          {helperText}
        </Typography>
      )}

      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
        {t('upload.supportedFormats')} • {t('upload.maxSize')}
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Warning />
            {error}
          </Box>
        </Alert>
      )}

      {files.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            {t('upload.filesSelected')} ({files.length})
          </Typography>
          <List dense>
            {files.map((file, index) => (
              <ListItem key={index} divider>
                <InsertDriveFile sx={{ mr: 1 }} />
                <ListItemText
                  primary={file.name}
                  secondary={
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                      <Chip 
                        label={formatFileSize(file.size)} 
                        size="small" 
                        variant="outlined" 
                      />
                      <Chip 
                        label={file.type || 'unknown'} 
                        size="small" 
                        variant="outlined" 
                      />
                    </Box>
                  }
                />
                <ListItemSecondaryAction>
                  <IconButton 
                    edge="end" 
                    onClick={() => removeFile(index)}
                    color="error"
                    size="small"
                  >
                    <Delete />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </Box>
      )}
    </Box>
  );
};
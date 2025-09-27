// src/components/ui/DataTable.tsx
// Univerzální tabulka pro zobrazení dat

import React, { useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TableSortLabel,
  Paper,
  Box,
  Typography,
  Chip,
  Tooltip,
} from '@mui/material';
import { visuallyHidden } from '@mui/utils';

export interface Column {
  id: string;
  label: string;
  minWidth?: number;
  align?: 'right' | 'left' | 'center';
  format?: (value: any) => string | React.ReactNode;
  sortable?: boolean;
  type?: 'text' | 'number' | 'confidence' | 'badge';
}

interface DataTableProps {
  columns: Column[];
  rows: any[];
  pagination?: boolean;
  defaultRowsPerPage?: number;
  maxHeight?: number | string;
  stickyHeader?: boolean;
  emptyMessage?: string;
}

type Order = 'asc' | 'desc';

export const DataTable: React.FC<DataTableProps> = ({
  columns,
  rows,
  pagination = true,
  defaultRowsPerPage = 10,
  maxHeight = 400,
  stickyHeader = true,
  emptyMessage = 'No data available'
}) => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(defaultRowsPerPage);
  const [order, setOrder] = useState<Order>('asc');
  const [orderBy, setOrderBy] = useState<string>('');

  const handleRequestSort = (property: string) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(+event.target.value);
    setPage(0);
  };

  // Sorting logic
  const sortedRows = React.useMemo(() => {
    if (!orderBy) return rows;

    return [...rows].sort((a, b) => {
      const aValue = a[orderBy];
      const bValue = b[orderBy];

      if (aValue === bValue) return 0;
      
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return order === 'asc' ? aValue - bValue : bValue - aValue;
      }
      
      const aString = String(aValue || '').toLowerCase();
      const bString = String(bValue || '').toLowerCase();
      
      if (order === 'asc') {
        return aString < bString ? -1 : 1;
      } else {
        return aString > bString ? -1 : 1;
      }
    });
  }, [rows, order, orderBy]);

  // Pagination
  const paginatedRows = pagination 
    ? sortedRows.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
    : sortedRows;

  // Formatování hodnot podle typu sloupce
  const formatCellValue = (value: any, column: Column) => {
    if (value === null || value === undefined) {
      return '-';
    }

    if (column.format) {
      return column.format(value);
    }

    switch (column.type) {
      case 'confidence':
        const confidence = typeof value === 'number' ? value : parseFloat(value);
        const color = confidence >= 0.8 ? 'success' : confidence >= 0.6 ? 'warning' : 'error';
        return (
          <Chip 
            label={`${(confidence * 100).toFixed(0)}%`}
            color={color}
            size="small"
            variant="outlined"
          />
        );
      
      case 'badge':
        return (
          <Chip 
            label={value}
            size="small"
            variant="outlined"
          />
        );
      
      case 'number':
        if (typeof value === 'number') {
          return value.toLocaleString();
        }
        return value;
      
      default:
        return value;
    }
  };

  if (rows.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">
          {emptyMessage}
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ width: '100%', overflow: 'hidden' }}>
      <TableContainer sx={{ maxHeight }}>
        <Table stickyHeader={stickyHeader} size="small">
          <TableHead>
            <TableRow>
              {columns.map((column) => (
                <TableCell
                  key={column.id}
                  align={column.align}
                  style={{ minWidth: column.minWidth }}
                  sortDirection={orderBy === column.id ? order : false}
                >
                  {column.sortable !== false ? (
                    <TableSortLabel
                      active={orderBy === column.id}
                      direction={orderBy === column.id ? order : 'asc'}
                      onClick={() => handleRequestSort(column.id)}
                    >
                      {column.label}
                      {orderBy === column.id ? (
                        <Box component="span" sx={visuallyHidden}>
                          {order === 'desc' ? 'sorted descending' : 'sorted ascending'}
                        </Box>
                      ) : null}
                    </TableSortLabel>
                  ) : (
                    column.label
                  )}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedRows.map((row, index) => (
              <TableRow hover role="checkbox" tabIndex={-1} key={index}>
                {columns.map((column) => {
                  const value = row[column.id];
                  return (
                    <TableCell key={column.id} align={column.align}>
                      {typeof value === 'string' && value.length > 50 ? (
                        <Tooltip title={value}>
                          <span>{formatCellValue(value, column)}</span>
                        </Tooltip>
                      ) : (
                        formatCellValue(value, column)
                      )}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      
      {pagination && (
        <TablePagination
          rowsPerPageOptions={[5, 10, 25, 50]}
          component="div"
          count={rows.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      )}
    </Paper>
  );
};
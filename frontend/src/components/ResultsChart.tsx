import React from 'react';
import { Card, Typography, Radio, Space } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';
import type { ConcreteMatch, MaterialMatch, VolumeEntry } from '../types/api';

const { Title } = Typography;

interface ResultsChartProps {
  title: string;
  data: ConcreteMatch[] | MaterialMatch[] | VolumeEntry[];
  type: 'concrete' | 'materials' | 'volumes';
  chartType?: 'bar' | 'pie' | 'line';
  onChartTypeChange?: (type: 'bar' | 'pie' | 'line') => void;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#ffc658', '#ff7c7c'];

const ResultsChart: React.FC<ResultsChartProps> = ({
  title,
  data,
  type,
  chartType = 'bar',
  onChartTypeChange,
}) => {
  const { t } = useTranslation();

  const processConcreteData = (data: ConcreteMatch[]) => {
    const gradeCounts = data.reduce((acc, item) => {
      acc[item.grade] = (acc[item.grade] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(gradeCounts).map(([grade, count]) => ({
      name: grade,
      value: count,
      count,
    }));
  };

  const processMaterialData = (data: MaterialMatch[]) => {
    const materialCounts = data.reduce((acc, item) => {
      acc[item.material] = (acc[item.material] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(materialCounts).map(([material, count]) => ({
      name: material,
      value: count,
      count,
    }));
  };

  const processVolumeData = (data: VolumeEntry[]) => {
    const categoryCounts = data.reduce((acc, item) => {
      const category = item.category || 'Uncategorized';
      acc[category] = (acc[category] || 0) + item.quantity;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(categoryCounts).map(([category, quantity]) => ({
      name: category,
      value: quantity,
      quantity,
    }));
  };

  const getChartData = () => {
    switch (type) {
      case 'concrete':
        return processConcreteData(data as ConcreteMatch[]);
      case 'materials':
        return processMaterialData(data as MaterialMatch[]);
      case 'volumes':
        return processVolumeData(data as VolumeEntry[]);
      default:
        return [];
    }
  };

  const chartData = getChartData();

  const renderBarChart = () => (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar 
          dataKey="value" 
          fill="#1890ff" 
          name={type === 'volumes' ? t('analysis.materials.quantity') : t('common.results')}
        />
      </BarChart>
    </ResponsiveContainer>
  );

  const renderPieChart = () => (
    <ResponsiveContainer width="100%" height={400}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ name, percent }: any) => `${name} ${(percent * 100).toFixed(0)}%`}
          outerRadius={120}
          fill="#8884d8"
          dataKey="value"
        >
          {chartData.map((_, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );

  const renderLineChart = () => (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line 
          type="monotone" 
          dataKey="value" 
          stroke="#1890ff" 
          strokeWidth={2}
          name={type === 'volumes' ? t('analysis.materials.quantity') : t('common.results')}
        />
      </LineChart>
    </ResponsiveContainer>
  );

  const renderChart = () => {
    switch (chartType) {
      case 'bar':
        return renderBarChart();
      case 'pie':
        return renderPieChart();
      case 'line':
        return renderLineChart();
      default:
        return renderBarChart();
    }
  };

  if (chartData.length === 0) {
    return (
      <Card>
        <Title level={4}>{title}</Title>
        <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
          {t('common.loading')}
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={4}>{title} ({chartData.length} items)</Title>
          {onChartTypeChange && (
            <Radio.Group
              value={chartType}
              onChange={(e) => onChartTypeChange(e.target.value)}
              size="small"
            >
              <Radio.Button value="bar">Bar</Radio.Button>
              <Radio.Button value="pie">Pie</Radio.Button>
              <Radio.Button value="line">Line</Radio.Button>
            </Radio.Group>
          )}
        </div>
        
        {renderChart()}
      </Space>
    </Card>
  );
};

export default ResultsChart;
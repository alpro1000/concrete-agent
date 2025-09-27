// src/utils/download.ts
// Utility funkce pro export a download reportů

import { AnalysisResult } from '../types';

export const exportToExcel = async (data: AnalysisResult, filename: string) => {
  // Pro Excel export bychom potřebovali knihovnu jako xlsx
  // Prozatím fallback na CSV
  return exportToCSV(data, filename);
};

export const exportToCSV = (data: AnalysisResult, filename: string) => {
  const csvSections: string[] = [];

  // Concrete Analysis
  if (data.concrete_analysis?.grades?.length > 0) {
    csvSections.push('=== CONCRETE GRADES ===');
    csvSections.push('Grade,Location,Context,Confidence,Source');
    data.concrete_analysis.grades.forEach(grade => {
      csvSections.push([
        grade.grade,
        grade.location,
        grade.context,
        grade.confidence,
        grade.source_document
      ].map(field => `"${String(field).replace(/"/g, '""')}"`).join(','));
    });
    csvSections.push('');
  }

  // Volume Analysis
  if (data.volume_analysis?.volumes?.length > 0) {
    csvSections.push('=== VOLUMES ===');
    csvSections.push('Grade,Element,Volume_m3,Area_m2,Cost,Confidence,Source');
    data.volume_analysis.volumes.forEach(volume => {
      csvSections.push([
        volume.concrete_grade,
        volume.construction_element,
        volume.volume_m3 || '',
        volume.area_m2 || '',
        volume.cost || '',
        volume.confidence,
        volume.source_document
      ].map(field => `"${String(field).replace(/"/g, '""')}"`).join(','));
    });
    csvSections.push('');
  }

  // Material Analysis
  if (data.material_analysis?.materials?.length > 0) {
    csvSections.push('=== MATERIALS ===');
    csvSections.push('Type,Name,Specification,Quantity,Unit,Context,Confidence,Source');
    data.material_analysis.materials.forEach(material => {
      csvSections.push([
        material.material_type,
        material.material_name,
        material.specification,
        material.quantity || '',
        material.unit,
        material.context,
        material.confidence,
        material.source_document
      ].map(field => `"${String(field).replace(/"/g, '""')}"`).join(','));
    });
  }

  const csvContent = csvSections.join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  
  // Download
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${filename}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
};

export const exportToPDF = async (data: AnalysisResult, filename: string) => {
  // Pro PDF export bychom potřebovali knihovnu jako jsPDF
  // Prozatím fallback na plain text
  const textContent = createTextReport(data);
  const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8;' });
  
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${filename}.txt`;
  link.click();
  URL.revokeObjectURL(link.href);
};

export const exportToMarkdown = (data: AnalysisResult, filename: string) => {
  let markdown = `# ConcreteAgent Analysis Report\n\n`;
  markdown += `Generated on: ${new Date().toLocaleString()}\n\n`;

  // Summary
  markdown += `## Summary\n\n`;
  markdown += `- **Documents analyzed**: ${data.request_parameters?.documents_count || 0}\n`;
  markdown += `- **Material query**: ${data.request_parameters?.material_query || 'All materials'}\n`;
  markdown += `- **Language**: ${data.request_parameters?.language || 'cs'}\n`;
  markdown += `- **Claude AI**: ${data.request_parameters?.use_claude ? 'Enabled' : 'Disabled'}\n\n`;

  // Concrete Analysis
  if (data.concrete_analysis?.grades?.length > 0) {
    markdown += `## Concrete Grades\n\n`;
    markdown += `Total grades found: **${data.concrete_analysis.total_grades}**\n\n`;
    markdown += `| Grade | Location | Context | Confidence | Source |\n`;
    markdown += `|-------|----------|---------|------------|--------|\n`;
    
    data.concrete_analysis.grades.forEach(grade => {
      markdown += `| ${grade.grade} | ${grade.location} | ${grade.context} | ${(grade.confidence * 100).toFixed(0)}% | ${grade.source_document} |\n`;
    });
    markdown += `\n`;
  }

  // Volume Analysis
  if (data.volume_analysis?.volumes?.length > 0) {
    markdown += `## Volumes\n\n`;
    markdown += `- **Total volume**: ${data.volume_analysis.total_volume_m3?.toFixed(2) || 0} m³\n`;
    markdown += `- **Total cost**: ${data.volume_analysis.total_cost?.toLocaleString() || 0} CZK\n\n`;
    
    markdown += `| Grade | Element | Volume (m³) | Area (m²) | Cost (CZK) | Confidence |\n`;
    markdown += `|-------|---------|-------------|-----------|------------|------------|\n`;
    
    data.volume_analysis.volumes.forEach(volume => {
      markdown += `| ${volume.concrete_grade} | ${volume.construction_element} | ${volume.volume_m3?.toFixed(2) || '-'} | ${volume.area_m2?.toFixed(2) || '-'} | ${volume.cost?.toLocaleString() || '-'} | ${(volume.confidence * 100).toFixed(0)}% |\n`;
    });
    markdown += `\n`;
  }

  // Material Analysis
  if (data.material_analysis?.materials?.length > 0) {
    markdown += `## Materials\n\n`;
    markdown += `Total materials found: **${data.material_analysis.total_materials}**\n\n`;
    
    markdown += `| Type | Name | Specification | Quantity | Unit | Context | Confidence |\n`;
    markdown += `|------|------|---------------|----------|------|---------|------------|\n`;
    
    data.material_analysis.materials.forEach(material => {
      markdown += `| ${material.material_type} | ${material.material_name} | ${material.specification} | ${material.quantity || '-'} | ${material.unit} | ${material.context} | ${(material.confidence * 100).toFixed(0)}% |\n`;
    });
    markdown += `\n`;
  }

  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${filename}.md`;
  link.click();
  URL.revokeObjectURL(link.href);
};

const createTextReport = (data: AnalysisResult): string => {
  let report = `ConcreteAgent Analysis Report\n`;
  report += `Generated on: ${new Date().toLocaleString()}\n`;
  report += `${'='.repeat(50)}\n\n`;

  // Summary
  report += `SUMMARY\n`;
  report += `- Documents analyzed: ${data.request_parameters?.documents_count || 0}\n`;
  report += `- Material query: ${data.request_parameters?.material_query || 'All materials'}\n`;
  report += `- Language: ${data.request_parameters?.language || 'cs'}\n`;
  report += `- Claude AI: ${data.request_parameters?.use_claude ? 'Enabled' : 'Disabled'}\n\n`;

  // Concrete grades
  if (data.concrete_analysis?.grades?.length > 0) {
    report += `CONCRETE GRADES (${data.concrete_analysis.total_grades})\n`;
    report += `${'-'.repeat(30)}\n`;
    data.concrete_analysis.grades.forEach((grade, index) => {
      report += `${index + 1}. ${grade.grade}\n`;
      report += `   Location: ${grade.location}\n`;
      report += `   Context: ${grade.context}\n`;
      report += `   Confidence: ${(grade.confidence * 100).toFixed(0)}%\n`;
      report += `   Source: ${grade.source_document}\n\n`;
    });
  }

  // Volumes
  if (data.volume_analysis?.volumes?.length > 0) {
    report += `VOLUMES\n`;
    report += `Total volume: ${data.volume_analysis.total_volume_m3?.toFixed(2) || 0} m³\n`;
    report += `Total cost: ${data.volume_analysis.total_cost?.toLocaleString() || 0} CZK\n`;
    report += `${'-'.repeat(30)}\n`;
    data.volume_analysis.volumes.forEach((volume, index) => {
      report += `${index + 1}. ${volume.concrete_grade} - ${volume.construction_element}\n`;
      if (volume.volume_m3) report += `   Volume: ${volume.volume_m3.toFixed(2)} m³\n`;
      if (volume.area_m2) report += `   Area: ${volume.area_m2.toFixed(2)} m²\n`;
      if (volume.cost) report += `   Cost: ${volume.cost.toLocaleString()} CZK\n`;
      report += `   Confidence: ${(volume.confidence * 100).toFixed(0)}%\n\n`;
    });
  }

  // Materials
  if (data.material_analysis?.materials?.length > 0) {
    report += `MATERIALS (${data.material_analysis.total_materials})\n`;
    report += `${'-'.repeat(30)}\n`;
    data.material_analysis.materials.forEach((material, index) => {
      report += `${index + 1}. ${material.material_name} (${material.material_type})\n`;
      report += `   Specification: ${material.specification}\n`;
      if (material.quantity) {
        report += `   Quantity: ${material.quantity} ${material.unit}\n`;
      }
      report += `   Context: ${material.context}\n`;
      report += `   Confidence: ${(material.confidence * 100).toFixed(0)}%\n\n`;
    });
  }

  return report;
};
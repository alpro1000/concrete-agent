import React from 'react';
import AuditResult from '../artifacts/AuditResult';
import PositionBreakdown from '../artifacts/PositionBreakdown';
import MaterialsSummary from '../artifacts/MaterialsSummary';
import ResourcesCalc from '../artifacts/ResourcesCalc';

export default function ArtifactPanel({ artifact }) {
  if (!artifact) {
    return (
      <div className="w-96 bg-gray-100 border-l border-gray-200 flex flex-col items-center justify-center text-gray-500">
        <div className="text-center">
          <div className="text-4xl mb-2">📊</div>
          <p>Výsledky se zobrazí zde</p>
        </div>
      </div>
    );
  }

  const renderArtifact = () => {
    switch (artifact.type) {
      case 'audit_result':
        return <AuditResult data={artifact.data} />;
      case 'position_breakdown':
        return <PositionBreakdown data={artifact.data} />;
      case 'materials_summary':
        return <MaterialsSummary data={artifact.data} />;
      case 'resources_calc':
        return <ResourcesCalc data={artifact.data} />;
      default:
        return <div>Neznámý typ artefaktu</div>;
    }
  };

  return (
    <div className="w-96 bg-gray-100 border-l border-gray-200 flex flex-col">
      <div className="p-4 border-b border-gray-200 bg-white">
        <h3 className="font-bold text-sm">{artifact.title}</h3>
      </div>
      <div className="flex-1 overflow-y-auto p-4">{renderArtifact()}</div>
    </div>
  );
}

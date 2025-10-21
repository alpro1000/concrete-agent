import React from 'react';
import AuditResult from '../artifacts/AuditResult';
import PositionBreakdown from '../artifacts/PositionBreakdown';
import MaterialsSummary from '../artifacts/MaterialsSummary';
import ResourcesCalc from '../artifacts/ResourcesCalc';

const ARTIFACT_RENDERERS = {
  audit_result: AuditResult,
  position_breakdown: PositionBreakdown,
  materials_summary: MaterialsSummary,
  resources_calc: ResourcesCalc,
};

export default function ArtifactPanel({ artifact, isLoading }) {
  if (!artifact && !isLoading) {
    return (
      <div className="hidden lg:flex w-96 bg-gradient-to-b from-gray-100 to-gray-50 border-l border-gray-200 flex-col items-center justify-center text-gray-500">
        <div className="text-center">
          <div className="text-5xl mb-3 opacity-30">📊</div>
          <p className="text-sm font-medium">Výsledky se zobrazí zde</p>
        </div>
      </div>
    );
  }

  return (
    <div className="hidden lg:flex w-96 bg-gray-100 border-l border-gray-200 flex-col">
      <div className="p-4 bg-white border-b border-gray-200">
        <h3 className="font-bold text-sm text-gray-900">{artifact?.title || 'Zpracování...'}</h3>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin">⏳</div>
          </div>
        ) : artifact && ARTIFACT_RENDERERS[artifact.type] ? (
          React.createElement(ARTIFACT_RENDERERS[artifact.type], { data: artifact.data })
        ) : (
          <div className="text-center text-gray-500">Neznámý typ</div>
        )}
      </div>
    </div>
  );
}

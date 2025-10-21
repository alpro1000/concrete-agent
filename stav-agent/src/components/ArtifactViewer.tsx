import React from 'react';
import type { ChatArtifact } from '../services/chatApi';
import AuditResult from './artifacts/AuditResult';
import MaterialsSummary from './artifacts/MaterialsSummary';
import PositionBreakdown from './artifacts/PositionBreakdown';
import ResourcesCalc from './artifacts/ResourcesCalc';

const ARTIFACT_COMPONENTS: Record<string, React.ComponentType<{ data: unknown }>> = {
  audit_result: AuditResult,
  materials_summary: MaterialsSummary,
  position_breakdown: PositionBreakdown,
  resources_calc: ResourcesCalc,
};

interface ArtifactViewerProps {
  artifact?: ChatArtifact;
}

const ArtifactViewer: React.FC<ArtifactViewerProps> = ({ artifact }) => {
  if (!artifact || !artifact.type) {
    return null;
  }

  const Renderer = ARTIFACT_COMPONENTS[artifact.type];

  if (!Renderer) {
    return null;
  }

  return (
    <div className="mt-4 rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className="border-b border-gray-200 px-4 py-3">
        <h4 className="text-sm font-semibold text-gray-700">{artifact.title}</h4>
      </div>
      <div className="px-4 py-3 text-sm text-gray-700">
        <Renderer data={artifact.data as any} />
      </div>
    </div>
  );
};

export default ArtifactViewer;

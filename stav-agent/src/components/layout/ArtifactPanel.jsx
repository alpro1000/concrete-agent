import React from 'react';
import ArtifactViewer from '../ArtifactViewer';

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
      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin">⏳</div>
          </div>
        ) : artifact ? (
          <ArtifactViewer artifact={artifact} variant="panel" />
        ) : (
          <div className="text-center text-gray-500">Neznámý typ</div>
        )}
      </div>
    </div>
  );
}

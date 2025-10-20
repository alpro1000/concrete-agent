import React from 'react';
import { X, BookOpen } from 'lucide-react';

export default function Sidebar({ isOpen, onToggle, projects, onSelectProject }) {
  return (
    <div className={`${isOpen ? 'w-64' : 'w-0'} bg-gray-900 text-white transition-all overflow-hidden flex flex-col`}>
      <div className="p-4 border-b border-gray-700 flex items-center justify-between">
        <h2 className="font-bold">Projekty</h2>
        <button onClick={onToggle} className="hover:bg-gray-800 p-1 rounded">
          <X size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-2">
          {projects?.map((project) => (
            <div
              key={project.id ?? project.project_id}
              onClick={() => onSelectProject(project)}
              className="p-3 rounded bg-gray-800 hover:bg-gray-700 cursor-pointer text-sm transition"
            >
              <div className="font-semibold flex items-center gap-2">
                📋 {project.name}
              </div>
              {project.positions_total && (
                <div className="text-xs text-gray-400 mt-1">
                  {project.positions_total} pozic
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="border-t border-gray-700 p-4 text-xs space-y-1 text-gray-300">
        <div className="flex items-center gap-2">
          <BookOpen size={14} /> KB Status
        </div>
        <div>✓ OTSKP kódy: 2847</div>
        <div>✓ Ceny: 1254 pos</div>
        <div>✓ Normy: ČSN aktuální</div>
      </div>
    </div>
  );
}

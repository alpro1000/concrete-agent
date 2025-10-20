import React from 'react';
import { Plus, Settings, LogOut } from 'lucide-react';

export default function Header({ onNewProject }) {
  return (
    <div className="bg-white border-b border-gray-200 p-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-gray-900">🏗️ Stav Agent</h1>
      </div>

      <div className="flex gap-2">
        <button
          onClick={onNewProject}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          <Plus size={18} /> Nový projekt
        </button>

        <button className="p-2 hover:bg-gray-100 rounded-lg transition">
          <Settings size={20} className="text-gray-600" />
        </button>

        <button className="p-2 hover:bg-gray-100 rounded-lg transition">
          <LogOut size={20} className="text-gray-600" />
        </button>
      </div>
    </div>
  );
}

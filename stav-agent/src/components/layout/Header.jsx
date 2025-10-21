import React from 'react';
import { Plus, Settings, LogOut, Menu } from 'lucide-react';

export default function Header({ onNewProject, onToggleSidebar, currentProject }) {
  return (
    <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between shadow-sm">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="p-2 hover:bg-gray-100 rounded-lg transition lg:hidden"
        >
          <Menu size={20} className="text-gray-600" />
        </button>
        <h1 className="text-xl font-bold text-gray-900">🏗️ Stav Agent</h1>
        {currentProject && (
          <span className="text-sm text-gray-500 ml-2">
            / {currentProject.name || currentProject.project_name}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onNewProject}
          className="hidden sm:flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium"
        >
          <Plus size={18} /> Nový projekt
        </button>

        <button className="p-2 hover:bg-gray-100 rounded-lg transition" title="Nastavení">
          <Settings size={20} className="text-gray-600" />
        </button>

        <button className="p-2 hover:bg-gray-100 rounded-lg transition" title="Odhlásit se">
          <LogOut size={20} className="text-gray-600" />
        </button>
      </div>
    </header>
  );
}

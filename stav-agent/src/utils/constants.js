export const QUICK_ACTIONS = [
  {
    id: 'audit',
    label: 'Audit pozice',
    icon: '✓',
    color: 'bg-blue-100 text-blue-700 hover:bg-blue-200',
    description: 'Zkontroluj všechny pozice',
    apiAction: 'audit_positions',
  },
  {
    id: 'breakdown',
    label: 'Rozebrat',
    icon: '📊',
    color: 'bg-purple-100 text-purple-700 hover:bg-purple-200',
    description: 'Rozeber strukturu SO',
    apiAction: 'breakdown_structure',
  },
  {
    id: 'materials',
    label: 'Materiály',
    icon: '🧱',
    color: 'bg-orange-100 text-orange-700 hover:bg-orange-200',
    description: 'Seznam všech materiálů',
    apiAction: 'materials_summary',
  },
  {
    id: 'resources',
    label: 'Zdroje',
    icon: '⚙️',
    color: 'bg-green-100 text-green-700 hover:bg-green-200',
    description: 'Pracovní hodiny a technika',
    apiAction: 'calculate_resources',
  },
];

export const ARTIFACT_TYPES = {
  AUDIT_RESULT: 'audit_result',
  POSITION_BREAKDOWN: 'position_breakdown',
  MATERIALS_SUMMARY: 'materials_summary',
  RESOURCES_CALC: 'resources_calc',
  PROJECT_SUMMARY: 'project_summary',
};

export const STATUS_COLORS = {
  GREEN: 'bg-green-50 text-green-700 border-green-300',
  AMBER: 'bg-yellow-50 text-yellow-700 border-yellow-300',
  RED: 'bg-red-50 text-red-700 border-red-300',
};

export const MESSAGE_TYPES = {
  USER: 'user',
  AI: 'ai',
  SYSTEM: 'system',
};

export const THEMES = {
  LIGHT: 'light',
  DARK: 'dark',
};

export const PROJECT_STATUSES = {
  UPLOADED: 'UPLOADED',
  AUDITED: 'AUDITED',
  EXPORTED: 'EXPORTED',
  ERROR: 'ERROR',
};

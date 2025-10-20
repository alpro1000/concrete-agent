export const QUICK_ACTIONS = [
  {
    id: 'audit',
    label: 'Audit pozice',
    icon: '✓',
    color: 'bg-blue-100 text-blue-700',
    description: 'Zkontroluj všechny pozice',
  },
  {
    id: 'breakdown',
    label: 'Rozebrat smetu',
    icon: '📊',
    color: 'bg-purple-100 text-purple-700',
    description: 'Rozeber strukturu SO',
  },
  {
    id: 'materials',
    label: 'Materiály',
    icon: '🧱',
    color: 'bg-orange-100 text-orange-700',
    description: 'Seznam všech materiálů',
  },
  {
    id: 'resources',
    label: 'Zdroje',
    icon: '⚙️',
    color: 'bg-green-100 text-green-700',
    description: 'Pracovní hodiny a technika',
  },
];

export const ARTIFACT_TYPES = {
  AUDIT_RESULT: 'audit_result',
  POSITION_BREAKDOWN: 'position_breakdown',
  MATERIALS_SUMMARY: 'materials_summary',
  RESOURCES_CALC: 'resources_calc',
};

export const STATUS_COLORS = {
  GREEN: 'bg-green-50 text-green-700 border-green-200',
  AMBER: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  RED: 'bg-red-50 text-red-700 border-red-200',
};

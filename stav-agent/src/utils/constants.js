export const QUICK_ACTIONS = [
  {
    id: 'kontrola',
    label: 'Kontrola',
    czech_name: 'Kontrola pozic',
    icon: '✓',
    color: 'bg-blue-100 text-blue-700 hover:bg-blue-200',
    description: 'Zkontroluj pozice podle norem',
    apiAction: 'audit_positions',
    options: { check_norms: true, check_catalog: true },
  },
  {
    id: 'vymer',
    label: 'Výměr',
    czech_name: 'Výkaz výměr',
    icon: '📊',
    color: 'bg-purple-100 text-purple-700 hover:bg-purple-200',
    description: 'Výkaz výměr podle objektů a sekcí',
    apiAction: 'vykaz_vymer',
    options: { by_section: true, totals: true },
  },
  {
    id: 'materialy',
    label: 'Materiály',
    czech_name: 'Detailní seznam materiálů',
    icon: '🧱',
    color: 'bg-orange-100 text-orange-700 hover:bg-orange-200',
    description: 'Detailní seznam všech materiálů',
    apiAction: 'materials_detailed',
    options: { show_sources: true, show_characteristics: true, show_suppliers: true },
  },
  {
    id: 'zdroje',
    label: 'Zdroje',
    czech_name: 'Přehled zdrojů',
    icon: '⚙️',
    color: 'bg-green-100 text-green-700 hover:bg-green-200',
    description: 'Pracovníci, technika a harmonogram',
    apiAction: 'resource_sheet',
    options: { by_section: true, include_timeline: true },
  },
  {
    id: 'shrnuti',
    label: 'Shrnutí',
    czech_name: 'Souhrn projektu',
    icon: '📋',
    color: 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200',
    description: 'Kompletní projektové shrnutí',
    apiAction: 'project_summary',
    options: { detail_level: 'full' },
  },
];

export const ARTIFACT_TYPES = {
  AUDIT_RESULT: 'audit_result',
  VYKAZ_VYMER: 'vykaz_vymer',
  MATERIALS_DETAILED: 'materials_detailed',
  RESOURCE_SHEET: 'resource_sheet',
  PROJECT_SUMMARY: 'project_summary',
  TECH_CARD: 'tech_card',
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

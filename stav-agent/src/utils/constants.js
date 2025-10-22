export const QUICK_ACTIONS = [
  {
    id: 'kontrola',
    label: '✓ Kontrola',
    czech_name: 'Kontrola pozic',
    description: 'Zkontroluj všechny pozice podle norem a katalogů',
    apiAction: 'audit_positions',
    color: 'bg-blue-100 text-blue-700 hover:bg-blue-200',
    icon: '✓',
  },
  {
    id: 'vymer',
    label: '📊 Výměr',
    czech_name: 'Výkaz výměr',
    description: 'Agreguj pozice po sekcích, vypočítej součty',
    apiAction: 'vykaz_vymer',
    color: 'bg-purple-100 text-purple-700 hover:bg-purple-200',
    icon: '📊',
  },
  {
    id: 'materialy',
    label: '🧱 Materiály',
    czech_name: 'Detailní seznam materiálů',
    description: 'Vypis všechny materiály s vlastnostmi a dodavateli',
    apiAction: 'materials_detailed',
    color: 'bg-orange-100 text-orange-700 hover:bg-orange-200',
    icon: '🧱',
  },
  {
    id: 'zdroje',
    label: '⚙️ Zdroje',
    czech_name: 'Ресурсная ведомость',
    description: 'Vypočítej pracovní sílu, techniku, harmonogram',
    apiAction: 'resource_sheet',
    color: 'bg-green-100 text-green-700 hover:bg-green-200',
    icon: '⚙️',
  },
  {
    id: 'shrnuti',
    label: '📋 Shrnutí',
    czech_name: 'Celkové shrnutí projektu',
    description: 'Přehled projektu, rozpočet, rizika a doporučení',
    apiAction: 'project_summary',
    color: 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200',
    icon: '📋',
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

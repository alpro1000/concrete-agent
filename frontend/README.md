# ConcreteAgent Frontend

Frontend aplikace pro multi-agentní systém analýzy stavebních konstrukcí s podporou českého, anglického a ruského jazyka.

## Architektura a principy

### Struktura komponent

```
src/
├── components/
│   ├── agents/           # Komponenty pro každého agenta
│   │   ├── ConcreteAgent.tsx       # Zobrazení marky betonu
│   │   ├── VolumeAgent.tsx         # Zobrazení objemů a nákladů
│   │   ├── MaterialAgent.tsx       # Zobrazení materiálů
│   │   └── DrawingVolumeAgent.tsx  # Zobrazení geometrie z výkresů
│   └── ui/               # Obecné UI komponenty
│       ├── FileUpload.tsx          # Upload souborů
│       ├── LanguageSwitch.tsx      # Přepínač jazyka
│       └── DataTable.tsx           # Tabulka s daty
├── locales/             # Jazykové soubory
│   ├── cs.json         # Čeština
│   ├── en.json         # Angličtina
│   └── ru.json         # Ruština
├── services/           # API služby
│   └── api.ts         # Komunikace s backend API
├── types/             # TypeScript typy
│   └── index.ts      # Společné typy
└── utils/            # Pomocné funkce
    └── download.ts   # Export reportů
```

### Modularita a rozšiřitelnost

#### Přidání nového agenta

1. **Vytvořte nový komponent** v `src/components/agents/`:
```typescript
// src/components/agents/NewAgent.tsx
import React from 'react';
import { Card, CardContent, Typography } from '@mui/material';

interface NewAgentProps {
  data: any; // Definujte vlastní typ
  loading: boolean;
}

export const NewAgent: React.FC<NewAgentProps> = ({ data, loading }) => {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6">Nový Agent</Typography>
        {/* Vaše implementace */}
      </CardContent>
    </Card>
  );
};
```

2. **Přidejte typ dat** do `src/types/index.ts`:
```typescript
export interface NewAgentResult {
  // Definujte strukturu dat z API
}
```

3. **Zaregistrujte komponent** v `src/App.tsx`:
```typescript
import { NewAgent } from './components/agents/NewAgent';

// V render funkci přidejte:
<NewAgent data={analysisResult?.new_agent_data} loading={loading} />
```

#### Přidání nového jazyka

1. **Vytvořte jazykový soubor** `src/locales/[jazyk].json`
2. **Přidejte jazyk** do `src/utils/i18n.ts`:
```typescript
const resources = {
  cs: { translation: cs },
  en: { translation: en },
  ru: { translation: ru },
  [novyJazyk]: { translation: novyJazykData }
};
```
3. **Přidejte možnost** do `LanguageSwitch` komponenty

### Technologie

- **React 18** s TypeScript
- **Material-UI (MUI)** - UI komponenty
- **Chart.js + react-chartjs-2** - Grafy a diagramy
- **react-i18next** - Internacionalizace
- **Axios** - HTTP requesty
- **react-dropzone** - Upload souborů

### API Integrace

Aplikace komunikuje s backend API na následujících endpointech:

- `POST /analyze/materials` - Hlavní endpoint pro analýzu
- `GET /health` - Kontrola stavu serveru

#### Formát požadavku

```typescript
const formData = new FormData();
formData.append('docs', file1);
formData.append('docs', file2);
formData.append('smeta', smetaFile);
formData.append('material_query', 'výztuž');
formData.append('use_claude', 'true');
formData.append('language', 'cz');
```

#### Formát odpovědi

```typescript
interface AnalysisResult {
  success: boolean;
  concrete_analysis: ConcreteAnalysisResult;
  volume_analysis: VolumeAnalysisResult;
  material_analysis: MaterialAnalysisResult;
  drawing_analysis?: DrawingAnalysisResult;
  analysis_status: Record<string, string>;
}
```

## Spuštění aplikace

### Vývojové prostředí

```bash
cd frontend
npm install
npm start
```

Aplikace se spustí na [http://localhost:3000](http://localhost:3000)

### Produkční build  

```bash
npm run build
```

### Backend připojení

Ujistěte se, že backend běží na `http://localhost:8000`. Pro změnu API URL upravte proměnnou v `src/services/api.ts`.

## Bezpečnost a kompatibilita

- ✅ Neovlivňuje existující backend kód
- ✅ Všechny změny jsou pouze v `/frontend` složce
- ✅ Bezpečné zobrazování chyb uživateli
- ✅ Validace uploadovaných souborů
- ✅ Modulární architektura pro snadné testování

## Příklady použití

### Upload a analýza souborů

```javascript
// 1. Nahrajte PDF/DOCX soubory
// 2. Zadejte dotaz na materiál (např. "výztuž", "okna")
// 3. Vyberte jazyk (čeština/angličtina/ruština)
// 4. Klikněte "Spustit analýzu"
// 5. Výsledky se zobrazí v sekcích pro každého agenta
```

### Export výsledků

- **Excel** - Tabulková data
- **PDF** - Formátovaný report
- **JSON** - Strukturovaná data pro další zpracování
- **Markdown** - Lidsky čitelný formát

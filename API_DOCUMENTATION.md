# API Endpoints Documentation - New Features

## Part 1: Simplified Position Analysis with User Selection

### 1. Import All Positions (No Limits)
```http
POST /api/positions/import/{project_id}
```

**Description**: Import ALL positions from document without any limitations (max_rows, max_chars removed).

**Response**:
```json
{
  "success": true,
  "project_id": "uuid",
  "project_name": "Stavba XYZ",
  "total_positions": 2547,
  "positions": [
    {
      "position_number": "15",
      "description": "ZÁKLADY ZE ŽELEZOBETONU DO C30/37",
      "quantity": 150.5,
      "unit": "m³",
      "unit_price": 2450.00,
      "total_price": 368725.00
    },
    {
      "position_number": "16",
      "description": "Beton C25/30",
      "quantity": 85.2,
      "unit": "m³",
      "unit_price": 2200.00,
      "total_price": 187440.00
    }
  ],
  "message": "📊 Smeta importována: 2547 pozic"
}
```

### 2. Get Positions for Selection
```http
GET /api/positions/{project_id}
```

**Description**: Retrieve all imported positions for user to select via checkboxes in UI.

**Response**:
```json
{
  "project_id": "uuid",
  "project_name": "Stavba XYZ",
  "total_positions": 2547,
  "positions": [...],
  "message": "📊 2547 pozic připraveno k výběru"
}
```

### 3. Analyze Selected Positions
```http
POST /api/positions/analyze/{project_id}
```

**Request Body**:
```json
{
  "selected_positions": ["15", "234", "567"]
}
```

**Description**: Analyze ONLY the positions selected by user (no automatic classification).

**Response**:
```json
{
  "success": true,
  "project_id": "uuid",
  "project_name": "Stavba XYZ",
  "total_positions": 2547,
  "selected_positions": 3,
  "analyzed_positions": 3,
  "summary": {
    "total_positions": 3,
    "green_count": 2,
    "amber_count": 1,
    "red_count": 0
  },
  "positions": {
    "green": [...],
    "amber": [...],
    "red": [...]
  }
}
```

## Part 2: OCR and Drawing Analysis

### 1. Upload Construction Drawing
```http
POST /api/drawings/upload
```

**Parameters**:
- `project_id` (string): ID projektu
- `drawing_file` (file): Výkres (PDF, PNG, JPG)
- `drawing_type` (string): Typ výkresu (situace, půdorys, řez, detail)

**Response**:
```json
{
  "success": true,
  "project_id": "uuid",
  "drawing_path": "/path/to/drawing.pdf",
  "drawing_type": "půdorys",
  "message": "Výkres nahrán: drawing_20250108_143022.pdf",
  "next_step": "Použijte POST /api/drawings/analyze pro analýzu"
}
```

### 2. Analyze Drawing with OCR/Vision
```http
POST /api/drawings/analyze
```

**Request Body**:
```json
{
  "project_id": "uuid",
  "drawing_path": "/path/to/drawing.pdf",
  "drawing_type": "půdorys"
}
```

**Description**: Performs comprehensive analysis using GPT-4 Vision:
- OCR text extraction
- Construction element identification (PILOTY, ZÁKLADY, PILÍŘE, OPĚRY)
- Material specifications (BETON, OCEL, OPÁLUBKA)
- Czech standards (ČSN EN 206+A2, TKP KAP. 18)
- Exposure classes (XA2+XC2, XF3+XC2)
- Surface categories (Aa, C1a, C2d, Bd, E)

**Response**:
```json
{
  "success": true,
  "drawing_id": "dwg_abc123",
  "project_id": "uuid",
  "analysis": {
    "drawing_id": "dwg_abc123",
    "project_id": "uuid",
    "file_name": "pudorys_1np.pdf",
    "elements": [
      {
        "element_type": "ZÁKLADY",
        "dimensions": "2000x500x400mm",
        "material": "Beton C30/37",
        "position_mark": "Z1",
        "quantity": 12
      },
      {
        "element_type": "PILÍŘE",
        "dimensions": "400x400mm",
        "material": "Beton C35/45",
        "position_mark": "P1",
        "quantity": 8
      }
    ],
    "materials": [
      {
        "material_type": "BETON",
        "specification": "C30/37",
        "quantity": 15.5,
        "unit": "m³",
        "location": "Základy Z1-Z12",
        "standard": "ČSN EN 206+A2"
      },
      {
        "material_type": "OCEL",
        "specification": "B500B",
        "location": "Výztuž Z1-Z12",
        "standard": "ČSN EN 10080"
      }
    ],
    "standards": [
      "ČSN EN 206+A2",
      "TKP KAP. 18",
      "ČSN EN 1992"
    ],
    "exposure_classes": [
      {
        "code": "XA2+XC2",
        "description": "Chemická agrese + karbonatizace",
        "requirements": [
          "Min. krycí vrstva 50mm",
          "Max. w/c 0.45"
        ]
      }
    ],
    "surface_categories": [
      {
        "category": "C2d",
        "finish_requirements": "pohledový beton s nízkou četností vad"
      }
    ],
    "drawing_title": "PŮDORYS 1.NP",
    "drawing_number": "001",
    "scale": "1:50",
    "confidence": "HIGH"
  }
}
```

### 3. Link Drawing to Estimate
```http
POST /api/drawings/link-estimate
```

**Request Body**:
```json
{
  "project_id": "uuid",
  "drawing_id": "dwg_abc123"
}
```

**Description**: Automatically links construction elements from drawing to positions in estimate.

**Response**:
```json
{
  "success": true,
  "project_id": "uuid",
  "drawing_id": "dwg_abc123",
  "links_created": 8,
  "links": [
    {
      "drawing_id": "dwg_abc123",
      "position_number": "15",
      "element_type": "ZÁKLADY",
      "confidence": 0.85,
      "notes": "Matched based on ZÁKLADY and description"
    },
    {
      "drawing_id": "dwg_abc123",
      "position_number": "234",
      "element_type": "PILÍŘE",
      "confidence": 0.92,
      "notes": "Matched based on PILÍŘE and description"
    }
  ],
  "message": "Vytvořeno 8 propojení mezi výkresem a smetou"
}
```

## Czech Construction Standards Supported

### Materials (Materiály)
- **BETON**: Various classes (C12/15, C16/20, C20/25, C25/30, C30/37, C35/45, C40/50, C45/55)
- **OCEL**: Reinforcement steel (B500A, B500B, B500C)
- **OPÁLUBKA**: Formwork systems (systémová, rámová, stěnová)

### Standards (Normy)
- **ČSN EN 206+A2**: Concrete specification
- **ČSN EN 1992**: Eurocode 2 - Design of concrete structures
- **ČSN EN 10080**: Steel for reinforcement of concrete
- **TKP KAP. 18**: Technical quality conditions

### Exposure Classes (Třídy prostředí)
- **XC1-XC4**: Carbonation
- **XD1-XD3**: Chlorides (non-marine)
- **XS1-XS3**: Chlorides (marine)
- **XF1-XF4**: Freeze-thaw
- **XA1-XA3**: Chemical attack

Common combinations:
- **XA2+XC2**: Chemical aggression + carbonation
- **XF3+XC2**: Freeze-thaw + carbonation
- **XC4+XD1**: Carbonation + chlorides

### Surface Categories (Kategorie povrchů)
- **Aa**: Smooth architectural concrete
- **Bd**: Standard operational surface
- **C1a, C2a, C2d**: Various grades of architectural concrete
- **E**: Elementary (no requirements)

### Construction Elements (Konstrukční prvky)
- **PILOTY**: Piles, micropiles
- **ZÁKLADY**: Foundations (strips, pads, slabs)
- **PILÍŘE**: Columns, posts
- **OPĚRY**: Retaining walls, sheet piling
- **STĚNY**: Walls (load-bearing, infill)
- **STROPY**: Floors (monolithic, precast)

## User Interface Flow

### Simplified Workflow
1. **Upload** → Load estimate file (Excel/PDF/XML)
2. **Import** → System imports ALL positions without limits
3. **Display** → User sees all positions in table with checkboxes
4. **Select** → User checks the positions they want to analyze
5. **Analyze** → System analyzes ONLY selected positions
6. **Review** → User reviews results

### Example UI
```
📊 Smeta importována: 2,547 pozic

☑️  Pozice #15: "ZÁKLADY ZE ŽELEZOBETONU DO C30/37" (150.5 m³)
☐   Pozice #16: "Beton C25/30" (85.2 m³)
☑️  Pozice #234: "Opálubka stěn" (320.0 m²)
☐   Pozice #235: "Výztuž B500B" (1250.0 kg)

[Vybrat vše] [Zrušit výběr] [Filtrovat]

[Analyzovat vybrané (2 pozice)] ← User clicks when ready
```

## Notes
- No automatic classification or limitations
- User has full control over which positions to analyze
- All Czech construction standards fully supported
- OCR and Vision analysis for construction drawings
- Automatic linking between drawings and estimates

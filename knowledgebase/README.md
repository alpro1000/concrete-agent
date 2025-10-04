# Knowledge Base

This directory contains normative documents, standards, materials database, and labor norms used by the Stav Agent system.

## Structure

```
knowledgebase/
├── standards/          # Construction standards and codes
│   ├── csn.json       # ČSN (Czech Standards)
│   └── urs_kros_codes.json  # KROS, RTS budget codes
├── materials/         # Construction materials database
│   └── base.json     # Basic materials catalog
└── labor/            # Labor norms and productivity data
    └── norms.json    # Labor norms per ČSN and ÚRS
```

## Usage

Knowledge base files are loaded by agents during analysis to provide:
- Standard compliance checking
- Material specifications and properties
- Cost estimation codes (KROS/RTS)
- Labor productivity norms
- Technology and methodology standards

## Data Format

All files use JSON format with UTF-8 encoding. Each entry should include:
- `id`: Unique identifier
- `name`: Human-readable name (Czech)
- `description`: Detailed description
- `source`: Reference to standard/norm
- `updated_at`: Last update timestamp

## API Access

Knowledge base data is accessible via API endpoints:
- `GET /api/v1/knowledge/standards` - Construction standards
- `GET /api/v1/knowledge/materials` - Materials catalog
- `GET /api/v1/knowledge/labor` - Labor norms

## Maintenance

Knowledge base should be updated:
- When new ČSN/GOST standards are published
- When KROS/RTS codes are revised
- When material prices or specifications change
- When labor norms are updated

Last updated: 2025-01-XX

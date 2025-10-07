# Concrete Agent

AI-powered construction document analysis system.

## Project Structure

```
concrete-agent/
├── app/                    # FastAPI application
│   ├── core/              # Core functionality (LLM service, config, etc.)
│   ├── routers/           # API route handlers
│   └── schemas/           # Pydantic models and schemas
├── agents/                # AI agents for document processing
│   ├── boq_parser/        # Bill of Quantities parser agent
│   └── tzd_reader/        # Technical documentation reader agent
├── parsers/               # Document parsers (PDF, DOCX, etc.)
├── utils/                 # Utility functions and helpers
├── tests/                 # Test suite
├── frontend/              # Frontend application
└── .github/              # GitHub workflows and actions
```

## Getting Started

This project is a construction document analysis system that uses AI agents to process and analyze technical documents, bills of quantities, and drawings.

For more information, see the documentation in the `.github/workflows` directory.

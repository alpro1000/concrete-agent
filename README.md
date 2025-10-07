# Concrete Agent

AI-powered construction planning and analysis system using Claude and GPT-4.

## Project Structure

```
.
├── app/                        # Main application code
│   ├── core/                   # Core application logic
│   ├── services/               # Service layer
│   ├── models/                 # Data models
│   ├── utils/                  # Utility functions
│   ├── prompts/                # AI prompt templates
│   │   ├── claude/             # Claude-specific prompts
│   │   │   ├── parsing/        # Parsing prompts
│   │   │   ├── audit/          # Audit prompts
│   │   │   └── generation/     # Generation prompts
│   │   └── gpt4/               # GPT-4 prompts
│   └── knowledge_base/         # Knowledge base directories
│       ├── B1_Normy_Standardy/       # Standards and norms
│       ├── B2_Tech_Cards/            # Technical cards
│       ├── B3_Pricing/               # Pricing information
│       ├── B4_Historical/projects/   # Historical project data
│       ├── B5_URS_KROS4/             # URS KROS4 documentation
│       ├── B6_RTS/                   # RTS documentation
│       ├── B7_Company_Rules/         # Company rules
│       └── B8_Templates/             # Document templates
├── data/                       # Data storage
│   ├── raw/                    # Raw input data
│   ├── processed/              # Processed data
│   └── results/                # Output results
├── logs/                       # Application logs
│   ├── claude_calls/           # Claude API logs
│   └── gpt4_calls/             # GPT-4 API logs
└── web/                        # Web interface
    ├── static/                 # Static assets
    │   ├── css/                # Stylesheets
    │   └── js/                 # JavaScript files
    └── assets/                 # Other assets (images, etc.)
```

## Quick Start

### Prerequisites

- Python 3.8+
- pip package manager
- Claude API key (from Anthropic)
- OpenAI API key (optional, for GPT-4)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/alpro1000/concrete-agent.git
   cd concrete-agent
   ```

2. **Create virtual environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Copy artifact files to their directories**
   - Place your specific artifact files in the appropriate directories

4. **Create environment file**
   ```bash
   cp .env.example .env
   ```

5. **Add your API keys to .env**
   ```bash
   # Edit .env and add your API keys
   CLAUDE_API_KEY=your_claude_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here  # Optional
   ```

6. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

7. **Run the application**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

8. **Access the application**
   - Web interface: http://localhost:8000
   - API documentation: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

## Features

- 🤖 AI-powered analysis using Claude and GPT-4
- 📊 Construction planning and cost estimation
- 📚 Comprehensive knowledge base management
- 🔍 Document parsing and analysis
- ✅ Automated auditing
- 📝 Report generation
- 🌐 Web-based interface

## Directory Details

### Knowledge Base Structure

The knowledge base is organized into 8 main sections:

1. **B1_Normy_Standardy** - Construction standards and norms
2. **B2_Tech_Cards** - Technical specification cards
3. **B3_Pricing** - Material and labor pricing data
4. **B4_Historical** - Historical project information
5. **B5_URS_KROS4** - URS KROS4 system documentation
6. **B6_RTS** - RTS (Russian Technical Specifications)
7. **B7_Company_Rules** - Internal company guidelines
8. **B8_Templates** - Document templates

### Prompts Organization

Prompts are organized by AI model and task type:
- Claude prompts are separated into parsing, audit, and generation tasks
- GPT-4 prompts have their own dedicated directory

### Data Flow

- **raw/** - Input documents and data files
- **processed/** - Cleaned and normalized data
- **results/** - Final output and generated reports

## Development

### Running Tests
```bash
pytest
```

### Code Style
```bash
black .
flake8 .
```

### Type Checking
```bash
mypy app/
```

## API Endpoints

- `GET /` - Home page
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation
- `GET /redoc` - Alternative API documentation

## Configuration

Configuration is managed through environment variables in `.env`:

- `CLAUDE_API_KEY` - Anthropic Claude API key
- `OPENAI_API_KEY` - OpenAI API key (for GPT-4)
- `APP_ENV` - Application environment (development/production)
- `DEBUG` - Debug mode toggle
- `DATABASE_URL` - Database connection string
- `HOST` - Server host address
- `PORT` - Server port number

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Add your license here]

## Support

For issues and questions, please open an issue on GitHub.

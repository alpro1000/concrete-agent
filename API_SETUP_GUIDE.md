# API Configuration Guide

## Overview

The Construction Analysis API supports multiple AI services for enhanced analysis. To enable full functionality, you need to configure API keys for the services you want to use.

## Required API Keys

### Anthropic Claude API (Recommended)
- **Purpose**: Advanced concrete and materials analysis
- **Environment Variable**: `ANTHROPIC_API_KEY`
- **How to get**: Sign up at https://console.anthropic.com/
- **Models Used**: claude-3-7-sonnet-20250219

### OpenAI API (Optional)
- **Purpose**: Alternative AI analysis and fallback
- **Environment Variable**: `OPENAI_API_KEY`
- **How to get**: Sign up at https://platform.openai.com/
- **Models Used**: gpt-4o-mini, gpt-5 variants

## Configuration Methods

### Method 1: Environment Variables
```bash
export ANTHROPIC_API_KEY="your_anthropic_api_key_here"
export OPENAI_API_KEY="your_openai_api_key_here"
```

### Method 2: .env File
Create a `.env` file in the project root:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
USE_CLAUDE=true
```

### Method 3: Docker Environment
```bash
docker run -e ANTHROPIC_API_KEY=your_key -e OPENAI_API_KEY=your_key your_image
```

## Service Behavior

### With API Keys Configured
- ✅ Full AI-powered analysis available
- ✅ Enhanced concrete grade detection
- ✅ Advanced material classification
- ✅ Detailed structural analysis reports

### Without API Keys
- ✅ Service still functions normally
- ✅ Local knowledge-based analysis works
- ⚠️ AI-enhanced features are disabled
- ⚠️ Users get clear feedback about missing configuration

## Checking Configuration Status

### API Endpoint
```bash
curl http://localhost:8000/status
```

### Response Example
```json
{
  "api_configuration": {
    "anthropic_api_key": {
      "configured": false,
      "status": "❌ Missing - Claude analysis will be unavailable"
    },
    "openai_api_key": {
      "configured": false,
      "status": "❌ Missing - OpenAI analysis will be unavailable"
    }
  },
  "setup_instructions": {
    "missing_apis": ["anthropic_api_key", "openai_api_key"],
    "message": "To enable full functionality, configure missing API keys in environment variables"
  }
}
```

## Error Handling

The service now provides clear, user-friendly error messages when APIs are unavailable:

### Frontend Error Messages
- "LLM service is not configured. Please check API keys in server configuration."
- "Network error - unable to connect to server. Please check if the server is running."

### API Response Errors
```json
{
  "claude_unavailable": true,
  "claude_error": "Claude API недоступен - проверьте ANTHROPIC_API_KEY"
}
```

## Troubleshooting

### Common Issues

1. **"Network Error" in Frontend**
   - Usually means API keys are not configured
   - Check `/status` endpoint for configuration details
   - Verify API keys are valid and have sufficient credits

2. **Service Works But No AI Analysis**
   - Check if `USE_CLAUDE=true` is set
   - Verify API keys are correctly formatted
   - Check server logs for initialization warnings

3. **Intermittent Failures**
   - May indicate API rate limits or quota issues
   - Service will retry failed requests automatically
   - Local analysis continues to work as fallback

### Support
For additional support, check:
- Server logs for detailed error messages
- `/status` endpoint for configuration validation
- GitHub issues for known problems
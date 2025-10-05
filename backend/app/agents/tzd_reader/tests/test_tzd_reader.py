"""
Tests for TZD Reader Agent.
"""

import pytest
from backend.app.agents.tzd_reader.agent import TZDReaderAgent
from backend.app.agents.base_agent import AgentResult


@pytest.mark.asyncio
async def test_tzd_reader_basic():
    """Test basic TZD reader functionality."""
    agent = TZDReaderAgent()
    
    sample_document = """
    TECHNICKÁ ZADÁVACÍ DOKUMENTACE:
    
    BETONOVÉ KONSTRUKCE:
    Beton C25/30, prostředí XC1
    Výztuž B500B podle ČSN EN 10080
    
    MATERIÁLY:
    Cement CEM I 42,5 R
    Kamenivo 0-16 mm
    """
    
    input_data = {
        "document": sample_document
    }
    
    result = await agent.execute(input_data)
    
    assert isinstance(result, AgentResult)
    assert result.success is True
    assert "parsed_data" in result.data
    assert len(result.reasoning_chain) > 0


@pytest.mark.asyncio
async def test_tzd_reader_missing_document():
    """Test TZD reader with missing document."""
    from backend.app.core.exceptions import AgentException
    
    agent = TZDReaderAgent()
    input_data = {}
    
    result = await agent.execute(input_data)
    
    assert result.success is False
    assert len(result.errors) > 0


@pytest.mark.asyncio
async def test_tzd_reader_empty_document():
    """Test TZD reader with empty document."""
    agent = TZDReaderAgent()
    
    input_data = {
        "document": ""
    }
    
    result = await agent.execute(input_data)
    
    assert isinstance(result, AgentResult)


@pytest.mark.asyncio
async def test_tzd_reader_parsing():
    """Test document parsing logic."""
    agent = TZDReaderAgent()
    
    document = """
    SECTION 1:
    Content line 1
    Content line 2
    
    SECTION 2:
    Content line 3
    """
    
    parsed = agent._parse_document(document)
    
    assert "sections" in parsed
    assert len(parsed["sections"]) >= 0
    assert "document_type" in parsed
    assert parsed["document_type"] == "TZD"

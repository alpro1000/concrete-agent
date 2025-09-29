"""
Tests for centralized LLM service
"""

import pytest
import os
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.core.llm_service import LLMService, LLMProvider, get_llm_service, claude_models, openai_models


class TestLLMService:
    """Test cases for centralized LLM service"""
    
    def setup_method(self):
        """Setup for each test"""
        # Reset global instance
        import app.core.llm_service
        app.core.llm_service._llm_service = None
    
    def test_init_with_api_keys(self):
        """Test LLM service initialization with API keys"""
        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'test-anthropic-key',
            'OPENAI_API_KEY': 'test-openai-key',
            'PERPLEXITY_API_KEY': 'test-perplexity-key'
        }):
            service = LLMService()
            
            assert service.anthropic_api_key == 'test-anthropic-key'
            assert service.openai_api_key == 'test-openai-key'
            assert service.perplexity_api_key == 'test-perplexity-key'
    
    def test_init_without_api_keys(self):
        """Test LLM service initialization without API keys"""
        with patch.dict(os.environ, {}, clear=True):
            service = LLMService()
            
            assert service.anthropic_api_key is None
            assert service.openai_api_key is None
            assert service.perplexity_api_key is None
            assert service.claude_client is None
            assert service.openai_client is None
    
    def test_model_mappings(self):
        """Test that model mappings are correctly defined"""
        assert 'opus' in claude_models
        assert 'sonnet' in claude_models
        assert 'gpt5' in openai_models
        assert 'gpt5-mini' in openai_models
        
        # Check that values are proper model names
        assert claude_models['opus'] == 'claude-opus-4-1-20250805'
        assert openai_models['gpt5'] == 'gpt-5-2025-08-07'
    
    def test_get_available_providers(self):
        """Test getting available providers"""
        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'test-key',
            'OPENAI_API_KEY': 'test-key',
        }):
            service = LLMService()
            providers = service.get_available_providers()
            
            assert LLMProvider.CLAUDE in providers
            assert LLMProvider.GPT in providers
            assert LLMProvider.PERPLEXITY not in providers
    
    def test_get_available_models(self):
        """Test getting available models"""
        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'test-key',
            'OPENAI_API_KEY': 'test-key',
        }):
            service = LLMService()
            models = service.get_available_models()
            
            assert 'claude' in models
            assert 'openai' in models
            assert 'opus' in models['claude']
            assert 'gpt5' in models['openai']
    
    def test_run_sync_claude(self):
        """Test sync run method with Claude"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            service = LLMService()
            
            # Mock the Claude client
            mock_response = Mock()
            mock_response.content = [Mock(text="Test response")]
            
            with patch.object(service, 'claude_client') as mock_client:
                mock_client.messages.create.return_value = mock_response
                
                result = service.run("Test prompt", provider="claude", model="opus")
                
                # Check that the correct model was used
                mock_client.messages.create.assert_called_once()
                call_args = mock_client.messages.create.call_args
                assert call_args[1]['model'] == claude_models['opus']
                assert call_args[1]['messages'][0]['content'] == "Test prompt"
    
    def test_run_sync_openai(self):
        """Test sync run method with OpenAI"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            service = LLMService()
            
            # Mock the OpenAI client
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="Test response"))]
            
            with patch.object(service, 'openai_client') as mock_client:
                mock_client.chat.completions.create.return_value = mock_response
                
                result = service.run("Test prompt", provider="openai", model="gpt5")
                
                # Check that the correct model was used
                mock_client.chat.completions.create.assert_called_once()
                call_args = mock_client.chat.completions.create.call_args
                assert call_args[1]['model'] == openai_models['gpt5']
                assert call_args[1]['messages'][0]['content'] == "Test prompt"
    
    def test_run_sync_perplexity(self):
        """Test sync run method with Perplexity"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test-key'}):
            service = LLMService()
            
            mock_response = {
                "choices": [{"message": {"content": "Test response"}}]
            }
            
            with patch('requests.post') as mock_post:
                mock_post.return_value.json.return_value = mock_response
                
                result = service.run("Test prompt", provider="perplexity")
                
                # Check that the request was made to Perplexity
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert "perplexity.ai" in call_args[0][0]
                assert call_args[1]['json']['model'] == "sonar-large-chat"
    
    def test_run_unknown_provider(self):
        """Test run method with unknown provider"""
        service = LLMService()
        
        with pytest.raises(ValueError, match="Unknown provider"):
            service.run("Test prompt", provider="unknown")
    
    def test_run_unknown_model(self):
        """Test run method with unknown model"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            service = LLMService()
            
            with pytest.raises(ValueError, match="Unknown Claude model"):
                service.run("Test prompt", provider="claude", model="unknown")
    
    def test_get_llm_service_singleton(self):
        """Test that get_llm_service returns singleton"""
        service1 = get_llm_service()
        service2 = get_llm_service()
        
        assert service1 is service2
    
    @pytest.mark.asyncio
    async def test_async_run_prompt_backward_compatibility(self):
        """Test that async run_prompt method still works for backward compatibility"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            service = LLMService()
            
            # Mock the async call_claude method
            with patch.object(service, 'call_claude', new_callable=AsyncMock) as mock_call:
                mock_call.return_value = {"content": "Test response", "success": True}
                
                result = await service.run_prompt("claude", "Test prompt")
                
                assert result["content"] == "Test response"
                assert result["success"] is True
                mock_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_prompt_model_mapping(self):
        """Test that run_prompt correctly maps model aliases to full model names"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            service = LLMService()
            
            # Mock the async call_claude method to capture the model parameter
            async def mock_call_claude(prompt, model, max_tokens, system_prompt):
                return {
                    "provider": "claude",
                    "model": model,  # Return the actual model that was passed
                    "content": "Test response", 
                    "success": True
                }
            
            with patch.object(service, 'call_claude', side_effect=mock_call_claude):
                # Test 1: 'sonnet' alias should map to full model name
                result = await service.run_prompt("claude", "Test prompt", model="sonnet")
                assert result["model"] == claude_models["sonnet"]
                
                # Test 2: 'opus' alias should map to full model name
                result = await service.run_prompt("claude", "Test prompt", model="opus")
                assert result["model"] == claude_models["opus"]
                
                # Test 3: Full model name should pass through unchanged
                full_model = "claude-3-haiku-20240307"
                result = await service.run_prompt("claude", "Test prompt", model=full_model)
                assert result["model"] == full_model
                
                # Test 4: No model should use default
                result = await service.run_prompt("claude", "Test prompt")
                assert result["model"] == "claude-3-sonnet-20240229"
    
    def test_get_status(self):
        """Test service status method"""
        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'test-key',
            'OPENAI_API_KEY': 'test-key',
        }):
            service = LLMService()
            status = service.get_status()
            
            assert status["claude_available"] is True
            assert status["gpt_available"] is True
            assert status["perplexity_available"] is False
            assert "model_mappings" in status
            assert "claude" in status["model_mappings"]
            assert "openai" in status["model_mappings"]


if __name__ == "__main__":
    pytest.main([__file__])
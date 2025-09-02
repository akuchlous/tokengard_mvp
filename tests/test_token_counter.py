#!/usr/bin/env python3
"""
Unit tests for the token counter module
"""

import pytest
from app.utils.token_counter import TokenCounter, token_counter


class TestTokenCounter:
    """Test the TokenCounter class."""
    
    def test_token_counter_creation(self):
        """Test creating a TokenCounter."""
        counter = TokenCounter()
        assert counter is not None
        assert 'gpt-3.5-turbo' in counter.model_costs
        assert 'gpt-4' in counter.model_costs
        assert 'default' in counter.model_costs
    
    def test_count_tokens_empty_text(self):
        """Test counting tokens for empty text."""
        counter = TokenCounter()
        assert counter.count_tokens("") == 0
        assert counter.count_tokens(None) == 0
    
    def test_count_tokens_simple_text(self):
        """Test counting tokens for simple text."""
        counter = TokenCounter()
        
        # Simple text
        text1 = "Hello world"
        tokens1 = counter.count_tokens(text1)
        assert tokens1 > 0
        assert isinstance(tokens1, int)
        
        # Longer text
        text2 = "This is a longer text with multiple words to test token counting functionality."
        tokens2 = counter.count_tokens(text2)
        assert tokens2 > tokens1  # Longer text should have more tokens
    
    def test_count_tokens_special_characters(self):
        """Test counting tokens for text with special characters."""
        counter = TokenCounter()
        
        text = "Hello, world! How are you? I'm fine, thank you."
        tokens = counter.count_tokens(text)
        assert tokens > 0
    
    def test_estimate_cost(self):
        """Test cost estimation."""
        counter = TokenCounter()
        
        # Test with GPT-3.5
        cost_info = counter.estimate_cost(1000, 500, 'gpt-3.5-turbo')
        
        assert cost_info['input_tokens'] == 1000
        assert cost_info['output_tokens'] == 500
        assert cost_info['total_tokens'] == 1500
        assert cost_info['model'] == 'gpt-3.5-turbo'
        assert cost_info['input_cost'] > 0
        assert cost_info['output_cost'] > 0
        assert cost_info['total_cost'] > 0
        assert cost_info['total_cost'] == cost_info['input_cost'] + cost_info['output_cost']
    
    def test_estimate_cost_unknown_model(self):
        """Test cost estimation with unknown model (should use default)."""
        counter = TokenCounter()
        
        cost_info = counter.estimate_cost(1000, 500, 'unknown-model')
        
        assert cost_info['model'] == 'unknown-model'
        assert cost_info['total_cost'] > 0  # Should still calculate cost
    
    def test_analyze_request(self):
        """Test request analysis."""
        counter = TokenCounter()
        
        request_data = {
            'text': 'Hello world, this is a test request.',
            'model': 'gpt-3.5-turbo',
            'api_key': 'test-key'
        }
        
        analysis = counter.analyze_request(request_data)
        
        assert analysis['input_text'] == request_data['text']
        assert analysis['input_tokens'] > 0
        assert analysis['model'] == 'gpt-3.5-turbo'
        assert 'cost_estimate' in analysis
        assert analysis['cost_estimate']['input_tokens'] == analysis['input_tokens']
    
    def test_analyze_request_empty_text(self):
        """Test request analysis with empty text."""
        counter = TokenCounter()
        
        request_data = {
            'text': '',
            'model': 'gpt-3.5-turbo'
        }
        
        analysis = counter.analyze_request(request_data)
        
        assert analysis['input_text'] == ''
        assert analysis['input_tokens'] == 0
        assert analysis['cost_estimate']['input_tokens'] == 0
    
    def test_analyze_response_openai_format(self):
        """Test response analysis with OpenAI format."""
        counter = TokenCounter()
        
        response_data = {
            'choices': [
                {
                    'message': {
                        'content': 'This is a test response from the LLM.'
                    }
                }
            ]
        }
        
        analysis = counter.analyze_response(response_data, 'gpt-3.5-turbo')
        
        assert analysis['output_text'] == 'This is a test response from the LLM.'
        assert analysis['output_tokens'] > 0
        assert analysis['model'] == 'gpt-3.5-turbo'
        assert analysis['response_format'] == 'dict'
    
    def test_analyze_response_simple_format(self):
        """Test response analysis with simple format."""
        counter = TokenCounter()
        
        response_data = {
            'content': 'Simple response content'
        }
        
        analysis = counter.analyze_response(response_data, 'gpt-4')
        
        assert analysis['output_text'] == 'Simple response content'
        assert analysis['output_tokens'] > 0
        assert analysis['model'] == 'gpt-4'
    
    def test_analyze_response_string(self):
        """Test response analysis with string response."""
        counter = TokenCounter()
        
        response_data = "This is a string response"
        
        analysis = counter.analyze_response(response_data, 'default')
        
        assert analysis['output_text'] == "This is a string response"
        assert analysis['output_tokens'] > 0
        assert analysis['model'] == 'default'
        assert analysis['response_format'] == 'str'
    
    def test_calculate_cost_savings(self):
        """Test cost savings calculation."""
        counter = TokenCounter()
        
        savings = counter.calculate_cost_savings(1000, 500, 'gpt-3.5-turbo')
        
        assert savings['cache_hit'] is True
        assert savings['cost_saved'] > 0
        assert savings['tokens_saved'] == 1500
        assert savings['model'] == 'gpt-3.5-turbo'
        assert 'savings_breakdown' in savings
        assert savings['savings_breakdown']['total_cost_saved'] == savings['cost_saved']
    
    def test_calculate_cost_savings_zero_tokens(self):
        """Test cost savings calculation with zero tokens."""
        counter = TokenCounter()
        
        savings = counter.calculate_cost_savings(0, 0, 'gpt-3.5-turbo')
        
        assert savings['cache_hit'] is True
        assert savings['cost_saved'] == 0.0
        assert savings['tokens_saved'] == 0


class TestGlobalTokenCounter:
    """Test the global token counter instance."""
    
    def test_global_instance_exists(self):
        """Test that the global token counter instance exists."""
        assert token_counter is not None
        assert isinstance(token_counter, TokenCounter)
    
    def test_global_instance_is_singleton(self):
        """Test that global instance is a singleton."""
        from app.utils.token_counter import token_counter as counter1
        from app.utils.token_counter import token_counter as counter2
        
        assert counter1 is counter2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

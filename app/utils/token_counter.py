"""
Token Counter and Cost Estimation

FLOW OVERVIEW
- count_tokens(text)
  • Heuristic token estimator suitable for approximations when provider tokenizer is unavailable.
- estimate_cost(input_tokens, output_tokens, model)
  • Convert token counts into dollar estimates using per-1K token pricing.
- analyze_request(request_data)
  • Extract text/model, count input tokens, return preliminary cost estimate.
- analyze_response(response_data, model)
  • Extract assistant text from common response shapes and count output tokens.
- calculate_cost_savings(input_tokens, output_tokens, model)
  • Compute hypothetical cost avoided when serving from cache.

Notes
- Pricing values are approximations and should be updated for production.
- Replace with provider tokenizers (e.g., tiktoken) for accurate counts if needed.
"""

import re
import logging
from typing import Dict, Any, Tuple


class TokenCounter:
    """Handles token counting and cost estimation."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Token cost estimates (per 1K tokens) - these are approximate and should be updated
        # Based on OpenAI pricing as of 2024
        self.model_costs = {
            'gpt-3.5-turbo': {
                'input': 0.0015,   # $0.0015 per 1K input tokens
                'output': 0.002    # $0.002 per 1K output tokens
            },
            'gpt-4': {
                'input': 0.03,     # $0.03 per 1K input tokens
                'output': 0.06     # $0.06 per 1K output tokens
            },
            'gpt-4-turbo': {
                'input': 0.01,     # $0.01 per 1K input tokens
                'output': 0.03     # $0.03 per 1K output tokens
            },
            'default': {
                'input': 0.0015,   # Default to GPT-3.5 pricing
                'output': 0.002
            }
        }
    
    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text using a simple approximation.
        
        This is a rough estimation. For production use, consider using
        the actual tokenizer from the LLM provider (e.g., tiktoken for OpenAI).
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        # Simple approximation: ~4 characters per token for English text
        # This is a rough estimate and may vary based on language and content
        char_count = len(text)
        
        # Account for whitespace and special characters
        # Remove extra whitespace and count words
        words = re.findall(r'\S+', text)
        word_count = len(words)
        
        # Estimate tokens as roughly 75% of word count + some overhead
        # This is a conservative estimate
        estimated_tokens = max(1, int(word_count * 0.75 + char_count * 0.1))
        
        return estimated_tokens
    
    def estimate_cost(self, input_tokens: int, output_tokens: int, model: str = 'default') -> Dict[str, Any]:
        """
        Estimate cost for token usage.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name for pricing
            
        Returns:
            Dictionary with cost information
        """
        model_key = model if model in self.model_costs else 'default'
        costs = self.model_costs[model_key]
        
        input_cost = (input_tokens / 1000) * costs['input']
        output_cost = (output_tokens / 1000) * costs['output']
        total_cost = input_cost + output_cost
        
        return {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens,
            'input_cost': round(input_cost, 6),
            'output_cost': round(output_cost, 6),
            'total_cost': round(total_cost, 6),
            'model': model,
            'cost_per_1k_input': costs['input'],
            'cost_per_1k_output': costs['output']
        }
    
    def analyze_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze request data and return token/cost information.
        
        Args:
            request_data: Request data dictionary
            
        Returns:
            Dictionary with token and cost analysis
        """
        text = request_data.get('text', '')
        model = request_data.get('model', 'default')
        
        input_tokens = self.count_tokens(text)
        
        return {
            'input_text': text,
            'input_tokens': input_tokens,
            'model': model,
            'cost_estimate': self.estimate_cost(input_tokens, 0, model)  # No output tokens yet
        }
    
    def analyze_response(self, response_data: Dict[str, Any], model: str = 'default') -> Dict[str, Any]:
        """
        Analyze response data and return token/cost information.
        
        Args:
            response_data: Response data dictionary
            model: Model name for pricing
            
        Returns:
            Dictionary with token and cost analysis
        """
        # Extract response text from various possible formats
        response_text = ""
        
        if isinstance(response_data, dict):
            # Try to extract text from common response formats
            if 'choices' in response_data and response_data['choices']:
                choice = response_data['choices'][0]
                if 'message' in choice and 'content' in choice['message']:
                    response_text = choice['message']['content']
                elif 'text' in choice:
                    response_text = choice['text']
            elif 'content' in response_data:
                response_text = response_data['content']
            elif 'text' in response_data:
                response_text = response_data['text']
            elif 'response' in response_data:
                response_text = str(response_data['response'])
        elif isinstance(response_data, str):
            response_text = response_data
        
        output_tokens = self.count_tokens(response_text)
        
        return {
            'output_text': response_text,
            'output_tokens': output_tokens,
            'model': model,
            'response_format': type(response_data).__name__
        }
    
    def calculate_cost_savings(self, input_tokens: int, output_tokens: int, model: str = 'default') -> Dict[str, Any]:
        """
        Calculate cost savings from cache hit (cost would be zero).
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name for pricing
            
        Returns:
            Dictionary with cost savings information
        """
        cost_info = self.estimate_cost(input_tokens, output_tokens, model)
        
        return {
            'cache_hit': True,
            'cost_saved': cost_info['total_cost'],
            'tokens_saved': cost_info['total_tokens'],
            'model': model,
            'savings_breakdown': {
                'input_cost_saved': cost_info['input_cost'],
                'output_cost_saved': cost_info['output_cost'],
                'total_cost_saved': cost_info['total_cost']
            }
        }


# Global instance
token_counter = TokenCounter()

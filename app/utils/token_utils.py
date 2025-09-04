"""
Token utilities using tiktoken and pricing.json

FLOW OVERVIEW
- load_pricing(): Load JSON pricing table from project root.
- get_encoding_for_model(model): Resolve tiktoken encoding for a given model.
- count_tokens(text, model): Return token count using tiktoken for the given model.
- estimate_cost(token_count, model, is_output=False): Use pricing.json per-1k rates to estimate cost.
"""

import json
import os
from typing import Dict

import tiktoken


_PRICING_CACHE: Dict[str, Dict[str, float]] = {}


def load_pricing() -> Dict[str, Dict[str, float]]:
    global _PRICING_CACHE
    if _PRICING_CACHE:
        return _PRICING_CACHE
    # pricing.json at project root
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pricing_path = os.path.join(root, 'pricing.json')
    with open(pricing_path, 'r', encoding='utf-8') as f:
        _PRICING_CACHE = json.load(f)
    return _PRICING_CACHE


def get_encoding_for_model(model: str):
    # Map common model families to encodings
    try:
        return tiktoken.encoding_for_model(model)
    except Exception:
        # Fallback to cl100k_base commonly used across GPT-3.5/4 families
        return tiktoken.get_encoding('cl100k_base')


def count_tokens(text: str, model: str = 'gpt-3.5-turbo') -> int:
    if not text:
        return 0
    enc = get_encoding_for_model(model)
    return len(enc.encode(text))


def estimate_cost(token_count: int, model: str = 'gpt-3.5-turbo', is_output: bool = False) -> float:
    pricing = load_pricing()
    model_key = model if model in pricing else 'gpt-3.5-turbo'
    per_1k = pricing[model_key]['output_per_1k' if is_output else 'input_per_1k']
    cost = (token_count / 1000.0) * float(per_1k)
    return round(cost, 6)



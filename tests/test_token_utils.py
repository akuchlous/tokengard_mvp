import json
import os

import pytest

from app.utils.token_utils import count_tokens, estimate_cost, load_pricing


def test_count_tokens_short_strings():
    # Basic sanity: token count should be > 0 for short non-empty string
    assert count_tokens("hello", "gpt-3.5-turbo") > 0
    assert count_tokens("hello world", "gpt-3.5-turbo") >= count_tokens("hello", "gpt-3.5-turbo")


def test_estimate_cost_matches_pricing():
    pricing = load_pricing()
    # Use a simple token count (1000) to match per_1k directly
    for model, rates in pricing.items():
        inp = estimate_cost(1000, model, is_output=False)
        out = estimate_cost(1000, model, is_output=True)
        assert inp == pytest.approx(rates['input_per_1k'], rel=1e-6)
        assert out == pytest.approx(rates['output_per_1k'], rel=1e-6)


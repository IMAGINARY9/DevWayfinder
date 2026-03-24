"""Tests for token counting and cost estimation utilities."""

from unittest.mock import MagicMock

import pytest

from devwayfinder.core.protocols import SummarizationContext
from devwayfinder.utils.tokens import (
    MODEL_PRICING,
    TokenEstimate,
    CostEstimate,
    BatchCostSummary,
    estimate_tokens_for_text,
    estimate_context_tokens,
    estimate_output_tokens,
    estimate_total_tokens,
    estimate_cost,
    estimate_cost_for_context,
)


class TestTokenEstimate:
    """Test TokenEstimate dataclass."""

    def test_creation(self):
        """Test creating a TokenEstimate."""
        token_est = TokenEstimate(input_tokens=100, output_tokens=50, total_tokens=150)
        assert token_est.input_tokens == 100
        assert token_est.output_tokens == 50
        assert token_est.total_tokens == 150

    def test_zero_tokens(self):
        """Test TokenEstimate with zero tokens."""
        token_est = TokenEstimate(input_tokens=0, output_tokens=0, total_tokens=0)
        assert token_est.total_tokens == 0

    def test_large_token_counts(self):
        """Test TokenEstimate with large token counts."""
        token_est = TokenEstimate(input_tokens=1_000_000, output_tokens=500_000, total_tokens=1_500_000)
        assert token_est.total_tokens == 1_500_000

    def test_to_dict(self):
        """Test converting TokenEstimate to dict."""
        token_est = TokenEstimate(input_tokens=100, output_tokens=50, total_tokens=150)
        d = token_est.to_dict()
        assert d["input_tokens"] == 100
        assert d["output_tokens"] == 50
        assert d["total_tokens"] == 150


class TestCostEstimate:
    """Test CostEstimate dataclass."""

    def test_creation(self):
        """Test creating a CostEstimate."""
        cost_est = CostEstimate(input_cost=0.001, output_cost=0.0005, total_cost=0.0015)
        assert cost_est.input_cost == 0.001
        assert cost_est.output_cost == 0.0005
        assert cost_est.total_cost == 0.0015

    def test_str_formatting(self):
        """Test string formatting of cost."""
        cost_est = CostEstimate(input_cost=0.00001, output_cost=0.00005, total_cost=0.00006)
        formatted = str(cost_est)
        # Should be a string with proper formatting
        assert isinstance(formatted, str)
        assert "$" in formatted or "0" in formatted

    def test_zero_cost(self):
        """Test CostEstimate with zero cost."""
        cost_est = CostEstimate(input_cost=0.0, output_cost=0.0, total_cost=0.0)
        assert cost_est.total_cost == 0.0

    def test_very_small_costs(self):
        """Test CostEstimate with very small costs."""
        cost_est = CostEstimate(input_cost=0.000001, output_cost=0.000002, total_cost=0.000003)
        assert cost_est.total_cost == 0.000003

    def test_large_costs(self):
        """Test CostEstimate with large costs."""
        cost_est = CostEstimate(input_cost=10.0, output_cost=20.0, total_cost=30.0)
        assert cost_est.total_cost == 30.0

    def test_to_dict(self):
        """Test converting CostEstimate to dict."""
        cost_est = CostEstimate(input_cost=0.001, output_cost=0.0005, total_cost=0.0015)
        d = cost_est.to_dict()
        assert "input_cost" in d
        assert "output_cost" in d
        assert "total_cost" in d
        assert d["currency"] == "USD"


class TestBatchCostSummary:
    """Test BatchCostSummary dataclass."""

    def test_creation_empty(self):
        """Test creating an empty BatchCostSummary."""
        summary = BatchCostSummary(
            total_tokens=0,
            input_tokens=0,
            output_tokens=0,
            total_cost=0.0,
            operations_count=0,
            cost_per_operation=0.0,
            free_operations=0,
            llm_operations=0,
        )
        assert summary.operations_count == 0
        assert summary.total_cost == 0.0

    def test_creation_with_costs(self):
        """Test creating a BatchCostSummary with costs."""
        summary = BatchCostSummary(
            total_tokens=2000,
            input_tokens=1000,
            output_tokens=1000,
            total_cost=0.0045,
            operations_count=2,
            cost_per_operation=0.00225,
            free_operations=0,
            llm_operations=2,
        )
        assert summary.operations_count == 2
        assert summary.total_cost == 0.0045

    def test_str_formatting(self):
        """Test string formatting of batch summary."""
        summary = BatchCostSummary(
            total_tokens=2000,
            input_tokens=1000,
            output_tokens=1000,
            total_cost=0.0045,
            operations_count=2,
            cost_per_operation=0.00225,
            free_operations=1,
            llm_operations=1,
        )
        formatted = str(summary)
        assert isinstance(formatted, str)
        assert len(formatted) > 0

    def test_to_dict(self):
        """Test converting batch summary to dict."""
        summary = BatchCostSummary(
            total_tokens=2000,
            input_tokens=1000,
            output_tokens=1000,
            total_cost=0.0045,
            operations_count=2,
            cost_per_operation=0.00225,
            free_operations=0,
            llm_operations=2,
        )
        d = summary.to_dict()
        assert d["operations_count"] == 2
        assert d["total_cost"] == 0.0045


class TestTokenEstimationFunctions:
    """Test token estimation functions."""

    def test_estimate_tokens_for_text_short(self):
        """Test token estimation for short text."""
        text = "hello world"
        tokens = estimate_tokens_for_text(text)
        # "hello world" = 11 chars, should be ~3 tokens (11/4 = 2.75 ≈ 3)
        assert isinstance(tokens, int)
        assert tokens > 0

    def test_estimate_tokens_for_text_long(self):
        """Test token estimation for long text."""
        text = "x" * 1000  # 1000 characters
        tokens = estimate_tokens_for_text(text)
        # 1000 chars / 4 chars per token = 250 tokens
        assert tokens == 250

    def test_estimate_tokens_for_empty_text(self):
        """Test token estimation for empty text."""
        tokens = estimate_tokens_for_text("")
        assert tokens == 0

    def test_estimate_tokens_for_none_text(self):
        """Test token estimation for None text."""
        tokens = estimate_tokens_for_text(None)
        assert tokens == 0

    def test_estimate_context_tokens(self):
        """Test context token estimation."""
        context = MagicMock(spec=SummarizationContext)
        context.module_name = "test_module"
        context.file_content = None
        context.docstrings = ["This is a docstring."]
        context.signatures = ["def func(): pass"]
        context.imports = ["import os", "import sys"]
        context.exports = ["func", "CLASS"]
        context.neighbors = []

        tokens = estimate_context_tokens(context)
        assert isinstance(tokens, int)
        assert tokens > 0

    def test_estimate_output_tokens(self):
        """Test output tokens estimation."""
        tokens = estimate_output_tokens()
        # Default is 256 tokens
        assert tokens == 256

    def test_estimate_total_tokens(self):
        """Test total tokens estimation."""
        context = MagicMock(spec=SummarizationContext)
        context.module_name = "test"
        context.file_content = None
        context.docstrings = []
        context.signatures = []
        context.imports = []
        context.exports = []
        context.neighbors = []

        total = estimate_total_tokens(context)
        assert isinstance(total, TokenEstimate)
        # Should be context tokens + 256 output tokens
        assert total.output_tokens == 256
        assert total.input_tokens > 0
        assert total.total_tokens == total.input_tokens + total.output_tokens

    def test_estimate_total_tokens_with_custom_output(self):
        """Test total tokens with custom output token count."""
        context = MagicMock(spec=SummarizationContext)
        context.module_name = "test"
        context.file_content = None
        context.docstrings = []
        context.signatures = []
        context.imports = []
        context.exports = []
        context.neighbors = []

        total = estimate_total_tokens(context, output_tokens=512)
        assert total.output_tokens == 512
        assert total.total_tokens == total.input_tokens + 512

    def test_estimate_total_tokens_complex_context(self):
        """Test total tokens with complex context."""
        context = MagicMock(spec=SummarizationContext)
        context.module_name = "complex_module" * 5  # Longer name
        context.file_content = "x" * 500  # Some file content
        context.docstrings = [
            "Long docstring " * 20,  # Long docstring
            "Another docstring",
        ]
        context.signatures = [f"def func_{i}(): pass" for i in range(10)]
        context.imports = [f"import module_{i}" for i in range(15)]
        context.exports = [f"export_{i}" for i in range(8)]
        context.neighbors = [f"neighbor_{i}" for i in range(5)]

        total = estimate_total_tokens(context)
        assert total.total_tokens > 256  # Should have significant input tokens
        assert total.output_tokens == 256


class TestCostEstimationFunctions:
    """Test cost estimation functions."""

    def test_estimate_cost_basic(self):
        """Test basic cost estimation."""
        tokens = TokenEstimate(input_tokens=1000, output_tokens=500, total_tokens=1500)
        cost = estimate_cost(tokens, model_name="gpt-4o-mini")
        
        assert isinstance(cost, CostEstimate)
        assert cost.input_cost > 0
        assert cost.output_cost > 0
        assert cost.total_cost > 0

    def test_estimate_cost_zero_tokens(self):
        """Test cost estimation with zero tokens."""
        tokens = TokenEstimate(input_tokens=0, output_tokens=0, total_tokens=0)
        cost = estimate_cost(tokens, model_name="gpt-4o-mini")
        
        assert cost.input_cost == 0.0
        assert cost.output_cost == 0.0
        assert cost.total_cost == 0.0

    def test_estimate_cost_different_models(self):
        """Test cost estimation with different models."""
        tokens = TokenEstimate(input_tokens=1000, output_tokens=500, total_tokens=1500)
        
        # GPT-4o should be more expensive than GPT-4o-mini
        cost_4o = estimate_cost(tokens, model_name="gpt-4o")
        cost_mini = estimate_cost(tokens, model_name="gpt-4o-mini")
        
        assert cost_4o.total_cost > cost_mini.total_cost

    def test_estimate_cost_local_model(self):
        """Test cost estimation for local models (zero cost)."""
        tokens = TokenEstimate(input_tokens=1000, output_tokens=500, total_tokens=1500)
        cost = estimate_cost(tokens, model_name="mistral:7b")
        
        # Local models should have zero cost
        assert cost.total_cost == 0.0

    def test_estimate_cost_for_context(self):
        """Test cost estimation from context."""
        context = MagicMock(spec=SummarizationContext)
        context.module_name = "test_module"
        context.file_content = None
        context.docstrings = ["Test docstring"]
        context.signatures = ["def func(): pass"]
        context.imports = ["import os"]
        context.exports = ["func"]
        context.neighbors = []

        cost = estimate_cost_for_context(context, model_name="gpt-4o-mini")
        assert isinstance(cost, CostEstimate)
        assert cost.total_cost >= 0

    def test_estimate_cost_for_context_gpt4(self):
        """Test cost estimation from context with GPT-4."""
        context = MagicMock(spec=SummarizationContext)
        context.module_name = "large_module" * 10
        context.file_content = "x" * 1000
        context.docstrings = ["Detailed docstring " * 20]
        context.signatures = [f"def func_{i}(): pass" for i in range(20)]
        context.imports = [f"import mod_{i}" for i in range(20)]
        context.exports = [f"exp_{i}" for i in range(20)]
        context.neighbors = [f"neighbor_{i}" for i in range(5)]

        cost = estimate_cost_for_context(context, model_name="gpt-4o")
        # GPT-4o should have cost for complex context
        assert isinstance(cost, CostEstimate)
        assert cost.total_cost > 0

    def test_estimate_cost_default_model(self):
        """Test cost estimation with default model."""
        tokens = TokenEstimate(input_tokens=1000, output_tokens=500, total_tokens=1500)
        cost = estimate_cost(tokens)  # No model specified
        
        # Should use default (gpt-4o-mini)
        cost_mini = estimate_cost(tokens, model_name="gpt-4o-mini")
        assert cost.total_cost == cost_mini.total_cost

    def test_estimate_cost_unknown_model(self):
        """Test cost estimation with unknown model."""
        tokens = TokenEstimate(input_tokens=1000, output_tokens=500, total_tokens=1500)
        cost = estimate_cost(tokens, model_name="unknown-model-xyz")
        
        # Unknown models default to free
        assert cost.total_cost == 0.0


class TestModelPricing:
    """Test model pricing database."""

    def test_all_models_have_pricing(self):
        """Test that all models have valid pricing."""
        assert len(MODEL_PRICING) > 0
        
        for model_name, pricing in MODEL_PRICING.items():
            assert isinstance(model_name, str)
            assert "input_cost_per_1m" in pricing
            assert "output_cost_per_1m" in pricing
            assert "context_window" in pricing
            
            # Prices should be non-negative
            assert pricing["input_cost_per_1m"] >= 0
            assert pricing["output_cost_per_1m"] >= 0
            assert pricing["context_window"] > 0

    def test_gpt4o_pricing(self):
        """Test GPT-4o pricing exists."""
        assert "gpt-4o" in MODEL_PRICING
        pricing = MODEL_PRICING["gpt-4o"]
        
        assert pricing["input_cost_per_1m"] > 0  # Paid model
        assert pricing["output_cost_per_1m"] > 0
        assert pricing["context_window"] >= 4096

    def test_gpt4o_mini_pricing(self):
        """Test GPT-4o-mini pricing exists."""
        assert "gpt-4o-mini" in MODEL_PRICING
        pricing = MODEL_PRICING["gpt-4o-mini"]
        
        assert pricing["input_cost_per_1m"] > 0
        assert pricing["output_cost_per_1m"] > 0

    def test_local_model_pricing(self):
        """Test local model pricing (should be free)."""
        local_models = ["mistral:7b", "llama2", "neural-chat"]
        
        for model in local_models:
            if model in MODEL_PRICING:
                pricing = MODEL_PRICING[model]
                assert pricing["input_cost_per_1m"] == 0.0
                assert pricing["output_cost_per_1m"] == 0.0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_estimate_tokens_unicode_text(self):
        """Test token estimation with Unicode text."""
        text = "Hello 世界 🌍 مرحبا мир"
        tokens = estimate_tokens_for_text(text)
        assert isinstance(tokens, int)
        assert tokens >= 0

    def test_context_with_empty_lists(self):
        """Test context with empty lists."""
        context = MagicMock(spec=SummarizationContext)
        context.module_name = "test"
        context.file_content = None
        context.docstrings = []
        context.signatures = []
        context.imports = []
        context.exports = []
        context.neighbors = []

        tokens = estimate_context_tokens(context)
        assert isinstance(tokens, int)
        assert tokens >= 0

    def test_context_with_long_lists(self):
        """Test context with many items."""
        context = MagicMock(spec=SummarizationContext)
        context.module_name = "test"
        context.file_content = None
        context.docstrings = [f"doc_{i}" for i in range(50)]
        context.signatures = [f"sig_{i}" for i in range(50)]
        context.imports = [f"import_{i}" for i in range(50)]
        context.exports = [f"export_{i}" for i in range(50)]
        context.neighbors = [f"neighbor_{i}" for i in range(50)]

        tokens = estimate_context_tokens(context)
        assert isinstance(tokens, int)
        assert tokens > 0


class TestFormatting:
    """Test formatting of costs and estimates."""

    def test_cost_formatting_small_amount(self):
        """Test formatting of small cost amount."""
        cost = CostEstimate(input_cost=0.000001, output_cost=0.000001, total_cost=0.000002)
        formatted = str(cost)
        assert isinstance(formatted, str)

    def test_cost_formatting_large_amount(self):
        """Test formatting of large cost amount."""
        cost = CostEstimate(input_cost=100.0, output_cost=200.0, total_cost=300.0)
        formatted = str(cost)
        assert isinstance(formatted, str)

    def test_cost_formatting_zero(self):
        """Test formatting of zero cost."""
        cost = CostEstimate(input_cost=0.0, output_cost=0.0, total_cost=0.0)
        formatted = str(cost)
        assert isinstance(formatted, str)
        assert "$" in formatted or "0" in formatted

    def test_cost_formatting_mid_range(self):
        """Test formatting of mid-range costs."""
        cost = CostEstimate(input_cost=0.005, output_cost=0.010, total_cost=0.015)
        formatted = str(cost)
        assert isinstance(formatted, str)
        assert "$" in formatted


class TestIntegration:
    """Integration tests for token and cost estimation."""

    def test_full_pipeline_context_to_cost(self):
        """Test full pipeline from context to cost."""
        context = MagicMock(spec=SummarizationContext)
        context.module_name = "integration_test"
        context.file_content = "x" * 200
        context.docstrings = ["Test"]
        context.signatures = ["def test(): pass"]
        context.imports = ["import os"]
        context.exports = ["test"]
        context.neighbors = []

        # Full pipeline
        cost = estimate_cost_for_context(context, model_name="gpt-4o-mini")
        
        assert isinstance(cost, CostEstimate)
        assert cost.total_cost >= 0
        assert cost.input_cost >= 0
        assert cost.output_cost >= 0

    def test_batch_summary_calculation(self):
        """Test batch summary cost calculation."""
        costs = []
        for i in range(5):
            cost = CostEstimate(
                input_cost=0.001 * (i + 1),
                output_cost=0.0005 * (i + 1),
                total_cost=0.0015 * (i + 1),
            )
            costs.append(cost)

        total_cost = sum(c.total_cost for c in costs)
        summary = BatchCostSummary(
            total_tokens=7500,  # 5 * 1500 tokens
            input_tokens=5000,  # 5 * 1000
            output_tokens=2500,  # 5 * 500
            total_cost=total_cost,
            operations_count=5,
            cost_per_operation=total_cost / 5,
            free_operations=1,
            llm_operations=4,
        )

        assert summary.operations_count == 5
        assert summary.total_tokens == 7500
        assert summary.llm_operations == 4


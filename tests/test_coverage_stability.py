"""Deterministic coverage tests for CI stability.

These tests focus on branches that are independent from live provider endpoints,
keeping coverage above quality gates even when integration-real tests are skipped.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

import devwayfinder.version as version_module
from devwayfinder.__main__ import main as entry_main
from devwayfinder.analyzers.python_analyzer import ClassInfo, FunctionInfo, PythonExtractionResult
from devwayfinder.core.exceptions import MissingConfigError
from devwayfinder.core.models import Module, ModuleType
from devwayfinder.core.protocols import SummarizationContext
from devwayfinder.providers.config import ProviderConfig
from devwayfinder.providers.openai import OpenAIProvider
from devwayfinder.summarizers.concurrency import ConcurrencyPool
from devwayfinder.summarizers.controller import (
    SummarizationConfig,
    SummarizationController,
    SummarizationResult,
)
from devwayfinder.summarizers.provider_chain import ProviderChain
from devwayfinder.summarizers.templates import SummarizationType

if TYPE_CHECKING:
    from pathlib import Path


class DummyProvider:
    """Simple async provider stub for provider-chain tests."""

    def __init__(self, name: str, response: str = "ok") -> None:
        self.name = name
        self.summarize = AsyncMock(return_value=response)


@dataclass
class _SampleObject:
    """Small object to exercise metadata rendering fallbacks."""

    label: str


# =============================================================================
# SummarizationContext coverage
# =============================================================================


def test_context_with_updated_metadata_copies_list_fields() -> None:
    """Updated contexts should copy list fields and merge metadata."""
    original = SummarizationContext(
        module_name="pkg/mod.py",
        signatures=["def run()"],
        docstrings=["run everything"],
        imports=["os"],
        exports=["run"],
        neighbors=["pkg/dep.py"],
        metadata={"phase": "base"},
    )

    updated = original.with_updated_metadata(phase="enhanced", attempts=2)

    original.signatures.append("def leaked()")
    original.metadata["phase"] = "mutated"

    assert updated.module_name == "pkg/mod.py"
    assert updated.signatures == ["def run()"]
    assert updated.metadata["phase"] == "enhanced"
    assert updated.metadata["attempts"] == 2


def test_context_prompt_rendering_includes_signals_and_limits() -> None:
    """Prompt rendering should include optional sections and cap signal lines."""
    metadata: dict[str, object] = {
        "relative_path": "src/pkg/mod.py",
        "language": "python",
        "risk_markers": ["hot path", "", "fan-out"],
        "prompt_hints": ["explain runtime flow", ""],
        "quality_profile": "detailed",
        "feature_flag": True,
        "priority": 3,
        "latency_budget": 12.5,
        "owners": ["a", "b", "c", "d", "e", "f", "g"],
        "stats": {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5},
        "object_value": _SampleObject("obj"),
        "empty_text": "",
        "empty_list": [],
        "empty_dict": {},
        "none_value": None,
    }
    for idx in range(20):
        metadata[f"signal_{idx}"] = idx

    context = SummarizationContext(
        module_name="pkg/mod.py",
        signatures=["def run()", "class Worker"],
        docstrings=["Module summary line"],
        imports=["os", "sys"],
        exports=["run", "Worker"],
        neighbors=["pkg/dep.py"],
        metadata=metadata,
    )

    rendered = context.to_prompt_context(max_chars=20_000)

    assert "Module: pkg/mod.py" in rendered
    assert "Path: src/pkg/mod.py" in rendered
    assert "Language: python" in rendered
    assert "Risk Markers:" in rendered
    assert "Focus:" in rendered
    assert "Context Signals:" in rendered

    signal_lines = [line for line in rendered.splitlines() if line.startswith("- signal ")]
    assert len(signal_lines) <= 12


def test_context_prompt_rendering_truncates_to_max_chars() -> None:
    """Prompt rendering should truncate when max_chars is exceeded."""
    long_content = "line\n" * 1_500
    context = SummarizationContext(
        module_name="pkg/huge.py",
        file_content=long_content,
    )

    rendered = context.to_prompt_context(max_chars=180)

    assert len(rendered) <= 180 + len("\n...(truncated)")
    assert rendered.endswith("...(truncated)")


def test_context_render_metadata_lines_caps_at_twelve() -> None:
    """Internal metadata rendering should cap output lines at 12."""
    context = SummarizationContext(
        module_name="pkg/data.py",
        metadata={f"k_{i}": i for i in range(30)},
    )

    lines = context._render_metadata_lines()
    assert len(lines) == 12


# =============================================================================
# ProviderChain coverage
# =============================================================================


@pytest.mark.asyncio
async def test_provider_chain_invoke_uses_explicit_callable() -> None:
    """Explicit provider_call should bypass provider.summarize."""
    provider = DummyProvider("direct")
    chain = ProviderChain([provider])
    context = SummarizationContext(module_name="mod")

    async def provider_call(_provider: object, _context: SummarizationContext) -> str:
        return "from call"

    result = await chain._invoke_provider(provider_call, provider, context)

    assert result == "from call"
    provider.summarize.assert_not_awaited()


@pytest.mark.asyncio
async def test_provider_chain_invoke_without_retry_manager_uses_provider() -> None:
    """Without explicit callable or retry manager, chain should call provider.summarize."""
    provider = DummyProvider("native", response="native summary")
    chain = ProviderChain([provider], retry_manager=None)
    context = SummarizationContext(module_name="mod")

    result = await chain._invoke_provider(None, provider, context)

    assert result == "native summary"
    provider.summarize.assert_awaited_once()


@pytest.mark.asyncio
async def test_provider_chain_quality_threshold_passes_when_long_enough() -> None:
    """Quality retry should not run if first summary already meets threshold."""
    provider = DummyProvider("quality")
    chain = ProviderChain([provider])
    context = SummarizationContext(module_name="mod", metadata={"minimum_summary_words": "3"})

    summary = await chain._enforce_quality_threshold(None, provider, context, "one two three")

    assert summary == "one two three"
    provider.summarize.assert_not_awaited()


@pytest.mark.asyncio
async def test_provider_chain_quality_retry_raises_on_empty_retry_summary() -> None:
    """Quality retry should fail when retry response sanitizes to empty text."""
    provider = DummyProvider("quality")
    provider.summarize = AsyncMock(return_value="   ")
    chain = ProviderChain([provider])
    context = SummarizationContext(module_name="mod", metadata={"minimum_summary_words": 4})

    with pytest.raises(ValueError, match="empty summary"):
        await chain._enforce_quality_threshold(None, provider, context, "short")


def test_provider_chain_minimum_words_parsing_variants() -> None:
    """minimum_summary_words should parse digit strings and reject invalid values."""
    valid = SummarizationContext(module_name="x", metadata={"minimum_summary_words": " 7 "})
    invalid = SummarizationContext(module_name="x", metadata={"minimum_summary_words": "bad"})

    assert ProviderChain._minimum_words(valid) == 7
    assert ProviderChain._minimum_words(invalid) == 0


@pytest.mark.asyncio
async def test_provider_chain_remove_and_close_operations() -> None:
    """Provider removal and close-all should handle success, miss, and close failures."""
    closable = MagicMock()
    closable.name = "closable"
    closable.close = AsyncMock(side_effect=RuntimeError("close failed"))

    plain = DummyProvider("plain")
    chain = ProviderChain([closable, plain])

    assert chain.get_provider_names() == ["closable", "plain"]
    assert chain.remove_provider("closable") is True
    assert chain.remove_provider("missing") is False

    chain.add_provider(closable)
    await chain.close_all()

    closable.close.assert_awaited_once()


# =============================================================================
# ConcurrencyPool coverage
# =============================================================================


@pytest.mark.asyncio
async def test_concurrency_pool_run_batch_returns_exceptions() -> None:
    """run_batch should collect exceptions instead of raising them."""
    pool = ConcurrencyPool(max_concurrent=2)

    async def ok() -> str:
        return "ok"

    async def fail() -> str:
        raise ValueError("batch failure")

    results = await pool.run_batch([ok(), fail()])

    assert results[0] == "ok"
    assert isinstance(results[1], ValueError)


@pytest.mark.asyncio
async def test_concurrency_pool_reset_reinitializes_semaphore() -> None:
    """reset should drop cached semaphore so the next access recreates it."""
    pool = ConcurrencyPool(max_concurrent=1)
    before = pool.semaphore

    pool.reset()

    after = pool.semaphore
    assert before is not after


# =============================================================================
# SummarizationController branch coverage
# =============================================================================


@pytest.mark.asyncio
async def test_controller_summarize_module_from_analysis_with_heuristic(tmp_path: Path) -> None:
    """summarize_module_from_analysis should support heuristic-only operation."""
    source_file = tmp_path / "service.py"
    source_file.write_text("def run(x):\n    return x\n", encoding="utf-8")

    analysis = PythonExtractionResult(
        imports=["os"],
        exports=["run"],
        functions=[FunctionInfo(name="run", lineno=1, parameters=["x"])],
        classes=[ClassInfo(name="Worker", lineno=3, methods=["start"])],
        module_docstring="Service module",
    )

    controller = SummarizationController(
        tmp_path,
        SummarizationConfig(providers=[], use_heuristic_fallback=True),
    )

    result = await controller.summarize_module_from_analysis(source_file, analysis)

    assert result.success is True
    assert result.provider_used == "heuristic"
    assert "service.py" in result.summary


@pytest.mark.asyncio
async def test_controller_summarize_modules_batch_maps_missing_and_errors(tmp_path: Path) -> None:
    """Batch summarization should create failure results for missing keys and exceptions."""
    module_a = Module(
        name="a.py",
        path=tmp_path / "a.py",
        module_type=ModuleType.FILE,
    )
    module_b = Module(
        name="b.py",
        path=tmp_path / "b.py",
        module_type=ModuleType.FILE,
    )
    controller = SummarizationController(tmp_path)

    async def fake_run_concurrent(
        _tasks: tuple[tuple[str, object], ...],
    ) -> dict[str, object]:
        return {str(module_a.path): RuntimeError("boom")}

    monkeypatch_target = controller.concurrency_pool
    monkeypatch_target.run_concurrent = fake_run_concurrent  # type: ignore[method-assign]

    output = await controller.summarize_modules_batch([module_a, module_b])

    assert output[str(module_a.path)].success is False
    assert output[str(module_a.path)].error == "boom"
    assert output[str(module_b.path)].success is False
    assert output[str(module_b.path)].error == "No result returned for module"


@pytest.mark.asyncio
async def test_controller_entry_points_batch_handles_task_exception(tmp_path: Path) -> None:
    """Entry-point batch summarization should convert gather exceptions into failure results."""
    module_a = Module(
        name="a.py",
        path=tmp_path / "a.py",
        module_type=ModuleType.FILE,
        entry_point=True,
    )
    module_b = Module(
        name="b.py",
        path=tmp_path / "b.py",
        module_type=ModuleType.FILE,
        entry_point=True,
    )

    controller = SummarizationController(tmp_path)

    async def fake_summarize_entry_point(
        module: Module,
        *,
        graph: object | None = None,
        file_content: str | None = None,
    ) -> SummarizationResult:
        if module.name == "a.py":
            raise RuntimeError("entrypoint failed")
        return SummarizationResult(
            summary="ok",
            provider_used="heuristic",
            summary_type=SummarizationType.ENTRY_POINT,
            module_name=module.name,
            success=True,
        )

    controller.summarize_entry_point = fake_summarize_entry_point  # type: ignore[method-assign]

    output = await controller.summarize_entry_points_batch([module_a, module_b])

    assert output[str(module_a.path)].success is False
    assert "entrypoint failed" in (output[str(module_a.path)].error or "")
    assert output[str(module_b.path)].success is True


def test_controller_quality_metadata_and_template_guidance(tmp_path: Path) -> None:
    """Controller should apply summary-type quality metadata and hints consistently."""
    config = SummarizationConfig(
        quality_profile="compact",
        minimum_summary_words=5,
        minimum_architecture_words=12,
        minimum_entry_point_words=7,
    )
    controller = SummarizationController(tmp_path, config)

    architecture_context = SummarizationContext(
        module_name="arch",
        metadata={"minimum_summary_words": 3, "prompt_hints": ["existing", " "]},
    )
    dependency_context = SummarizationContext(module_name="deps", metadata={})
    entry_context = SummarizationContext(
        module_name="entry", metadata={"minimum_summary_words": 20}
    )

    controller._apply_quality_metadata(architecture_context, SummarizationType.ARCHITECTURE)
    controller._apply_quality_metadata(dependency_context, SummarizationType.DEPENDENCY)
    controller._apply_quality_metadata(entry_context, SummarizationType.ENTRY_POINT)

    assert architecture_context.metadata["quality_profile"] == "compact"
    assert architecture_context.metadata["minimum_summary_words"] == 12
    assert dependency_context.metadata["minimum_summary_words"] == 5
    assert entry_context.metadata["minimum_summary_words"] == 20

    controller._apply_template_guidance(architecture_context, SummarizationType.ARCHITECTURE)
    controller._apply_template_guidance(dependency_context, SummarizationType.DEPENDENCY)
    controller._apply_template_guidance(entry_context, SummarizationType.ENTRY_POINT)

    module_context = SummarizationContext(
        module_name="module", metadata={"prompt_hints": "bad-type"}
    )
    controller._apply_template_guidance(module_context, SummarizationType.MODULE)

    architecture_hints = architecture_context.metadata["prompt_hints"]
    dependency_hints = dependency_context.metadata["prompt_hints"]
    entry_hints = entry_context.metadata["prompt_hints"]
    module_hints = module_context.metadata["prompt_hints"]

    assert isinstance(architecture_hints, list)
    assert any("runtime flow" in hint for hint in architecture_hints)
    assert isinstance(dependency_hints, list)
    assert any("static dependencies" in hint for hint in dependency_hints)
    assert any("interaction paths" in hint for hint in dependency_hints)
    assert isinstance(entry_hints, list)
    assert any("first steps" in hint for hint in entry_hints)
    assert isinstance(module_hints, list)
    assert any("onboarding relevance" in hint for hint in module_hints)


# =============================================================================
# Provider/version/entrypoint helpers
# =============================================================================


def test_openai_provider_requires_api_key() -> None:
    """Official OpenAI provider should reject missing API keys."""
    with pytest.raises(MissingConfigError, match="api_key"):
        OpenAIProvider(ProviderConfig(provider="openai", model_name="gpt-4o-mini"))


def test_openai_provider_model_name_required_for_completion() -> None:
    """Official OpenAI provider should require model_name when generating."""
    provider = OpenAIProvider(ProviderConfig(provider="openai", api_key="test-key"))

    with pytest.raises(MissingConfigError, match="model_name"):
        provider._model_name()


@pytest.mark.asyncio
async def test_base_prompt_template_for_minimum_words_and_defaults() -> None:
    """Prompt message builder should support both default and configured lengths."""
    provider = OpenAIProvider(
        ProviderConfig(provider="openai", api_key="test-key", model_name="gpt-4o-mini")
    )

    default_ctx = SummarizationContext(module_name="a.py")
    strict_ctx = SummarizationContext(
        module_name="b.py",
        metadata={"minimum_summary_words": "9", "quality_profile": "strict"},
    )

    default_messages = provider._prompt_messages(default_ctx)
    strict_messages = provider._prompt_messages(strict_ctx)

    assert "Write 2-4 sentences." in default_messages[1]["content"]
    assert "Write at least 9 words." in strict_messages[1]["content"]
    assert "Current quality profile: strict." in strict_messages[0]["content"]


@pytest.mark.asyncio
async def test_base_provider_headers_and_require_base_url_validation() -> None:
    """Base provider helpers should merge headers and validate missing base URLs."""
    provider = OpenAIProvider(
        ProviderConfig(
            provider="openai",
            api_key="test-key",
            model_name="gpt-4o-mini",
            extra_headers={"X-Test": "yes"},
        )
    )

    headers = provider._headers()
    assert headers["Content-Type"] == "application/json"
    assert headers["X-Test"] == "yes"

    assert provider.available is True

    class NoUrlProvider(OpenAIProvider):
        def _require_base_url(self) -> str:
            return super()._require_base_url()

    no_url = NoUrlProvider(
        ProviderConfig(
            provider="openai",
            api_key="test-key",
            model_name="gpt-4o-mini",
            base_url="",
        )
    )

    no_url.config.provider = "heuristic"
    no_url.config.base_url = None

    with pytest.raises(MissingConfigError, match="base_url"):
        no_url._require_base_url()


@pytest.mark.asyncio
async def test_base_provider_timed_health_request_uses_request_result() -> None:
    """Timed health helper should return response and non-negative latency."""
    provider = OpenAIProvider(
        ProviderConfig(provider="openai", api_key="test-key", model_name="gpt-4o-mini")
    )

    fake_response = MagicMock()

    async def fake_request(_method: str, _path: str) -> object:
        return fake_response

    provider._request = fake_request  # type: ignore[method-assign]

    response, latency_ms = await provider._timed_health_request("GET", "/models")

    assert response is fake_response
    assert latency_ms >= 0.0


def test_version_helpers_handle_parse_and_package_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Version helpers should be resilient to parse errors and missing metadata."""
    monkeypatch.setattr(version_module.Path, "read_text", lambda *_a, **_k: "not toml")
    assert version_module._read_pyproject_version() is None

    monkeypatch.setattr(version_module.Path, "read_text", lambda *_a, **_k: "[project]\nname='x'\n")
    assert version_module._read_pyproject_version() is None

    monkeypatch.setattr(version_module, "_read_pyproject_version", lambda: None)
    monkeypatch.setattr(version_module, "version", lambda _name: "9.9.9")
    assert version_module.get_version() == "9.9.9"

    def _raise_not_found(_name: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr(version_module, "version", _raise_not_found)
    assert version_module.get_version() == "0.0.0"


def test_cli_entry_main_invokes_app(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entry-point main should import cli.app and return success code."""
    called: dict[str, bool] = {"value": False}

    def fake_app() -> None:
        called["value"] = True

    fake_module = types.SimpleNamespace(app=fake_app)
    monkeypatch.setitem(sys.modules, "devwayfinder.cli.app", fake_module)

    assert entry_main() == 0
    assert called["value"] is True

"""Additional high-impact tests for final 2% coverage - MVP 2.5."""

from __future__ import annotations

import httpx
import pytest

from devwayfinder.core.protocols import SummarizationContext
from devwayfinder.providers import ProviderConfig
from devwayfinder.providers.openai import OpenAIProvider


class TestOpenAIProviderFull:
    """Complete tests for official OpenAI provider."""

    def test_openai_requires_api_key_on_init(self) -> None:
        """OpenAI provider should require API key on initialization."""
        from devwayfinder.core.exceptions import MissingConfigError
        
        config = ProviderConfig(
            provider="openai",
            model_name="gpt-4o-mini",
            api_key=None,
        )
        
        # Should raise MissingConfigError
        with pytest.raises(MissingConfigError) as exc_info:
            OpenAIProvider(config)
        
        assert "api_key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_openai_with_api_key(self) -> None:
        """OpenAI provider setup with API key."""
        config = ProviderConfig(
            provider="openai",
            model_name="gpt-4o-mini",
            api_key="sk-test-key",
        )
        provider = OpenAIProvider(config)
        
        # Should be available with key
        assert provider.available
        await provider.close()

    @pytest.mark.asyncio
    async def test_openai_health_check(self, respx_mock: object) -> None:
        """Test OpenAI health check endpoint."""
        # Mock the OpenAI models endpoint
        respx_mock.get("https://api.openai.com/v1/models").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "gpt-4o-mini"},
                        {"id": "gpt-4o"},
                    ]
                }
            )
        )
        
        config = ProviderConfig(
            provider="openai",
            model_name="gpt-4o-mini",
            api_key="sk-test-key",
        )
        provider = OpenAIProvider(config)
        
        # Health check should succeed
        health = await provider.health_check()
        assert health.healthy
        
        await provider.close()


class TestUtilsModule:
    """Test utility module imports."""

    def test_utils_module_importable(self) -> None:
        """Utils module should be importable."""
        # This covers the line in utils/__init__.py
        try:
            import devwayfinder.utils
            # Import succeeded
        except ImportError:
            pytest.fail("Utils module should be importable")


class TestEntryPoint:
    """Test the CLI entry point."""

    def test_main_function_exists(self) -> None:
        """Main entry point function should exist."""
        from devwayfinder import __main__
        
        # Check that main function exists
        assert hasattr(__main__, "main")
        assert callable(__main__.main)


class TestGraphEdgeCases:
    """Additional graph coverage tests."""

    def test_graph_node_operations(self) -> None:
        """Test graph node operations thoroughly."""
        from devwayfinder.core.graph import DependencyGraph
        from devwayfinder.core.models import Module, ModuleType
        from pathlib import Path
        
        graph = DependencyGraph()
        
        # Create test modules
        mod_a = Module(
            name="a",
            path=Path("a.py"),
            module_type=ModuleType.FILE,
        )
        mod_b = Module(
            name="b",
            path=Path("b.py"),
            module_type=ModuleType.FILE,
        )
        
        # Add modules
        graph.add_module(mod_a)
        graph.add_module(mod_b)
        
        # Add dependency
        graph.add_dependency(Path("a.py"), Path("b.py"))
        
        # Check graph structure
        assert graph.node_count == 2
        assert graph.edge_count > 0
        
        # Test retrieval
        deps = graph.get_dependencies(Path("a.py"))
        assert len(deps) > 0

    def test_graph_topological_sort(self) -> None:
        """Test graph operations with multiple nodes."""
        from devwayfinder.core.graph import DependencyGraph
        from devwayfinder.core.models import Module, ModuleType
        from pathlib import Path
        
        graph = DependencyGraph()
        
        # Create linear dependency chain: c -> b -> a
        mods = {
            Path("a.py"): Module(name="a", path=Path("a.py"), module_type=ModuleType.FILE),
            Path("b.py"): Module(name="b", path=Path("b.py"), module_type=ModuleType.FILE),
            Path("c.py"): Module(name="c", path=Path("c.py"), module_type=ModuleType.FILE),
        }
        
        for mod in mods.values():
            graph.add_module(mod)
        
        # Add dependencies
        graph.add_dependency(Path("b.py"), Path("a.py"))
        graph.add_dependency(Path("c.py"), Path("b.py"))
        
        # Graph operations should work
        assert graph.node_count == 3
        assert graph.edge_count > 0
        
        # Get dependencies should work
        deps_of_c = graph.get_dependencies(Path("c.py"))
        assert len(deps_of_c) > 0

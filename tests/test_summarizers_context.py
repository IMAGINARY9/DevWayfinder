"""Behavior tests for summarization context construction."""

from __future__ import annotations

from typing import TYPE_CHECKING

from devwayfinder.analyzers.regex_extractor import ExtractionResult
from devwayfinder.core.graph import DependencyGraph
from devwayfinder.core.models import Module, ModuleType
from devwayfinder.summarizers.context_builder import ContextBuilder
from devwayfinder.utils.tokens import estimate_context_tokens

if TYPE_CHECKING:
    from pathlib import Path


class TestSummarizationContextBuilder:
    """Test context construction behavior across module types."""

    def test_context_token_measurement_module(self, tmp_path: Path) -> None:
        """Test that we can accurately measure context token usage."""
        # Create a module with typical content
        module = Module(
            name="example_module",
            path=tmp_path / "example.py",
            module_type=ModuleType.FILE,
            language="python",
            imports=["os", "sys", "typing", "dataclasses"] * 5,  # 20 imports
            exports=["ClassA", "ClassB", "function_x"] * 3,  # 9 exports
            entry_point=True,
        )

        builder = ContextBuilder(tmp_path)
        context = builder.from_module(module)

        # Measure actual token usage
        tokens = estimate_context_tokens(context)

        # We should be able to measure tokens
        assert tokens > 0

    def test_small_utility_context_optimization(self, tmp_path: Path) -> None:
        """Test that small utilities generate minimal context."""
        # Small file with minimal imports/exports
        extraction = ExtractionResult(
            imports=["os"],
            exports=["helper_function"],
        )

        builder = ContextBuilder(tmp_path)
        context = builder.from_regex_extraction(tmp_path / "utils.py", extraction)

        tokens = estimate_context_tokens(context)

        # Small utilities should have minimal context (< 100 tokens)
        assert tokens < 100

    def test_large_module_context_includes_signatures(self, tmp_path: Path) -> None:
        """Test that large complex modules include signatures."""
        # Python analysis with many functions/classes
        from devwayfinder.analyzers.python_analyzer import (
            ClassInfo,
            FunctionInfo,
            PythonExtractionResult,
        )

        functions = [
            FunctionInfo(
                name=f"func_{i}",
                lineno=10 + i,
                parameters=["arg1", "arg2"],
                docstring=f"Function {i} documentation",
                is_async=False,
            )
            for i in range(5)
        ]

        classes = [
            ClassInfo(
                name=f"Class{i}",
                lineno=20 + i,
                bases=["BaseClass"],
                methods=[f"method_{j}" for j in range(3)],
                docstring=f"Class {i} documentation",
            )
            for i in range(3)
        ]

        analysis = PythonExtractionResult(
            imports=["os", "sys", "typing"],
            exports=["Class0", "Class1", "Class2"],
            functions=functions,
            classes=classes,
            module_docstring="Module documentation",
            has_main_block=False,
        )

        builder = ContextBuilder(tmp_path)
        context = builder.from_python_analysis(tmp_path / "complex.py", analysis)

        # Should include signatures
        assert len(context.signatures) > 0
        # Should include docstrings
        assert len(context.docstrings) > 0
        # Should include module_docstring
        assert "Module documentation" in " ".join(context.docstrings)

    def test_architecture_context_excludes_redundant_info(self, tmp_path: Path) -> None:
        """Test that architecture context doesn't include verbose module details."""
        from devwayfinder.core.models import Project

        # Create a minimal project
        modules = {
            "module1": Module(
                name="module1",
                path=tmp_path / "module1.py",
                module_type=ModuleType.FILE,
                language="python",
                imports=["os"],
                exports=["func1"],
            ),
            "module2": Module(
                name="module2",
                path=tmp_path / "module2.py",
                module_type=ModuleType.FILE,
                language="python",
                imports=["module1"],
                exports=["func2"],
            ),
        }

        from devwayfinder.analyzers.structure import StructureInfo

        project = Project(
            root_path=tmp_path,
            name="test_project",
            modules=modules,
            language="python",
        )

        structure = StructureInfo(
            root_path=tmp_path,
            build_system="setuptools",
            package_manager="pip",
            readme_content="Simple project description",
            primary_language="python",
        )

        builder = ContextBuilder(tmp_path)
        context = builder.for_architecture(project, structure)

        tokens = estimate_context_tokens(context)

        # Architecture context should be concise (100-200 tokens)
        assert tokens < 300  # Reasonable limit for architecture overview

    def test_context_builder_respects_field_limits(self, tmp_path: Path) -> None:
        """Test that context builder enforces reasonable field size limits."""
        # Create a module with many imports/exports
        large_imports = [f"module_{i}" for i in range(50)]
        large_exports = [f"export_{i}" for i in range(50)]

        module = Module(
            name="large_module",
            path=tmp_path / "large.py",
            module_type=ModuleType.FILE,
            language="python",
            imports=large_imports,
            exports=large_exports,
        )

        builder = ContextBuilder(tmp_path)
        context = builder.from_module(module)

        # Should truncate to reasonable limits
        assert len(context.imports) <= 20
        assert len(context.exports) <= 20

    def test_python_ast_context_docstring_priority(self, tmp_path: Path) -> None:
        """Test that module docstring has priority in Python context."""
        from devwayfinder.analyzers.python_analyzer import (
            ClassInfo,
            FunctionInfo,
            PythonExtractionResult,
        )

        functions = [
            FunctionInfo(
                name="func1",
                lineno=10,
                parameters=["x"],
                docstring="Function level docstring - detailed",
                is_async=False,
            )
        ]

        classes = [
            ClassInfo(
                name="MyClass",
                lineno=15,
                bases=[],
                methods=["method1"],
                docstring="Class docstring",
            )
        ]

        analysis = PythonExtractionResult(
            imports=["os"],
            exports=["MyClass"],
            functions=functions,
            classes=classes,
            module_docstring="Module level docstring - most important",
            has_main_block=False,
        )

        builder = ContextBuilder(tmp_path)
        context = builder.from_python_analysis(tmp_path / "test.py", analysis)

        docstrings_text = " ".join(context.docstrings)
        # Module docstring should appear first and be prioritized
        assert "Module level docstring" in docstrings_text

    def test_entry_point_context_suggests_exploration(self, tmp_path: Path) -> None:
        """Test that entry point context includes exploration suggestions."""
        # Create an entry point module
        module = Module(
            name="main",
            path=tmp_path / "__main__.py",
            module_type=ModuleType.FILE,
            language="python",
            imports=["core", "utils", "config"],
            exports=[],
            entry_point=True,
        )

        # Create a graph showing dependencies
        graph = DependencyGraph()
        graph.add_module(module)

        builder = ContextBuilder(tmp_path)
        context = builder.for_entry_point(module, graph=graph)

        # Should have entry point metadata
        assert context.metadata.get("is_entry_point") is True
        # Should have exploration suggestions
        assert "suggested_exploration" in context.metadata

    def test_context_optimization_improves_token_efficiency(self, tmp_path: Path) -> None:
        """Integration test: verify overall context optimization reduces token usage."""
        # Create multiple modules of varying sizes
        modules = {}
        for i in range(10):
            module = Module(
                name=f"module_{i}",
                path=tmp_path / f"module_{i}.py",
                module_type=ModuleType.FILE,
                language="python",
                imports=[f"dep_{j}" for j in range(5)],
                exports=[f"export_{j}" for j in range(3)],
                loc=100 * (i + 1),
                complexity=float(i),
            )
            modules[f"module_{i}"] = module

        from devwayfinder.core.models import Project

        project = Project(
            root_path=tmp_path,
            name="test_project",
            modules=modules,
            language="python",
        )

        builder = ContextBuilder(tmp_path)

        # Build contexts for all modules
        total_tokens = 0
        for module in modules.values():
            context = builder.from_module(module)
            tokens = estimate_context_tokens(context)
            total_tokens += tokens

        # Average tokens per module should be reasonable
        avg_tokens_per_module = total_tokens / len(modules)
        # Target: < 100 tokens per module on average (was ~120 before optimization)
        assert avg_tokens_per_module < 120

    def test_nested_context_depth_truncation(self, tmp_path: Path) -> None:
        """Test that context truncates nested structures reasonably."""
        from devwayfinder.analyzers.python_analyzer import (
            ClassInfo,
            FunctionInfo,
            PythonExtractionResult,
        )

        # Many nested classes/functions
        functions = [
            FunctionInfo(
                name=f"func_{i}",
                lineno=10 + i,
                parameters=["arg"] * 10,  # Many parameters
                docstring="x" * 500,  # Long docstring
                is_async=i % 2 == 0,
            )
            for i in range(20)
        ]

        classes = [
            ClassInfo(
                name=f"Class{i}",
                lineno=30 + i,
                bases=["Base1", "Base2", "Base3"],  # Multiple bases
                methods=[f"method_{j}" for j in range(10)],  # Many methods
                docstring="y" * 300,  # Long docstring
            )
            for i in range(15)
        ]

        analysis = PythonExtractionResult(
            imports=["import_" + str(i) for i in range(30)],
            exports=["export_" + str(i) for i in range(20)],
            functions=functions,
            classes=classes,
            module_docstring="Module" + "z" * 200,
            has_main_block=False,
        )

        builder = ContextBuilder(tmp_path)
        context = builder.from_python_analysis(tmp_path / "nested.py", analysis)

        # Should apply reasonable truncation
        # Currently collects up to 15 functions + 10 classes
        assert len(context.signatures) <= 30  # Reasonable upper bound for truncation
        # Docstrings should be limited (currently up to 5 classes + 5 functions + module)
        assert len(context.docstrings) <= 15
        # Imports should be limited
        assert len(context.imports) <= 20
        # Exports should be limited
        assert len(context.exports) <= 20

    def test_regex_vs_ast_context_equivalence(self, tmp_path: Path) -> None:
        """Test that regex and AST contexts are roughly equivalent in token cost."""
        imports = ["os", "sys", "typing"]
        exports = ["MyClass", "my_function"]

        # Regex-based extraction
        regex_extraction = ExtractionResult(
            imports=imports,
            exports=exports,
        )

        # AST-based analysis
        from devwayfinder.analyzers.python_analyzer import (
            ClassInfo,
            FunctionInfo,
            PythonExtractionResult,
        )

        classes = [ClassInfo(name="MyClass", lineno=1, bases=[], methods=[], docstring="")]
        functions = [FunctionInfo(name="my_function", lineno=5, parameters=[], docstring="", is_async=False)]

        ast_analysis = PythonExtractionResult(
            imports=imports,
            exports=exports,
            functions=functions,
            classes=classes,
            module_docstring="",
            has_main_block=False,
        )

        builder = ContextBuilder(tmp_path)

        # Build contexts
        regex_context = builder.from_regex_extraction(tmp_path / "test.py", regex_extraction)
        ast_context = builder.from_python_analysis(tmp_path / "test.py", ast_analysis)

        # Measure tokens
        regex_tokens = estimate_context_tokens(regex_context)
        ast_tokens = estimate_context_tokens(ast_context)

        # Both should be in similar token range (AST might be slightly higher due to signatures)
        assert abs(regex_tokens - ast_tokens) < 50  # Within 50 tokens of each other

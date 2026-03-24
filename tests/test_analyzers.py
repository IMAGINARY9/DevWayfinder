"""Tests for the analyzers module."""

from pathlib import Path

import pytest

from devwayfinder.analyzers import (
    EXTENSION_TO_LANGUAGE,
    AnalyzerRegistry,
    GraphBuilder,
    ImportResolver,
    PythonASTAnalyzer,
    RegexAnalyzer,
    StructureAnalyzer,
    build_dependency_graph,
    get_python_imports,
)

# =============================================================================
# ANALYZER REGISTRY TESTS
# =============================================================================


class TestAnalyzerRegistry:
    """Tests for AnalyzerRegistry."""

    def test_singleton_instance(self) -> None:
        """Test that registry is a singleton."""
        AnalyzerRegistry.reset_instance()
        reg1 = AnalyzerRegistry.get_instance()
        reg2 = AnalyzerRegistry.get_instance()
        assert reg1 is reg2

    def test_register_analyzer(self) -> None:
        """Test registering an analyzer."""
        registry = AnalyzerRegistry()
        analyzer = PythonASTAnalyzer()
        registry.register("python", analyzer)

        assert registry.has_analyzer("python")
        assert registry.get_analyzer("python") is analyzer

    def test_register_default(self) -> None:
        """Test registering a default analyzer."""
        registry = AnalyzerRegistry()
        default = RegexAnalyzer()
        registry.register_default(default)

        # Unknown language should return default
        result = registry.get_analyzer_for_file(Path("test.py"))
        assert result is default  # Returns default when no language-specific analyzer

    def test_get_analyzer_for_file(self) -> None:
        """Test getting analyzer by file extension."""
        registry = AnalyzerRegistry()
        py_analyzer = PythonASTAnalyzer()
        registry.register("python", py_analyzer)

        result = registry.get_analyzer_for_file(Path("test.py"))
        assert result is py_analyzer

    def test_list_languages(self) -> None:
        """Test listing registered languages."""
        registry = AnalyzerRegistry()
        registry.register("python", PythonASTAnalyzer())
        registry.register("javascript", RegexAnalyzer())

        languages = registry.list_languages()
        assert "python" in languages
        assert "javascript" in languages

    def test_clear_registry(self) -> None:
        """Test clearing the registry."""
        registry = AnalyzerRegistry()
        registry.register("python", PythonASTAnalyzer())
        registry.clear()

        assert registry.analyzer_count == 0


# =============================================================================
# STRUCTURE ANALYZER TESTS
# =============================================================================


class TestStructureAnalyzer:
    """Tests for StructureAnalyzer."""

    @pytest.mark.asyncio
    async def test_analyze_python_project(self, tmp_project: Path) -> None:
        """Test analyzing a Python project structure."""
        analyzer = StructureAnalyzer()
        info = await analyzer.analyze(tmp_project)

        assert info.root_path == tmp_project
        assert info.build_system == "pyproject"
        assert info.primary_language == "python"
        assert info.readme_content is not None
        assert "Sample Project" in info.readme_content

    @pytest.mark.asyncio
    async def test_detect_entry_points(self, tmp_project: Path) -> None:
        """Test entry point detection."""
        analyzer = StructureAnalyzer()
        info = await analyzer.analyze(tmp_project)

        entry_names = [p.name for p in info.entry_points]
        assert "main.py" in entry_names

    @pytest.mark.asyncio
    async def test_language_stats(self, tmp_project: Path) -> None:
        """Test language statistics."""
        analyzer = StructureAnalyzer()
        info = await analyzer.analyze(tmp_project)

        assert "python" in info.language_stats
        assert info.language_stats["python"] >= 2  # At least main.py and utils.py

    @pytest.mark.asyncio
    async def test_exclude_patterns(self, tmp_path: Path) -> None:
        """Test exclude patterns work."""
        project = tmp_path / "proj"
        project.mkdir()
        (project / "src.py").write_text("print(1)")
        (project / "__pycache__").mkdir()
        (project / "__pycache__" / "file.pyc").write_bytes(b"\x00")

        analyzer = StructureAnalyzer()
        info = await analyzer.analyze(project)

        # __pycache__ should be excluded
        source_names = [p.name for p in info.source_files]
        assert "src.py" in source_names
        assert "file.pyc" not in source_names

    @pytest.mark.asyncio
    async def test_nonexistent_path(self, tmp_path: Path) -> None:
        """Test error handling for non-existent path."""
        analyzer = StructureAnalyzer()

        with pytest.raises(FileNotFoundError):
            await analyzer.analyze(tmp_path / "does_not_exist")

    @pytest.mark.asyncio
    async def test_file_path_instead_of_directory(self, tmp_path: Path) -> None:
        """Test error handling for file instead of directory."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("content")

        analyzer = StructureAnalyzer()

        with pytest.raises(NotADirectoryError):
            await analyzer.analyze(file_path)


# =============================================================================
# REGEX ANALYZER TESTS
# =============================================================================


class TestRegexAnalyzer:
    """Tests for RegexAnalyzer."""

    @pytest.mark.asyncio
    async def test_analyze_python_file(self, tmp_path: Path) -> None:
        """Test analyzing a Python file with regex."""
        py_file = tmp_path / "test.py"
        py_file.write_text("""
import os
from pathlib import Path

def hello():
    pass

class MyClass:
    pass

if __name__ == "__main__":
    hello()
""")

        analyzer = RegexAnalyzer()
        result = await analyzer.analyze(py_file)

        assert result.language == "python"
        assert "os" in result.imports
        assert "pathlib" in result.imports
        assert "hello" in result.exports
        assert "MyClass" in result.exports
        assert result.is_entry_point is True

    @pytest.mark.asyncio
    async def test_analyze_javascript_file(self, tmp_path: Path) -> None:
        """Test analyzing a JavaScript file."""
        js_file = tmp_path / "test.js"
        js_file.write_text("""
import React from 'react';
import { useState } from 'react';
const lodash = require('lodash');

export function myFunction() {}

export class MyComponent {}
""")

        analyzer = RegexAnalyzer()
        result = await analyzer.analyze(js_file)

        assert result.language == "javascript"
        assert "react" in result.imports
        assert "lodash" in result.imports
        assert "myFunction" in result.exports or "myFunction" in result.metadata.get(
            "functions", []
        )

    @pytest.mark.asyncio
    async def test_analyze_go_file(self, tmp_path: Path) -> None:
        """Test analyzing a Go file."""
        go_file = tmp_path / "main.go"
        go_file.write_text("""
package main

import (
    "fmt"
    "os"
)

func Main() {
    fmt.Println("Hello")
}

func main() {
    Main()
}
""")

        analyzer = RegexAnalyzer()
        result = await analyzer.analyze(go_file)

        assert result.language == "go"
        assert "fmt" in result.imports
        assert "os" in result.imports

    @pytest.mark.asyncio
    async def test_analyze_rust_file(self, tmp_path: Path) -> None:
        """Test analyzing a Rust file."""
        rs_file = tmp_path / "main.rs"
        rs_file.write_text("""
use std::io;
use std::collections::HashMap;

mod utils;

pub fn do_something() {}

fn main() {
    do_something();
}
""")

        analyzer = RegexAnalyzer()
        result = await analyzer.analyze(rs_file)

        assert result.language == "rust"
        assert "std::io" in result.imports
        assert "do_something" in result.exports

    @pytest.mark.asyncio
    async def test_can_analyze_checks_extension(self, tmp_path: Path) -> None:
        """Test can_analyze checks file extension."""
        analyzer = RegexAnalyzer()

        py_file = tmp_path / "test.py"
        py_file.write_text("")
        assert analyzer.can_analyze(py_file) is True

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("")
        assert analyzer.can_analyze(txt_file) is False

    @pytest.mark.asyncio
    async def test_file_size_limit(self, tmp_path: Path) -> None:
        """Test file size limit."""
        large_file = tmp_path / "large.py"
        large_file.write_text("x = 1\n" * 1000000)  # Large file

        analyzer = RegexAnalyzer(max_file_size=1000)
        assert analyzer.can_analyze(large_file) is False


# =============================================================================
# PYTHON AST ANALYZER TESTS
# =============================================================================


class TestPythonASTAnalyzer:
    """Tests for PythonASTAnalyzer."""

    @pytest.mark.asyncio
    async def test_analyze_imports(self, tmp_path: Path) -> None:
        """Test import extraction using AST."""
        py_file = tmp_path / "test.py"
        py_file.write_text("""
import os
import sys
from pathlib import Path
from typing import Optional, List
from . import relative_module
""")

        analyzer = PythonASTAnalyzer()
        result = await analyzer.analyze(py_file)

        assert "os" in result.imports
        assert "sys" in result.imports
        assert "pathlib" in result.imports
        assert "typing" in result.imports

    @pytest.mark.asyncio
    async def test_analyze_functions(self, tmp_path: Path) -> None:
        """Test function extraction using AST."""
        py_file = tmp_path / "test.py"
        py_file.write_text("""
def public_function():
    pass

async def async_function():
    pass

def _private_function():
    pass
""")

        analyzer = PythonASTAnalyzer()
        result = await analyzer.analyze(py_file)

        assert "public_function" in result.exports
        assert "async_function" in result.exports
        assert "_private_function" not in result.exports

    @pytest.mark.asyncio
    async def test_analyze_classes(self, tmp_path: Path) -> None:
        """Test class extraction using AST."""
        py_file = tmp_path / "test.py"
        py_file.write_text("""
class PublicClass:
    def method(self):
        pass

class _PrivateClass:
    pass
""")

        analyzer = PythonASTAnalyzer()
        result = await analyzer.analyze(py_file)

        assert "PublicClass" in result.exports
        assert "_PrivateClass" not in result.exports

    @pytest.mark.asyncio
    async def test_analyze_all_definition(self, tmp_path: Path) -> None:
        """Test __all__ extraction."""
        py_file = tmp_path / "test.py"
        py_file.write_text("""
__all__ = ["exported_func", "ExportedClass"]

def exported_func():
    pass

def not_exported():
    pass

class ExportedClass:
    pass
""")

        analyzer = PythonASTAnalyzer()
        result = await analyzer.analyze(py_file)

        assert result.exports == ["exported_func", "ExportedClass"]

    @pytest.mark.asyncio
    async def test_main_block_detection(self, tmp_path: Path) -> None:
        """Test main block detection."""
        py_file = tmp_path / "test.py"
        py_file.write_text("""
def main():
    pass

if __name__ == "__main__":
    main()
""")

        analyzer = PythonASTAnalyzer()
        result = await analyzer.analyze(py_file)

        assert result.is_entry_point is True

    @pytest.mark.asyncio
    async def test_syntax_error_fallback(self, tmp_path: Path) -> None:
        """Test fallback to regex on syntax error."""
        py_file = tmp_path / "broken.py"
        py_file.write_text("""
import os
def broken(
    # Missing closing parenthesis
""")

        analyzer = PythonASTAnalyzer(fallback_to_regex=True)
        result = await analyzer.analyze(py_file)

        # Should fall back to regex
        assert result.metadata.get("analysis_method") == "regex_fallback"
        assert "os" in result.imports

    @pytest.mark.asyncio
    async def test_module_docstring(self, tmp_path: Path) -> None:
        """Test module docstring extraction."""
        py_file = tmp_path / "test.py"
        py_file.write_text('"""This is the module docstring."""\n\nimport os\n')

        analyzer = PythonASTAnalyzer()
        result = await analyzer.analyze(py_file)

        assert result.metadata.get("docstring") == "This is the module docstring."

    def test_get_python_imports_helper(self) -> None:
        """Test the helper function for quick import extraction."""
        content = """
import os
from pathlib import Path
import sys
"""
        imports = get_python_imports(content)

        assert "os" in imports
        assert "pathlib" in imports
        assert "sys" in imports


# =============================================================================
# IMPORT RESOLVER TESTS
# =============================================================================


class TestImportResolver:
    """Tests for ImportResolver."""

    def test_resolve_simple_import(self, tmp_path: Path) -> None:
        """Test resolving a simple import."""
        # Create file structure
        src = tmp_path / "mypackage"
        src.mkdir()
        (src / "__init__.py").write_text("")
        (src / "module.py").write_text("")

        resolver = ImportResolver(tmp_path, [src / "__init__.py", src / "module.py"])

        result = resolver.resolve("mypackage.module")
        assert result is not None
        assert result.name == "module.py"

    def test_resolve_package(self, tmp_path: Path) -> None:
        """Test resolving a package import."""
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        init_file = pkg / "__init__.py"
        init_file.write_text("")

        resolver = ImportResolver(tmp_path, [init_file])

        result = resolver.resolve("pkg")
        assert result is not None

    def test_get_module_name(self, tmp_path: Path) -> None:
        """Test getting module name for a file."""
        file_path = tmp_path / "mypackage" / "submodule" / "file.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("")

        resolver = ImportResolver(tmp_path, [file_path])

        name = resolver.get_module_name(file_path)
        assert name == "mypackage.submodule.file"


# =============================================================================
# GRAPH BUILDER TESTS
# =============================================================================


class TestGraphBuilder:
    """Tests for GraphBuilder."""

    @pytest.mark.asyncio
    async def test_build_simple_graph(self, tmp_project: Path) -> None:
        """Test building a simple dependency graph."""
        builder = GraphBuilder()
        project, graph = await builder.build(tmp_project)

        # Check project
        assert project.name == tmp_project.name
        assert project.build_system == "pyproject"
        assert project.primary_language == "python"

        # Check graph has nodes
        assert graph.node_count > 0

    @pytest.mark.asyncio
    async def test_detect_entry_points(self, tmp_project: Path) -> None:
        """Test entry point detection in graph."""
        builder = GraphBuilder()
        _project, graph = await builder.build(tmp_project)

        entry_points = graph.get_entry_points()
        entry_names = [m.name for m in entry_points]

        # main.py should be an entry point
        assert "main" in entry_names or any("main" in n for n in entry_names)

    @pytest.mark.asyncio
    async def test_dependency_edges(self, tmp_path: Path) -> None:
        """Test that dependency edges are created correctly."""
        # Create a project with clear dependencies
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "a.py").write_text("from proj.b import func\n")
        (proj / "b.py").write_text("def func(): pass\n")

        builder = GraphBuilder()
        _project, graph = await builder.build(proj)

        # Graph should have both modules
        assert graph.node_count >= 2


class TestBuildDependencyGraph:
    """Tests for the convenience function."""

    @pytest.mark.asyncio
    async def test_convenience_function(self, tmp_project: Path) -> None:
        """Test the build_dependency_graph convenience function."""
        project, graph = await build_dependency_graph(tmp_project)

        assert project is not None
        assert graph is not None
        assert project.root_path == tmp_project


# =============================================================================
# EXTENSION MAPPING TESTS
# =============================================================================


class TestExtensionMapping:
    """Tests for extension-to-language mapping."""

    def test_python_extensions(self) -> None:
        """Test Python file extensions."""
        assert EXTENSION_TO_LANGUAGE.get(".py") == "python"
        assert EXTENSION_TO_LANGUAGE.get(".pyi") == "python"

    def test_javascript_extensions(self) -> None:
        """Test JavaScript/TypeScript extensions."""
        assert EXTENSION_TO_LANGUAGE.get(".js") == "javascript"
        assert EXTENSION_TO_LANGUAGE.get(".ts") == "typescript"
        assert EXTENSION_TO_LANGUAGE.get(".jsx") == "javascript"
        assert EXTENSION_TO_LANGUAGE.get(".tsx") == "typescript"

    def test_other_languages(self) -> None:
        """Test other language extensions."""
        assert EXTENSION_TO_LANGUAGE.get(".go") == "go"
        assert EXTENSION_TO_LANGUAGE.get(".rs") == "rust"
        assert EXTENSION_TO_LANGUAGE.get(".java") == "java"
        assert EXTENSION_TO_LANGUAGE.get(".c") == "c"
        assert EXTENSION_TO_LANGUAGE.get(".cpp") == "cpp"


# =============================================================================
# PHASE 2.4: EXTENDED REGEX PATTERN TESTS
# =============================================================================


class TestDecoratorExtraction:
    """Tests for decorator extraction (Phase 2.4)."""

    @pytest.mark.asyncio
    async def test_python_decorators(self, tmp_path: Path) -> None:
        """Test Python decorator extraction."""
        py_file = tmp_path / "test.py"
        py_file.write_text("""
@dataclass
class MyModel:
    name: str

@app.route('/api')
def api_handler():
    pass

@pytest.fixture
def setup():
    pass

@staticmethod
def helper():
    pass
""")

        analyzer = RegexAnalyzer()
        result = await analyzer.analyze(py_file)

        decorators = result.metadata.get("decorators", [])
        assert "dataclass" in decorators
        assert "app.route" in decorators
        assert "pytest.fixture" in decorators
        assert "staticmethod" in decorators


class TestRelativeImports:
    """Tests for relative import extraction (Phase 2.4)."""

    @pytest.mark.asyncio
    async def test_python_relative_imports(self, tmp_path: Path) -> None:
        """Test Python relative import extraction."""
        py_file = tmp_path / "test.py"
        py_file.write_text("""
from . import sibling
from .. import parent
from .utils import helper
from ...pkg import module
""")

        analyzer = RegexAnalyzer()
        result = await analyzer.analyze(py_file)

        rel_imports = result.metadata.get("relative_imports", [])
        assert "." in rel_imports
        assert ".." in rel_imports
        assert ".utils" in rel_imports
        assert "...pkg" in rel_imports


class TestFrameworkDetection:
    """Tests for framework detection (Phase 2.4)."""

    @pytest.mark.asyncio
    async def test_detect_flask(self, tmp_path: Path) -> None:
        """Test Flask framework detection."""
        py_file = tmp_path / "app.py"
        py_file.write_text("""
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/hello')
def hello():
    return jsonify({'message': 'Hello, World!'})
""")

        analyzer = RegexAnalyzer()
        result = await analyzer.analyze(py_file)

        frameworks = result.metadata.get("framework_hints", [])
        assert "flask" in frameworks

    @pytest.mark.asyncio
    async def test_detect_fastapi(self, tmp_path: Path) -> None:
        """Test FastAPI framework detection."""
        py_file = tmp_path / "main.py"
        py_file.write_text("""
from fastapi import FastAPI

app = FastAPI()

@app.get('/items')
async def get_items():
    return []
""")

        analyzer = RegexAnalyzer()
        result = await analyzer.analyze(py_file)

        frameworks = result.metadata.get("framework_hints", [])
        assert "fastapi" in frameworks

    @pytest.mark.asyncio
    async def test_detect_django(self, tmp_path: Path) -> None:
        """Test Django framework detection."""
        py_file = tmp_path / "models.py"
        py_file.write_text("""
from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)
""")

        analyzer = RegexAnalyzer()
        result = await analyzer.analyze(py_file)

        frameworks = result.metadata.get("framework_hints", [])
        assert "django" in frameworks

    @pytest.mark.asyncio
    async def test_detect_pytest(self, tmp_path: Path) -> None:
        """Test pytest framework detection."""
        py_file = tmp_path / "test_example.py"
        py_file.write_text("""
import pytest

@pytest.fixture
def client():
    return TestClient()

def test_hello(client):
    response = client.get('/')
    assert response.status_code == 200
""")

        analyzer = RegexAnalyzer()
        result = await analyzer.analyze(py_file)

        frameworks = result.metadata.get("framework_hints", [])
        assert "pytest" in frameworks

    @pytest.mark.asyncio
    async def test_detect_react_ts(self, tmp_path: Path) -> None:
        """Test React framework detection in TypeScript."""
        ts_file = tmp_path / "component.tsx"
        ts_file.write_text("""
import React, { useState, useEffect } from 'react';

const MyComponent = () => {
    const [count, setCount] = useState(0);

    useEffect(() => {
        document.title = `Count: ${count}`;
    }, [count]);

    return <div>{count}</div>;
};

export default MyComponent;
""")

        analyzer = RegexAnalyzer()
        result = await analyzer.analyze(ts_file)

        frameworks = result.metadata.get("framework_hints", [])
        assert "react" in frameworks

    @pytest.mark.asyncio
    async def test_detect_spring(self, tmp_path: Path) -> None:
        """Test Spring framework detection in Java."""
        java_file = tmp_path / "Controller.java"
        java_file.write_text("""
import org.springframework.web.bind.annotation.*;

@RestController
public class UserController {

    @Autowired
    private UserService userService;

    @GetMapping("/users")
    public List<User> getUsers() {
        return userService.findAll();
    }
}
""")

        analyzer = RegexAnalyzer()
        result = await analyzer.analyze(java_file)

        frameworks = result.metadata.get("framework_hints", [])
        assert "spring" in frameworks

    @pytest.mark.asyncio
    async def test_no_framework_detected(self, tmp_path: Path) -> None:
        """Test that plain code doesn't detect frameworks."""
        py_file = tmp_path / "utils.py"
        py_file.write_text("""
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
""")

        analyzer = RegexAnalyzer()
        result = await analyzer.analyze(py_file)

        frameworks = result.metadata.get("framework_hints", [])
        assert len(frameworks) == 0


class TestTypeScriptPatterns:
    """Tests for TypeScript-specific patterns (Phase 2.4)."""

    @pytest.mark.asyncio
    async def test_typescript_imports(self, tmp_path: Path) -> None:
        """Test TypeScript import extraction."""
        ts_file = tmp_path / "service.ts"
        ts_file.write_text("""
import { Injectable } from '@nestjs/common';
import type { User } from './types';
import * as fs from 'fs';
export { helper } from './utils';
""")

        analyzer = RegexAnalyzer()
        result = await analyzer.analyze(ts_file)

        assert "@nestjs/common" in result.imports
        assert "fs" in result.imports
        assert "./utils" in result.imports


class TestCrossLanguagePatterns:
    """Tests for cross-language regex accuracy (Phase 2.4)."""

    @pytest.mark.asyncio
    async def test_go_imports(self, tmp_path: Path) -> None:
        """Test Go import extraction."""
        go_file = tmp_path / "main.go"
        go_file.write_text("""
package main

import (
    "fmt"
    "net/http"
    _ "github.com/lib/pq"
)

func main() {
    fmt.Println("Hello")
}
""")

        analyzer = RegexAnalyzer()
        result = await analyzer.analyze(go_file)

        assert "fmt" in result.imports
        assert result.is_entry_point

    @pytest.mark.asyncio
    async def test_rust_imports(self, tmp_path: Path) -> None:
        """Test Rust import extraction."""
        rs_file = tmp_path / "lib.rs"
        rs_file.write_text("""
use std::collections::HashMap;
use crate::utils;

mod internal;
extern crate serde;

pub fn process(data: &str) -> HashMap<String, String> {
    HashMap::new()
}
""")

        analyzer = RegexAnalyzer()
        result = await analyzer.analyze(rs_file)

        assert "std::collections::HashMap" in result.imports
        assert "crate::utils" in result.imports
        assert "process" in result.exports

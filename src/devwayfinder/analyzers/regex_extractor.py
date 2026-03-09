"""Regex-based import/export extraction for multiple languages."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from devwayfinder.analyzers.base import (
    EXTENSION_TO_LANGUAGE,
    BaseAnalyzer,
)
from devwayfinder.core.protocols import AnalysisResult

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class ExtractionResult:
    """Result of regex extraction from a source file."""

    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    docstring: str | None = None
    has_main_block: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# IMPORT PATTERNS
# =============================================================================

# Python import patterns
PYTHON_IMPORT_PATTERNS = [
    # import module
    re.compile(r"^\s*import\s+([\w.]+)(?:\s+as\s+\w+)?", re.MULTILINE),
    # from module import ...
    re.compile(r"^\s*from\s+([\w.]+)\s+import\s+", re.MULTILINE),
]

# JavaScript/TypeScript import patterns
JS_IMPORT_PATTERNS = [
    # import ... from 'module'
    re.compile(r"""^\s*import\s+.+?\s+from\s+['"]([^'"]+)['"]""", re.MULTILINE),
    # import 'module' (side-effect import)
    re.compile(r"""^\s*import\s+['"]([^'"]+)['"]""", re.MULTILINE),
    # require('module')
    re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""", re.MULTILINE),
    # dynamic import('module')
    re.compile(r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)""", re.MULTILINE),
]

# Go import patterns
GO_IMPORT_PATTERNS = [
    # import "package"
    re.compile(r"""^\s*import\s+(?:[\w.]+\s+)?["']([^"']+)["']""", re.MULTILINE),
    # import ( "package" )
    re.compile(r"""^\s*["']([^"']+)["']""", re.MULTILINE),
]

# Rust import patterns
RUST_IMPORT_PATTERNS = [
    # use crate::module
    re.compile(r"^\s*use\s+([\w:]+)", re.MULTILINE),
    # mod module
    re.compile(r"^\s*mod\s+(\w+)", re.MULTILINE),
    # extern crate
    re.compile(r"^\s*extern\s+crate\s+(\w+)", re.MULTILINE),
]

# Java/Kotlin import patterns
JAVA_IMPORT_PATTERNS = [
    # import package.Class
    re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)", re.MULTILINE),
]

# C# import patterns
CSHARP_IMPORT_PATTERNS = [
    # using Namespace
    re.compile(r"^\s*using\s+(?:static\s+)?([\w.]+)", re.MULTILINE),
]

# C/C++ include patterns
C_IMPORT_PATTERNS = [
    # #include "header.h"
    re.compile(r"""^\s*#\s*include\s+["']([^"']+)["']""", re.MULTILINE),
    # #include <header>
    re.compile(r"""^\s*#\s*include\s+<([^>]+)>""", re.MULTILINE),
]

# Ruby import patterns
RUBY_IMPORT_PATTERNS = [
    # require 'gem'
    re.compile(r"""^\s*require\s+['"]([^'"]+)['"]""", re.MULTILINE),
    # require_relative './file'
    re.compile(r"""^\s*require_relative\s+['"]([^'"]+)['"]""", re.MULTILINE),
    # load 'file'
    re.compile(r"""^\s*load\s+['"]([^'"]+)['"]""", re.MULTILINE),
]

# PHP import patterns
PHP_IMPORT_PATTERNS = [
    # use Namespace\Class
    re.compile(r"^\s*use\s+([\w\\]+)", re.MULTILINE),
    # require/include
    re.compile(r"""^\s*(?:require|include)(?:_once)?\s+['"]([^'"]+)['"]""", re.MULTILINE),
]

# Swift import patterns
SWIFT_IMPORT_PATTERNS = [
    # import Framework
    re.compile(r"^\s*import\s+(\w+)", re.MULTILINE),
]

# =============================================================================
# EXPORT/DECLARATION PATTERNS
# =============================================================================

# Python export patterns
PYTHON_EXPORT_PATTERNS = {
    "functions": re.compile(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(", re.MULTILINE),
    "classes": re.compile(r"^\s*class\s+(\w+)(?:\s*\(|\s*:)", re.MULTILINE),
    "__all__": re.compile(r"^\s*__all__\s*=\s*\[([^\]]+)\]", re.MULTILINE | re.DOTALL),
}

# JavaScript/TypeScript export patterns
JS_EXPORT_PATTERNS = {
    "functions": re.compile(
        r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(", re.MULTILINE
    ),
    "classes": re.compile(r"^\s*(?:export\s+)?class\s+(\w+)", re.MULTILINE),
    "exports": re.compile(r"^\s*export\s+(?:default\s+)?(?:const|let|var|function|class)\s+(\w+)", re.MULTILINE),
    "module_exports": re.compile(r"module\.exports\s*=\s*\{([^}]+)\}", re.MULTILINE | re.DOTALL),
}

# Go export patterns (public = starts with uppercase)
GO_EXPORT_PATTERNS = {
    "functions": re.compile(r"^\s*func\s+(?:\(\s*\w+\s+[*]?\w+\s*\)\s+)?([A-Z]\w*)\s*\(", re.MULTILINE),
    "types": re.compile(r"^\s*type\s+([A-Z]\w*)\s+", re.MULTILINE),
}

# Rust export patterns
RUST_EXPORT_PATTERNS = {
    "functions": re.compile(r"^\s*pub(?:\s+async)?\s+fn\s+(\w+)", re.MULTILINE),
    "structs": re.compile(r"^\s*pub\s+struct\s+(\w+)", re.MULTILINE),
    "enums": re.compile(r"^\s*pub\s+enum\s+(\w+)", re.MULTILINE),
    "traits": re.compile(r"^\s*pub\s+trait\s+(\w+)", re.MULTILINE),
}

# Java export patterns
JAVA_EXPORT_PATTERNS = {
    "classes": re.compile(r"^\s*(?:public\s+)?(?:abstract\s+)?class\s+(\w+)", re.MULTILINE),
    "interfaces": re.compile(r"^\s*(?:public\s+)?interface\s+(\w+)", re.MULTILINE),
    "methods": re.compile(
        r"^\s*(?:public|protected)\s+(?:static\s+)?(?:final\s+)?[\w<>,\s]+\s+(\w+)\s*\(",
        re.MULTILINE,
    ),
}

# C# export patterns
CSHARP_EXPORT_PATTERNS = {
    "classes": re.compile(r"^\s*(?:public\s+)?(?:partial\s+)?(?:abstract\s+)?class\s+(\w+)", re.MULTILINE),
    "interfaces": re.compile(r"^\s*(?:public\s+)?interface\s+(\w+)", re.MULTILINE),
    "methods": re.compile(
        r"^\s*(?:public|protected|internal)\s+(?:static\s+)?(?:async\s+)?[\w<>,\s]+\s+(\w+)\s*\(",
        re.MULTILINE,
    ),
}

# C/C++ patterns
C_EXPORT_PATTERNS = {
    "functions": re.compile(r"^\s*(?:[\w*]+\s+)+(\w+)\s*\([^;{]*\)\s*\{", re.MULTILINE),
    "structs": re.compile(r"^\s*(?:typedef\s+)?struct\s+(\w+)", re.MULTILINE),
}

# Main block patterns
MAIN_PATTERNS = {
    "python": re.compile(r"""if\s+__name__\s*==\s*['"]__main__['"]"""),
    "go": re.compile(r"func\s+main\s*\(\s*\)"),
    "rust": re.compile(r"fn\s+main\s*\(\s*\)"),
    "c": re.compile(r"int\s+main\s*\("),
    "cpp": re.compile(r"int\s+main\s*\("),
    "java": re.compile(r"public\s+static\s+void\s+main\s*\("),
    "csharp": re.compile(r"static\s+(?:async\s+)?(?:void|Task|int)\s+Main\s*\("),
}

# Docstring patterns
DOCSTRING_PATTERNS = {
    "python": re.compile(r'^(?:def|class)[^\n]+\n\s*"""([^"]+)"""', re.MULTILINE),
    "python_module": re.compile(r'^"""([^"]+)"""', re.MULTILINE),
}

# Map language to patterns
IMPORT_PATTERNS_BY_LANGUAGE: dict[str, list[re.Pattern[str]]] = {
    "python": PYTHON_IMPORT_PATTERNS,
    "javascript": JS_IMPORT_PATTERNS,
    "typescript": JS_IMPORT_PATTERNS,
    "go": GO_IMPORT_PATTERNS,
    "rust": RUST_IMPORT_PATTERNS,
    "java": JAVA_IMPORT_PATTERNS,
    "kotlin": JAVA_IMPORT_PATTERNS,
    "csharp": CSHARP_IMPORT_PATTERNS,
    "c": C_IMPORT_PATTERNS,
    "cpp": C_IMPORT_PATTERNS,
    "ruby": RUBY_IMPORT_PATTERNS,
    "php": PHP_IMPORT_PATTERNS,
    "swift": SWIFT_IMPORT_PATTERNS,
}

EXPORT_PATTERNS_BY_LANGUAGE: dict[str, dict[str, re.Pattern[str]]] = {
    "python": PYTHON_EXPORT_PATTERNS,
    "javascript": JS_EXPORT_PATTERNS,
    "typescript": JS_EXPORT_PATTERNS,
    "go": GO_EXPORT_PATTERNS,
    "rust": RUST_EXPORT_PATTERNS,
    "java": JAVA_EXPORT_PATTERNS,
    "kotlin": JAVA_EXPORT_PATTERNS,
    "csharp": CSHARP_EXPORT_PATTERNS,
    "c": C_EXPORT_PATTERNS,
    "cpp": C_EXPORT_PATTERNS,
}


class RegexAnalyzer(BaseAnalyzer):
    """
    Language-agnostic code analyzer using regex patterns.

    Extracts imports, exports, functions, and classes from source files
    using pattern matching. Works for any language with defined patterns.
    """

    # Support all known languages
    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = set(EXTENSION_TO_LANGUAGE.keys())
    SUPPORTED_LANGUAGES: ClassVar[list[str]] = list(IMPORT_PATTERNS_BY_LANGUAGE.keys())

    def __init__(
        self,
        exclude_patterns: list[str] | None = None,
        max_file_size: int = 1024 * 1024,  # 1MB default
    ) -> None:
        """
        Initialize regex analyzer.

        Args:
            exclude_patterns: Glob patterns for paths to exclude
            max_file_size: Maximum file size to process (bytes)
        """
        super().__init__(exclude_patterns)
        self.max_file_size = max_file_size

    def can_analyze(self, path: Path) -> bool:
        """Check if file can be analyzed."""
        if not path.is_file():
            return False

        # Check extension
        extension = path.suffix.lower()
        if extension not in EXTENSION_TO_LANGUAGE:
            return False

        # Check file size
        try:
            return path.stat().st_size <= self.max_file_size
        except OSError:
            return False

    async def analyze(self, path: Path) -> AnalysisResult:
        """
        Analyze a source file using regex patterns.

        Args:
            path: Path to source file

        Returns:
            Analysis result with imports and exports
        """
        language = self._detect_language(path)

        if not language:
            return AnalysisResult(
                path=path,
                language=None,
                metadata={"analysis_method": "regex", "skipped": "unknown_language"},
            )

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return AnalysisResult(
                path=path,
                language=language,
                metadata={"analysis_method": "regex", "error": str(e)},
            )

        extraction = self._extract(content, language)

        return AnalysisResult(
            path=path,
            imports=extraction.imports,
            exports=extraction.exports,
            is_entry_point=extraction.has_main_block,
            language=language,
            metadata={
                "analysis_method": "regex",
                "functions": extraction.functions,
                "classes": extraction.classes,
                "docstring": extraction.docstring,
            },
        )

    def _extract(self, content: str, language: str) -> ExtractionResult:
        """
        Extract imports and exports from content.

        Args:
            content: Source file content
            language: Programming language

        Returns:
            ExtractionResult with all extracted information
        """
        result = ExtractionResult()

        # Extract imports
        import_patterns = IMPORT_PATTERNS_BY_LANGUAGE.get(language, [])
        for pattern in import_patterns:
            matches = pattern.findall(content)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                import_name = str(match).strip()
                if import_name and import_name not in result.imports:
                    result.imports.append(import_name)

        # Extract exports/declarations
        export_patterns = EXPORT_PATTERNS_BY_LANGUAGE.get(language, {})

        if "functions" in export_patterns:
            matches = export_patterns["functions"].findall(content)
            for match in matches:
                name = str(match).strip()
                if name and not name.startswith("_"):
                    result.functions.append(name)
                    if name not in result.exports:
                        result.exports.append(name)

        if "classes" in export_patterns:
            matches = export_patterns["classes"].findall(content)
            for match in matches:
                name = str(match).strip()
                if name and not name.startswith("_"):
                    result.classes.append(name)
                    if name not in result.exports:
                        result.exports.append(name)

        # Handle Python's __all__
        if language == "python" and "__all__" in export_patterns:
            all_match = export_patterns["__all__"].search(content)
            if all_match:
                all_content = all_match.group(1)
                # Parse the __all__ list
                names = re.findall(r"""['"](\w+)['"]""", all_content)
                result.exports = list(names)

        # Handle JS module.exports
        if language in ("javascript", "typescript") and "module_exports" in export_patterns:
            exports_match = export_patterns["module_exports"].search(content)
            if exports_match:
                exports_content = exports_match.group(1)
                names = re.findall(r"(\w+)\s*(?:,|$)", exports_content)
                for name in names:
                    if name not in result.exports:
                        result.exports.append(name)

        # Other export patterns
        for key, pattern in export_patterns.items():
            if key not in ("functions", "classes", "__all__", "module_exports"):
                matches = pattern.findall(content)
                for match in matches:
                    name = str(match).strip() if not isinstance(match, tuple) else str(match[0]).strip()
                    if name and name not in result.exports:
                        result.exports.append(name)

        # Detect main block
        main_pattern = MAIN_PATTERNS.get(language)
        if main_pattern:
            result.has_main_block = bool(main_pattern.search(content))

        # Extract docstring (Python only for now)
        if language == "python":
            module_doc = DOCSTRING_PATTERNS["python_module"].search(content)
            if module_doc:
                result.docstring = module_doc.group(1).strip()

        return result

    def extract_imports(self, content: str, language: str) -> list[str]:
        """
        Extract only imports from content.

        Args:
            content: Source file content
            language: Programming language

        Returns:
            List of import names
        """
        return self._extract(content, language).imports

    def extract_exports(self, content: str, language: str) -> list[str]:
        """
        Extract only exports from content.

        Args:
            content: Source file content
            language: Programming language

        Returns:
            List of export names
        """
        return self._extract(content, language).exports


# Convenience function
async def analyze_with_regex(path: Path) -> AnalysisResult:
    """
    Analyze a file using regex patterns.

    Args:
        path: Path to source file

    Returns:
        Analysis result
    """
    analyzer = RegexAnalyzer()
    return await analyzer.analyze(path)

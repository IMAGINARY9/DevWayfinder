"""Python AST-based analyzer for accurate import/export extraction."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from devwayfinder.analyzers.base import BaseAnalyzer
from devwayfinder.analyzers.regex_extractor import RegexAnalyzer
from devwayfinder.core.protocols import AnalysisResult

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class PythonExtractionResult:
    """Detailed extraction result for Python files."""

    imports: list[str] = field(default_factory=list)
    from_imports: list[tuple[str, list[str]]] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    all_definition: list[str] | None = None
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    module_docstring: str | None = None
    has_main_block: bool = False
    global_variables: list[str] = field(default_factory=list)
    decorators_used: list[str] = field(default_factory=list)


@dataclass
class FunctionInfo:
    """Information about a Python function."""

    name: str
    lineno: int
    is_async: bool = False
    is_public: bool = True
    docstring: str | None = None
    parameters: list[str] = field(default_factory=list)
    return_type: str | None = None
    decorators: list[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    """Information about a Python class."""

    name: str
    lineno: int
    is_public: bool = True
    docstring: str | None = None
    bases: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)


class PythonASTAnalyzer(BaseAnalyzer):
    """
    Python-specific analyzer using the built-in AST module.

    Provides higher accuracy than regex for Python files.
    Falls back to regex if AST parsing fails.
    """

    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {".py", ".pyi", ".pyw"}
    SUPPORTED_LANGUAGES: ClassVar[list[str]] = ["python"]

    def __init__(
        self,
        exclude_patterns: list[str] | None = None,
        extract_signatures: bool = True,
        fallback_to_regex: bool = True,
    ) -> None:
        """
        Initialize Python AST analyzer.

        Args:
            exclude_patterns: Glob patterns to exclude
            extract_signatures: Whether to extract function signatures
            fallback_to_regex: Whether to fall back to regex on AST failure
        """
        super().__init__(exclude_patterns)
        self.extract_signatures = extract_signatures
        self.fallback_to_regex = fallback_to_regex
        self._regex_fallback = RegexAnalyzer(exclude_patterns)

    async def analyze(self, path: Path) -> AnalysisResult:
        """
        Analyze a Python file using AST.

        Args:
            path: Path to Python file

        Returns:
            Analysis result with imports and exports
        """
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return AnalysisResult(
                path=path,
                language="python",
                metadata={"analysis_method": "ast", "error": str(e)},
            )

        try:
            tree = ast.parse(content, filename=str(path))
            extraction = self._extract_from_ast(tree, content)

            # Determine exports: use __all__ if defined, otherwise public symbols
            if extraction.all_definition is not None:
                exports = extraction.all_definition
            else:
                exports = self._get_public_exports(extraction)

            # Flatten imports
            imports = self._flatten_imports(extraction)

            return AnalysisResult(
                path=path,
                imports=imports,
                exports=exports,
                is_entry_point=extraction.has_main_block,
                language="python",
                metadata={
                    "analysis_method": "ast",
                    "functions": [f.name for f in extraction.functions],
                    "classes": [c.name for c in extraction.classes],
                    "docstring": extraction.module_docstring,
                    "from_imports": extraction.from_imports,
                    "decorators_used": extraction.decorators_used,
                },
            )

        except SyntaxError as e:
            if self.fallback_to_regex:
                result = await self._regex_fallback.analyze(path)
                result.metadata["ast_error"] = str(e)
                result.metadata["analysis_method"] = "regex_fallback"
                return result
            else:
                return AnalysisResult(
                    path=path,
                    language="python",
                    metadata={
                        "analysis_method": "ast",
                        "error": f"SyntaxError: {e}",
                    },
                )

    def _extract_from_ast(self, tree: ast.Module, content: str) -> PythonExtractionResult:  # noqa: ARG002
        """
        Extract information from AST.

        Args:
            tree: Parsed AST
            content: Original source content (for docstrings)

        Returns:
            Extraction result
        """
        result = PythonExtractionResult()

        # Get module docstring
        result.module_docstring = ast.get_docstring(tree)

        for node in ast.walk(tree):
            # Handle imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    result.imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                names = [alias.name for alias in node.names]
                relative_prefix = "." * node.level
                module_name = node.module or ""
                full_module = f"{relative_prefix}{module_name}"

                if full_module:
                    result.from_imports.append((full_module, names))

            # Handle __all__ definition
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, ast.List):
                            result.all_definition = []
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    result.all_definition.append(elt.value)
                    # Track global variables
                    elif isinstance(target, ast.Name):
                        name = target.id
                        if not name.startswith("_"):
                            result.global_variables.append(name)

        # Process top-level definitions only
        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                func_info = self._extract_function(node)
                result.functions.append(func_info)
                result.decorators_used.extend(func_info.decorators)

            elif isinstance(node, ast.ClassDef):
                class_info = self._extract_class(node)
                result.classes.append(class_info)
                result.decorators_used.extend(class_info.decorators)

            # Check for if __name__ == "__main__"
            elif isinstance(node, ast.If):
                if self._is_main_block(node):
                    result.has_main_block = True

        return result

    def _flatten_imports(self, extraction: PythonExtractionResult) -> list[str]:
        """Flatten direct and from-import statements into graph-resolvable imports."""
        imports: list[str] = []
        seen: set[str] = set()

        def _add(import_name: str) -> None:
            cleaned = import_name.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                imports.append(cleaned)

        for import_name in extraction.imports:
            _add(import_name)

        for module, names in extraction.from_imports:
            # Pure dot prefixes (., .., ...) need imported names to resolve to siblings/parents.
            if module and set(module) != {"."}:
                _add(module)

            if module and set(module) == {"."}:
                for name in names:
                    if name != "*":
                        _add(f"{module}{name}")

        return imports

    def _extract_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionInfo:
        """Extract function information."""
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(f"{self._get_attribute_name(decorator)}")
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    decorators.append(decorator.func.id)
                elif isinstance(decorator.func, ast.Attribute):
                    decorators.append(self._get_attribute_name(decorator.func))

        # Extract parameters
        parameters = []
        for arg in node.args.args:
            param_name = arg.arg
            if arg.annotation:
                param_name += f": {self._annotation_to_string(arg.annotation)}"
            parameters.append(param_name)

        # Extract return type
        return_type = None
        if node.returns:
            return_type = self._annotation_to_string(node.returns)

        return FunctionInfo(
            name=node.name,
            lineno=node.lineno,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_public=not node.name.startswith("_"),
            docstring=ast.get_docstring(node),
            parameters=parameters,
            return_type=return_type,
            decorators=decorators,
        )

    def _extract_class(self, node: ast.ClassDef) -> ClassInfo:
        """Extract class information."""
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(self._get_attribute_name(decorator))

        # Extract base classes
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(self._get_attribute_name(base))

        # Extract methods
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                methods.append(item.name)

        return ClassInfo(
            name=node.name,
            lineno=node.lineno,
            is_public=not node.name.startswith("_"),
            docstring=ast.get_docstring(node),
            bases=bases,
            methods=methods,
            decorators=decorators,
        )

    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """Get full attribute name (e.g., 'module.submodule.attr')."""
        parts = [node.attr]
        current = node.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    def _annotation_to_string(self, node: ast.expr) -> str:
        """Convert type annotation AST to string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Attribute):
            return self._get_attribute_name(node)
        elif isinstance(node, ast.Subscript):
            value = self._annotation_to_string(node.value)
            slice_val = self._annotation_to_string(node.slice)
            return f"{value}[{slice_val}]"
        elif isinstance(node, ast.Tuple):
            elts = ", ".join(self._annotation_to_string(e) for e in node.elts)
            return elts
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            left = self._annotation_to_string(node.left)
            right = self._annotation_to_string(node.right)
            return f"{left} | {right}"
        else:
            return "..."

    def _is_main_block(self, node: ast.If) -> bool:
        """Check if this is 'if __name__ == "__main__"'."""
        test = node.test
        if isinstance(test, ast.Compare) and (
            isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)
            and len(test.comparators) == 1
        ):
            comp = test.comparators[0]
            if isinstance(comp, ast.Constant) and comp.value == "__main__":
                return True
        return False

    def _get_public_exports(self, extraction: PythonExtractionResult) -> list[str]:
        """Get list of public exports when __all__ is not defined."""
        exports = []

        # Add public functions
        for func in extraction.functions:
            if func.is_public:
                exports.append(func.name)

        # Add public classes
        for cls in extraction.classes:
            if cls.is_public:
                exports.append(cls.name)

        # Add public global variables (except common internal ones)
        internal_vars = {"__version__", "__author__", "__all__"}
        for var in extraction.global_variables:
            if var not in internal_vars and var not in exports:
                exports.append(var)

        return exports

    def resolve_relative_import(
        self, import_name: str, current_file: Path, project_root: Path
    ) -> str | None:
        """
        Resolve a relative import to an absolute module path.

        Args:
            import_name: Import string (may include leading dots)
            current_file: Path of the importing file
            project_root: Project root directory

        Returns:
            Resolved module path or None if resolution fails
        """
        if not import_name.startswith("."):
            return import_name

        # Count leading dots
        dots = 0
        for char in import_name:
            if char == ".":
                dots += 1
            else:
                break

        remaining = import_name[dots:]

        # Get the package path
        try:
            rel_path = current_file.relative_to(project_root)
        except ValueError:
            return None

        # Build the base package path
        parts = list(rel_path.parent.parts)

        # Go up directories based on dot count
        # One dot = current package, two dots = parent, etc.
        up_count = dots - 1
        if up_count > len(parts):
            return None

        if up_count > 0:
            parts = parts[:-up_count]

        # Combine with the import path
        if remaining:
            parts.append(remaining.replace(".", "/"))

        return ".".join(parts)


# Convenience function
async def analyze_python(path: Path) -> AnalysisResult:
    """
    Analyze a Python file.

    Args:
        path: Path to Python file

    Returns:
        Analysis result
    """
    analyzer = PythonASTAnalyzer()
    return await analyzer.analyze(path)


def get_python_imports(content: str) -> list[str]:
    """
    Quick extraction of imports from Python source.

    Args:
        content: Python source code

    Returns:
        List of imported module names
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    return imports

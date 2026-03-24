"""Directory structure analyzer."""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path

from devwayfinder.analyzers.base import EXTENSION_TO_LANGUAGE


@dataclass
class StructureInfo:
    """Information extracted from project structure."""

    root_path: Path
    build_system: str | None = None
    package_manager: str | None = None
    primary_language: str | None = None
    readme_content: str | None = None
    contributing_content: str | None = None
    changelog_content: str | None = None
    source_files: list[Path] = field(default_factory=list)
    entry_points: list[Path] = field(default_factory=list)
    config_files: list[Path] = field(default_factory=list)
    documentation_files: list[Path] = field(default_factory=list)
    language_stats: dict[str, int] = field(default_factory=dict)


# Build system detection patterns
BUILD_SYSTEM_FILES: dict[str, str] = {
    "pyproject.toml": "pyproject",
    "setup.py": "setuptools",
    "setup.cfg": "setuptools",
    "Pipfile": "pipenv",
    "package.json": "npm",
    "Cargo.toml": "cargo",
    "CMakeLists.txt": "cmake",
    "Makefile": "make",
    "build.gradle": "gradle",
    "build.gradle.kts": "gradle",
    "pom.xml": "maven",
    "meson.build": "meson",
    "BUILD": "bazel",
    "BUILD.bazel": "bazel",
    "WORKSPACE": "bazel",
    "go.mod": "go",
    "requirements.txt": "pip",
    "mix.exs": "mix",
    "Gemfile": "bundler",
    "composer.json": "composer",
    "pubspec.yaml": "pub",
    "Package.swift": "swift",
    "deno.json": "deno",
    "bun.lockb": "bun",
}

# Package manager detection
PACKAGE_MANAGER_FILES: dict[str, str] = {
    "package-lock.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "bun.lockb": "bun",
    "Pipfile.lock": "pipenv",
    "poetry.lock": "poetry",
    "pdm.lock": "pdm",
    "Cargo.lock": "cargo",
    "go.sum": "go",
    "Gemfile.lock": "bundler",
    "composer.lock": "composer",
    "pubspec.lock": "pub",
}

# Entry point filename patterns
ENTRY_POINT_PATTERNS: list[str] = [
    "main.py",
    "__main__.py",
    "app.py",
    "cli.py",
    "run.py",
    "server.py",
    "index.js",
    "index.ts",
    "main.js",
    "main.ts",
    "app.js",
    "app.ts",
    "server.js",
    "server.ts",
    "main.go",
    "main.rs",
    "lib.rs",
    "Main.java",
    "App.java",
    "Program.cs",
    "main.c",
    "main.cpp",
    "main.rb",
    "app.rb",
    "main.swift",
    "main.kt",
]

# Default exclude patterns
DEFAULT_EXCLUDES: list[str] = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "dist",
    "build",
    "*.egg-info",
    ".tox",
    ".nox",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "coverage",
    ".coverage",
    "htmlcov",
    ".idea",
    ".vscode",
    "*.min.js",
    "*.bundle.js",
    "target",
    "vendor",
    ".DS_Store",
    "Thumbs.db",
]

# Documentation file patterns
DOC_PATTERNS: list[str] = [
    "README*",
    "readme*",
    "CONTRIBUTING*",
    "contributing*",
    "CHANGELOG*",
    "changelog*",
    "HISTORY*",
    "history*",
    "AUTHORS*",
    "MAINTAINERS*",
    "LICENSE*",
    "COPYING*",
    "docs/*",
    "doc/*",
    "documentation/*",
]

# Binary file extensions to skip
BINARY_EXTENSIONS: set[str] = {
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".o",
    ".a",
    ".lib",
    ".bin",
    ".pyc",
    ".pyo",
    ".class",
    ".jar",
    ".war",
    ".ear",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".svg",
    ".webp",
    ".mp3",
    ".mp4",
    ".wav",
    ".avi",
    ".mov",
    ".mkv",
    ".flv",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".wasm",
}


class StructureAnalyzer:
    """
    Analyzes project directory structure.

    Detects build systems, package managers, entry points,
    and collects source file information.
    """

    def __init__(
        self,
        exclude_patterns: list[str] | None = None,
        respect_gitignore: bool = True,
    ) -> None:
        """
        Initialize structure analyzer.

        Args:
            exclude_patterns: Additional glob patterns to exclude
            respect_gitignore: Whether to parse and respect .gitignore
        """
        self.exclude_patterns = list(DEFAULT_EXCLUDES)
        if exclude_patterns:
            self.exclude_patterns.extend(exclude_patterns)
        self.respect_gitignore = respect_gitignore
        self._gitignore_patterns: list[str] = []

    async def analyze(self, root_path: Path) -> StructureInfo:
        """
        Analyze project directory structure.

        Args:
            root_path: Root directory to analyze

        Returns:
            StructureInfo with detected information
        """
        root_path = root_path.resolve()

        if not root_path.exists():
            raise FileNotFoundError(f"Path does not exist: {root_path}")

        if not root_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {root_path}")

        # Load .gitignore patterns if present
        if self.respect_gitignore:
            self._load_gitignore(root_path)

        info = StructureInfo(root_path=root_path)

        # Scan all files
        await self._scan_directory(root_path, info)

        # Detect build system and package manager
        info.build_system = self._detect_build_system(info.config_files)
        info.package_manager = self._detect_package_manager(info.config_files)

        # Read documentation files
        await self._read_documentation(root_path, info)

        # Detect primary language
        info.primary_language = self._detect_primary_language(info.language_stats)

        return info

    def _load_gitignore(self, root_path: Path) -> None:
        """Load .gitignore patterns."""
        gitignore_path = root_path / ".gitignore"
        if gitignore_path.is_file():
            try:
                content = gitignore_path.read_text(encoding="utf-8", errors="ignore")
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Remove leading / for directory patterns
                        pattern = line.lstrip("/")
                        self._gitignore_patterns.append(pattern)
            except OSError:
                pass  # Ignore read errors

    def _should_exclude(self, path: Path, root_path: Path) -> bool:
        """Check if a path should be excluded."""
        name = path.name
        try:
            rel_path = path.relative_to(root_path)
            rel_str = str(rel_path).replace("\\", "/")
        except ValueError:
            rel_str = name

        # Check default patterns
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
            if fnmatch.fnmatch(rel_str, pattern):
                return True

        # Check gitignore patterns
        for pattern in self._gitignore_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
            if fnmatch.fnmatch(rel_str, pattern):
                return True
            # Handle directory patterns ending with /
            if pattern.endswith("/") and path.is_dir() and fnmatch.fnmatch(name + "/", pattern):
                return True

        return False

    def _is_binary(self, path: Path) -> bool:
        """Check if file is binary based on extension."""
        return path.suffix.lower() in BINARY_EXTENSIONS

    async def _scan_directory(self, root_path: Path, info: StructureInfo) -> None:
        """Recursively scan directory for source files."""
        try:
            for entry in os.scandir(root_path):
                path = Path(entry.path)

                if self._should_exclude(path, info.root_path):
                    continue

                if entry.is_dir():
                    await self._scan_directory(path, info)
                elif entry.is_file():
                    await self._process_file(path, info)
        except PermissionError:
            pass  # Skip directories we can't access

    async def _process_file(self, path: Path, info: StructureInfo) -> None:
        """Process a single file."""
        name = path.name

        # Skip binary files
        if self._is_binary(path):
            return

        # Check for config/build files
        if name in BUILD_SYSTEM_FILES or name in PACKAGE_MANAGER_FILES:
            info.config_files.append(path)

        # Check for documentation files
        for pattern in DOC_PATTERNS:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(name.lower(), pattern.lower()):
                info.documentation_files.append(path)
                break

        # Check for entry points
        if name in ENTRY_POINT_PATTERNS or self._is_entry_point_pattern(name):
            info.entry_points.append(path)

        # Check for source files
        language = EXTENSION_TO_LANGUAGE.get(path.suffix.lower())
        if language:
            info.source_files.append(path)
            info.language_stats[language] = info.language_stats.get(language, 0) + 1

    def _is_entry_point_pattern(self, name: str) -> bool:
        """Check if filename matches entry point pattern."""
        name_lower = name.lower()

        # Check exact matches first
        if name in ENTRY_POINT_PATTERNS or name_lower in [p.lower() for p in ENTRY_POINT_PATTERNS]:
            return True

        # Check pattern matches
        return any(fnmatch.fnmatch(name_lower, p.lower()) for p in ENTRY_POINT_PATTERNS)

    def _detect_build_system(self, config_files: list[Path]) -> str | None:
        """Detect build system from config files."""
        names = {f.name for f in config_files}

        # Priority order for build systems
        priority = [
            ("pyproject.toml", "pyproject"),
            ("Cargo.toml", "cargo"),
            ("package.json", "npm"),
            ("go.mod", "go"),
            ("CMakeLists.txt", "cmake"),
            ("Makefile", "make"),
            ("build.gradle.kts", "gradle"),
            ("build.gradle", "gradle"),
            ("pom.xml", "maven"),
            ("setup.py", "setuptools"),
        ]

        for filename, system in priority:
            if filename in names:
                return system

        return None

    def _detect_package_manager(self, config_files: list[Path]) -> str | None:
        """Detect package manager from lock files."""
        names = {f.name for f in config_files}

        for filename, manager in PACKAGE_MANAGER_FILES.items():
            if filename in names:
                return manager

        return None

    def _detect_primary_language(self, language_stats: dict[str, int]) -> str | None:
        """Detect primary language by file count."""
        if not language_stats:
            return None

        return max(language_stats.items(), key=lambda x: x[1])[0]

    async def _read_documentation(self, root_path: Path, info: StructureInfo) -> None:
        """Read content of documentation files."""
        readme_patterns = ["README.md", "README.rst", "README.txt", "README"]
        contributing_patterns = [
            "CONTRIBUTING.md",
            "CONTRIBUTING.rst",
            "CONTRIBUTING.txt",
            "CONTRIBUTING",
        ]
        changelog_patterns = [
            "CHANGELOG.md",
            "CHANGELOG.rst",
            "CHANGELOG.txt",
            "CHANGELOG",
            "HISTORY.md",
            "HISTORY.rst",
        ]

        for pattern in readme_patterns:
            readme_path = root_path / pattern
            if readme_path.is_file():
                try:
                    info.readme_content = readme_path.read_text(encoding="utf-8", errors="replace")
                    break
                except OSError:
                    pass

        for pattern in contributing_patterns:
            contrib_path = root_path / pattern
            if contrib_path.is_file():
                try:
                    info.contributing_content = contrib_path.read_text(
                        encoding="utf-8", errors="replace"
                    )
                    break
                except OSError:
                    pass

        for pattern in changelog_patterns:
            changelog_path = root_path / pattern
            if changelog_path.is_file():
                try:
                    info.changelog_content = changelog_path.read_text(
                        encoding="utf-8", errors="replace"
                    )
                    break
                except OSError:
                    pass


# Convenience function
async def analyze_structure(
    path: Path,
    exclude_patterns: list[str] | None = None,
    respect_gitignore: bool = True,
) -> StructureInfo:
    """
    Analyze project structure.

    Args:
        path: Root directory path
        exclude_patterns: Additional patterns to exclude
        respect_gitignore: Whether to respect .gitignore

    Returns:
        StructureInfo with analysis results
    """
    analyzer = StructureAnalyzer(
        exclude_patterns=exclude_patterns,
        respect_gitignore=respect_gitignore,
    )
    return await analyzer.analyze(path)

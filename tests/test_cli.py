"""Tests for CLI commands."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from devwayfinder.cli.app import app
from devwayfinder.version import get_version

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from terminal output."""
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)


class TestVersionCommand:
    """Tests for the version command."""

    def test_version_command(self) -> None:
        """Test version command shows version."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "DevWayfinder version" in result.output
        assert get_version() in result.output


class TestAnalyzeCommand:
    """Tests for the analyze command."""

    def test_analyze_nonexistent_path(self) -> None:
        """Test analyze with nonexistent path fails."""
        result = runner.invoke(app, ["analyze", "/nonexistent/path"])
        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_analyze_help(self) -> None:
        """Test analyze command help."""
        result = runner.invoke(app, ["analyze", "--help"], color=False)
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "Analyze project structure" in output
        assert "--verbose" in output
        assert "--json" in output

    def test_analyze_current_project(self, tmp_path: Path) -> None:
        """Test analyze command on a simple project."""
        # Create a simple Python project
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def main():\n    pass\n")
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test-project"\n')

        result = runner.invoke(app, ["analyze", str(tmp_path)])
        assert result.exit_code == 0
        assert "Analysis complete" in result.output

    def test_analyze_json_output(self, tmp_path: Path) -> None:
        """Test analyze command with JSON output."""
        # Create a simple Python project
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def main():\n    pass\n")
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test-project"\n')

        result = runner.invoke(app, ["analyze", str(tmp_path), "--json"])
        assert result.exit_code == 0

        # The output should contain JSON with expected fields
        # We just check for presence of key strings since Rich formatting may interfere
        assert "project_name" in result.output
        assert "build_system" in result.output
        assert "graph" in result.output
        assert "node_count" in result.output

    def test_analyze_respects_project_config_excludes(self, tmp_path: Path) -> None:
        """Analyze should merge and apply exclude patterns from .devwayfinder/config.yaml."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def main():\n    return 1\n")

        (tmp_path / "generated").mkdir()
        (tmp_path / "generated" / "noise.py").write_text("def noise():\n    return 2\n")

        config_dir = tmp_path / ".devwayfinder"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text(
            "analysis:\n  exclude_patterns:\n    - generated\n",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["analyze", str(tmp_path), "--json"])
        assert result.exit_code == 0
        assert '"file_count": 1' in result.output


class TestGenerateCommand:
    """Tests for the generate command."""

    def test_generate_nonexistent_path(self) -> None:
        """Test generate with nonexistent path fails."""
        result = runner.invoke(app, ["generate", "/nonexistent/path", "--no-llm"])
        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_generate_help(self) -> None:
        """Test generate command help."""
        result = runner.invoke(app, ["generate", "--help"], color=False)
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "Generate onboarding guide" in output
        assert "--output" in output
        assert "--no-llm" in output
        assert "--model-provider" in output
        assert "--guide-template" in output

    def test_generate_heuristic_mode(self, tmp_path: Path) -> None:
        """Test generate command with heuristics only."""
        # Create a simple Python project
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text(
            '"""Main module."""\n\ndef main():\n    """Entry point."""\n    pass\n'
        )
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test-project"\n')

        result = runner.invoke(app, ["generate", str(tmp_path), "--no-llm"])
        assert result.exit_code == 0
        assert "Generation complete" in result.output or "Generated guide" in result.output
        assert "Preflight Estimate" in result.output
        assert "Cost (estimated)" in result.output
        assert "All providers failed" not in result.output

    def test_generate_to_file(self, tmp_path: Path) -> None:
        """Test generate command writes output to file."""
        # Create a simple Python project
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text('"""Main module."""\n\ndef main():\n    pass\n')
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test-project"\n')

        output_file = tmp_path / "ONBOARDING.md"
        result = runner.invoke(
            app, ["generate", str(tmp_path), "--no-llm", "--output", str(output_file)]
        )
        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "test-project" in content.lower() or len(content) > 0

    def test_generate_with_custom_guide_template(self, tmp_path: Path) -> None:
        """Test generate command with explicit guide template path."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text(
            '"""Main module."""\n\ndef main():\n    pass\n\nif __name__ == "__main__":\n    main()\n'
        )
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test-project"\n')

        template_file = tmp_path / "template.yaml"
        template_file.write_text(
            """
extends: default
sections:
  - type: start_here
    title: Read This First
""".strip()
            + "\n"
        )

        result = runner.invoke(
            app,
            [
                "generate",
                str(tmp_path),
                "--no-llm",
                "--guide-template",
                str(template_file),
            ],
        )

        assert result.exit_code == 0
        assert "Read This First" in result.output


class TestTestModelCommand:
    """Tests for the test-model command."""

    def test_test_model_help(self) -> None:
        """Test test-model command help."""
        result = runner.invoke(app, ["test-model", "--help"], color=False)
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "Test connection" in output
        assert "--provider" in output
        assert "--timeout" in output

    def test_test_model_invalid_provider(self) -> None:
        """Test test-model with invalid provider."""
        result = runner.invoke(app, ["test-model", "--provider", "invalid_provider"])
        assert result.exit_code == 1


class TestInitCommand:
    """Tests for the init command."""

    def test_init_help(self) -> None:
        """Test init command help."""
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "Initialize" in result.output

    def test_init_creates_config(self, tmp_path: Path) -> None:
        """Test init command creates configuration directory."""
        result = runner.invoke(app, ["init", str(tmp_path)])
        assert result.exit_code == 0
        assert "Configuration initialized" in result.output

        # Verify files created
        config_path = tmp_path / ".devwayfinder" / "config.yaml"
        assert config_path.exists()

        gitignore_path = tmp_path / ".devwayfinder" / ".gitignore"
        assert gitignore_path.exists()

    def test_init_detects_python_project(self, tmp_path: Path) -> None:
        """Test init auto-detects Python projects."""
        # Create a Python project indicator
        (tmp_path / "pyproject.toml").write_text('[project]\\nname = "test"')

        result = runner.invoke(app, ["init", str(tmp_path)])
        assert result.exit_code == 0
        assert "python" in result.output.lower()

    def test_init_list_templates(self) -> None:
        """Test init --list shows available templates."""
        result = runner.invoke(app, ["init", "--list"])
        assert result.exit_code == 0
        assert "python" in result.output
        assert "javascript" in result.output
        assert "default" in result.output

    def test_init_refuses_overwrite(self, tmp_path: Path) -> None:
        """Test init refuses to overwrite existing config."""
        # Create existing config
        config_dir = tmp_path / ".devwayfinder"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("existing: true")

        result = runner.invoke(app, ["init", str(tmp_path)])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_init_force_overwrites(self, tmp_path: Path) -> None:
        """Test init --force overwrites existing config."""
        # Create existing config
        config_dir = tmp_path / ".devwayfinder"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("existing: true")

        result = runner.invoke(app, ["init", str(tmp_path), "--force"])
        assert result.exit_code == 0
        assert "Configuration initialized" in result.output

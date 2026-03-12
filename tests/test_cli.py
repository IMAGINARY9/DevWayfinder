"""Tests for CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typer.testing import CliRunner

from devwayfinder.cli.app import app

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


class TestVersionCommand:
    """Tests for the version command."""

    def test_version_command(self) -> None:
        """Test version command shows version."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "DevWayfinder version" in result.output


class TestAnalyzeCommand:
    """Tests for the analyze command."""

    def test_analyze_nonexistent_path(self) -> None:
        """Test analyze with nonexistent path fails."""
        result = runner.invoke(app, ["analyze", "/nonexistent/path"])
        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_analyze_help(self) -> None:
        """Test analyze command help."""
        result = runner.invoke(app, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "Analyze project structure" in result.output
        assert "--verbose" in result.output
        assert "--json" in result.output

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


class TestGenerateCommand:
    """Tests for the generate command."""

    def test_generate_nonexistent_path(self) -> None:
        """Test generate with nonexistent path fails."""
        result = runner.invoke(app, ["generate", "/nonexistent/path", "--no-llm"])
        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_generate_help(self) -> None:
        """Test generate command help."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "Generate onboarding guide" in result.output
        assert "--output" in result.output
        assert "--no-llm" in result.output
        assert "--model-provider" in result.output

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

    def test_generate_to_file(self, tmp_path: Path) -> None:
        """Test generate command writes output to file."""
        # Create a simple Python project
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text(
            '"""Main module."""\n\ndef main():\n    pass\n'
        )
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test-project"\n')

        output_file = tmp_path / "ONBOARDING.md"
        result = runner.invoke(
            app, ["generate", str(tmp_path), "--no-llm", "--output", str(output_file)]
        )
        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "test-project" in content.lower() or len(content) > 0


class TestTestModelCommand:
    """Tests for the test-model command."""

    def test_test_model_help(self) -> None:
        """Test test-model command help."""
        result = runner.invoke(app, ["test-model", "--help"])
        assert result.exit_code == 0
        assert "Test connection" in result.output
        assert "--provider" in result.output
        assert "--timeout" in result.output

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

    def test_init_placeholder(self) -> None:
        """Test init command shows placeholder message."""
        result = runner.invoke(app, ["init", "."])
        assert result.exit_code == 0
        assert "MVP 2" in result.output

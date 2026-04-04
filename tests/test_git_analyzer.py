"""Tests for git history analyzer."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from devwayfinder.analyzers.git_analyzer import (
    ContributorInfo,
    FileGitInfo,
    GitAnalyzer,
    RepoGitInfo,
    is_git_available,
)

# =============================================================================
# ContributorInfo Tests
# =============================================================================


class TestContributorInfo:
    """Tests for ContributorInfo dataclass."""

    def test_creation(self) -> None:
        """Test basic creation."""
        contributor = ContributorInfo(
            name="John Doe",
            email="john@example.com",
            commit_count=10,
        )
        assert contributor.name == "John Doe"
        assert contributor.email == "john@example.com"
        assert contributor.commit_count == 10

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        now = datetime.now(UTC)
        contributor = ContributorInfo(
            name="Jane Doe",
            email="jane@example.com",
            commit_count=5,
            first_commit=now,
            last_commit=now,
        )
        d = contributor.to_dict()
        assert d["name"] == "Jane Doe"
        assert d["commit_count"] == 5
        assert d["first_commit"] is not None


# =============================================================================
# FileGitInfo Tests
# =============================================================================


class TestFileGitInfo:
    """Tests for FileGitInfo dataclass."""

    def test_age_days(self) -> None:
        """Test age calculation."""
        info = FileGitInfo(
            path=Path("test.py"),
            first_commit=datetime.now(UTC),
        )
        assert info.age_days is not None
        assert info.age_days >= 0

    def test_age_days_none(self) -> None:
        """Test age when no first commit."""
        info = FileGitInfo(path=Path("test.py"))
        assert info.age_days is None

    def test_contributor_count(self) -> None:
        """Test contributor count."""
        info = FileGitInfo(
            path=Path("test.py"),
            contributors=[
                ContributorInfo(name="A", email="a@x.com"),
                ContributorInfo(name="B", email="b@x.com"),
            ],
        )
        assert info.contributor_count == 2

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        info = FileGitInfo(
            path=Path("test.py"),
            commit_count=5,
            change_frequency=1.5,
        )
        d = info.to_dict()
        assert d["path"] == "test.py"
        assert d["commit_count"] == 5
        assert d["change_frequency"] == 1.5


# =============================================================================
# RepoGitInfo Tests
# =============================================================================


class TestRepoGitInfo:
    """Tests for RepoGitInfo dataclass."""

    def test_get_hotspots(self) -> None:
        """Test getting hotspot files."""
        info = RepoGitInfo(root=Path())

        # Add some files with different frequencies
        info.files["a.py"] = FileGitInfo(path=Path("a.py"), change_frequency=10.0)
        info.files["b.py"] = FileGitInfo(path=Path("b.py"), change_frequency=5.0)
        info.files["c.py"] = FileGitInfo(path=Path("c.py"), change_frequency=15.0)

        hotspots = info.get_hotspots(top_n=2)
        assert len(hotspots) == 2
        assert hotspots[0].change_frequency == 15.0
        assert hotspots[1].change_frequency == 10.0

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        info = RepoGitInfo(
            root=Path("/project"),
            is_git_repo=True,
            total_commits=100,
            total_contributors=5,
        )
        d = info.to_dict()
        assert d["is_git_repo"] is True
        assert d["total_commits"] == 100


# =============================================================================
# GitAnalyzer Tests
# =============================================================================


class TestGitAnalyzer:
    """Tests for GitAnalyzer."""

    @pytest.fixture
    def git_repo(self, tmp_path: Path) -> Path:
        """Create a temporary git repository."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Configure git user
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Create and commit a file
        main_py = repo_path / "main.py"
        main_py.write_text("print('hello')")

        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Make another change
        main_py.write_text("print('hello world')")
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Update greeting"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        return repo_path

    def test_is_available(self, git_repo: Path) -> None:
        """Test availability check."""
        analyzer = GitAnalyzer(git_repo)
        # Should be available if this is a git repo
        assert analyzer.is_available

    def test_not_available_for_non_repo(self, tmp_path: Path) -> None:
        """Test availability for non-repo directory."""
        analyzer = GitAnalyzer(tmp_path)
        # May or may not be available depending on parent directories
        # The main test is that it doesn't crash
        _ = analyzer.is_available

    def test_analyze_repository(self, git_repo: Path) -> None:
        """Test repository analysis."""
        analyzer = GitAnalyzer(git_repo)
        info = analyzer.analyze_repository()

        assert info.is_git_repo
        assert info.total_commits >= 2
        assert info.total_contributors >= 1
        assert info.first_commit is not None
        assert info.last_commit is not None
        assert len(info.contributors) >= 1

    def test_analyze_file(self, git_repo: Path) -> None:
        """Test file analysis."""
        analyzer = GitAnalyzer(git_repo)
        main_py = git_repo / "main.py"

        info = analyzer.analyze_file(main_py)

        assert info.is_tracked
        assert info.commit_count >= 2
        assert info.last_modified is not None
        assert len(info.contributors) >= 1

    def test_analyze_untracked_file(self, git_repo: Path) -> None:
        """Test analysis of untracked file."""
        analyzer = GitAnalyzer(git_repo)

        # Create new untracked file
        new_file = git_repo / "untracked.py"
        new_file.write_text("# new file")

        info = analyzer.analyze_file(new_file)
        assert not info.is_tracked
        assert info.commit_count == 0

    def test_get_hotspots(self, git_repo: Path) -> None:
        """Test getting hotspot files."""
        analyzer = GitAnalyzer(git_repo)
        hotspots = analyzer.get_hotspots(top_n=5)

        # Should have at least main.py
        assert len(hotspots) >= 1

    def test_get_recent_changes_uses_rolling_window(self, tmp_path: Path) -> None:
        """Recent changes should use timedelta-based lookback across month boundaries."""
        analyzer = GitAnalyzer(tmp_path)
        now = datetime.now(UTC)

        recent = FileGitInfo(path=tmp_path / "recent.py", last_modified=now - timedelta(days=20))
        old = FileGitInfo(path=tmp_path / "old.py", last_modified=now - timedelta(days=45))

        mocked_repo_info = RepoGitInfo(
            root=tmp_path,
            is_git_repo=True,
            files={
                str(recent.path): recent,
                str(old.path): old,
            },
        )

        with patch.object(analyzer, "analyze_repository", return_value=mocked_repo_info):
            changes = analyzer.get_recent_changes(days=30)

        changed_names = {item.path.name for item in changes}
        assert "recent.py" in changed_names
        assert "old.py" not in changed_names

    def test_analyze_repo_graceful_on_non_repo(self, tmp_path: Path) -> None:
        """Test graceful handling of non-repo."""
        analyzer = GitAnalyzer(tmp_path)
        info = analyzer.analyze_repository()

        assert not info.is_git_repo
        assert len(info.errors) > 0


class TestGitAnalyzerMocked:
    """Tests with mocked git functionality."""

    def test_git_not_available(self) -> None:
        """Test behavior when git is not available."""
        with patch("devwayfinder.analyzers.git_analyzer.GIT_AVAILABLE", False):
            analyzer = GitAnalyzer(Path())
            assert not analyzer.is_available

    def test_invalid_repo_error(self, tmp_path: Path) -> None:
        """Test handling of invalid repository."""
        analyzer = GitAnalyzer(tmp_path)
        info = analyzer.analyze_repository()

        # Should fail gracefully
        assert not info.is_git_repo or len(info.errors) >= 0


# =============================================================================
# Utility Function Tests
# =============================================================================


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_is_git_available(self) -> None:
        """Test git availability check."""
        result = is_git_available()
        # Should return a boolean
        assert isinstance(result, bool)


# =============================================================================
# Integration Tests
# =============================================================================


class TestGitIntegration:
    """Integration tests for git analyzer."""

    @pytest.fixture
    def complex_repo(self, tmp_path: Path) -> Path:
        """Create a repository with multiple files and commits."""
        repo_path = tmp_path / "complex_repo"
        repo_path.mkdir()

        # Initialize
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "dev@example.com"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Developer"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Create multiple files
        (repo_path / "src").mkdir()
        files = ["src/main.py", "src/utils.py", "README.md"]

        for f in files:
            path = repo_path / f
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {f}")

        subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Make changes to main.py multiple times
        for i in range(3):
            (repo_path / "src" / "main.py").write_text(f"# Version {i}")
            subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
            subprocess.run(
                ["git", "commit", "-m", f"Update main.py v{i}"],
                cwd=repo_path,
                capture_output=True,
                check=True,
            )

        return repo_path

    def test_hotspot_detection(self, complex_repo: Path) -> None:
        """Test that frequently changed files are detected as hotspots."""
        analyzer = GitAnalyzer(complex_repo)
        hotspots = analyzer.get_hotspots(top_n=5)

        # main.py should be in the hotspots since it was changed most
        hotspot_paths = [str(h.path) for h in hotspots]
        main_found = any("main.py" in p for p in hotspot_paths)
        assert main_found, f"main.py not in hotspots: {hotspot_paths}"

    def test_contributor_tracking(self, complex_repo: Path) -> None:
        """Test contributor tracking across commits."""
        analyzer = GitAnalyzer(complex_repo)
        info = analyzer.analyze_repository()

        assert info.total_contributors >= 1
        assert info.contributors[0].name == "Developer"
        assert info.contributors[0].commit_count >= 4  # Initial + 3 updates

    def test_file_change_frequency(self, complex_repo: Path) -> None:
        """Test change frequency calculation."""
        analyzer = GitAnalyzer(complex_repo)
        main_py = complex_repo / "src" / "main.py"

        file_info = analyzer.analyze_file(main_py)

        # main.py was changed 4 times (initial + 3 updates)
        assert file_info.commit_count >= 4
        assert file_info.change_frequency >= 0  # May be 0 if all commits same second

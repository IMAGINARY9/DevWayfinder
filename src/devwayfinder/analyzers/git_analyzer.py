"""Git history analyzer for code insights.

Provides git-based analysis including:
- Change frequency per file
- Contributor list per file
- Last modified date
- Commit history analysis
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Git import with graceful fallback
try:
    from git import Repo
    from git.exc import GitCommandError, InvalidGitRepositoryError

    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    Repo = None  # type: ignore[misc, assignment]
    InvalidGitRepositoryError = Exception  # type: ignore[misc, assignment]
    GitCommandError = Exception  # type: ignore[misc, assignment]



@dataclass
class ContributorInfo:
    """Information about a contributor."""

    name: str
    email: str
    commit_count: int = 0
    first_commit: datetime | None = None
    last_commit: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "email": self.email,
            "commit_count": self.commit_count,
            "first_commit": self.first_commit.isoformat() if self.first_commit else None,
            "last_commit": self.last_commit.isoformat() if self.last_commit else None,
        }


@dataclass
class FileGitInfo:
    """Git information for a single file."""

    path: Path
    last_modified: datetime | None = None
    first_commit: datetime | None = None
    commit_count: int = 0
    contributors: list[ContributorInfo] = field(default_factory=list)
    change_frequency: float = 0.0  # Changes per month
    is_tracked: bool = True

    @property
    def age_days(self) -> int | None:
        """Age of file in days since first commit."""
        if not self.first_commit:
            return None
        delta = datetime.now(UTC) - self.first_commit
        return delta.days

    @property
    def contributor_count(self) -> int:
        """Number of unique contributors."""
        return len(self.contributors)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": str(self.path),
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "first_commit": self.first_commit.isoformat() if self.first_commit else None,
            "commit_count": self.commit_count,
            "change_frequency": round(self.change_frequency, 3),
            "contributor_count": self.contributor_count,
            "contributors": [c.to_dict() for c in self.contributors],
            "is_tracked": self.is_tracked,
            "age_days": self.age_days,
        }


@dataclass
class RepoGitInfo:
    """Git information for a repository."""

    root: Path
    is_git_repo: bool = False
    default_branch: str | None = None
    total_commits: int = 0
    total_contributors: int = 0
    first_commit: datetime | None = None
    last_commit: datetime | None = None
    contributors: list[ContributorInfo] = field(default_factory=list)
    files: dict[str, FileGitInfo] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def age_days(self) -> int | None:
        """Age of repository in days."""
        if not self.first_commit:
            return None
        delta = datetime.now(UTC) - self.first_commit
        return delta.days

    def get_hotspots(self, top_n: int = 10) -> list[FileGitInfo]:
        """Get files with most changes (hotspots).

        Args:
            top_n: Number of files to return

        Returns:
            Top N files by change frequency
        """
        sorted_files = sorted(
            self.files.values(),
            key=lambda f: f.change_frequency,
            reverse=True,
        )
        return sorted_files[:top_n]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "root": str(self.root),
            "is_git_repo": self.is_git_repo,
            "default_branch": self.default_branch,
            "total_commits": self.total_commits,
            "total_contributors": self.total_contributors,
            "first_commit": self.first_commit.isoformat() if self.first_commit else None,
            "last_commit": self.last_commit.isoformat() if self.last_commit else None,
            "age_days": self.age_days,
            "contributors": [c.to_dict() for c in self.contributors],
            "errors": self.errors,
        }


class GitAnalyzer:
    """Analyzer for git repository history.

    Extracts:
    - Change frequency per file
    - Contributor information
    - Last modified dates
    - Commit history metrics
    """

    def __init__(
        self,
        project_root: Path,
        *,
        max_commits: int | None = None,
        cache_manager: Any | None = None,
    ) -> None:
        """Initialize git analyzer.

        Args:
            project_root: Root directory of the project
            max_commits: Maximum commits to analyze (None = all)
            cache_manager: Optional cache manager for caching results
        """
        self.project_root = Path(project_root).resolve()
        self.max_commits = max_commits
        self.cache_manager = cache_manager
        self._repo: Repo | None = None
        self._initialized = False

    @property
    def is_available(self) -> bool:
        """Check if git analysis is available."""
        if not GIT_AVAILABLE:
            return False
        return self._init_repo()

    def _init_repo(self) -> bool:
        """Initialize the git repository.

        Returns:
            True if successful, False otherwise
        """
        if self._initialized:
            return self._repo is not None

        self._initialized = True

        if not GIT_AVAILABLE:
            logger.warning("GitPython not installed, git analysis disabled")
            return False

        try:
            self._repo = Repo(self.project_root, search_parent_directories=True)
            return True
        except InvalidGitRepositoryError:
            logger.debug("Not a git repository: %s", self.project_root)
            return False
        except Exception as e:
            logger.warning("Failed to initialize git repo: %s", e)
            return False

    def analyze_repository(self) -> RepoGitInfo:
        """Analyze the entire repository.

        Returns:
            RepoGitInfo with repository-level information
        """
        info = RepoGitInfo(root=self.project_root)

        if not self._init_repo() or self._repo is None:
            info.errors.append("Not a git repository or git not available")
            return info

        info.is_git_repo = True

        try:
            # Get default branch
            try:
                info.default_branch = self._repo.active_branch.name
            except TypeError:
                # Detached HEAD state
                info.default_branch = "HEAD"

            # Analyze commits
            self._analyze_commits(info)

        except GitCommandError as e:
            info.errors.append(f"Git error: {e}")
            logger.warning("Git command error: %s", e)
        except Exception as e:
            info.errors.append(f"Analysis error: {e}")
            logger.exception("Error analyzing repository")

        return info

    def _analyze_commits(self, info: RepoGitInfo) -> None:
        """Analyze commit history."""
        if self._repo is None:
            return

        contributor_map: dict[str, ContributorInfo] = {}
        file_commits: dict[str, list[tuple[datetime, str, str]]] = {}

        try:
            commits = list(self._repo.iter_commits(max_count=self.max_commits))
        except Exception as e:
            info.errors.append(f"Failed to iterate commits: {e}")
            return

        info.total_commits = len(commits)

        if not commits:
            return

        # First and last commits
        info.last_commit = datetime.fromtimestamp(
            commits[0].committed_date, tz=UTC
        )
        info.first_commit = datetime.fromtimestamp(
            commits[-1].committed_date, tz=UTC
        )

        for commit in commits:
            commit_date = datetime.fromtimestamp(
                commit.committed_date, tz=UTC
            )
            author_email = commit.author.email or "unknown"
            author_name = commit.author.name or "Unknown"

            # Track contributor
            if author_email not in contributor_map:
                contributor_map[author_email] = ContributorInfo(
                    name=author_name,
                    email=author_email,
                )

            contributor = contributor_map[author_email]
            contributor.commit_count += 1

            if contributor.first_commit is None or commit_date < contributor.first_commit:
                contributor.first_commit = commit_date
            if contributor.last_commit is None or commit_date > contributor.last_commit:
                contributor.last_commit = commit_date

            # Track files changed
            try:
                for diff in commit.diff(commit.parents[0] if commit.parents else None):
                    file_path = diff.b_path or diff.a_path
                    if file_path:
                        if file_path not in file_commits:
                            file_commits[file_path] = []
                        file_commits[file_path].append(
                            (commit_date, author_name, author_email)
                        )
            except Exception:
                # Some commits might not have valid diffs
                pass

        # Convert contributor map to list, sorted by commit count
        info.contributors = sorted(
            contributor_map.values(),
            key=lambda c: c.commit_count,
            reverse=True,
        )
        info.total_contributors = len(info.contributors)

        # Calculate file-level info
        for file_path, commits_data in file_commits.items():
            full_path = self.project_root / file_path
            file_info = FileGitInfo(path=full_path)

            if commits_data:
                # Sort by date
                commits_data.sort(key=lambda x: x[0], reverse=True)

                file_info.last_modified = commits_data[0][0]
                file_info.first_commit = commits_data[-1][0]
                file_info.commit_count = len(commits_data)

                # Calculate change frequency (changes per month)
                if file_info.first_commit and file_info.last_modified:
                    age_days = (file_info.last_modified - file_info.first_commit).days
                    if age_days > 0:
                        months = age_days / 30.0
                        file_info.change_frequency = file_info.commit_count / max(months, 1)

                # Track file contributors
                file_contributors: dict[str, ContributorInfo] = {}
                for _commit_date, name, email in commits_data:
                    if email not in file_contributors:
                        file_contributors[email] = ContributorInfo(
                            name=name, email=email
                        )
                    file_contributors[email].commit_count += 1

                file_info.contributors = sorted(
                    file_contributors.values(),
                    key=lambda c: c.commit_count,
                    reverse=True,
                )

            info.files[str(full_path)] = file_info

    def analyze_file(self, file_path: Path) -> FileGitInfo:
        """Analyze a single file's git history.

        Args:
            file_path: Path to the file

        Returns:
            FileGitInfo with file-level information
        """
        file_path = Path(file_path).resolve()
        info = FileGitInfo(path=file_path)

        if not self._init_repo() or self._repo is None:
            info.is_tracked = False
            return info

        try:
            # Get relative path for git operations
            try:
                rel_path = file_path.relative_to(self.project_root)
            except ValueError:
                # File outside repo
                info.is_tracked = False
                return info

            # Get file commits
            try:
                commits = list(self._repo.iter_commits(
                    paths=str(rel_path),
                    max_count=self.max_commits,
                ))
            except Exception:
                info.is_tracked = False
                return info

            if not commits:
                info.is_tracked = False
                return info

            info.commit_count = len(commits)
            info.last_modified = datetime.fromtimestamp(
                commits[0].committed_date, tz=UTC
            )
            info.first_commit = datetime.fromtimestamp(
                commits[-1].committed_date, tz=UTC
            )

            # Calculate change frequency
            if info.first_commit and info.last_modified:
                age_days = (info.last_modified - info.first_commit).days
                if age_days > 0:
                    months = age_days / 30.0
                    info.change_frequency = info.commit_count / max(months, 1)

            # Track contributors
            contributor_map: dict[str, ContributorInfo] = {}
            for commit in commits:
                email = commit.author.email or "unknown"
                name = commit.author.name or "Unknown"

                if email not in contributor_map:
                    contributor_map[email] = ContributorInfo(name=name, email=email)
                contributor_map[email].commit_count += 1

            info.contributors = sorted(
                contributor_map.values(),
                key=lambda c: c.commit_count,
                reverse=True,
            )

        except Exception as e:
            logger.warning("Error analyzing file %s: %s", file_path, e)
            info.is_tracked = False

        return info

    def get_hotspots(
        self,
        top_n: int = 10,
        *,
        extensions: list[str] | None = None,
    ) -> list[FileGitInfo]:
        """Get files with most changes (hotspots).

        Args:
            top_n: Number of files to return
            extensions: Filter by file extensions

        Returns:
            Top N files by change frequency
        """
        repo_info = self.analyze_repository()

        files = list(repo_info.files.values())

        if extensions:
            files = [
                f for f in files
                if f.path.suffix.lower() in extensions
            ]

        return sorted(
            files,
            key=lambda f: f.change_frequency,
            reverse=True,
        )[:top_n]

    def get_recent_changes(
        self,
        days: int = 30,
        *,
        extensions: list[str] | None = None,
    ) -> list[FileGitInfo]:
        """Get files changed within a time period.

        Args:
            days: Number of days to look back
            extensions: Filter by file extensions

        Returns:
            Files changed within the time period
        """
        repo_info = self.analyze_repository()
        cutoff = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cutoff = cutoff.replace(day=max(1, cutoff.day - days))

        files = [
            f for f in repo_info.files.values()
            if f.last_modified and f.last_modified >= cutoff
        ]

        if extensions:
            files = [
                f for f in files
                if f.path.suffix.lower() in extensions
            ]

        return sorted(
            files,
            key=lambda f: f.last_modified or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )


def is_git_available() -> bool:
    """Check if git functionality is available.

    Returns:
        True if gitpython is installed
    """
    return GIT_AVAILABLE

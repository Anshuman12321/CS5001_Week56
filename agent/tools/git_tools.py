"""
Git operations - getting diffs and changed files.
"""
import subprocess
from typing import Optional


class GitOperations:
    """Wrapper for git commands."""

    @staticmethod
    def run_git(cmd: list[str]) -> str:
        """Execute a git command and return stdout."""
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()

    @staticmethod
    def _get_diff_target(
        base: Optional[str] = None,
        range_spec: Optional[str] = None
    ) -> str:
        """Determine what to diff against."""
        if base:
            return f"{base}...HEAD"
        return range_spec

    def fetch_diff(self, base: Optional[str], range_spec: Optional[str]) -> str:
        """Get the full diff output."""
        target = self._get_diff_target(base, range_spec)
        return self.run_git(["git", "diff", target])

    def fetch_changed_files(
        self, base: Optional[str], range_spec: Optional[str]
    ) -> list[str]:
        """Get list of files that changed."""
        target = self._get_diff_target(base, range_spec)
        output = self.run_git(["git", "diff", "--name-only", target])
        return [f for f in output.splitlines() if f.strip()]

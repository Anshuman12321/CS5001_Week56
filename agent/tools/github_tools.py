"""
GitHub API client for creating/fetching issues and PRs.
"""
import os
import requests
from typing import Optional


class GitHubAPI:
    """Client for GitHub REST API."""

    def __init__(self, repo: Optional[str] = None, token: Optional[str] = None):
        self.repo = repo or os.getenv("GITHUB_REPOSITORY")
        self.token = token or os.getenv("GITHUB_TOKEN")

        if not self.repo:
            raise ValueError("GITHUB_REPOSITORY environment variable not set")
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable not set")

        self.api_root = f"https://api.github.com/repos/{self.repo}"
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def create_issue(self, title: str, body: str) -> dict:
        """Create a new GitHub issue."""
        resp = requests.post(
            f"{self.api_root}/issues",
            headers=self.headers,
            json={"title": title, "body": body},
            timeout=30,
        )
        self._handle_error(resp, "create issue")
        
        data = resp.json()
        return {"number": data["number"], "url": data["html_url"]}

    def create_pull_request(
        self, title: str, body: str, head: str, base: str
    ) -> dict:
        """Create a new pull request."""
        resp = requests.post(
            f"{self.api_root}/pulls",
            headers=self.headers,
            json={"title": title, "body": body, "head": head, "base": base},
            timeout=30,
        )
        self._handle_error(resp, "create PR")
        
        data = resp.json()
        return {"number": data["number"], "url": data["html_url"]}

    def fetch_issue(self, number: int) -> dict:
        """Fetch an existing issue."""
        resp = requests.get(
            f"{self.api_root}/issues/{number}",
            headers=self.headers,
            timeout=30,
        )
        self._handle_error(resp, "fetch issue")
        return resp.json()

    def fetch_pr(self, number: int) -> dict:
        """Fetch an existing pull request."""
        resp = requests.get(
            f"{self.api_root}/pulls/{number}",
            headers=self.headers,
            timeout=30,
        )
        self._handle_error(resp, "fetch PR")
        return resp.json()

    @staticmethod
    def _handle_error(resp: requests.Response, operation: str) -> None:
        """Check response and raise error if failed."""
        if resp.ok:
            return

        try:
            error_data = resp.json()
            msg = error_data.get("message", resp.text)
        except Exception:
            msg = resp.text

        raise RuntimeError(
            f"GitHub API error during {operation}: {resp.status_code} - {msg}"
        )

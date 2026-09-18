"""Pulls real data from the GitHub REST API. No auth required for the
rate limits a prototype needs; pass a token via GITHUB_TOKEN to raise
the ceiling later.

This is the piece DESIGN.md calls a Lambda function (via LocalStack in
the real build). Here it's plain Python -- the infrastructure wrapper
comes after the logic is proven, not before.
"""

import os
from dataclasses import dataclass

import requests

from src.layer1.structural_checks import Commit

API = "https://api.github.com"
MAX_COMMITS = 30  # caps API calls (one per commit for stats) on an unauthenticated budget


@dataclass
class RepoInfo:
    created_at: str
    is_fork: bool
    parent_full_name: str | None
    dependency_files: dict[str, str]  # filename -> raw content, for tech-stack claims


def _headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _get(path: str) -> dict:
    resp = requests.get(f"{API}{path}", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_repo_info(owner: str, repo: str) -> RepoInfo:
    data = _get(f"/repos/{owner}/{repo}")
    parent = data.get("parent", {}).get("full_name") if data.get("fork") else None

    dependency_files: dict[str, str] = {}
    for filename in ("package.json", "requirements.txt", "go.mod", "pom.xml"):
        try:
            file_data = _get(f"/repos/{owner}/{repo}/contents/{filename}")
        except requests.HTTPError:
            continue
        if file_data.get("encoding") == "base64":
            import base64

            dependency_files[filename] = base64.b64decode(file_data["content"]).decode(
                "utf-8", errors="replace"
            )

    return RepoInfo(
        created_at=data["created_at"],
        is_fork=data.get("fork", False),
        parent_full_name=parent,
        dependency_files=dependency_files,
    )


def fetch_commits(owner: str, repo: str, max_commits: int = MAX_COMMITS) -> list[Commit]:
    """Real commits with real line counts.

    The list endpoint doesn't include stats, so each commit needs its
    own request -- that's the actual cost of authorship_share and
    timeline_shape being grounded in truth rather than an estimate.
    Capped at max_commits so a large, unfamiliar repo doesn't burn the
    whole rate-limit budget on one submission.
    """
    shas = [c["sha"] for c in _get(f"/repos/{owner}/{repo}/commits?per_page={max_commits}")]

    commits = []
    for sha in shas:
        detail = _get(f"/repos/{owner}/{repo}/commits/{sha}")
        author_login = (detail.get("author") or {}).get("login")
        commit_author_name = detail["commit"]["author"]["name"]
        date_str = detail["commit"]["author"]["date"]  # ISO 8601, e.g. 2026-01-01T12:00:00Z

        import datetime

        timestamp = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00")).timestamp()

        commits.append(
            Commit(
                author=author_login or commit_author_name,
                timestamp=timestamp,
                lines_changed=detail.get("stats", {}).get("total", 0),
            )
        )
    return commits


def fetch_commit_diff(owner: str, repo: str, sha: str) -> str:
    """The actual diff text for one commit -- what M.1 grounds its
    questions in."""
    resp = requests.get(
        f"{API}/repos/{owner}/{repo}/commits/{sha}",
        headers={**_headers(), "Accept": "application/vnd.github.v3.diff"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.text

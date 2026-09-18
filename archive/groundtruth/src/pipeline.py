"""Orchestration -- what DESIGN.md draws as Step Functions. Plain
Python calling plain functions for now; the LocalStack wiring wraps
around this without changing the logic inside it.
"""

from urllib.parse import urlparse

from src.layer1 import github_fetch
from src.layer1.claim_match import check_claim
from src.layer1.report import Report
from src.layer1.structural_checks import authorship_share, timeline_shape


def _parse_owner_repo(repo_url: str) -> tuple[str, str]:
    path = urlparse(repo_url).path.strip("/")
    owner, repo = path.split("/")[:2]
    return owner, repo.removesuffix(".git")


def run_layer1(candidate_id: str, repo_url: str, claims: list[str], candidate_github_username: str) -> Report:
    """Fetch real evidence once, then check every claim against it.

    This is Layer 1 end to end: GitHub data in, a confidence-scored
    report out. No model involved except inside check_claim, per
    DESIGN.md's split between deterministic checks and judgment.

    candidate_github_username is explicit and required -- the repo's
    URL owner is not a safe stand-in for who's claiming the work.
    An org-owned repo, a shared repo, or someone crediting a
    collaborator's fork would all silently score wrong otherwise.
    """
    owner, repo = _parse_owner_repo(repo_url)

    info = github_fetch.fetch_repo_info(owner, repo)
    commits = github_fetch.fetch_commits(owner, repo)

    share = authorship_share(commits, candidate_github_username)
    shape = timeline_shape(commits)

    results = [
        check_claim(
            claim=claim,
            author_share=share,
            commit_count=len(commits),
            timeline_shape=shape,
            is_fork=info.is_fork,
            parent_full_name=info.parent_full_name,
            dependency_files=info.dependency_files,
        )
        for claim in claims
    ]

    report = Report(candidate_id=candidate_id, repo_url=repo_url, claims=results)
    report.save()
    return report

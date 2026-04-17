from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from .config import settings


GITHUB_API = "https://api.github.com"


def _headers() -> dict[str, str]:
    if not settings.github_token:
        return {"Accept": "application/vnd.github+json"}
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


@dataclass
class WorkflowRun:
    id: int
    name: str
    branch: str
    status: str
    conclusion: str | None
    actor: str
    event: str
    created_at: datetime
    html_url: str
    duration_seconds: int | None
    head_sha: str

    @property
    def badge(self) -> str:
        if self.status in {"queued", "in_progress", "waiting"}:
            return "running"
        if self.conclusion == "success":
            return "success"
        if self.conclusion in {"failure", "timed_out", "startup_failure"}:
            return "failure"
        if self.conclusion == "cancelled":
            return "cancelled"
        return self.conclusion or "unknown"


@dataclass
class Branch:
    name: str
    sha: str
    protected: bool
    last_commit_message: str | None = None
    last_commit_author: str | None = None
    last_commit_date: datetime | None = None


@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    author: str
    head: str
    base: str
    draft: bool
    created_at: datetime
    updated_at: datetime
    html_url: str


class GitHubClient:
    def __init__(self, repo: str | None = None):
        self.repo = repo or settings.github_repo

    @property
    def configured(self) -> bool:
        return bool(settings.github_token)

    async def _get(self, client: httpx.AsyncClient, path: str, **params: Any) -> Any:
        r = await client.get(f"{GITHUB_API}{path}", headers=_headers(), params=params)
        r.raise_for_status()
        return r.json()

    async def workflow_runs(self, limit: int = 15) -> list[WorkflowRun]:
        async with httpx.AsyncClient(timeout=15) as client:
            data = await self._get(
                client, f"/repos/{self.repo}/actions/runs", per_page=limit
            )
        runs: list[WorkflowRun] = []
        for r in data.get("workflow_runs", []):
            created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            updated = datetime.fromisoformat(r["updated_at"].replace("Z", "+00:00"))
            runs.append(
                WorkflowRun(
                    id=r["id"],
                    name=r["name"] or r["display_title"],
                    branch=r["head_branch"] or "",
                    status=r["status"],
                    conclusion=r["conclusion"],
                    actor=(r.get("actor") or {}).get("login", "?"),
                    event=r["event"],
                    created_at=created,
                    html_url=r["html_url"],
                    duration_seconds=(
                        int((updated - created).total_seconds())
                        if r["status"] == "completed"
                        else None
                    ),
                    head_sha=r["head_sha"][:7],
                )
            )
        return runs

    async def branches(self) -> list[Branch]:
        async with httpx.AsyncClient(timeout=15) as client:
            data = await self._get(
                client, f"/repos/{self.repo}/branches", per_page=50
            )
            branches = [
                Branch(name=b["name"], sha=b["commit"]["sha"][:7], protected=b["protected"])
                for b in data
            ]

            for br in branches:
                commit = await self._get(
                    client, f"/repos/{self.repo}/commits/{br.sha}"
                )
                br.last_commit_message = (commit["commit"]["message"].splitlines() or [""])[0][:90]
                br.last_commit_author = commit["commit"]["author"]["name"]
                br.last_commit_date = datetime.fromisoformat(
                    commit["commit"]["author"]["date"].replace("Z", "+00:00")
                )
        return branches

    async def pull_requests(self) -> list[PullRequest]:
        async with httpx.AsyncClient(timeout=15) as client:
            data = await self._get(
                client,
                f"/repos/{self.repo}/pulls",
                state="open",
                per_page=20,
                sort="updated",
                direction="desc",
            )
        prs: list[PullRequest] = []
        for p in data:
            prs.append(
                PullRequest(
                    number=p["number"],
                    title=p["title"],
                    state=p["state"],
                    author=(p["user"] or {}).get("login", "?"),
                    head=p["head"]["ref"],
                    base=p["base"]["ref"],
                    draft=p["draft"],
                    created_at=datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(p["updated_at"].replace("Z", "+00:00")),
                    html_url=p["html_url"],
                )
            )
        return prs

    async def list_workflows(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=15) as client:
            data = await self._get(client, f"/repos/{self.repo}/actions/workflows")
        return [
            {"id": w["id"], "name": w["name"], "path": w["path"], "state": w["state"]}
            for w in data.get("workflows", [])
        ]

    async def dispatch_workflow(self, workflow_id: int, ref: str) -> bool:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{GITHUB_API}/repos/{self.repo}/actions/workflows/{workflow_id}/dispatches",
                headers=_headers(),
                json={"ref": ref},
            )
        return r.status_code == 204

    async def run_jobs(self, run_id: int) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=15) as client:
            data = await self._get(client, f"/repos/{self.repo}/actions/runs/{run_id}/jobs")
        jobs: list[dict[str, Any]] = []
        for j in data.get("jobs", []):
            steps = []
            for s in j.get("steps", []):
                steps.append({
                    "name": s["name"],
                    "status": s["status"],
                    "conclusion": s.get("conclusion"),
                    "number": s["number"],
                })
            jobs.append({
                "id": j["id"],
                "name": j["name"],
                "status": j["status"],
                "conclusion": j.get("conclusion"),
                "started_at": j.get("started_at"),
                "completed_at": j.get("completed_at"),
                "html_url": j["html_url"],
                "steps": steps,
            })
        return jobs

    async def test_results(self, limit: int = 10) -> list[dict[str, Any]]:
        runs = await self.workflow_runs(limit=limit)
        results: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=15) as client:
            for run in runs:
                data = await self._get(
                    client, f"/repos/{self.repo}/actions/runs/{run.id}/jobs"
                )
                jobs_summary = []
                for j in data.get("jobs", []):
                    total_steps = len(j.get("steps", []))
                    passed = sum(
                        1 for s in j.get("steps", []) if s.get("conclusion") == "success"
                    )
                    failed = sum(
                        1 for s in j.get("steps", [])
                        if s.get("conclusion") in ("failure", "timed_out")
                    )
                    jobs_summary.append({
                        "name": j["name"],
                        "conclusion": j.get("conclusion"),
                        "total_steps": total_steps,
                        "passed": passed,
                        "failed": failed,
                        "html_url": j["html_url"],
                    })
                results.append({
                    "run_id": run.id,
                    "commit": run.head_sha,
                    "branch": run.branch,
                    "badge": run.badge,
                    "created_at": run.created_at,
                    "html_url": run.html_url,
                    "jobs": jobs_summary,
                })
        return results

    async def repo_summary(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            repo = await self._get(client, f"/repos/{self.repo}")
        return {
            "full_name": repo["full_name"],
            "default_branch": repo["default_branch"],
            "open_issues": repo["open_issues_count"],
            "visibility": repo["visibility"],
            "html_url": repo["html_url"],
            "updated_at": datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00")),
        }

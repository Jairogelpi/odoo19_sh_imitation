from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx
from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import backups, db_manager, docs_browser
from .config import settings
from .mcp_gateway import gateway
from .github_api import GitHubClient

log = logging.getLogger("control-plane")
logging.basicConfig(level=logging.INFO)

APP_ROOT = Path(__file__).parent
templates = Jinja2Templates(directory=str(APP_ROOT / "templates"))

app = FastAPI(
    title="Odoo19 Control Plane",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.mount("/static", StaticFiles(directory=str(APP_ROOT / "static")), name="static")

gh = GitHubClient()


def _base_context(request: Request, section: str) -> dict:
    return {
        "request": request,
        "section": section,
        "env": settings.stack_env,
        "repo": settings.github_repo,
        "github_configured": gh.configured,
    }


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return RedirectResponse(url="/backups", status_code=status.HTTP_302_FOUND)


@app.get("/backups", response_class=HTMLResponse)
async def backups_view(request: Request, msg: str | None = None, ok: int = 1):
    error: str | None = None
    entries = []
    meta: dict = {}
    try:
        entries, meta = await backups.list_backups()
    except Exception as exc:
        error = f"No se pudo leer pgbackrest info: {exc}"
        log.exception("list backups failed")

    ctx = _base_context(request, "backups")
    ctx.update(
        {
            "entries": entries,
            "meta": meta,
            "allowed_envs": settings.allowed_envs,
            "error": error,
            "flash": msg,
            "flash_ok": bool(ok),
        }
    )
    return templates.TemplateResponse("backups.html", ctx)


@app.post("/backups/restore")
async def backups_restore(
    label: str = Form(...),
    target_env: str = Form(...),
    confirm: str = Form(...),
):
    if target_env not in settings.allowed_envs:
        raise HTTPException(400, f"Entorno no permitido: {target_env}")
    if confirm != target_env:
        return RedirectResponse(
            url=f"/backups?ok=0&msg=La+confirmación+debe+coincidir+exactamente+con+'{target_env}'",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if target_env == settings.stack_env == "dev":
        ok, output = await backups.restore_local(label)
        msg = (
            f"Restore {label} completado en dev"
            if ok
            else f"Restore {label} falló en dev (ver logs)"
        )
        log.info("restore %s result=%s\n%s", label, ok, output)
        return RedirectResponse(
            url=f"/backups?ok={1 if ok else 0}&msg={msg}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    recipe = backups.remote_restore_recipe(target_env, label)
    return HTMLResponse(
        _render_recipe(target_env, label, recipe),
        status_code=200,
    )


def _render_recipe(env: str, label: str, recipe: str) -> str:
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<link rel="stylesheet" href="/static/app.css"></head>'
        '<body class="page"><main class="container"><a href="/backups" class="back">← Volver</a>'
        f'<h1>Restore {label} → {env}</h1>'
        '<p class="muted">Este entorno no se ejecuta desde aquí. Copia y pega el bloque '
        'siguiente en la máquina correspondiente (por SSH).</p>'
        f'<pre class="recipe">{recipe}</pre>'
        '</main></body></html>'
    )


@app.get("/deploys", response_class=HTMLResponse)
async def deploys_view(request: Request):
    runs: list = []
    branches: list = []
    prs: list = []
    repo_meta: dict = {}
    errors: list[str] = []

    if gh.configured:
        async def safe(coro, name):
            try:
                return await coro
            except httpx.HTTPStatusError as exc:
                errors.append(f"{name}: HTTP {exc.response.status_code}")
            except Exception as exc:
                errors.append(f"{name}: {exc}")
            return None

        runs_res, branches_res, prs_res, repo_res, wf_res = await asyncio.gather(
            safe(gh.workflow_runs(), "workflow_runs"),
            safe(gh.branches(), "branches"),
            safe(gh.pull_requests(), "pulls"),
            safe(gh.repo_summary(), "repo"),
            safe(gh.list_workflows(), "workflows"),
        )
        runs = runs_res or []
        branches = branches_res or []
        prs = prs_res or []
        repo_meta = repo_res or {}
        workflows = wf_res or []
    else:
        errors.append(
            "GITHUB_TOKEN no configurado. Añádelo a .env y reinicia control-plane."
        )
        workflows = []

    ctx = _base_context(request, "deploys")
    ctx.update(
        {
            "runs": runs,
            "branches": branches,
            "prs": prs,
            "repo_meta": repo_meta,
            "workflows": workflows,
            "errors": errors,
        }
    )
    return templates.TemplateResponse("deploys.html", ctx)


@app.post("/deploys/dispatch")
async def deploys_dispatch(
    workflow_id: int = Form(...),
    ref: str = Form(...),
):
    if not gh.configured:
        raise HTTPException(400, "GITHUB_TOKEN no configurado")
    ok = await gh.dispatch_workflow(workflow_id, ref)
    msg = (
        f"Workflow disparado en rama {ref}"
        if ok
        else f"No se pudo disparar el workflow (¿rama {ref} existe? ¿workflow acepta dispatch?)"
    )
    return RedirectResponse(
        url=f"/deploys?msg={msg}&ok={1 if ok else 0}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.get("/tests", response_class=HTMLResponse)
async def tests_view(request: Request):
    results: list = []
    errors: list[str] = []

    if gh.configured:
        try:
            results = await gh.test_results(limit=10)
        except Exception as exc:
            errors.append(f"test_results: {exc}")
            log.exception("test results failed")
    else:
        errors.append("GITHUB_TOKEN no configurado.")

    ctx = _base_context(request, "tests")
    ctx.update({"results": results, "errors": errors})
    return templates.TemplateResponse("tests.html", ctx)


@app.get("/db", response_class=HTMLResponse)
async def db_view(request: Request, msg: str | None = None, ok: int = 1):
    error: str | None = None
    databases: list = []
    try:
        databases = await db_manager.list_databases()
    except Exception as exc:
        error = f"No se pudo listar las bases de datos: {exc}"
        log.exception("list databases failed")

    ctx = _base_context(request, "db")
    ctx.update({
        "databases": databases,
        "error": error,
        "flash": msg,
        "flash_ok": bool(ok),
    })
    return templates.TemplateResponse("db.html", ctx)


@app.post("/db/create")
async def db_create(name: str = Form(...)):
    if not name.strip():
        raise HTTPException(400, "Nombre vacío")
    ok, output = await db_manager.create_database(name.strip())
    msg = f"Base de datos '{name}' creada" if ok else f"Error: {output}"
    return RedirectResponse(
        url=f"/db?ok={1 if ok else 0}&msg={msg}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/db/duplicate")
async def db_duplicate(source: str = Form(...), target: str = Form(...)):
    if not target.strip():
        raise HTTPException(400, "Nombre destino vacío")
    ok, output = await db_manager.duplicate_database(source, target.strip())
    msg = f"Base de datos '{source}' duplicada como '{target}'" if ok else f"Error: {output}"
    return RedirectResponse(
        url=f"/db?ok={1 if ok else 0}&msg={msg}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/db/drop")
async def db_drop(name: str = Form(...), confirm: str = Form(...)):
    if confirm != name:
        return RedirectResponse(
            url=f"/db?ok=0&msg=Confirmación+incorrecta",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    ok, output = await db_manager.drop_database(name)
    msg = f"Base de datos '{name}' eliminada" if ok else f"Error: {output}"
    return RedirectResponse(
        url=f"/db?ok={1 if ok else 0}&msg={msg}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.get("/docs", response_class=HTMLResponse)
async def docs_view(request: Request, path: str = ""):
    tree = docs_browser.build_tree()
    rendered_title: str | None = None
    rendered_html: str | None = None
    error: str | None = None

    if path:
        try:
            rendered_title, rendered_html = docs_browser.read_markdown(path)
        except (FileNotFoundError, ValueError) as exc:
            error = str(exc)

    ctx = _base_context(request, "docs")
    ctx.update(
        {
            "tree": tree,
            "active_path": path,
            "rendered_title": rendered_title,
            "rendered_html": rendered_html,
            "error": error,
        }
    )
    return templates.TemplateResponse("docs.html", ctx)


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "env": settings.stack_env}


@app.post("/mcp")
async def mcp(request: Request):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="MCP payload must be a JSON object")

    response = await gateway.handle_jsonrpc(payload)
    if response is None:
        return Response(status_code=204)
    return JSONResponse(response)

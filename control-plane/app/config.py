import os
from dataclasses import dataclass


def _env_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _env_tuple(name: str, default: str) -> tuple[str, ...]:
    raw = os.getenv(name, default)
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    stack_env: str = os.getenv("STACK_ENV", "dev")
    pgbackrest_container: str = os.getenv("PGBACKREST_CONTAINER", "odoo19-pgbackrest-1")
    odoo_container: str = os.getenv("ODOO_CONTAINER", "odoo19-odoo-1")
    db_container: str = os.getenv("DB_CONTAINER", "odoo19-db-1")
    stanza: str = os.getenv("PGBACKREST_STANZA", "odoo")
    github_token: str | None = os.getenv("GITHUB_TOKEN")
    github_repo: str = os.getenv("GITHUB_REPO", "Jairogelpi/odoo19_sh_imitation")
    docs_root: str = os.getenv("DOCS_ROOT", "/app/docs")
    openclaw_addons_custom_root: str = os.getenv("OPENCLAW_ADDONS_CUSTOM_ROOT", "/workspace/addons_custom")
    openclaw_workspace_root: str = os.getenv("OPENCLAW_WORKSPACE_ROOT", "/workspace")
    openclaw_shell_enabled: bool = _env_bool("OPENCLAW_SHELL_ENABLED", "0")
    allowed_envs: tuple[str, ...] = _env_tuple("ALLOWED_ENVS", "dev,staging,prod")
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    openrouter_api_base: str = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.5-air:free")
    openrouter_fallback_model: str = os.getenv("OPENROUTER_FALLBACK_MODEL", "openrouter/elephant-alpha")
    openrouter_reasoning_enabled: bool = _env_bool("OPENROUTER_REASONING_ENABLED", "1")
    openrouter_timeout_seconds: int = int(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "90"))
    openrouter_title: str = os.getenv("OPENROUTER_TITLE", "OpenClaw Control Plane")
    openrouter_referer: str = os.getenv("OPENROUTER_REFERER", "http://localhost:8082")
    openclaw_obsidian_mcp_url: str = os.getenv("OPENCLAW_OBSIDIAN_MCP_URL", "")
    openclaw_obsidian_mcp_token: str = os.getenv("OPENCLAW_OBSIDIAN_MCP_TOKEN", "")
    openclaw_obsidian_mcp_timeout_seconds: int = int(os.getenv("OPENCLAW_OBSIDIAN_MCP_TIMEOUT_SECONDS", "30"))
    openclaw_memory_mcp_url: str = os.getenv("OPENCLAW_MEMORY_MCP_URL", "")
    openclaw_memory_mcp_token: str = os.getenv("OPENCLAW_MEMORY_MCP_TOKEN", "")
    openclaw_memory_mcp_timeout_seconds: int = int(os.getenv("OPENCLAW_MEMORY_MCP_TIMEOUT_SECONDS", "30"))
    openclaw_context7_mcp_url: str = os.getenv("OPENCLAW_CONTEXT7_MCP_URL", "")
    openclaw_context7_mcp_token: str = os.getenv("OPENCLAW_CONTEXT7_MCP_TOKEN", "")
    openclaw_context7_mcp_timeout_seconds: int = int(os.getenv("OPENCLAW_CONTEXT7_MCP_TIMEOUT_SECONDS", "30"))
    openclaw_context7_resolve_tool_name: str = os.getenv("OPENCLAW_CONTEXT7_RESOLVE_TOOL_NAME", "resolve-library-id")
    openclaw_context7_query_tool_name: str = os.getenv("OPENCLAW_CONTEXT7_QUERY_TOOL_NAME", "query-docs")
    openclaw_cif_lookup_mcp_url: str = os.getenv("OPENCLAW_CIF_LOOKUP_MCP_URL", "")
    openclaw_cif_lookup_mcp_token: str = os.getenv("OPENCLAW_CIF_LOOKUP_MCP_TOKEN", "")
    openclaw_cif_lookup_mcp_timeout_seconds: int = int(os.getenv("OPENCLAW_CIF_LOOKUP_MCP_TIMEOUT_SECONDS", "30"))
    openclaw_lead_mining_mcp_url: str = os.getenv("OPENCLAW_LEAD_MINING_MCP_URL", "")
    openclaw_lead_mining_mcp_token: str = os.getenv("OPENCLAW_LEAD_MINING_MCP_TOKEN", "")
    openclaw_lead_mining_mcp_timeout_seconds: int = int(os.getenv("OPENCLAW_LEAD_MINING_MCP_TIMEOUT_SECONDS", "120"))


settings = Settings()

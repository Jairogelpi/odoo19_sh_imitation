#!/usr/bin/env bash
set -euo pipefail

require_env() {
  local var_name="$1"
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required environment variable: ${var_name}" >&2
    exit 1
  fi
}

if [[ $# -lt 3 ]]; then
  echo "Usage: STAGING_ENV_FILE=/path/to/staging.env $0 <db_dump_path> <filestore_archive> <target_database>"
  exit 1
fi

require_env STAGING_ENV_FILE

db_dump_path="$1"
filestore_archive="$2"
target_database="$3"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
neutralize_sql="${script_dir}/staging-neutralize.sql"

if [[ ! "${target_database}" =~ ^[a-zA-Z0-9_]+$ ]]; then
  echo "Target database must contain only letters, numbers, and underscores: ${target_database}" >&2
  exit 1
fi

if [[ ! -f "${STAGING_ENV_FILE}" ]]; then
  echo "Staging env file not found: ${STAGING_ENV_FILE}" >&2
  exit 1
fi

if [[ ! -f "${db_dump_path}" ]]; then
  echo "Database dump not found: ${db_dump_path}" >&2
  exit 1
fi

if [[ ! -f "${filestore_archive}" ]]; then
  echo "Filestore archive not found: ${filestore_archive}" >&2
  exit 1
fi

if [[ ! -f "${neutralize_sql}" ]]; then
  echo "Neutralization SQL not found: ${neutralize_sql}" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${STAGING_ENV_FILE}"
set +a

POSTGRES_USER="${POSTGRES_USER:-odoo}"
STAGING_WEB_BASE_URL="${STAGING_WEB_BASE_URL:-}"
STAGING_MAILPIT_SMTP_HOST="${STAGING_MAILPIT_SMTP_HOST:-mailpit}"
STAGING_MAILPIT_SMTP_PORT="${STAGING_MAILPIT_SMTP_PORT:-1025}"

compose_args=(
  --env-file "${STAGING_ENV_FILE}"
  -f compose.yaml
  -f compose.staging.yaml
)

run_db_psql() {
  local database_name="$1"
  shift
  docker compose "${compose_args[@]}" exec -T db \
    psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${database_name}" "$@"
}

docker compose "${compose_args[@]}" config > /dev/null
docker compose "${compose_args[@]}" up -d db redis mailpit

until docker compose "${compose_args[@]}" exec -T db pg_isready -U "${POSTGRES_USER}" -d postgres > /dev/null 2>&1; do
  echo "Waiting for staging database..."
  sleep 2
done

run_db_psql postgres <<SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '${target_database}'
  AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS "${target_database}";
CREATE DATABASE "${target_database}" OWNER "${POSTGRES_USER}" TEMPLATE template0;
SQL

case "${db_dump_path}" in
  *.sql)
    cat "${db_dump_path}" | docker compose "${compose_args[@]}" exec -T db \
      psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${target_database}"
    ;;
  *.sql.gz)
    gzip -dc "${db_dump_path}" | docker compose "${compose_args[@]}" exec -T db \
      psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${target_database}"
    ;;
  *.dump|*.backup|*.pgdump)
    cat "${db_dump_path}" | docker compose "${compose_args[@]}" exec -T db \
      pg_restore --no-owner --no-privileges -U "${POSTGRES_USER}" -d "${target_database}"
    ;;
  *.dump.gz|*.backup.gz|*.pgdump.gz)
    gzip -dc "${db_dump_path}" | docker compose "${compose_args[@]}" exec -T db \
      pg_restore --no-owner --no-privileges -U "${POSTGRES_USER}" -d "${target_database}"
    ;;
  *)
    echo "Unsupported database dump format: ${db_dump_path}" >&2
    exit 1
    ;;
esac

docker compose "${compose_args[@]}" up -d odoo nginx

docker compose "${compose_args[@]}" exec -T odoo bash -lc "
  set -euo pipefail
  target_path=\"/var/lib/odoo/filestore/${target_database}\"
  rm -rf \"\${target_path}\"
  mkdir -p \"\${target_path}\"
  tar -xzf - -C \"\${target_path}\"
" < "${filestore_archive}"

docker compose "${compose_args[@]}" exec -T db \
  psql \
    -v ON_ERROR_STOP=1 \
    -v staging_web_base_url="${STAGING_WEB_BASE_URL}" \
    -v staging_mailpit_host="${STAGING_MAILPIT_SMTP_HOST}" \
    -v staging_mailpit_port="${STAGING_MAILPIT_SMTP_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${target_database}" < "${neutralize_sql}"

active_crons="$(run_db_psql "${target_database}" -Atc "SELECT COUNT(*) FROM ir_cron WHERE active;")"
active_fetchmail="$(run_db_psql "${target_database}" -Atc "SELECT COUNT(*) FROM fetchmail_server WHERE active;" 2>/dev/null || echo "0")"
active_mail_server="$(run_db_psql "${target_database}" -Atc "SELECT COALESCE(string_agg(smtp_host || ':' || smtp_port::text, ', '), 'none') FROM ir_mail_server WHERE active;" 2>/dev/null || echo "none")"
web_base_url="$(run_db_psql "${target_database}" -Atc "SELECT COALESCE(value, '') FROM ir_config_parameter WHERE key = 'web.base.url';" 2>/dev/null || true)"

cat <<EOF
Staging restore completed.

Smoke checks:
- Login URL should respond through Nginx: ${STAGING_WEB_BASE_URL:-https://staging.example.com}
- Active cron count: ${active_crons}
- Active fetchmail count: ${active_fetchmail}
- Active outbound mail target: ${active_mail_server}
- web.base.url: ${web_base_url}
- Mailpit UI is bound locally on the staging host at: http://127.0.0.1:${STAGING_MAILPIT_UI_PORT:-8025}

Recommended manual checks:
1. Log in to Odoo and confirm the restored database is the expected staging copy.
2. Inspect Settings > Technical > Scheduled Actions and confirm they are inactive.
3. Inspect Settings > Technical > Email > Outgoing Mail Servers and confirm Mailpit is the active target.
4. Only reopen staging access after the above checks pass.
EOF

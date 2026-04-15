#!/usr/bin/env bash
set -euo pipefail

require_env() {
  local var_name="$1"
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required environment variable: ${var_name}" >&2
    exit 1
  fi
}

if [[ $# -lt 1 ]]; then
  echo "Usage: OFFSITE_ENV_FILE=/path/to/prod.env $0 <output_dir>" >&2
  exit 1
fi

require_env OFFSITE_ENV_FILE

output_dir="$1"

if [[ ! -f "${OFFSITE_ENV_FILE}" ]]; then
  echo "Offsite env file not found: ${OFFSITE_ENV_FILE}" >&2
  exit 1
fi

mkdir -p "${output_dir}"

compose_args=(
  --env-file "${OFFSITE_ENV_FILE}"
  -f compose.yaml
  -f compose.prod.yaml
)

docker compose "${compose_args[@]}" config > /dev/null
docker compose "${compose_args[@]}" up -d db odoo > /dev/null

timestamp="$(date +%Y%m%d-%H%M%S)"
archive_path="${output_dir}/filestore-${timestamp}.tar.gz"

docker compose "${compose_args[@]}" exec -T odoo \
  bash -lc 'tar -czf - -C /var/lib/odoo filestore' > "${archive_path}"

echo "${archive_path}"

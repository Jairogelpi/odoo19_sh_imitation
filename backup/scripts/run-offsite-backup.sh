#!/usr/bin/env bash
set -euo pipefail

require_env() {
  local var_name="$1"
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required environment variable: ${var_name}" >&2
    exit 1
  fi
}

require_file() {
  local file_path="$1"
  if [[ ! -f "${file_path}" ]]; then
    echo "Required file not found: ${file_path}" >&2
    exit 1
  fi
}

require_env OFFSITE_ENV_FILE

if [[ ! -f "${OFFSITE_ENV_FILE}" ]]; then
  echo "Offsite env file not found: ${OFFSITE_ENV_FILE}" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${OFFSITE_ENV_FILE}"
set +a

require_env OFFSITE_LOCAL_ARCHIVE_DIR
require_env OFFSITE_S3_BUCKET
require_env OFFSITE_S3_ENDPOINT
require_env OFFSITE_S3_ACCESS_KEY_ID
require_env OFFSITE_S3_SECRET_ACCESS_KEY

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export_pgbackrest_script="${script_dir}/export-pgbackrest-repo.sh"
export_filestore_script="${script_dir}/export-odoo-filestore.sh"
sync_script="${script_dir}/offsite-sync-rclone.sh"

require_file "${export_pgbackrest_script}"
require_file "${export_filestore_script}"
require_file "${sync_script}"

pgbackrest_archive_dir="${OFFSITE_LOCAL_ARCHIVE_DIR%/}/pgbackrest"
filestore_archive_dir="${OFFSITE_LOCAL_ARCHIVE_DIR%/}/filestore"

mkdir -p "${pgbackrest_archive_dir}" "${filestore_archive_dir}"

compose_args=(
  --env-file "${OFFSITE_ENV_FILE}"
  -f compose.yaml
  -f compose.prod.yaml
)

docker compose "${compose_args[@]}" config > /dev/null
docker compose "${compose_args[@]}" up -d db pgbackrest odoo > /dev/null
docker compose "${compose_args[@]}" exec -T pgbackrest /scripts/backup-db.sh

pgbackrest_archive_path="$("${export_pgbackrest_script}" "${pgbackrest_archive_dir}")"
filestore_archive_path="$("${export_filestore_script}" "${filestore_archive_dir}")"

pgbackrest_remote_target="$("${sync_script}" "${pgbackrest_archive_dir}" "pgbackrest")"
filestore_remote_target="$("${sync_script}" "${filestore_archive_dir}" "filestore")"

cat <<EOF
Offsite backup completed.

Artifacts:
- pgBackRest archive: ${pgbackrest_archive_path}
- filestore archive: ${filestore_archive_path}

Remote targets:
- pgBackRest: ${pgbackrest_remote_target}
- filestore: ${filestore_remote_target}
EOF

#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <db_dump_path> <filestore_archive> <staging_filestore_dir>"
  exit 1
fi

db_dump_path="$1"
filestore_archive="$2"
staging_filestore_dir="$3"

cat <<EOF
Restore checklist:
1. Load the database dump into the staging PostgreSQL instance:
   psql -h <staging-db-host> -U <staging-user> -d <staging-db> < "$db_dump_path"
2. Restore the filestore archive:
   mkdir -p "$staging_filestore_dir"
   tar -xzf "$filestore_archive" -C "$staging_filestore_dir"
3. Apply staging-only neutralization before opening access.
4. Restart the staging stack and run smoke checks.
EOF

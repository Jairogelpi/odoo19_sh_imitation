#!/usr/bin/env bash
set -euo pipefail

wal_path="${1:?archive-push requires the WAL path as the first argument}"
stanza="${PGBACKREST_STANZA:-odoo}"
repo_path="${PGBACKREST_REPO1_PATH:-/var/lib/pgbackrest}"
archive_info="${repo_path}/archive/${stanza}/archive.info"
lock_dir="${repo_path}/bootstrap-${stanza}.lock"

ensure_stanza() {
  if [ -f "$archive_info" ]; then
    return
  fi

  mkdir -p "$repo_path"

  while [ ! -f "$archive_info" ]; do
    if mkdir "$lock_dir" 2>/dev/null; then
      trap 'rmdir "$lock_dir" >/dev/null 2>&1 || true' EXIT
      pgbackrest --stanza="$stanza" stanza-create
      rmdir "$lock_dir" >/dev/null 2>&1 || true
      trap - EXIT
    else
      sleep 1
    fi
  done
}

ensure_stanza

exec pgbackrest --stanza="$stanza" archive-push "$wal_path"

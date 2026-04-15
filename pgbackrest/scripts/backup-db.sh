#!/usr/bin/env bash
set -euo pipefail

stanza="${PGBACKREST_STANZA:-odoo}"
type="${PGBACKREST_TYPE:-full}"

pgbackrest --stanza="$stanza" --type="$type" backup

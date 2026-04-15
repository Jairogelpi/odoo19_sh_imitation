#!/usr/bin/env bash
set -euo pipefail

stanza="${PGBACKREST_STANZA:-odoo}"

pgbackrest --stanza="$stanza" stanza-create

#!/usr/bin/env bash
set -euo pipefail

require_env() {
  local var_name="$1"
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required environment variable: ${var_name}" >&2
    exit 1
  fi
}

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <source_dir> <remote_subpath>" >&2
  exit 1
fi

source_dir="$1"
remote_subpath="$2"

if [[ ! -d "${source_dir}" ]]; then
  echo "Source directory not found: ${source_dir}" >&2
  exit 1
fi

require_env OFFSITE_S3_BUCKET
require_env OFFSITE_S3_ENDPOINT
require_env OFFSITE_S3_ACCESS_KEY_ID
require_env OFFSITE_S3_SECRET_ACCESS_KEY

source_dir="$(cd "${source_dir}" && pwd)"
remote_prefix="${OFFSITE_S3_PATH_PREFIX:-}"
target="offsite:${OFFSITE_S3_BUCKET}"

if [[ -n "${remote_prefix}" ]]; then
  target="${target}/${remote_prefix%/}"
fi

if [[ -n "${remote_subpath}" ]]; then
  target="${target}/${remote_subpath#/}"
fi

docker run --rm \
  --mount "type=bind,source=${source_dir},target=/source,readonly" \
  -e RCLONE_CONFIG_OFFSITE_TYPE=s3 \
  -e RCLONE_CONFIG_OFFSITE_PROVIDER="${OFFSITE_S3_PROVIDER:-Other}" \
  -e RCLONE_CONFIG_OFFSITE_ACCESS_KEY_ID="${OFFSITE_S3_ACCESS_KEY_ID}" \
  -e RCLONE_CONFIG_OFFSITE_SECRET_ACCESS_KEY="${OFFSITE_S3_SECRET_ACCESS_KEY}" \
  -e RCLONE_CONFIG_OFFSITE_ENDPOINT="${OFFSITE_S3_ENDPOINT}" \
  -e RCLONE_CONFIG_OFFSITE_REGION="${OFFSITE_S3_REGION:-eu-west-1}" \
  -e RCLONE_CONFIG_OFFSITE_FORCE_PATH_STYLE="${OFFSITE_S3_FORCE_PATH_STYLE:-true}" \
  "${OFFSITE_RCLONE_IMAGE:-rclone/rclone:latest}" \
  sync /source "${target}" --create-empty-src-dirs --fast-list

echo "${target}"

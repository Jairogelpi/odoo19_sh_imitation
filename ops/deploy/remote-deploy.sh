#!/usr/bin/env bash
set -euo pipefail

require_env() {
  local var_name="$1"
  if [ -z "${!var_name:-}" ]; then
    echo "Missing required environment variable: ${var_name}" >&2
    exit 1
  fi
}

for var_name in \
  TARGET_ENV \
  DEPLOY_BRANCH \
  APP_DIR \
  ENV_FILE \
  GHCR_PULL_USERNAME \
  GHCR_PULL_TOKEN \
  ODOO_IMAGE \
  POSTGRES_IMAGE \
  PGBACKREST_IMAGE
do
  require_env "${var_name}"
done

case "${TARGET_ENV}" in
  dev)
    compose_override="compose.dev.yaml"
    ;;
  staging)
    compose_override="compose.staging.yaml"
    ;;
  prod)
    compose_override="compose.prod.yaml"
    ;;
  *)
    echo "Unsupported TARGET_ENV: ${TARGET_ENV}" >&2
    exit 1
    ;;
esac

if [ ! -d "${APP_DIR}/.git" ]; then
  echo "APP_DIR must point to a git checkout: ${APP_DIR}" >&2
  exit 1
fi

if [ ! -f "${ENV_FILE}" ]; then
  echo "ENV_FILE does not exist: ${ENV_FILE}" >&2
  exit 1
fi

cd "${APP_DIR}"

git fetch origin "${DEPLOY_BRANCH}"

if git show-ref --verify --quiet "refs/heads/${DEPLOY_BRANCH}"; then
  git checkout "${DEPLOY_BRANCH}"
else
  git checkout -b "${DEPLOY_BRANCH}" "origin/${DEPLOY_BRANCH}"
fi

git pull --ff-only origin "${DEPLOY_BRANCH}"

echo "${GHCR_PULL_TOKEN}" | docker login ghcr.io -u "${GHCR_PULL_USERNAME}" --password-stdin

export ODOO_IMAGE
export POSTGRES_IMAGE
export PGBACKREST_IMAGE

compose_args=(
  --env-file "${ENV_FILE}"
  -f compose.yaml
  -f "${compose_override}"
)

docker compose "${compose_args[@]}" config > /dev/null
docker compose "${compose_args[@]}" pull
docker compose "${compose_args[@]}" up -d --remove-orphans
docker compose "${compose_args[@]}" ps

#!/bin/sh
set -eu

DOMAIN="${CERTBOT_DOMAIN:?CERTBOT_DOMAIN required}"
EMAIL="${CERTBOT_EMAIL:?CERTBOT_EMAIL required}"
WEBROOT="/var/www/certbot"
RENEWAL_INTERVAL="${CERTBOT_RENEWAL_HOURS:-12}"

mkdir -p "$WEBROOT"

if [ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
  echo "==> Requesting initial certificate for $DOMAIN ..."
  certbot certonly --webroot -w "$WEBROOT" \
    -d "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --non-interactive \
    ${CERTBOT_EXTRA_ARGS:-}
fi

echo "==> Starting renewal loop (every ${RENEWAL_INTERVAL}h) ..."
while true; do
  sleep "${RENEWAL_INTERVAL}h" &
  wait $!
  echo "==> Attempting renewal ..."
  certbot renew --webroot -w "$WEBROOT" --non-interactive
  echo "==> Reloading nginx ..."
  wget -qO /dev/null http://nginx:80/healthz || true
done

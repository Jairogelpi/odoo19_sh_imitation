#!/usr/bin/env bash
set -euo pipefail

# Generate SPF, DKIM, and DMARC DNS TXT records for Odoo mail delivery.
# Usage: ./generate-dns-records.sh <domain> [dkim-selector]
#
# Outputs the DNS records to add to your domain's DNS zone.
# If an Odoo container is running, it extracts the DKIM public key
# from /var/lib/odoo/.dkim/ (if present).

DOMAIN="${1:?Usage: $0 <domain> [dkim-selector]}"
SELECTOR="${2:-odoo}"
ODOO_CONTAINER="${ODOO_CONTAINER:-odoo19-odoo-1}"
DKIM_KEY_PATH="/var/lib/odoo/.dkim/${SELECTOR}.key.pub"
SERVER_IP="${SERVER_IP:-}"

echo "============================================"
echo "  DNS records for: ${DOMAIN}"
echo "============================================"
echo ""

# --- SPF ---
echo "--- SPF Record ---"
echo "Type : TXT"
echo "Name : ${DOMAIN}"
if [ -n "$SERVER_IP" ]; then
  echo "Value: v=spf1 ip4:${SERVER_IP} ~all"
else
  echo "Value: v=spf1 a mx ~all"
  echo "  (set SERVER_IP env var for a specific ip4: directive)"
fi
echo ""

# --- DKIM ---
echo "--- DKIM Record ---"
DKIM_PUB=""
if docker inspect "$ODOO_CONTAINER" > /dev/null 2>&1; then
  DKIM_PUB=$(docker exec "$ODOO_CONTAINER" cat "$DKIM_KEY_PATH" 2>/dev/null || true)
fi

if [ -n "$DKIM_PUB" ]; then
  DKIM_DATA=$(echo "$DKIM_PUB" \
    | grep -v '^-----' \
    | tr -d '\n')
  echo "Type : TXT"
  echo "Name : ${SELECTOR}._domainkey.${DOMAIN}"
  echo "Value: v=DKIM1; k=rsa; p=${DKIM_DATA}"
else
  echo "Type : TXT"
  echo "Name : ${SELECTOR}._domainkey.${DOMAIN}"
  echo "Value: v=DKIM1; k=rsa; p=<YOUR_PUBLIC_KEY_HERE>"
  echo ""
  echo "  To generate a DKIM key pair:"
  echo "    openssl genrsa -out ${SELECTOR}.key 2048"
  echo "    openssl rsa -in ${SELECTOR}.key -pubout -out ${SELECTOR}.key.pub"
  echo "  Then place ${SELECTOR}.key in /var/lib/odoo/.dkim/ and configure"
  echo "  Odoo's outgoing mail server to sign with it."
fi
echo ""

# --- DMARC ---
echo "--- DMARC Record ---"
echo "Type : TXT"
echo "Name : _dmarc.${DOMAIN}"
echo "Value: v=DMARC1; p=none; rua=mailto:dmarc@${DOMAIN}; pct=100"
echo ""
echo "  Once deliverability is confirmed, tighten to p=quarantine or p=reject."
echo ""

# --- Return-Path / Reverse DNS ---
echo "--- Additional Recommendations ---"
echo "1. Set a PTR (reverse DNS) record for your server IP to ${DOMAIN}"
echo "2. In Odoo Settings > Outgoing Mail Servers, set the 'From Filter' to ${DOMAIN}"
echo "3. Consider adding a MTA-STS policy for inbound TLS enforcement"
echo ""
echo "============================================"
echo "  Add these records to your DNS provider."
echo "  Use https://mxtoolbox.com to verify."
echo "============================================"

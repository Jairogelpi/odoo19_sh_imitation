#!/bin/sh

mode="${NGINX_TLS_MODE:-disabled}"
template_root="/opt/odoo-nginx-templates"
target_template="/etc/nginx/templates/default.conf.template"

mkdir -p /etc/nginx/templates

case "$mode" in
  disabled)
    cp "$template_root/odoo.http.conf.template" "$target_template"
    ;;
  required)
    if [ ! -f /etc/nginx/certs/fullchain.pem ]; then
      echo "Missing TLS certificate: /etc/nginx/certs/fullchain.pem" >&2
      exit 1
    fi

    if [ ! -f /etc/nginx/certs/privkey.pem ]; then
      echo "Missing TLS private key: /etc/nginx/certs/privkey.pem" >&2
      exit 1
    fi

    cp "$template_root/odoo.https.conf.template" "$target_template"
    ;;
  acme)
    cp "$template_root/odoo.https-acme.conf.template" "$target_template"
    ;;
  *)
    echo "Unsupported NGINX_TLS_MODE: $mode (use: disabled | required | acme)" >&2
    exit 1
    ;;
esac

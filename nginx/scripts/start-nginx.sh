#!/bin/sh

sh /opt/odoo-nginx-scripts/configure-template.sh
exec /docker-entrypoint.sh nginx -g "daemon off;"

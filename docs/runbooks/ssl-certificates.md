# SSL Certificates

Gestión automática de certificados TLS con Let's Encrypt para staging y producción.

## Modos TLS

La variable `NGINX_TLS_MODE` controla el modo de TLS en nginx:

| Modo       | Descripción                                          |
|------------|------------------------------------------------------|
| `disabled` | Solo HTTP (default en dev)                           |
| `required` | HTTPS con certificados manuales                      |
| `acme`     | HTTPS con auto-provisioning Let's Encrypt (certbot)  |

## Uso con certbot automático

### 1. Configurar variables

En `.env`:

```env
SERVER_NAME=odoo.midominio.com
CERTBOT_EMAIL=admin@midominio.com
CERTBOT_RENEWAL_HOURS=12
```

### 2. Levantar con el overlay SSL

```bash
docker compose -f compose.yaml -f compose.prod.yaml -f compose.ssl.yaml up -d
```

Esto reemplaza el `NGINX_TLS_MODE=required` de `compose.prod.yaml` por `acme` y agrega el sidecar certbot.

### 3. Primer arranque

En el primer arranque, nginx servirá temporalmente en HTTP (puerto 80) para que certbot complete el challenge ACME. Una vez emitido el certificado, nginx empezará a servir HTTPS en el puerto 443.

### 4. Renovación automática

El sidecar certbot verifica la renovación cada 12 horas (configurable con `CERTBOT_RENEWAL_HOURS`). Los certificados Let's Encrypt se renuevan 30 días antes de expirar.

## Uso con certificados manuales

Si prefieres gestionar los certificados manualmente (wildcard, comprados, etc.):

```env
NGINX_TLS_MODE=required
NGINX_TLS_CERTS_DIR=/srv/odoo/tls/prod
```

Coloca `fullchain.pem` y `privkey.pem` en el directorio indicado.

## Testing con staging de Let's Encrypt

Para pruebas sin consumir el rate limit de producción:

```env
CERTBOT_EXTRA_ARGS=--staging
```

## Verificación

```bash
# Verificar certificado activo
openssl s_client -connect odoo.midominio.com:443 -servername odoo.midominio.com < /dev/null 2>/dev/null | openssl x509 -noout -dates

# Logs del certbot
docker compose logs certbot

# Forzar renovación manual
docker compose exec certbot certbot renew --force-renewal
```

## Arquitectura

```
Internet → :80/:443 → nginx
                         ├── /.well-known/acme-challenge/ → certbot-webroot (volume)
                         └── /* → odoo:8069
                       
certbot (sidecar)
  ├── Escribe challenges en certbot-webroot
  └── Escribe certs en certbot-certs → montado en nginx como /etc/nginx/certs
```

## Troubleshooting

- **"Challenge failed"**: Asegúrate de que el puerto 80 está abierto en el firewall y el DNS apunta al servidor.
- **Rate limit**: Let's Encrypt tiene un límite de 5 certificados duplicados por semana. Usa `--staging` para pruebas.
- **nginx no arranca con ACME**: En el primer arranque, nginx necesita que el directorio de certs exista (el volume lo crea automáticamente). Si falla, revisa `docker compose logs nginx`.

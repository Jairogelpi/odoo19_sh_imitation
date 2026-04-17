# Email DNS Records (SPF / DKIM / DMARC)

Configuración de registros DNS para que los correos enviados desde Odoo lleguen a la bandeja de entrada y no a spam.

## Script automático

```bash
ops/mail/generate-dns-records.sh odoo.midominio.com
```

Genera los registros SPF, DKIM y DMARC listos para copiar en tu proveedor DNS.

Variables opcionales:

| Variable         | Descripción                              |
|------------------|------------------------------------------|
| `SERVER_IP`      | IP del servidor (para SPF exacto)        |
| `ODOO_CONTAINER` | Nombre del contenedor Odoo               |

## Registros necesarios

### SPF

Indica qué servidores pueden enviar correo por tu dominio.

```
TXT  @  "v=spf1 a mx ip4:<TU_IP> ~all"
```

### DKIM

Firma criptográfica de los correos salientes.

```
TXT  odoo._domainkey  "v=DKIM1; k=rsa; p=<CLAVE_PUBLICA>"
```

Para generar el par de claves:

```bash
openssl genrsa -out odoo.key 2048
openssl rsa -in odoo.key -pubout -out odoo.key.pub
```

Coloca `odoo.key` en `/var/lib/odoo/.dkim/` dentro del contenedor Odoo.

### DMARC

Define la política cuando SPF o DKIM fallan.

```
TXT  _dmarc  "v=DMARC1; p=none; rua=mailto:dmarc@midominio.com; pct=100"
```

Empieza con `p=none` (monitoreo) y escala a `p=quarantine` o `p=reject` cuando confirmes que todo funciona.

## Verificación

```bash
# SPF
dig TXT midominio.com +short

# DKIM
dig TXT odoo._domainkey.midominio.com +short

# DMARC
dig TXT _dmarc.midominio.com +short

# Test completo
# https://mxtoolbox.com/SuperTool.aspx
```

## Configuración en Odoo

1. **Ajustes > Servidores de correo saliente**: configurar SMTP con tu servidor
2. **From Filter**: establecer a `midominio.com` para evitar spoofing
3. **Alias domain**: configurar en Ajustes > Técnico > Alias de correo

## PTR (Reverse DNS)

Configura un registro PTR en tu proveedor de hosting para que la IP del servidor resuelva a `odoo.midominio.com`. Esto mejora significativamente la reputación del sender.

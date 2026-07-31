# Installation guide

This guide covers the supported development installation and the expected layout for Odoo.sh and existing Odoo 19 deployments.

> [!WARNING]
> Flight Recorder is currently a development foundation. Do not enable it on a production database expecting automatic instrumentation or incident replay; those capabilities are not implemented yet.

## Supported target

- Odoo 19 Community is the primary CI target.
- Odoo 19 Enterprise is structurally compatible but does not yet have dedicated integration coverage.
- Docker Compose is the reproducible development path.
- Odoo.sh and on-premise installations should be validated on a disposable or staging database first.

## Option A — Docker Compose (recommended)

### Requirements

- Git
- Docker Desktop or Docker Engine
- Docker Compose v2 (`docker compose version`)
- Port 8069 available on localhost

### Clone the repository

Linux/macOS:

```bash
git clone https://github.com/Jairogelpi/odoo19_sh_imitation.git
cd odoo19_sh_imitation
cp .env.example .env
```

Windows PowerShell:

```powershell
git clone https://github.com/Jairogelpi/odoo19_sh_imitation.git
Set-Location odoo19_sh_imitation
Copy-Item .env.example .env
```

The included values are local-only development credentials. Change them if the stack will be reachable by anyone else.

### Pull the images

```bash
docker compose pull
```

### Start PostgreSQL

```bash
docker compose up -d --wait db
```

### Create a database and install Flight Recorder

```bash
docker compose run --rm odoo odoo \
  --database flight_recorder \
  --init flight_recorder \
  --stop-after-init \
  --no-http \
  --without-demo all
```

This is the same installation shape exercised by GitHub Actions against the official `odoo:19.0` image.

### Start Odoo

```bash
docker compose up -d
```

Open <http://127.0.0.1:8069> and select the `flight_recorder` database.

### Inspect health and logs

```bash
docker compose ps
docker compose logs -f odoo
```

### Stop or reset

Stop the containers while retaining the database:

```bash
docker compose down
```

Delete the local database and filestore volumes:

```bash
docker compose down --volumes --remove-orphans
```

> [!CAUTION]
> The second command permanently removes this Compose project's local PostgreSQL and Odoo data.

## Option B — Existing Odoo 19 source installation

Copy or symlink `addons/flight_recorder` into a directory included by your Odoo `addons_path`.

Install in a non-production database:

```bash
./odoo-bin \
  --database YOUR_TEST_DATABASE \
  --addons-path /path/to/odoo/addons,/path/to/odoo-flight-recorder/addons \
  --init flight_recorder \
  --stop-after-init \
  --no-http
```

For a later update:

```bash
./odoo-bin \
  --database YOUR_TEST_DATABASE \
  --addons-path /path/to/odoo/addons,/path/to/odoo-flight-recorder/addons \
  --update flight_recorder \
  --stop-after-init \
  --no-http
```

Always review the startup log for errors and confirm the module state in **Apps** before using the database.

## Option C — Odoo.sh

1. Add this project as its own repository or copy `addons/flight_recorder` into the custom-addons repository connected to Odoo.sh.
2. Push the change to a development branch.
3. Wait for the Odoo.sh build to complete.
4. Open the development database with developer mode enabled.
5. Update the Apps list if necessary.
6. Search for **Flight Recorder** and install it.
7. Promote only after the build, module installation, and access-control checks pass on staging.

The addon currently depends only on Odoo's `base` module and has no external Python dependency.

## Verify the installation

From Odoo shell:

```python
module = env["ir.module.module"].search(
    [("name", "=", "flight_recorder")],
    limit=1,
)
assert module.state == "installed", module.state
```

After installation, system administrators can use **Flight Recorder → Traces**
to inspect sale-confirmation evidence and export completed traces. Capture
allowlists are managed under **Flight Recorder → Capture Policies**.

Verify a downloaded archive without Odoo:

```bash
python tools/verify_incident.py path/to/trace.odoo-incident
```

## Developer setup

The framework-independent core and fast tests run without Odoo:

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
python tools/check_repository_hygiene.py
```

## Troubleshooting

### Port 8069 is already in use

Change the host side of the mapping in `compose.yaml`, for example:

```yaml
ports:
  - "127.0.0.1:8070:8069"
```

Then open <http://127.0.0.1:8070>.

### Odoo cannot connect to PostgreSQL

Check the database health and ensure the values in `.env` match the Compose services:

```bash
docker compose ps
docker compose logs db
```

### The addon does not appear in Apps

Confirm that:

- `addons/flight_recorder/__manifest__.py` exists;
- the addon directory is mounted or included in `addons_path`;
- the Apps list has been refreshed;
- the Odoo process can read the directory;
- the server was restarted after changing `addons_path`.

### Installation fails

Run the clean, non-HTTP installation and inspect the full log:

```bash
docker compose run --rm odoo odoo \
  --database flight_recorder_debug \
  --init flight_recorder \
  --stop-after-init \
  --no-http \
  --without-demo all \
  --log-level debug
```

Do not diagnose an installation against a database containing unrelated custom modules until the clean installation has been tested.

## Production note

The supplied Compose stack is deliberately minimal and local-only. It does not provide production TLS, backups, reverse proxying, monitoring, worker sizing, high availability, or hardened secret management. It must not be treated as a production Odoo deployment template.

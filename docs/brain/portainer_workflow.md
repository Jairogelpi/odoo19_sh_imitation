# Portainer Workflow

## Purpose
Step-by-step guide for using Portainer to operate the local stack safely and efficiently.

## When to use Portainer
- confirm which containers are running
- inspect logs after a deploy or restart
- restart one service without touching the rest of the stack
- review ports, mounts, networks, and environment variables
- inspect images and volumes
- check whether Portainer sees the local Docker environment correctly

## First-time setup
1. Open `https://localhost:9443`.
2. Accept the browser certificate warning if it appears.
3. Create the first admin user.
4. Choose the local Docker environment connected through the Docker socket.
5. Confirm Portainer shows the stack containers from this repository.

## Daily workflow
1. Open Portainer.
2. Go to the local environment.
3. Open the Containers list.
4. Verify the expected services are running: `db`, `redis`, `pgbackrest`, `odoo`, `nginx`, `pgadmin`, `obsidian`, `portainer`.
5. Open a container to review logs or inspect its configuration.
6. Use Restart for a simple reload.
7. Use Recreate only when you need the container to pick up image, volume, or environment changes.

## Screen-by-screen usage

### Home / Environment page
- confirm the local environment is connected
- check total container count and obvious error states
- enter the environment before touching individual services

### Containers list
- use this view for the normal day-to-day work
- sort by status if you need to spot stopped or unhealthy containers
- open the service you want to inspect instead of guessing from the terminal output

### Container details
- read the image name and tag first
- check published ports before trying to open a service in the browser
- inspect mounts before changing or removing a container
- check environment variables when a service behaves differently than expected
- use the log tab to confirm the startup sequence or error messages

### Network view
- confirm all repository services are attached to `odoo_net`
- verify a container can reach another service by name
- use this when Odoo cannot reach PostgreSQL or when a reverse proxy cannot reach Odoo

### Volume view
- confirm persistent data is attached to the expected service
- use this before deleting or recreating anything
- check that `portainer-data` exists so the Portainer login and settings survive restarts

### Image view
- confirm which image tag is in use before changing a service
- use it to see whether you are running a local build or a pulled image
- avoid pruning images unless you know they are no longer needed

### Stack view
- only use this if you intentionally want Portainer to manage a separate compose stack
- for this repository, treat the compose files in the repo as the source of truth

## What each Portainer screen is for

### Dashboard
- shows the overall environment health and resource overview
- use it to spot obvious container failures quickly

### Containers
- the main place to inspect running services
- use it to start, stop, restart, recreate, and inspect logs
- open container details to check ports, mounts, networks, and environment variables

### Images
- shows pulled and local images
- use it to confirm which tag is running
- prune old unused images only if you are sure they are not needed

### Volumes
- shows persistent data volumes such as `postgres-data`, `pgbackrest-repo`, `odoo-web-data`, `pgadmin-data`, `obsidian-config`, and `portainer-data`
- use it to verify persistence before deleting anything

### Networks
- shows the shared `odoo_net` bridge network
- use it to confirm containers are attached to the same internal network

### Stacks
- useful if you want Portainer to manage a separate compose deployment
- for this repository, keep the repository compose files as the source of truth

## Common tasks

### Restart one service
1. Open Containers.
2. Select the target container.
3. Choose Restart.
4. Recheck logs after the restart.

### Inspect logs
1. Open the container.
2. Switch to Logs.
3. Read the recent output.
4. If needed, compare with `docker compose logs` from the terminal.

### Confirm a healthy restart
1. Restart the service.
2. Wait for the container to become running again.
3. Check the logs for the normal startup path.
4. Open the service URL in the browser if it has one.

### Check a browser-facing service
1. Open the container details page.
2. Look at the published port.
3. Open the matching URL in the browser.
4. If the browser shows an auth prompt or certificate warning, compare it with the documented behavior in the README.

### Recreate a service
1. Open the container.
2. Choose Recreate.
3. Use this when you changed the image, environment, or mounts.
4. Recheck that the container still exposes the expected port.

### Inspect a volume
1. Open Volumes.
2. Select the relevant volume.
3. Confirm which container uses it.
4. Avoid deleting a volume unless you are sure the data is disposable.

### Confirm network wiring
1. Open Networks.
2. Select `odoo_net`.
3. Confirm the expected containers are attached.
4. Use this when a service cannot resolve another service by name.

## Recommended rules
- use Portainer for visibility and lifecycle actions
- use the repository compose files as the canonical configuration
- keep `portainer-data` persistent so your admin account survives restarts
- keep `/var/run/docker.sock` mounted so Portainer can manage the local Docker daemon
- do not treat Portainer as the only source of truth for the platform

## Good troubleshooting path
1. Check whether the container is running.
2. Check the logs.
3. Check the ports and mounts.
4. Check the network attachments.
5. Restart the service if the issue is transient.
6. Recreate the service if you changed configuration.
7. Return to the repository compose files if you need to make a real platform change.

## What not to do
- do not delete a volume unless the data is disposable
- do not edit the whole platform only in Portainer if the repository compose files also need to change
- do not remove the Docker socket mount if you want Portainer to manage the local Docker daemon
- do not expose internal services like `db`, `redis`, or `pgbackrest` directly on host ports without a strong reason

## Daily maintenance checklist
1. Open Portainer and confirm the environment is connected.
2. Check that the core services are running.
3. Review recent logs for services that were restarted or changed.
4. Confirm the volumes you care about are still present.
5. Confirm the browser-facing services still respond on their documented URLs.
6. Use the repository files when you need to make a permanent change.

## Related notes
- [Portainer](portainer.md)
- [Stack Topology](stack_topology.md)
- [Platform](platform.md)
- [Operations](operations.md)
- [Services](services.md)
- [Daily Checklist](daily_checklist.md)
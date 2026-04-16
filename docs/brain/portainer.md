# Portainer

## Purpose
Portainer is the local container-management UI for this stack.

It is attached to the Docker socket, so it can see and manage the containers created by the compose files in this repository.

## Access
- URL: `https://localhost:9443`
- First launch: create the initial admin user when Portainer prompts for it
- Browser note: a certificate warning on the first visit is expected because the local HTTPS endpoint uses a self-signed certificate

## What Portainer is best for
- Viewing all containers in one place
- Starting, stopping, restarting, and recreating containers
- Reading container logs without using the terminal
- Inspecting environment variables, ports, mounts, networks, and volumes
- Checking whether the stack is healthy after a change
- Managing persistent volumes such as `portainer-data`, `pgadmin-data`, `obsidian-config`, and the database volumes

## Recommended workflow
1. Open Portainer and connect it to the local Docker environment.
2. Use the Containers view to confirm the stack is running.
3. Use a container's details page to inspect logs, ports, mounts, and environment variables.
4. Restart a single container when a service needs a clean reload.
5. Recreate a container when you change image settings, mounts, or environment variables.
6. Use Stacks only if you want Portainer to manage a separate compose deployment from inside the UI.

## Good practices for this stack
- Keep `/var/run/docker.sock` mounted so Portainer can talk to the local Docker daemon.
- Keep `portainer-data` persistent so the admin account and settings survive restarts.
- Use Portainer for inspection and simple lifecycle actions, but keep the repository compose files as the source of truth.
- If you change compose files, regenerate or recreate the stack from the repository rather than editing everything only in the UI.
- Treat Portainer as an operational control plane, not as the only place where configuration lives.

## Common actions
- To restart Portainer itself, restart the `portainer` service from Docker Compose.
- To stop a noisy container, use the container action menu and then inspect logs.
- To confirm the port mapping, check the Ports section on the container detail page.
- To verify persistence, inspect the volume attachments before deleting anything.

## Related notes
- [Platform](platform.md)
- [Operations](operations.md)
- [Services](services.md)
- [Daily Checklist](daily_checklist.md)
- [Platform Bootstrap Status](platform_bootstrap_status.md)
- [Stack Topology](stack_topology.md)
- [Portainer Workflow](portainer_workflow.md)
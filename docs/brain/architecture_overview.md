# Architecture Overview

## Purpose
One-page summary of the platform as a Git-backed, Odoo.sh-style stack.

## Current platform contract

This is the part that stays stable while the future control plane grows around it.

| Layer | Summary |
| --- | --- |
| Edge | Nginx stays in front of Odoo. |
| Core runtime | db, redis, pgBackRest, and Odoo stay private and separate from any control plane. |
| Admin / support | pgAdmin, Portainer, Obsidian, and Mailpit stay local or staging support. |
| Delivery | Git, CI/CD, GHCR, env files, and named volumes are the deployment base. |

For the next system slice, see [Future Control Plane](future_control_plane.md).

## The shape

```mermaid
flowchart TB
  Browser[Access\nBrowser / Human]

  subgraph Edge[Edge]
    Nginx[Nginx]
  end

  subgraph Core[Core Runtime]
    Odoo[Odoo]
    DB[(PostgreSQL)]
    Redis[(Redis)]
    PgBackRest[pgBackRest]
  end

  subgraph Support[Admin / Support]
    PgAdmin[pgAdmin]
    Portainer[Portainer]
    Obsidian[Obsidian]
    Mailpit[Mailpit]
  end

  subgraph Delivery[Delivery / Persistence]
    Git[Git + GitHub Actions]
    GHCR[GHCR Images]
    Volumes[Named Volumes]
  end

  Browser --> Nginx
  Browser --> PgAdmin
  Browser --> Portainer
  Browser --> Obsidian

  Nginx --> Odoo
  Odoo --> DB
  Odoo --> Redis
  PgBackRest --> DB
  PgAdmin --> DB
  Odoo -. staging mail .-> Mailpit

  Git --> GHCR
  GHCR --> Odoo
  GHCR --> DB
  GHCR --> PgBackRest
  Volumes --- DB
  Volumes --- Redis
  Volumes --- PgBackRest
  Volumes --- Odoo
  Volumes --- PgAdmin
  Volumes --- Portainer
  Volumes --- Obsidian

  classDef access fill:#f2f2f2,stroke:#777,color:#111,stroke-width:1px;
  classDef edge fill:#dbeafe,stroke:#2563eb,color:#0f172a,stroke-width:1px;
  classDef core fill:#dcfce7,stroke:#16a34a,color:#052e16,stroke-width:1px;
  classDef support fill:#fef3c7,stroke:#d97706,color:#451a03,stroke-width:1px;
  classDef delivery fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1px;

  class Browser access;
  class Nginx edge;
  class Odoo,DB,Redis,PgBackRest core;
  class PgAdmin,Portainer,Obsidian,Mailpit support;
  class Git,GHCR,Volumes delivery;
```

## Five layers

### Access
- browser entry points for users and admins

### Edge
- `nginx` forwards browser traffic to Odoo

### Core runtime
- `db`, `redis`, `pgbackrest`, `odoo`

### Admin and support
- `pgadmin`, `portainer`, `obsidian`, `mailpit`

### Delivery and persistence
- Git, GitHub Actions, GHCR, env files, named volumes

## One-line mental model

- access comes in through the browser
- edge routes traffic to the app
- core services run privately on `odoo_net`
- admin tools stay local-only
- delivery comes from Git, not from manual UI edits

## Quick read

- browser -> nginx -> odoo -> db/redis
- pgbackrest reads the database and backup volumes
- pgadmin inspects the database
- portainer inspects and manages containers
- obsidian holds the docs vault
- mailpit catches staging mail
- Git + CI/CD + GHCR move the platform forward

## Rules

- do not expose internal services unless there is a real reason
- keep `pgadmin`, `obsidian`, and `portainer` local/admin-only
- keep `mailpit` loopback-only in staging
- use Git and environment files for durable changes
- use Portainer for operations, not as the only source of truth

## Related notes
- [Platform](platform.md)
- [Platform Bootstrap Status](platform_bootstrap_status.md)
- [Stack Topology](stack_topology.md)
- [Delivery](delivery.md)
- [Future Control Plane](future_control_plane.md)
- [Service Map](../architecture/service-map.md)
- [Portainer Workflow](portainer_workflow.md)
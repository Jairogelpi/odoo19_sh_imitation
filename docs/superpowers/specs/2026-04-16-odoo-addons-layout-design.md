# Odoo Addons Layout Design

Date: 2026-04-16
Status: Approved for planning
Scope: Shared addons strategy for `dev`, `staging`, and `prod`

## 1. Objective

Define a clean, Git-driven addons layout for this Odoo platform so custom modules can be developed locally, promoted between environments, and deployed reproducibly through Docker without manual server-side addon management.

## 2. Current Repository Baseline

Current platform behavior before this change:

- the repository mounts `./addons` into the Odoo container
- all extra addons are exposed through a single path: `/mnt/extra-addons`
- all Odoo configs point `addons_path` to `/mnt/extra-addons`
- there is no first-class separation between:
  - custom modules written in-house
  - third-party or shared modules tracked in the repository

This works for simple cases, but it does not clearly express ownership or promotion intent.

## 3. Final Design Decisions

The following decisions were explicitly approved during design:

- keep `addons/` in the repository
- add a second repository folder: `addons_custom/`
- both folders must be mounted inside Docker in all environments
- `addons_custom/` stores in-house modules
- `addons/` stores third-party, OCA, or otherwise non-custom modules that are still promoted through Git
- Odoo must read `addons_custom` first, then `addons`
- no manual editing of modules inside containers or directly on VPS hosts
- Git remains the single source of truth for addon promotion between environments

## 4. Target Runtime Layout

### 4.1 Repository structure

Target addon structure:

```text
addons/
  <third_party_module>/
  <oca_module>/

addons_custom/
  <custom_module>/
```

### 4.2 Container mounts

The Odoo container will mount:

- `./addons` -> `/mnt/extra-addons`
- `./addons_custom` -> `/mnt/custom-addons`

### 4.3 Odoo addon resolution order

All Odoo configs will use:

```ini
addons_path = /mnt/custom-addons,/mnt/extra-addons
```

This gives custom modules precedence over non-custom repository addons when both trees are present.

## 5. Environment Model

The same addon layout applies to every environment:

- `dev`
- `staging`
- `prod`

No environment gets a different addon folder convention. Promotion is done by promoting Git commits, not by copying modules manually between servers.

## 6. Operational Workflow

### 6.1 Custom development

Custom modules are created in:

```text
addons_custom/<module_name>/
```

Typical flow:

1. build or edit the custom module in `dev`
2. test with the local Docker stack
3. commit to Git
4. promote the same code to `staging`
5. promote the same code to `prod`

### 6.2 Third-party modules

Third-party or shared repository addons live in:

```text
addons/<module_name>/
```

They follow the same Git promotion model as custom modules.

### 6.3 Installation and upgrade behavior

Once deployed, Odoo discovers both paths automatically.

Operational expectations:

- new module install: `-i <module_name>`
- installed module update: `-u <module_name>`
- no extra server-side copy step is required if the module is already in the repository and mounted by Docker

## 7. Migration Strategy

This change must be conservative.

Migration rules:

- do not move existing modules automatically
- keep all existing content under `addons/` untouched
- add `addons_custom/` as a new capability
- allow gradual migration of in-house modules from `addons/` to `addons_custom/` later, module by module

This avoids accidental breakage from mass moves during the platform change.

## 8. Files To Update In Implementation

Expected implementation touch points:

- `compose.yaml`
- `config/odoo.conf`
- `config/odoo.staging.conf`
- `config/odoo.prod.conf`
- `config/odoo.conf.example`
- `README.md`
- `docs/runbooks/local-development.md`
- `docs/runbooks/deployment-over-ssh.md`
- `docs/brain/platform_bootstrap_status.md`

Expected new repository artifact:

- `addons_custom/` with a minimal placeholder file so the directory is tracked in Git

## 9. Verification Requirements

Implementation is only complete when all of the following are verified:

- `docker compose -f compose.yaml -f compose.dev.yaml config` still resolves cleanly
- the dev stack still starts successfully
- Odoo still responds normally after the addon path change
- repository docs consistently describe:
  - what belongs in `addons/`
  - what belongs in `addons_custom/`
  - how Git promotion between environments works

## 10. Risks And Guardrails

Primary risks:

- confusion about where a module should live
- accidental duplicate module names across both trees
- future manual server changes drifting away from Git

Guardrails:

- `addons_custom/` is the default location for in-house development
- `addons/` is reserved for non-custom repository addons
- custom path is listed first in `addons_path`
- documentation must clearly forbid editing addons directly inside running containers or VPS hosts

## 11. Outcome

After implementation, this platform will have a clear two-lane addon model:

- `addons/` for third-party and shared repository modules
- `addons_custom/` for in-house modules

Both lanes will be fully Docker-mounted and Git-promoted across `dev`, `staging`, and `prod`, which supports a clean Odoo development and release workflow without manual drift.

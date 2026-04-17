# Odoo Addons Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add first-class support for `addons/` and `addons_custom/` in every Dockerized environment so third-party modules and in-house modules can be promoted through Git between `dev`, `staging`, and `prod`.

**Architecture:** Keep the existing `addons/` lane intact and introduce a second mounted lane, `addons_custom/`, with higher priority in Odoo's `addons_path`. Validate the change with a scaffold contract test first, then update compose/config/runtime docs so all environments share one reproducible addon model.

**Tech Stack:** Docker Compose, Odoo 19, Python `unittest`, Markdown runbooks

---

## File Structure Map

### Existing files to modify

- `compose.yaml`
  - Mount `./addons_custom` into the Odoo container alongside the existing `./addons` mount.
- `config/odoo.conf`
  - Change `addons_path` to read `addons_custom` first and `addons` second.
- `config/odoo.staging.conf`
  - Apply the same dual-path addon contract as local development.
- `config/odoo.prod.conf`
  - Apply the same dual-path addon contract as production.
- `config/odoo.conf.example`
  - Keep the example config aligned with the runtime convention.
- `tests/test_platform_scaffold.py`
  - Add a contract test that protects the new addon layout across compose, config, and docs.
- `README.md`
  - Document what belongs in `addons/` versus `addons_custom/`.
- `docs/runbooks/local-development.md`
  - Document the local module workflow and both mounted addon trees.
- `docs/runbooks/deployment-over-ssh.md`
  - Document that both addon trees are Git-promoted and available on remote deploys.
- `docs/brain/platform_bootstrap_status.md`
  - Record the new addon layout as part of the current platform state.

### New files to create

- `addons_custom/.gitkeep`
  - Track the new custom addon directory in Git until real modules are added.

### Verification targets

- `python -m unittest discover -s tests -p 'test_*.py' -v`
- `docker compose -f compose.yaml -f compose.dev.yaml config`
- `docker compose -f compose.yaml -f compose.staging.yaml config`
- `docker compose -f compose.yaml -f compose.prod.yaml config`
- `docker compose -f compose.yaml -f compose.dev.yaml up -d`
- `powershell -ExecutionPolicy Bypass -File .\ops\health\check-local-stack.ps1`

### Task 1: Lock the new addon layout into tests first

**Files:**
- Modify: `tests/test_platform_scaffold.py`
- Test: `python -m unittest discover -s tests -p 'test_*.py' -v`

- [ ] **Step 1: Add a focused failing contract test for the dual addon layout**

Add a new test method in `tests/test_platform_scaffold.py` that asserts:

```python
self.assertIn("./addons:/mnt/extra-addons", compose)
self.assertIn("./addons_custom:/mnt/custom-addons", compose)
self.assertIn("addons_path = /mnt/custom-addons,/mnt/extra-addons", dev_conf)
self.assertIn("addons_path = /mnt/custom-addons,/mnt/extra-addons", staging_conf)
self.assertIn("addons_path = /mnt/custom-addons,/mnt/extra-addons", prod_conf)
```

- [ ] **Step 2: Run the test to verify it fails for the current layout**

Run:

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: FAIL in the new addon-layout test because `compose.yaml` and the `odoo.conf` files still expose only `/mnt/extra-addons`.

- [ ] **Step 3: Keep the test scoped to platform contract, not to specific module names**

Use only mount-path, `addons_path`, and docs assertions. Do not assert the presence of any real addon module directory yet.

- [ ] **Step 4: Re-run just the scaffold file once the test is in place**

Run:

```powershell
python -m unittest tests.test_platform_scaffold -v
```

Expected: the new test fails, existing tests remain understandable, and the failure message clearly points at the missing dual-addon configuration.

- [ ] **Step 5: Commit the red test once implementation is ready to begin**

```bash
git add tests/test_platform_scaffold.py
git commit -m "test: define dual addons layout contract"
```

### Task 2: Implement the dual mounted addon runtime

**Files:**
- Modify: `compose.yaml`
- Modify: `config/odoo.conf`
- Modify: `config/odoo.staging.conf`
- Modify: `config/odoo.prod.conf`
- Modify: `config/odoo.conf.example`
- Create: `addons_custom/.gitkeep`
- Test: `docker compose -f compose.yaml -f compose.dev.yaml config`
- Test: `docker compose -f compose.yaml -f compose.staging.yaml config`
- Test: `docker compose -f compose.yaml -f compose.prod.yaml config`

- [ ] **Step 1: Update the Odoo service volume mounts**

Modify `compose.yaml` so the Odoo container mounts both trees:

```yaml
    volumes:
      - odoo-web-data:/var/lib/odoo
      - ./config:/etc/odoo:ro
      - ./addons:/mnt/extra-addons
      - ./addons_custom:/mnt/custom-addons
```

- [ ] **Step 2: Update every tracked Odoo config to the new addon resolution order**

Set this exact line in:

- `config/odoo.conf`
- `config/odoo.staging.conf`
- `config/odoo.prod.conf`
- `config/odoo.conf.example`

```ini
addons_path = /mnt/custom-addons,/mnt/extra-addons
```

- [ ] **Step 3: Create the tracked custom addon directory**

Create:

```text
addons_custom/.gitkeep
```

This ensures the repository shape is visible before the first custom module lands.

- [ ] **Step 4: Verify compose resolution in all supported environment shapes**

Run:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml config
docker compose -f compose.yaml -f compose.staging.yaml config
docker compose -f compose.yaml -f compose.prod.yaml config
```

Expected: all three commands exit `0` and render the Odoo service with both addon mounts intact.

- [ ] **Step 5: Re-run the scaffold tests to turn the addon-layout test green**

Run:

```powershell
python -m unittest tests.test_platform_scaffold -v
```

Expected: the new addon-layout contract passes along with the pre-existing platform contract tests.

- [ ] **Step 6: Commit the runtime layout change**

```bash
git add compose.yaml config/odoo.conf config/odoo.staging.conf config/odoo.prod.conf config/odoo.conf.example addons_custom/.gitkeep tests/test_platform_scaffold.py
git commit -m "feat: add dual addons layout for dockerized environments"
```

### Task 3: Align the docs with the new two-lane addon model

**Files:**
- Modify: `README.md`
- Modify: `docs/runbooks/local-development.md`
- Modify: `docs/runbooks/deployment-over-ssh.md`
- Modify: `docs/brain/platform_bootstrap_status.md`
- Test: `python -m unittest discover -s tests -p 'test_*.py' -v`

- [ ] **Step 1: Update the README module section**

Replace the old single-path guidance with short operator guidance that says:

- `addons/` is for third-party, OCA, or shared repository modules
- `addons_custom/` is for in-house modules
- both are mounted inside Docker
- Odoo resolves `addons_custom` first

- [ ] **Step 2: Update the local development runbook**

Add the expected local structure:

```text
addons/
addons_custom/
```

Document that custom development belongs in `addons_custom/<module_name>/`.

- [ ] **Step 3: Update the remote deploy runbook**

Add a short note that the deploy flow promotes both addon trees through Git and that no manual addon copy step should happen on the VPS host.

- [ ] **Step 4: Update the platform brain status doc**

Record the dual-addon layout as part of the platform baseline and note that `addons_custom` now exists specifically for in-house modules.

- [ ] **Step 5: Extend the scaffold test to protect the new docs contract**

Add assertions like:

```python
self.assertIn("addons_custom/", readme)
self.assertIn("addons_custom/", local_runbook)
self.assertIn("addons_custom/", deploy_runbook)
self.assertIn("addons_custom", brain_status)
```

- [ ] **Step 6: Run the full scaffold test suite**

Run:

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: all tests pass, including the new docs assertions for the addon layout.

- [ ] **Step 7: Commit the documentation alignment**

```bash
git add README.md docs/runbooks/local-development.md docs/runbooks/deployment-over-ssh.md docs/brain/platform_bootstrap_status.md tests/test_platform_scaffold.py
git commit -m "docs: align platform docs with dual addons layout"
```

### Task 4: Verify the live dev runtime still behaves correctly

**Files:**
- Test: `compose.yaml`
- Test: `compose.dev.yaml`
- Test: runtime container mounts and Odoo health

- [ ] **Step 1: Boot the dev stack with the new addon layout**

Run:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml up -d
```

Expected: `db`, `redis`, `pgbackrest`, `odoo`, and `nginx` come up without mount or config errors.

- [ ] **Step 2: Verify the Odoo container sees both addon trees**

Run:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml exec -T odoo sh -lc "grep '^addons_path' /etc/odoo/odoo.conf && ls -la /mnt/custom-addons && ls -la /mnt/extra-addons"
```

Expected:

- the config prints `addons_path = /mnt/custom-addons,/mnt/extra-addons`
- `/mnt/custom-addons` exists
- `/mnt/extra-addons` exists

- [ ] **Step 3: Re-run the local health script**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\health\check-local-stack.ps1
```

Expected: the base local stack still passes after the addon path change.

- [ ] **Step 4: Capture final verification with the full test suite**

Run:

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: full green test output with no addon-layout regressions.

- [ ] **Step 5: Commit the final verified slice**

```bash
git add compose.yaml config/ README.md docs/ tests/test_platform_scaffold.py addons_custom/.gitkeep
git commit -m "feat: support addons and addons_custom across environments"
```

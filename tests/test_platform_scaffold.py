import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


class PlatformScaffoldTests(unittest.TestCase):
    def test_dual_addons_layout_is_mounted_and_prioritized(self) -> None:
        compose = read("compose.yaml")
        dev_conf = read("config/odoo.conf")
        staging_conf = read("config/odoo.staging.conf")
        prod_conf = read("config/odoo.prod.conf")
        conf_example = read("config/odoo.conf.example")

        self.assertIn("./addons:/mnt/extra-addons", compose)
        self.assertIn("./addons_custom:/mnt/custom-addons", compose)
        self.assertIn("addons_path = /mnt/custom-addons,/mnt/extra-addons", dev_conf)
        self.assertIn("addons_path = /mnt/custom-addons,/mnt/extra-addons", staging_conf)
        self.assertIn("addons_path = /mnt/custom-addons,/mnt/extra-addons", prod_conf)
        self.assertIn("addons_path = /mnt/custom-addons,/mnt/extra-addons", conf_example)

    def test_dual_addons_layout_is_documented_for_operators(self) -> None:
        readme = read("README.md")
        local_runbook = read("docs/runbooks/local-development.md")
        deploy_runbook = read("docs/runbooks/deployment-over-ssh.md")
        brain_status = read("docs/brain/platform_bootstrap_status.md")

        self.assertIn("`addons/` for third-party, OCA, or shared repository modules", readme)
        self.assertIn("`addons_custom/` for in-house modules", readme)
        self.assertIn("`addons_custom/<module_name>/`", local_runbook)
        self.assertIn("`addons/` and `addons_custom/`", deploy_runbook)
        self.assertIn("no manual addon copy step should happen on the VPS host", deploy_runbook)
        self.assertIn("`addons_custom/` now exists for in-house modules", brain_status)

    def test_environment_state_model_is_documented_in_runbooks_and_brain(self) -> None:
        env_runbook = read("docs/runbooks/environments-and-promotions.md")
        env_brain = read("docs/brain/environment_state_model.md")
        brain_home = read("docs/00_Odoo_Brain.md")
        delivery = read("docs/brain/delivery.md")
        topology = read("docs/brain/stack_topology.md")

        self.assertIn("Git stores code, compose files, docs, and addon trees", env_runbook)
        self.assertIn("Docker named volumes store live runtime state", env_runbook)
        self.assertIn("The current local database in this workspace is `essensi`", env_runbook)
        self.assertIn("A module can exist in Git and still be uninstalled in a database", env_runbook)
        self.assertIn("graph TD", env_brain)
        self.assertIn("Git[Git repo + branches + addons]", env_brain)
        self.assertIn("LocalDB[(Local PostgreSQL", env_brain)
        self.assertIn("StageDB[(Staging PostgreSQL", env_brain)
        self.assertIn("ProdDB[(Production PostgreSQL", env_brain)
        self.assertIn("[Environment State Model](brain/environment_state_model.md)", brain_home)
        self.assertIn("[Environment State Model](environment_state_model.md)", delivery)
        self.assertIn("[Environment State Model](environment_state_model.md)", topology)

    def test_staging_and_prod_require_real_nginx_tls_contract(self) -> None:
        https_template = read("nginx/templates/odoo.https.conf.template")
        nginx_bootstrap = read("nginx/scripts/configure-template.sh")
        compose_prod = read("compose.prod.yaml")
        compose_staging = read("compose.staging.yaml")

        self.assertIn("listen 443 ssl", https_template)
        self.assertIn("return 301 https://$host$request_uri;", https_template)
        self.assertIn("/etc/nginx/certs/fullchain.pem", https_template)
        self.assertIn("/etc/nginx/certs/privkey.pem", https_template)
        self.assertIn("mkdir -p /etc/nginx/templates", nginx_bootstrap)
        self.assertIn('mode="${NGINX_TLS_MODE:-disabled}"', nginx_bootstrap)
        self.assertIn("NGINX_TLS_MODE: required", compose_prod)
        self.assertIn("NGINX_TLS_MODE: required", compose_staging)
        self.assertIn("${NGINX_TLS_CERTS_DIR:-/etc/odoo/tls}:/etc/nginx/certs:ro", compose_prod)
        self.assertIn("${NGINX_TLS_CERTS_DIR:-/etc/odoo/tls}:/etc/nginx/certs:ro", compose_staging)

    def test_base_and_admin_health_checks_are_split(self) -> None:
        base_check = read("ops/health/check-local-stack.ps1")
        admin_check = read("ops/health/check-admin-stack.ps1")
        local_runbook = read("docs/runbooks/local-development.md")
        readme = read("README.md")

        self.assertNotIn("Obsidian auth gate", base_check)
        self.assertNotIn("http://localhost:3000", base_check)
        self.assertIn("Obsidian auth gate", admin_check)
        self.assertIn("check-admin-stack.ps1", local_runbook)
        self.assertIn("check-admin-stack.ps1", readme)

    def test_openrouter_model_is_pinned_for_agentic_tasks(self) -> None:
        compose_admin = read("compose.admin.yaml")
        runbook = read("docs/runbooks/control-plane.md")
        openclaw_readme = read("addons_custom/openclaw/README.md")

        self.assertIn("OPENROUTER_MODEL: ${OPENROUTER_MODEL:-z-ai/glm-4.5-air:free}", compose_admin)
        self.assertIn("OPENROUTER_FALLBACK_MODEL: ${OPENROUTER_FALLBACK_MODEL:-openrouter/elephant-alpha}", compose_admin)
        self.assertIn("OPENROUTER_REASONING_ENABLED: ${OPENROUTER_REASONING_ENABLED:-1}", compose_admin)
        self.assertIn("z-ai/glm-4.5-air:free", runbook)
        self.assertIn("openrouter/elephant-alpha", runbook)
        self.assertIn("z-ai/glm-4.5-air:free", openclaw_readme)
        self.assertIn("openrouter/elephant-alpha", openclaw_readme)

    def test_verification_scope_is_documented_and_checked_in_ci(self) -> None:
        backup_runbook = read("docs/runbooks/backup-and-restore.md")
        deploy_runbook = read("docs/runbooks/deployment-over-ssh.md")
        ci_runbook = read("docs/runbooks/ci-cd-scaffold.md")
        workflow = read(".github/workflows/platform-ci.yml")

        self.assertIn("syntax-checked", backup_runbook)
        self.assertIn("end-to-end restore drill against a real backup set is still pending", backup_runbook)
        self.assertIn("syntax-checked", deploy_runbook)
        self.assertIn("live deploy to a real target host is still pending", deploy_runbook)
        self.assertIn("syntax-checks critical shell and PowerShell scripts", ci_runbook)
        self.assertIn("Shell syntax check critical scripts", workflow)
        self.assertIn("PowerShell syntax check health scripts", workflow)

    def test_lobby_monitors_use_container_reachable_targets(self) -> None:
        services = read("homepage/config/services.yaml")
        http_template = read("nginx/templates/odoo.http.conf.template")
        https_template = read("nginx/templates/odoo.https.conf.template")
        lobby_runbook = read("docs/runbooks/lobby-homepage.md")

        self.assertIn("siteMonitor: http://nginx/healthz", services)
        self.assertIn("siteMonitor: http://odoo:8069/web/login", services)
        self.assertIn("siteMonitor: http://pgadmin:80", services)
        self.assertIn("siteMonitor: http://portainer:9000", services)
        self.assertNotIn("siteMonitor: http://obsidian:3000", services)
        self.assertNotIn("siteMonitor: http://localhost", services)
        self.assertIn("location = /healthz {", http_template)
        self.assertIn("location = /healthz {", https_template)
        self.assertIn("site monitors must use container-reachable addresses", lobby_runbook)

    def test_compose_variants_still_resolve(self) -> None:
        for override in ("compose.dev.yaml", "compose.staging.yaml", "compose.prod.yaml"):
            result = subprocess.run(
                ["docker", "compose", "-f", "compose.yaml", "-f", override, "config"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                result.returncode,
                0,
                msg=f"docker compose config failed for {override}: {result.stderr}",
            )


if __name__ == "__main__":
    unittest.main()

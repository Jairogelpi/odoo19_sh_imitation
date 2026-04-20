import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def read_bytes(rel_path: str) -> bytes:
    return (REPO_ROOT / rel_path).read_bytes()


class PlatformScaffoldTests(unittest.TestCase):
    def test_nginx_shell_scripts_use_lf_line_endings(self) -> None:
        for rel_path in (
            "nginx/scripts/configure-template.sh",
            "nginx/scripts/start-nginx.sh",
        ):
            self.assertNotIn(
                b"\r\n",
                read_bytes(rel_path),
                msg=f"{rel_path} should use LF line endings for Linux containers",
            )

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

    def test_pgbackrest_bootstrap_is_automatic_for_base_stack(self) -> None:
        compose = read("compose.yaml")
        dockerfile = read("postgres_image/Dockerfile")
        readme = read("README.md")
        backup_runbook = read("docs/runbooks/backup-and-restore.md")
        local_runbook = read("docs/runbooks/local-development.md")

        self.assertIn("/usr/local/bin/pgbackrest-archive.sh %p", compose)
        self.assertIn("COPY postgres_image/scripts/pgbackrest-archive.sh /usr/local/bin/pgbackrest-archive.sh", dockerfile)
        self.assertIn("chmod +x /usr/local/bin/pgbackrest-archive.sh", dockerfile)
        self.assertIn("The base stack now auto-bootstraps the local pgBackRest stanza", readme)
        self.assertIn("No manual `stanza-create` step is required for the first local startup anymore.", backup_runbook)
        self.assertIn("If you ever replace the `pgbackrest-repo` volume manually", backup_runbook)
        self.assertIn("Manual `stanza-create` is now only a repair command", local_runbook)

    def test_legacy_compose_stack_uses_a_non_default_filename(self) -> None:
        legacy_compose = REPO_ROOT / "compose.legacy.yaml"
        old_legacy_compose = REPO_ROOT / "docker-compose.yml"
        readme = read("README.md")
        local_runbook = read("docs/runbooks/local-development.md")
        platform_bootstrap = read("docs/architecture/platform-bootstrap.md")

        self.assertTrue(legacy_compose.exists(), msg="compose.legacy.yaml should exist for the documented legacy stack")
        self.assertFalse(old_legacy_compose.exists(), msg="docker-compose.yml should not exist because it conflicts with compose.yaml")
        self.assertIn("`compose.legacy.yaml` remains available as the legacy compatibility stack", readme)
        self.assertIn("docker compose -f compose.legacy.yaml up -d", local_runbook)
        self.assertIn("docker compose -f compose.legacy.yaml up -d", platform_bootstrap)

    def test_admin_observability_services_are_documented(self) -> None:
        compose_admin = read("compose.admin.yaml")
        env_example = read(".env.example")
        env_dev_example = read(".env.dev.example")
        env_staging_example = read(".env.staging.example")
        env_prod_example = read(".env.prod.example")
        readme = read("README.md")
        local_runbook = read("docs/runbooks/local-development.md")
        service_map = read("docs/architecture/service-map.md")
        services_note = read("docs/brain/services.md")
        admin_observability_runbook = read("docs/runbooks/admin-observability-tooling.md")

        for service_name in (
            "obsidian-mcp",
            "memory-mcp",
            "context7-mcp",
            "cif-lookup-mcp",
            "dozzle",
            "code-server",
            "web-terminal",
            "cadvisor",
            "node-exporter",
            "prometheus",
            "grafana",
        ):
            self.assertIn(f"{service_name}:", compose_admin)
            self.assertIn(f"`{service_name}`", service_map)
            self.assertIn(f"`{service_name}`", admin_observability_runbook)

        self.assertIn("[Admin and observability tooling](docs/runbooks/admin-observability-tooling.md)", readme)
        self.assertIn("http://localhost:8082", readme)
        self.assertIn("http://localhost:8083", readme)
        self.assertIn("http://localhost:8084", readme)
        self.assertIn("http://localhost:8085", readme)
        self.assertIn("http://localhost:3002", readme)
        self.assertIn("http://localhost:8083", local_runbook)
        self.assertIn("http://localhost:8084", local_runbook)
        self.assertIn("http://localhost:8085", local_runbook)
        self.assertIn("http://localhost:3002", local_runbook)
        self.assertIn("[Admin and observability tooling](../runbooks/admin-observability-tooling.md)", services_note)

        for env_file in (env_example, env_dev_example, env_staging_example, env_prod_example):
            self.assertIn("OPENCLAW_CIF_LOOKUP_MCP_TOKEN=", env_file)
            self.assertIn("CODE_SERVER_PASSWORD=", env_file)
            self.assertIn("GRAFANA_ADMIN_USER=", env_file)
            self.assertIn("GRAFANA_ADMIN_PASSWORD=", env_file)

    def test_training_tooling_is_documented_in_vault(self) -> None:
        readme = read("README.md")
        training_ready = read("docs/training/TRAINING_READY.md")
        training_real = read("docs/training/01-real-training-integration.md")
        training_hf = read("docs/training/02-huggingface-finetuning.md")
        training_inventory = read("docs/training/03-training-script-inventory.md")
        hf_status = read("docs/brain/hf_training_status_2026-04-18.md")

        self.assertIn("[Training script inventory](docs/training/03-training-script-inventory.md)", readme)
        self.assertIn("scripts/odoo-hf-integration.py", training_inventory)
        self.assertIn("scripts/setup-hf-training.py", training_inventory)
        self.assertIn("scripts/push_openclaw_dataset_to_hf.py", training_inventory)
        self.assertIn("scripts/train_mistral_lora_free_gpu.py", training_inventory)
        self.assertIn("scripts/kaggle_daily_train_runner.py", training_inventory)
        self.assertIn("scripts/write_training_run_report.py", training_inventory)
        self.assertIn("scripts/odoo-hf-integration.py", training_hf)
        self.assertIn("scripts/setup-hf-training.py --export-episodes", training_hf)
        self.assertIn("scripts/odoo-hf-integration.py", training_real)
        self.assertNotIn("To be created", training_ready)
        self.assertNotIn("python3 scripts/setup-hf-training.py  # To be created", training_ready)
        self.assertIn("scripts/odoo-hf-integration.py", hf_status)
        self.assertIn("scripts/push_openclaw_dataset_to_hf.py", hf_status)

    def test_vault_token_operations_are_documented_in_vault(self) -> None:
        readme = read("README.md")
        brain_home = read("docs/00_Odoo_Brain.md")
        services_note = read("docs/brain/services.md")
        cost_effective = read("docs/runbooks/COST-EFFECTIVE-TOKEN-MANAGEMENT.md")
        vault_ops = read("docs/runbooks/vault-token-operations.md")

        self.assertIn("[Vault token operations](docs/runbooks/vault-token-operations.md)", readme)
        self.assertIn("[Vault token operations](runbooks/vault-token-operations.md)", brain_home)
        self.assertIn("[Vault token operations](../runbooks/vault-token-operations.md)", services_note)
        self.assertIn("`vault`: optional self-hosted secrets sidecar", services_note)
        self.assertIn("[Vault token operations](vault-token-operations.md)", cost_effective)

        for artifact in (
            "compose.vault.yaml",
            "vault/config.hcl",
            "setup-vault.sh",
            "generate-tokens.ps1",
            "deploy-with-vault.sh",
            "backup-vault.sh",
            "restore-vault.sh",
            "check-vault-health.sh",
            "emergency-revoke-token.sh",
            "ops/emergency/backup-vault.sh",
            "ops/emergency/check-vault-health.sh",
            "ops/emergency/emergency-revoke-token.sh",
            "secret/openclaw/mcp-tokens-staging",
            "openclaw-vault",
            "openclaw_vault_1",
            "different secret path conventions",
            "tokens_context.ps1",
        ):
            self.assertIn(artifact, vault_ops)

    def test_openclaw_external_skills_are_imported_and_documented(self) -> None:
        self_improvement_skill = read(".github/skills/self-improvement/SKILL.md")
        skill_vetter = read(".github/skills/skill-vetter/SKILL.md")
        self_improvement_meta = read(".github/skills/self-improvement/_meta.json")
        skill_vetter_meta = read(".github/skills/skill-vetter/_meta.json")
        openclaw_note = read("docs/brain/openclaw.md")
        taxonomy_note = read("docs/brain/openclaw_taxonomy.md")
        umbrella_skill = read(".github/skills/openclaw/SKILL.md")

        self.assertIn('name: self-improvement', self_improvement_skill)
        self.assertIn("description: Use when", self_improvement_skill)
        self.assertIn("Do not log secrets", self_improvement_skill)
        self.assertIn("openclaw hooks enable self-improvement", self_improvement_skill)
        self.assertIn("vendored in `.github/skills/self-improvement/`", self_improvement_skill)
        self.assertIn(".github/skills/self-improvement/hooks/openclaw", self_improvement_skill)
        self.assertNotIn("metadata:", self_improvement_skill)
        self.assertNotIn("clawdhub install self-improving-agent", self_improvement_skill)
        self.assertIn('"slug": "self-improving-agent"', self_improvement_meta)

        self.assertIn('name: skill-vetter', skill_vetter)
        self.assertIn("Never install a skill without vetting it first", skill_vetter)
        self.assertIn("Requests credentials/tokens/API keys", skill_vetter)
        self.assertIn('"slug": "skill-vetter"', skill_vetter_meta)

        self.assertIn("self-improvement", openclaw_note)
        self.assertIn("skill-vetter", openclaw_note)
        self.assertIn("opt-in", openclaw_note)
        self.assertIn("vendored in this repository", openclaw_note)
        self.assertIn("Auxiliary process skills", taxonomy_note)
        self.assertIn("self-improvement", taxonomy_note)
        self.assertIn("skill-vetter", taxonomy_note)
        self.assertIn("self-improvement", umbrella_skill)
        self.assertIn("skill-vetter", umbrella_skill)

    def test_openclaw_ontology_skill_is_curated_and_documented(self) -> None:
        ontology_skill = read(".github/skills/ontology/SKILL.md")
        ontology_meta = read(".github/skills/ontology/_meta.json")
        ontology_origin = read(".github/skills/ontology/.clawhub/origin.json")
        ontology_readme = read(".github/skills/ontology/README.md")
        ontology_helper = read(".github/skills/ontology/scripts/ontology.py")
        openclaw_note = read("docs/brain/openclaw.md")
        taxonomy_note = read("docs/brain/openclaw_taxonomy.md")
        umbrella_skill = read(".github/skills/openclaw/SKILL.md")
        ontology_note = read("docs/brain/openclaw_ontology.md")

        self.assertIn("name: ontology", ontology_skill)
        self.assertIn("description: Use when", ontology_skill)
        self.assertIn("memory/ontology/graph.jsonl", ontology_skill)
        self.assertIn("not a source of truth for Odoo records", ontology_skill)
        self.assertIn("does not auto-sync with Odoo, Obsidian, or OpenClaw memory", ontology_skill)
        self.assertIn("vendored helper script is limited to local file operations", ontology_skill)
        self.assertIn('"slug": "ontology"', ontology_meta)
        self.assertIn('"slug": "ontology"', ontology_origin)
        self.assertIn("audited repo-local fork", ontology_readme)
        self.assertTrue((REPO_ROOT / ".github/skills/ontology/scripts").exists())
        self.assertIn("resolve_safe_path", ontology_helper)
        self.assertIn("must stay within workspace root", ontology_helper)
        self.assertNotIn("import subprocess", ontology_helper)
        self.assertNotIn("subprocess.", ontology_helper)
        self.assertNotIn("requests", ontology_helper)
        self.assertNotIn("urllib", ontology_helper)
        self.assertNotIn("socket", ontology_helper)
        self.assertNotIn("os.system", ontology_helper)
        self.assertNotIn("eval(", ontology_helper)
        self.assertNotIn("exec(", ontology_helper)

        self.assertIn("ontology", openclaw_note)
        self.assertIn("not a source of truth", openclaw_note)
        self.assertIn("ontology", taxonomy_note)
        self.assertIn("ontology", umbrella_skill)
        self.assertIn("line-by-line audit", ontology_note)
        self.assertIn("scripts/ontology.py", ontology_note)

    def test_openclaw_ontology_helper_script_enforces_workspace_bounds(self) -> None:
        script_path = REPO_ROOT / ".github/skills/ontology" / "scripts" / "ontology.py"
        self.assertTrue(script_path.exists(), msg="ontology helper script should be vendored locally")

        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp_dir:
            tmp_path = Path(tmp_dir)
            graph_rel = (tmp_path / "graph.jsonl").relative_to(REPO_ROOT).as_posix()

            create_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "create",
                    "--type",
                    "Person",
                    "--props",
                    '{"name":"Alice"}',
                    "--graph",
                    graph_rel,
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(create_result.returncode, 0, msg=create_result.stderr)
            self.assertIn('"type": "Person"', create_result.stdout)

            list_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "list",
                    "--graph",
                    graph_rel,
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(list_result.returncode, 0, msg=list_result.stderr)
            self.assertIn('"Alice"', list_result.stdout)

        traversal_result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "list",
                "--graph",
                "../escape.jsonl",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(traversal_result.returncode, 0)
        self.assertIn(
            "must stay within workspace root",
            f"{traversal_result.stdout}\n{traversal_result.stderr}",
        )

    def test_openclaw_vault_documents_third_party_odoo_skill_stance(self) -> None:
        openclaw_note = read("docs/brain/openclaw.md")
        taxonomy_note = read("docs/brain/openclaw_taxonomy.md")
        odoo_skills_note = read("docs/brain/openclaw_third_party_odoo_skills.md")

        self.assertNotIn("Recommended existing Odoo 19 skill from OpenClaw/ClawHub", openclaw_note)
        self.assertIn("Third-party Odoo skills from ClawHub", openclaw_note)
        self.assertIn(".github/skills/odoo-erp-connector/", openclaw_note)
        self.assertIn("not as the recommended production path", openclaw_note)
        self.assertIn("Current repo-specific vetting notes", openclaw_note)

        self.assertIn("third-party Odoo skills are reference material", taxonomy_note)
        self.assertIn("Third-Party Odoo Skills", taxonomy_note)

        self.assertIn("2026-04-18", odoo_skills_note)
        self.assertIn("Odoo Reporting", odoo_skills_note)
        self.assertIn("Openclaw Skill for Odoo", odoo_skills_note)
        self.assertIn("Clawhub Package Full", odoo_skills_note)
        self.assertIn("Odoo Manager", odoo_skills_note)
        self.assertIn("openclaw.execute_request", odoo_skills_note)
        self.assertIn("reference only", odoo_skills_note)
        self.assertIn("No direct fit", odoo_skills_note)

    def test_vendored_odoo_connector_is_marked_as_reference_only(self) -> None:
        connector_skill = read(".github/skills/odoo-erp-connector/SKILL.md")
        connector_readme = read(".github/skills/odoo-erp-connector/README.md")

        self.assertIn("Repo-local note for `odoo19_sh_imitation`", connector_skill)
        self.assertIn("not the preferred production path", connector_skill)
        self.assertIn("openclaw.execute_request", connector_skill)
        self.assertIn("request-first contract", connector_skill)
        self.assertIn("docs/brain/openclaw_third_party_odoo_skills.md", connector_skill)

        self.assertIn("## Repo-local note", connector_readme)
        self.assertIn("not the preferred production path", connector_readme)
        self.assertIn("policy allowlists", connector_readme)
        self.assertIn("openclaw.execute_request", connector_readme)
        self.assertIn("docs/brain/openclaw_third_party_odoo_skills.md", connector_readme)

    def test_openclaw_advisory_skills_are_curated_and_documented(self) -> None:
        postgres_skill = read(".github/skills/postgresql-advisor/SKILL.md")
        postgres_readme = read(".github/skills/postgresql-advisor/README.md")
        postgres_meta = read(".github/skills/postgresql-advisor/_meta.json")
        postgres_origin = read(".github/skills/postgresql-advisor/.clawhub/origin.json")
        grafana_skill = read(".github/skills/grafana-advisor/SKILL.md")
        grafana_readme = read(".github/skills/grafana-advisor/README.md")
        grafana_meta = read(".github/skills/grafana-advisor/_meta.json")
        grafana_origin = read(".github/skills/grafana-advisor/.clawhub/origin.json")
        advisory_note = read("docs/brain/openclaw_advisory_skills.md")
        openclaw_note = read("docs/brain/openclaw.md")
        taxonomy_note = read("docs/brain/openclaw_taxonomy.md")
        umbrella_skill = read(".github/skills/openclaw/SKILL.md")

        self.assertIn("name: postgresql-advisor", postgres_skill)
        self.assertIn("advisory only", postgres_skill)
        self.assertIn("not the preferred operational path for database execution", postgres_skill)
        self.assertIn("openclaw-db", postgres_skill)
        self.assertIn("psql", postgres_skill)
        self.assertIn("pgcli", postgres_skill)
        self.assertNotIn("npx clawhub install", postgres_skill)
        self.assertIn('"slug": "pg"', postgres_meta)
        self.assertIn('"slug": "pg"', postgres_origin)
        self.assertIn("Curated repo-local adaptation", postgres_readme)

        self.assertIn("name: grafana-advisor", grafana_skill)
        self.assertIn("advisory only", grafana_skill)
        self.assertIn("does not connect to Grafana automatically", grafana_skill)
        self.assertIn("does not write dashboards", grafana_skill)
        self.assertNotIn("npx clawhub install", grafana_skill)
        self.assertIn('"slug": "grafana"', grafana_meta)
        self.assertIn('"slug": "grafana"', grafana_origin)
        self.assertIn("Curated repo-local adaptation", grafana_readme)

        self.assertIn("postgresql-advisor", advisory_note)
        self.assertIn("grafana-advisor", advisory_note)
        self.assertIn("instruction-only", advisory_note)
        self.assertIn("do not replace `openclaw-db`", advisory_note)
        self.assertIn("postgresql-advisor", openclaw_note)
        self.assertIn("grafana-advisor", openclaw_note)
        self.assertIn("advisory-only", openclaw_note)
        self.assertIn("postgresql-advisor", taxonomy_note)
        self.assertIn("grafana-advisor", taxonomy_note)
        self.assertIn("postgresql-advisor", umbrella_skill)
        self.assertIn("grafana-advisor", umbrella_skill)

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

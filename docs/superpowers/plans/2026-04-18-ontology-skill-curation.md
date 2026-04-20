# Ontology Skill Curation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `ontology` as a repo-local, curated OpenClaw skill with source traceability and vault documentation, while keeping it optional and explicitly non-authoritative.

**Architecture:** Vendor a documentation-first fork under `.github/skills/ontology/` instead of importing the upstream executable helpers unchanged. Document it in the OpenClaw vault as an optional local knowledge model that does not auto-sync with Odoo, Obsidian, or persistent memory.

**Tech Stack:** Markdown skills, JSON metadata, Python `unittest` contract tests

---

### Task 1: Lock the contract in tests

**Files:**
- Modify: `tests/test_platform_scaffold.py`
- Test: `tests/test_platform_scaffold.py`

- [ ] **Step 1: Write the failing test**

Add a test that requires:
- `.github/skills/ontology/SKILL.md` to exist with `name: ontology` and `description: Use when`
- repo-local wording that marks it optional and not a source of truth for Odoo/OpenClaw state
- `_meta.json` and `.clawhub/origin.json` to preserve upstream slug traceability
- vault notes and umbrella skill to mention `ontology`
- no vendored `scripts/` directory yet

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_platform_scaffold.PlatformScaffoldTests.test_openclaw_ontology_skill_is_curated_and_documented -v`
Expected: FAIL because the ontology skill is not yet vendored locally.

- [ ] **Step 3: Write minimal implementation**

Create the minimal skill folder and docs needed to satisfy the contract without importing executable helpers.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_platform_scaffold.PlatformScaffoldTests.test_openclaw_ontology_skill_is_curated_and_documented -v`
Expected: PASS

### Task 2: Vendor the curated ontology skill

**Files:**
- Create: `.github/skills/ontology/SKILL.md`
- Create: `.github/skills/ontology/README.md`
- Create: `.github/skills/ontology/_meta.json`
- Create: `.github/skills/ontology/.clawhub/origin.json`

- [ ] **Step 1: Write the failing test**

Covered by Task 1.

- [ ] **Step 2: Run test to verify it fails**

Covered by Task 1.

- [ ] **Step 3: Write minimal implementation**

Create a curated `SKILL.md` that:
- keeps OpenClaw-compatible frontmatter
- references upstream provenance
- states `memory/ontology/graph.jsonl` as optional local storage
- explicitly says it does not auto-sync with Odoo, Obsidian, or OpenClaw memory
- does not vendor upstream executable helpers yet

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_platform_scaffold.PlatformScaffoldTests.test_openclaw_ontology_skill_is_curated_and_documented -v`
Expected: PASS

### Task 3: Document ontology in the OpenClaw vault

**Files:**
- Modify: `docs/brain/openclaw.md`
- Modify: `docs/brain/openclaw_taxonomy.md`
- Modify: `.github/skills/openclaw/SKILL.md`

- [ ] **Step 1: Write the failing test**

Covered by Task 1.

- [ ] **Step 2: Run test to verify it fails**

Covered by Task 1.

- [ ] **Step 3: Write minimal implementation**

Add `ontology` to the local skill map and taxonomy as an auxiliary optional skill, with explicit wording that it is not authoritative system memory.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_platform_scaffold.PlatformScaffoldTests.test_openclaw_ontology_skill_is_curated_and_documented -v`
Expected: PASS

### Task 4: Verify surrounding contracts

**Files:**
- Test: `tests/test_platform_scaffold.py`

- [ ] **Step 1: Run focused verification**

Run: `python -m unittest tests.test_platform_scaffold.PlatformScaffoldTests.test_openclaw_external_skills_are_imported_and_documented tests.test_platform_scaffold.PlatformScaffoldTests.test_openclaw_ontology_skill_is_curated_and_documented -v`
Expected: PASS

- [ ] **Step 2: Run broader scaffold verification**

Run: `python -m unittest tests.test_platform_scaffold -v`
Expected: ontology contract passes; existing unrelated `addons_path` failure may remain and must be reported as residual pre-existing debt.

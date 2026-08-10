# Official Plugin Capability Firewall Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` (recommended for this isolated worktree) or,
> when the user explicitly requests delegated agents,
> `superpowers:subagent-driven-development`. Steps use checkbox (`- [ ]`)
> syntax for tracking.

**Goal:** Enforce official-first analytics delegation through a closed-world,
provenance-locked plugin firewall and one target-scoped Power BI routing gate.

**Architecture:** The integration catalog declares every capability a harness
may activate. Pure manifest observation compares the active Claude plugin or
Codex projection with that declaration and blocks any extra, unsafe, moving, or
unproven capability. Power BI routing consumes that discovery result together
with exact-table readiness and approval evidence, then selects one executor or
returns concrete blockers.

**Tech Stack:** Python 3.13+, frozen dataclasses, pathlib, JSON/YAML, argparse,
pytest, existing Seshat git/readiness helpers.

## Global Constraints

- Do not ratify ADR 0018, unpark F016, launch an MCP server, publish Power BI,
  install a plugin, or change tenant state.
- Do not self-grant or synthesize an approval; read only named-human committed
  approvals.
- Do not use repo-wide readiness or approval as target authorization.
- Do not copy or fork upstream skill guidance into Seshat.
- Unknown or undeclared capability state blocks; no numeric score is permitted.
- Use `apply_patch` for authored file edits and test-first red/green cycles for
  every production behavior change.

---

## File map

- `src/seshat/integrations/catalog.py`: single authored declaration of allowed
  native-plugin and projected-skill capability sets.
- `src/seshat/integrations/plugin_manifest.py`: pure normalization and
  closed-world comparison of locked and active plugin surfaces.
- `src/seshat/integrations/discovery.py`: harness observation and categorical
  discovery verdicts.
- `src/seshat/pbi_mcp/detect.py`: exact-table readiness and approval facts.
- `src/seshat/pbi_mcp/recommend.py`: one fail-closed Power BI route decision.
- `src/seshat/cli/parser_pbi_mcp.py` and
  `src/seshat/cli/commands/pbi_mcp.py`: explicit harness discovery input and
  machine-consistent exit codes.
- `src/seshat/pbir_authoring_gate.py`: shared committed design-approval gate for
  bounded PBIR writers.
- `src/seshat/cli/parser.py` and the four PBIR writer modules: require and apply
  the shared gate before mutation.
- `docs/capabilities/upstream-gaps.yaml`: reviewed temporary Seshat capability
  gaps and retirement triggers.
- `docs/capabilities/capabilities.yaml`, `docs/capabilities/README.md`, and
  public router docs: aligned ownership statements.

---

### Task 1: Declare a closed-world activation contract

**Files:**
- Modify: `src/seshat/integrations/catalog.py`
- Modify: `tests/unit/test_official_skill_discovery.py`

**Interfaces:**
- Produces:
  `McpSurfacePolicy`, `NativePluginPolicy`, and
  `SkillActivation.native_plugins: tuple[NativePluginPolicy, ...]`.
- Preserves: existing `SkillTarget` and `Component` callers.

- [ ] **Step 1: Write catalog validation tests**

Add tests that construct invalid declarations and assert fail-closed errors:

```python
def test_native_plugin_policy_refuses_duplicate_skill_names() -> None:
    with pytest.raises(ValueError, match="duplicate allowed skill"):
        NativePluginPolicy(
            plugin_id="x@y",
            manifest_path=".claude-plugin/marketplace.json",
            manifest_name="x",
            allowed_skills=("same", "same"),
        )


def test_powerbi_catalog_declares_design_and_blocks_broad_plugin() -> None:
    item = component("fabric-skills")
    claude = next(a for a in item.skill_activations if a.harness == CLAUDE_CODE)
    names = {target.name for target in claude.targets}
    assert "powerbi-report-design" in names
    policy = next(
        p for p in claude.native_plugins
        if p.plugin_id == "powerbi-authoring@fabric-collection"
    )
    assert "powerbi-report-planning" in policy.incompatible_capabilities
    assert "powerbi-report-management" in policy.incompatible_capabilities
```

- [ ] **Step 2: Run the new tests and confirm RED**

Run:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_official_skill_discovery.py -q
```

Expected: collection/import failure because the policy types and
`native_plugins` field do not exist.

- [ ] **Step 3: Add the minimal catalog types and invariants**

Implement these frozen records:

```python
@dataclass(frozen=True)
class McpSurfacePolicy:
    name: str
    transport: str
    package: str | None = None
    required_args: tuple[str, ...] = ()
    forbidden_args: tuple[str, ...] = ()
    forbid_moving_coordinate: bool = True


@dataclass(frozen=True)
class NativePluginPolicy:
    plugin_id: str
    manifest_path: str
    manifest_name: str
    allowed_skills: tuple[str, ...]
    allowed_mcp_servers: tuple[McpSurfacePolicy, ...] = ()
    allowed_agents: tuple[str, ...] = ()
    allowed_hooks: tuple[str, ...] = ()
    incompatible_capabilities: tuple[str, ...] = ()
```

Validate contained manifest paths, non-blank identities, unique set members,
supported transports (`stdio`, `http`, `sse`), and non-overlap between allowed
and incompatible capability names.

Declare the complete reviewed dbt and Dagster Claude surfaces. Add
`powerbi-report-design` to the Microsoft required paths and both harness target
sets. Declare the current Power BI Claude bundle incompatible because it also
activates planning/management and a default-write `@latest` modeling MCP.

- [ ] **Step 4: Run the catalog tests and confirm GREEN**

Run the Step 2 command. Expected: all tests pass.

- [ ] **Step 5: Commit the catalog contract**

```powershell
git add src/seshat/integrations/catalog.py tests/unit/test_official_skill_discovery.py
git commit -m "feat: declare closed-world plugin capabilities"
```

---

### Task 2: Normalize and compare complete Claude plugin surfaces

**Files:**
- Create: `src/seshat/integrations/plugin_manifest.py`
- Create: `tests/unit/test_plugin_manifest.py`

**Interfaces:**
- Produces:
  `ObservedPlugin`, `ManifestBlocker`,
  `observe_plugin(install_path: Path, inventory_entry: Mapping[str, object])`,
  `locked_plugin_policy(upstream_root: Path, policy: NativePluginPolicy)`, and
  `compare_plugin(policy, locked, observed) -> tuple[ManifestBlocker, ...]`.
- Consumes: Task 1 policy dataclasses.

- [ ] **Step 1: Write one failing test per adversarial surface**

Use real temporary plugin directories and JSON manifests. Cover:

```python
@pytest.mark.parametrize("extra_kind", ["skill", "mcp", "agent", "hook"])
def test_undeclared_plugin_capability_blocks(tmp_path: Path, extra_kind: str) -> None:
    policy, locked, observed = plugin_fixture(tmp_path, extra_kind=extra_kind)
    blockers = compare_plugin(policy, locked, observed)
    assert any(blocker.kind == f"undeclared-{extra_kind}" for blocker in blockers)


def test_powerbi_mcp_requires_fixed_readonly_coordinate(tmp_path: Path) -> None:
    policy, locked, observed = powerbi_plugin_fixture(
        tmp_path,
        package="@microsoft/powerbi-modeling-mcp@latest",
        args=("--start",),
    )
    details = " ".join(b.detail for b in compare_plugin(policy, locked, observed))
    assert "moving coordinate" in details
    assert "--readonly" in details
```

Also cover plugin version mismatch, missing capability enumeration, explicit
`--readwrite`, `--read-write`, and `--skipconfirmation`.

- [ ] **Step 2: Run the new module tests and confirm RED**

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_plugin_manifest.py -q
```

Expected: import failure because `plugin_manifest` does not exist.

- [ ] **Step 3: Implement pure observation and comparison**

Normalize skills from immediate `skills/*/SKILL.md`, agents from the declared
agent list/directory, hooks from plugin metadata, and MCP servers from the
inventory entry or installed plugin manifest. If a class cannot be enumerated,
record it as unknown and block comparison. Compare exact sets; validate each MCP
against its transport, package coordinate, required arguments, and forbidden
arguments. Never contact a network or execute a plugin.

- [ ] **Step 4: Run module tests and confirm GREEN**

Run the Step 2 command. Expected: all tests pass.

- [ ] **Step 5: Commit the pure firewall**

```powershell
git add src/seshat/integrations/plugin_manifest.py tests/unit/test_plugin_manifest.py
git commit -m "feat: validate complete native plugin surfaces"
```

---

### Task 3: Enforce the firewall in harness discovery

**Files:**
- Modify: `src/seshat/integrations/discovery.py`
- Modify: `src/seshat/integrations/render.py`
- Modify: `tests/unit/test_official_skill_discovery.py`
- Modify: `tests/unit/test_integrations_setup.py`

**Interfaces:**
- Produces:
  `inspect_locked_component(root: Path, component_id: str, harness: str, ...)`
  for target consumers such as the Power BI router.
- Extends `SkillDiscovery.evidence` and `blockers`; does not add a score.

- [ ] **Step 1: Add failing Claude provenance and expansion tests**

Add real fixtures proving:

```python
def test_expected_files_do_not_hide_an_extra_claude_skill(tmp_path: Path) -> None:
    result = discover_claude_fixture(tmp_path, extra_skill="publish-everything")
    assert result.status == CONFLICT
    assert result.discoverable is False


def test_active_plugin_version_must_match_locked_manifest(tmp_path: Path) -> None:
    result = discover_claude_fixture(
        tmp_path, locked_version="1.2.3", active_version="1.2.4"
    )
    assert result.status == STALE
    assert result.discoverable is False
```

Add a Power BI fixture whose expected skill files exist but whose incompatible
planning/management/MCP capabilities keep it blocked.

- [ ] **Step 2: Add a failing Codex extra-projection test**

Create one allowed hard-linked projection and one additional hard-linked skill
from the same locked upstream root. Assert `CONFLICT`, while an unrelated user
skill not linked to that upstream root remains allowed.

- [ ] **Step 3: Run discovery tests and confirm RED**

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_official_skill_discovery.py tests/unit/test_integrations_setup.py -q
```

Expected: the extra capability/version/projection cases are reported
discoverable by the old implementation.

- [ ] **Step 4: Integrate complete manifest comparison**

For Claude, validate the locked checkout marker/ref first, then compare every
native plugin policy using Task 2. Map incompatible or undeclared capabilities
to `CONFLICT`, version/ref mismatch to `STALE`, and unreadable/unknown manifests
to `FAILED`.

For Codex, preserve `samefile` checks for named targets and scan immediate
projected `*/SKILL.md` files for additional hard links into the same locked
upstream checkout. Do not classify unrelated user skills as extras.

Implement `inspect_locked_component` by reading the integration lock, requiring
the component record and install marker, deriving the exact locked ref, and
calling the existing discovery engine for one component/harness.

- [ ] **Step 5: Run discovery tests and confirm GREEN**

Run the Step 3 command. Expected: all tests pass and renderers expose concrete
blockers without absolute paths in committed artifacts.

- [ ] **Step 6: Commit discovery enforcement**

```powershell
git add src/seshat/integrations/discovery.py src/seshat/integrations/render.py tests/unit/test_official_skill_discovery.py tests/unit/test_integrations_setup.py
git commit -m "feat: enforce closed-world skill discovery"
```

---

### Task 4: Make Power BI facts exact-table and approval scoped

**Files:**
- Modify: `src/seshat/pbi_mcp/detect.py`
- Modify: `tests/unit/test_pbi_mcp_detect.py`
- Modify: `tests/unit/test_pbi_mcp_recommend.py`

**Interfaces:**
- Produces:
  `read_table_approval(repo_root, table, stage) -> str`, where the result is
  `recorded | absent` from the exact table record.
- Extends `DetectedFacts` with
  `target_semantic_model_ready`, `dashboard_design_approval`, and
  `official_report_skills: tuple[str, ...]`.
- Retains repo-wide summary fields for display only; recommendation code must not
  authorize from them.

- [ ] **Step 1: Add the cross-table regression tests**

```python
def test_target_facts_do_not_borrow_semantic_or_approval(tmp_path: Path) -> None:
    write_record(tmp_path, "table_a", semantic="pass", dashboard_approval=True)
    write_record(tmp_path, "table_b", semantic="not_started")
    facts = detect_facts(tmp_path, target="table_b", which=lambda _: None)
    assert facts.target_semantic_model_ready == READINESS_NOT_PASS
    assert facts.dashboard_design_approval == APPROVAL_ABSENT


def test_invalid_target_cannot_escape_mapping_directory(tmp_path: Path) -> None:
    assert read_table_approval(tmp_path, "../table_a", "dashboard_ready") == APPROVAL_ABSENT
```

- [ ] **Step 2: Run target-fact tests and confirm RED**

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_pbi_mcp_detect.py tests/unit/test_pbi_mcp_recommend.py -q
```

Expected: missing fields/functions and the current model-edit borrowing case
fails the desired assertion.

- [ ] **Step 3: Implement exact-table readers**

Reuse the path-validation and YAML parsing rules in `read_table_stage`. Read
only an approval row whose `stage` exactly matches, whose `owner`, `at`, and
`note` are non-empty strings, and whose record belongs to the exact table.
Populate target semantic and design-approval facts when `target` is present;
otherwise use fail-closed `missing`/`absent` values.

- [ ] **Step 4: Run target-fact tests and confirm GREEN**

Run the Step 2 command. Expected: all tests pass.

- [ ] **Step 5: Commit target scoping**

```powershell
git add src/seshat/pbi_mcp/detect.py tests/unit/test_pbi_mcp_detect.py tests/unit/test_pbi_mcp_recommend.py
git commit -m "fix: scope Power BI facts to the exact table"
```

---

### Task 5: Connect official discovery to one fail-closed route decision

**Files:**
- Modify: `src/seshat/pbi_mcp/recommend.py`
- Modify: `src/seshat/cli/parser_pbi_mcp.py`
- Modify: `src/seshat/cli/commands/pbi_mcp.py`
- Modify: `tests/unit/test_pbi_mcp_recommend.py`
- Modify: `tests/unit/test_pbi_mcp_cli.py`

**Interfaces:**
- Adds `--harness {claude-code,codex}` to `pbi-mcp doctor`.
- Consumes Task 3 `inspect_locked_component` and Task 4 exact-table facts.
- Preserves the closed intent vocabulary and categorical `Recommendation`.

- [ ] **Step 1: Write failing routing tests**

Cover these exact outcomes:

```python
def test_model_edit_requires_exact_target_and_stays_parked() -> None:
    result = recommend("model-edit", ready_facts(target=None))
    assert result.blocked
    assert "--target" in " ".join(result.missing_prerequisites)


def test_report_authoring_allows_only_compatible_discovered_skill() -> None:
    facts = ready_facts(
        dashboard_design_approval=APPROVAL_RECORDED,
        official_report_skills=("powerbi-report-authoring",),
    )
    result = recommend("report-authoring", facts)
    assert result.blocked is False
    assert result.surface == SURFACE_OFFICIAL_REPORT_AUTHORING


def test_published_query_unknown_prerequisites_block() -> None:
    result = recommend("published-query", ready_facts())
    assert result.blocked
    assert result.missing_prerequisites
```

Add CLI tests proving every recommendation with prerequisites exits 2, and
compatible discovery is passed into the pure recommender. Use an injected or
monkeypatched read-only discovery function; do not install a plugin.

- [ ] **Step 2: Run recommendation/CLI tests and confirm RED**

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_pbi_mcp_recommend.py tests/unit/test_pbi_mcp_cli.py -q
```

Expected: model-edit and published-query currently return unblocked, while
report-authoring is permanently blocked.

- [ ] **Step 3: Implement minimal fail-closed routing**

- Require an exact target for every mutating intent.
- Use `target_semantic_model_ready`, never the repository fold.
- Keep model-edit blocked with an explicit `F016 remains parked` blocker.
- Require exact target semantic pass, named dashboard design approval, and
  compatible discovery for report authoring.
- Require target semantic pass and design approval for formatting.
- Treat unknown remote tenant prerequisites as blockers; do not convert them
  into local readiness facts.
- Make `_run_doctor` return 2 whenever blockers/prerequisites exist.

When `--harness` is supplied, call `inspect_locked_component` for
`fabric-skills`; include only discoverable target names in
`official_report_skills`. Without a harness, discovery is not checked and
official authoring remains blocked.

- [ ] **Step 4: Run recommendation/CLI tests and confirm GREEN**

Run the Step 2 command. Expected: all tests pass.

- [ ] **Step 5: Reproduce the original attack against the repository**

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m seshat.cli pbi-mcp doctor --repo . --intent model-edit --target demo_sample_orders --json
```

Expected: exit 2, exact target reported not ready, and F016 remains parked.

- [ ] **Step 6: Commit the unified route decision**

```powershell
git add src/seshat/pbi_mcp/recommend.py src/seshat/cli/parser_pbi_mcp.py src/seshat/cli/commands/pbi_mcp.py tests/unit/test_pbi_mcp_recommend.py tests/unit/test_pbi_mcp_cli.py
git commit -m "fix: unify Power BI discovery and target gates"
```

---

### Task 6: Gate every bounded PBIR writer before mutation

**Files:**
- Create: `src/seshat/pbir_authoring_gate.py`
- Create: `tests/unit/test_pbir_authoring_gate.py`
- Modify: `src/seshat/cli/parser.py`
- Modify: `src/seshat/pbir_theme_apply.py`
- Modify: `src/seshat/pbir_visual_format.py`
- Modify: `src/seshat/pbir_page_background.py`
- Modify: `src/seshat/pbir_geometry.py`
- Modify: `tests/unit/test_pbir_theme_apply_cli.py`
- Modify: `tests/unit/test_pbir_visual_format_cli.py`
- Modify: `tests/unit/test_pbir_page_background_cli.py`
- Modify: `tests/unit/test_pbir_geometry_cli.py`

**Interfaces:**
- Produces:
  `PbirGateResult(allowed: bool, blockers: tuple[str, ...])` and
  `check_pbir_authoring_gate(repo_root: Path, table: str) -> PbirGateResult`.
- Adds required `--repo ROOT --table TABLE` arguments to all four mutating PBIR
  commands.

- [ ] **Step 1: Write gate tests using a real temporary git repository**

Use the established `tests/unit/test_gitstate.py` subprocess pattern. Commit an
exact table readiness record and verify:

```python
def test_gate_requires_committed_semantic_pass_and_dashboard_approval(repo: Path) -> None:
    write_and_commit_readiness(repo, "orders", semantic="pass", approval=False)
    result = check_pbir_authoring_gate(repo, "orders")
    assert result.allowed is False
    assert any("dashboard_ready approval" in item for item in result.blockers)


def test_dirty_approval_record_is_not_authority(repo: Path) -> None:
    write_and_commit_readiness(repo, "orders", semantic="pass", approval=False)
    add_uncommitted_dashboard_approval(repo, "orders")
    assert check_pbir_authoring_gate(repo, "orders").allowed is False
```

Also test exact-table isolation, invalid table paths, malformed YAML, and the
fully committed passing case.

- [ ] **Step 2: Run the new gate tests and confirm RED**

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_pbir_authoring_gate.py -q
```

Expected: import failure because the gate module does not exist.

- [ ] **Step 3: Implement the committed gate**

Read `mappings/<table>/readiness-status.yaml` through
`gitstate.committed_text`. Require exact target semantic pass and one complete
named-human `dashboard_ready` approval row. Return blockers; never write or
advance readiness.

- [ ] **Step 4: Add CLI mutation-before-gate regression tests**

For each writer, invoke it against a copied fixture with a blocked repo and
assert exit 2 plus byte-identical target files. Update successful cases to pass
`--repo` and `--table` from a committed ready fixture.

- [ ] **Step 5: Run writer CLI tests and confirm RED**

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_pbir_authoring_gate.py tests/unit/test_pbir_theme_apply_cli.py tests/unit/test_pbir_visual_format_cli.py tests/unit/test_pbir_page_background_cli.py tests/unit/test_pbir_geometry_cli.py -q
```

Expected: old parsers reject the new arguments or mutate without consulting the
gate.

- [ ] **Step 6: Wire the gate before every writer call**

Add common parser arguments through one helper. In each CLI entrypoint, call the
gate before reading mutation payloads or writing files; print each blocker to
stderr and return 2. Keep direct pure writer functions unchanged so their
allow-list unit tests remain focused on file mechanics.

- [ ] **Step 7: Run writer tests and confirm GREEN**

Run the Step 5 command. Expected: all tests pass.

- [ ] **Step 8: Commit the PBIR execution gate**

```powershell
git add src/seshat/pbir_authoring_gate.py src/seshat/cli/parser.py src/seshat/pbir_theme_apply.py src/seshat/pbir_visual_format.py src/seshat/pbir_page_background.py src/seshat/pbir_geometry.py tests/unit/test_pbir_authoring_gate.py tests/unit/test_pbir_theme_apply_cli.py tests/unit/test_pbir_visual_format_cli.py tests/unit/test_pbir_page_background_cli.py tests/unit/test_pbir_geometry_cli.py
git commit -m "fix: gate bounded PBIR mutations on approved design"
```

---

### Task 7: Record official ownership and temporary capability gaps

**Files:**
- Create: `docs/capabilities/upstream-gaps.yaml`
- Modify: `docs/capabilities/capabilities.yaml`
- Modify: `docs/capabilities/README.md`
- Modify: `distribution/bundle-templates/shared/skills/powerbi-workflows/SKILL.md`
- Modify: `distribution/bundle-templates/shared/skills/pbi-mcp-doctor/SKILL.md`
- Modify: `docs/install/fabric-powerbi-integrations.md`
- Modify: `tests/contract/test_powerbi_ownership_routing.py`
- Create: `tests/contract/test_upstream_capability_gaps.py`

**Interfaces:**
- Produces a declarative gap record with fields:
  `id`, `seshat_capability`, `upstream_checked`, `checked_at`, `gap`, `scope`,
  `review_by`, and `retire_when`.
- Does not create a new CLI or readiness rule.

- [ ] **Step 1: Write failing ownership and gap-contract tests**

Require official capability entries for Microsoft report design and authoring;
require planning/management to be deferred/incompatible; require every locally
owned overlapping Power BI writer to cite one non-expired gap record. Add the
stale README assertions that would have caught the audit finding:

```python
def test_capability_readme_names_current_official_execution() -> None:
    text = (ROOT / "docs/capabilities/README.md").read_text(encoding="utf-8")
    assert "does not invoke an official executor today" not in text
    assert "powerbi-report-design" in text
    assert "powerbi-report-authoring" in text
```

- [ ] **Step 2: Run contract tests and confirm RED**

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest tests/contract/test_powerbi_ownership_routing.py tests/contract/test_upstream_capability_gaps.py -q
```

Expected: missing design capability/gap registry and stale README failures.

- [ ] **Step 3: Align manifest, router, and docs**

Record Microsoft report design and authoring as official owners. Explain that
Seshat owns readiness/business semantics and consumes official output. Mark the
full Claude Power BI plugin incompatible until its complete MCP and skill set is
safe. Record the bounded PBIR writer gap as temporary deterministic,
binding-preserving, allow-listed patching, with review date `2026-11-10` and
retirement when an approved official surface supplies the same constrained
operation under the firewall.

Update every command example for the four PBIR writers with `--repo` and
`--table`. Remove the stale Phase 3 prose.

- [ ] **Step 4: Run ownership/gap tests and confirm GREEN**

Run the Step 2 command. Expected: all tests pass.

- [ ] **Step 5: Run deterministic bundle generation/check**

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe scripts/export_agent_bundles.py
.\.venv\Scripts\python.exe scripts/export_agent_bundles.py --check
```

Expected: the canonical exporter regenerates only the Claude and Codex bundle
roots, then the check prints `PASS: generated Claude and Codex bundles match
reviewed inputs` and exits 0.

- [ ] **Step 6: Commit ownership and gap records**

```powershell
git add docs/capabilities/upstream-gaps.yaml docs/capabilities/capabilities.yaml docs/capabilities/README.md distribution/bundle-templates/shared/skills/powerbi-workflows/SKILL.md distribution/bundle-templates/shared/skills/pbi-mcp-doctor/SKILL.md docs/install/fabric-powerbi-integrations.md tests/contract/test_powerbi_ownership_routing.py tests/contract/test_upstream_capability_gaps.py integrations/claude-code/seshat-bi integrations/codex/seshat-bi
git commit -m "docs: align official Power BI ownership and gaps"
```

---

### Task 8: Run focused and repository-wide verification

**Files:**
- Modify only files required by failures caused by Tasks 1-7.

**Interfaces:**
- Consumes all prior task interfaces.
- Produces fresh verification evidence; no readiness or approval artifacts.

- [ ] **Step 1: Run focused security and ownership tests**

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_plugin_manifest.py tests/unit/test_official_skill_discovery.py tests/unit/test_integrations_setup.py tests/unit/test_pbi_mcp_detect.py tests/unit/test_pbi_mcp_recommend.py tests/unit/test_pbi_mcp_cli.py tests/unit/test_pbir_authoring_gate.py tests/unit/test_pbir_theme_apply_cli.py tests/unit/test_pbir_visual_format_cli.py tests/unit/test_pbir_page_background_cli.py tests/unit/test_pbir_geometry_cli.py tests/contract/test_powerbi_ownership_routing.py tests/contract/test_upstream_capability_gaps.py tests/contract/test_dbt_ownership_routing.py tests/contract/test_dagster_ownership_routing.py -q
```

Expected: zero failures.

- [ ] **Step 2: Run lint and formatting checks**

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
```

Expected: zero errors and no files requiring formatting.

- [ ] **Step 3: Run capability and static governance checks**

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m seshat.capability_inventory --format json
.\.venv\Scripts\python.exe -m seshat.cli check
```

Expected: capability inventory exit 0; `seshat check` exit 0. Any existing
readiness warning is reported separately and is not relabelled a pass.

- [ ] **Step 4: Run the canonical CI test and packaging commands**

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest -m unit
.\.venv\Scripts\python.exe -m pytest tests/contract/test_dbt_documentation.py tests/contract/test_dbt_package_contract.py tests/contract/test_dbt_project.py tests/contract/test_dbt_public_surface.py tests/integration/test_dbt_artifact_flow.py
.\.venv\Scripts\python.exe -m pytest tests/contract/test_public_knowledge_allowlist.py tests/contract/test_generated_agent_bundles.py tests/contract/test_release_version_sync.py tests/contract/test_release_evidence_models.py
.\.venv\Scripts\python.exe scripts/export_agent_bundles.py --check
npm test
```

Expected: each command exits 0. These are the repository's credential-free CI
unit, governed-dbt, public-distribution, generated-bundle, and npm packaging
gates. If a command exceeds the available execution window, report the timeout
and last completed test count; do not claim it passed.

- [ ] **Step 5: Verify generated-bundle drift and repository state**

```powershell
git diff --check
git status --short --branch
```

Expected: no whitespace errors; only intentional implementation changes or a
clean tree after commits.

- [ ] **Step 6: Apply the verification-before-completion skill**

Read the skill, compare every completion claim with fresh command output, and
report focused tests, full-suite status, lint, governance, bundle drift, and git
state separately.

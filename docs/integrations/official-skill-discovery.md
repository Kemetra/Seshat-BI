# Official skill activation and discovery

Seshat treats three facts separately:

1. **installed** -- the exact cataloged upstream payload is present under
   `.seshat/integrations/skills/<component>`;
2. **activated** -- a supported harness has registered the native plugin or an
   Agent Skills projection;
3. **discoverable** -- the expected official skill identities can be resolved
   from that activation.

A clone proves only the first fact. A normal plan remains network-free and
write-free and reports harness discovery as `not-checked`. Request a read-only
probe explicitly:

```text
seshat integrations setup --profile analytics-full --harness claude-code
seshat integrations setup --profile analytics-full --harness codex --json
```

The probe never installs, enables, updates, copies, or removes a plugin or
skill. Missing activation returns a blocker and the upstream/operator action.

## Supported paths

| Upstream | Catalog install | Claude Code activation | Codex activation | Discovery proof |
|---|---|---|---|---|
| Microsoft Fabric / Power BI | exact `microsoft/skills-for-fabric` ref | native `fabric-skills@fabric-collection` plus `powerbi-authoring@fabric-collection` plugins | provenance-preserving Agent Skills links from the locked payload into `$CODEX_HOME/skills` | enabled Claude plugin inventory plus expected `SKILL.md` files, or Codex targets resolving to the locked files |
| dbt Labs | exact `dbt-labs/dbt-agent-skills` ref | native `dbt@dbt-agent-marketplace` plugin | provenance-preserving Agent Skills links from the locked payload into `$CODEX_HOME/skills` | expected dbt skill identities resolve through the selected harness |
| Dagster | exact `dagster-io/skills` ref | native `dagster-expert@dagster` plugin | provenance-preserving Agent Skills link from the locked payload into `$CODEX_HOME/skills` | `dagster-expert` resolves through the selected harness |

For Codex, an independently copied `SKILL.md` is a conflict rather than a pass.
The discovery check requires the projected file to be the locked upstream file,
so an upgrade cannot silently leave a detached copy behind. Start a new Codex
session after changing skill links.

For Claude Code, the upstream native plugin is the execution surface. The
catalog clone remains the exact install/provenance record; native plugin version
and skill paths are reported separately as discovery evidence.

## Upgrade behavior

- A catalog refresh/apply may land a new exact upstream ref. Re-run both harness
  checks after it lands.
- Claude plugins follow their upstream `plugin update` mechanism; the discovery
  probe verifies the resulting enabled plugin and skill identities.
- Codex projections must still resolve to the newly locked payload. A stale or
  copied target fails closed.
- Broader reproducible re-vendor/update automation belongs to Phase 8; this
  phase establishes the machine-checkable activation boundary it will use.

None of these outcomes changes readiness, grants approval, or proves an
official executor's live result. Matching intent still enters through the
Seshat router and its pre/post governance seams.

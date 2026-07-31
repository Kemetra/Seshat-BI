# Contract: bundled server declaration

**Feature**: 138-agent-driven-bundle | **Story**: US1 | **Enforced by**:
`tests/contract/test_public_command_surface.py`,
`tests/contract/test_generated_agent_bundles.py`

## Interface

One shared source declares the read-only governor; each harness manifest points
at the copy projected into its bundle root.

```text
distribution/bundle-templates/shared/<server-declaration>
            │
            ├──▶ integrations/claude-code/seshat-bi/   + manifest pointer
            └──▶ integrations/codex/seshat-bi/         + manifest pointer
```

## Obligations

1. Enabling the plugin MUST make the governor's tools available with **no manual
   registration step**, on both harnesses.
2. The declaration MUST expose exactly the six existing read-only tools:
   `seshat_get_status`, `seshat_get_next_action`, `seshat_explain_blockers`,
   `seshat_prepare_approval_request`, `seshat_run_static_check`,
   `seshat_export_evidence_pack`. This feature adds no tool.
3. The declaration MUST carry **no repository path argument**. Workspace
   resolution uses the CLI's existing `.` default (research R2). A literal path
   would name the plugin's own installed location and make the governor report on
   the wrong tree.
4. The declaration MUST carry no credential, no secret, and no environment value
   that could hold one.
5. Both bundles MUST receive an identical declaration; only the harness-specific
   manifest key referencing it may differ.
6. `distribution/public-command-surface.yaml` MUST gain a bundled-server artifact
   class, and its symmetry reconciliation MUST exempt that class explicitly, on
   the stated ground that such a component has no wrapper template and no
   knowledge-allowlist entry.

## Prohibitions

- The exemption in obligation 6 MUST be scoped to the bundled-server class alone.
  Loosening the reconciliation for every class would discard the invariant that
  makes the surface trustworthy: that a shipped command has a reviewed wrapper and
  an allowlist entry.
- No declared tool may advance a readiness stage, grant an approval, write a
  readiness artifact, or emit a confidence, health, maturity or completeness
  value.
- The governor SDK MUST remain an optional extra. No story may make it a hard
  dependency of the plugin or of the static check path.
- The manual registration form MUST NOT be deleted from the documentation — it is
  demoted to the non-plugin path, not removed.

## Degradation

When the optional extra is absent, server construction fails and the existing
guarded path reports a named two-lane install hint with a non-zero exit. That
guard covers construction specifically, not the serve loop; that distinction was
established deliberately and MUST NOT be widened, or an unrelated import failure
in a running server would be misreported as a missing extra.

The agent MUST NOT simulate a governor response, and MUST NOT report the loop as
available, when the tools are absent.

## Acceptance evidence

Verified on each harness at the versions the support matrix names: tools present
after install with no registration step; the governor reporting on the user's
workspace rather than the plugin directory; and, with the extra removed, a named
actionable instruction rather than silence.

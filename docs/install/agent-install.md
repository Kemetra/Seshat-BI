# Claude Code agent installation

> **Status: draft.** The repository contains the canonical Seshat BI plugin source and a repository-root marketplace manifest, but no owner publication action has been performed.

When the marketplace is released, the public Claude Code flow is:

```text
/plugin marketplace add ahmed-shaaban-94/Seshat_BI
/plugin install seshat-bi@seshat-bi-marketplace
/plugin marketplace update
```

The marketplace stays in this repository; its root manifest points to `integrations/claude-code/seshat-bi`. This is the canonical, single-source distribution model. No mirror repository is created.

The plugin exposes the Seshat skill and `/seshat-check`, `/seshat-init`, `/seshat-next`, and `/seshat-review` commands. Open Claude Code in a Seshat workspace and ask it to perform only the next allowed action; it must report the evidence-backed Source Ready onboarding action rather than invent a readiness pass or score.

For plugin development only, use the local marketplace command:

```text
claude plugin marketplace add ./integrations/claude-code
```

That local-path command is never the public installation instruction. The plugin's module fallback remains `python -m retail.cli` during the compatibility period; the primary module is `python -m seshat.cli`.
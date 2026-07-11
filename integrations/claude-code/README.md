# Seshat BI Claude Code plugin

> **Status: draft.** This directory is the canonical plugin source inside `Seshat_BI`; it is not a separately published marketplace.

When an owner releases the repository-root marketplace, users add and install it with:

```text
/plugin marketplace add ahmed-shaaban-94/Seshat_BI
/plugin install seshat-bi@seshat-bi-marketplace
/plugin marketplace update
```

The repository-root `.claude-plugin/marketplace.json` uses this directory as its relative plugin source. That keeps the product in one repository and avoids a hand-maintained mirror.

For local development only:

```text
claude plugin marketplace add ./integrations/claude-code
/plugin install seshat-bi@seshat-bi-marketplace
```

The local directory form is not a public install command. The plugin contains the existing Seshat skill and `/seshat-*` commands without adding a CLI verb. Its primary CLI command is `seshat`; `python -m retail.cli` remains a legacy compatibility fallback during the module transition.
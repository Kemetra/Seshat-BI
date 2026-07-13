# Seshat BI Claude Code integration

The generated plugin is rooted at `seshat-bi/`. The repository's only Claude
marketplace manifest is `/.claude-plugin/marketplace.json`; do not add another
manifest below this integration directory.

After the repository candidate is public, users add and install it with:

```text
/plugin marketplace add ahmed-shaaban-94/Seshat_BI
/plugin install seshat-bi@seshat-bi-marketplace
/plugin marketplace update
```

The repository-root `.claude-plugin/marketplace.json` uses this directory as its relative plugin source. That keeps the product in one repository and avoids a hand-maintained mirror.

For local validation only, add the repository root:

```text
claude plugin marketplace add .
/plugin install seshat-bi@seshat-bi-marketplace
```

The local directory form is not a public install command. Generated files under
`seshat-bi/` must be changed through the allowlist/templates and exporter. The
plugin contains the Seshat router, five reviewed Knowledge Bases, and
`/seshat-*` commands without adding a Python CLI verb.
